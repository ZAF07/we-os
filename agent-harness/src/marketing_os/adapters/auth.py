"""Identity adapters — verifying bearer tokens against a managed IdP.

Implements the :class:`~marketing_os.ports.TokenVerifier` port (ADR-0013). The
engine verifies tokens **independently** of the frontend, so a request reaching
it directly is held to the same standard as one routed through the BFF.

Verification is plain OIDC: fetch the issuer's published signing keys over JWKS
and check the signature, the issuer, the audience and the expiry. Nothing here
is vendor-specific except which claim names the tenant — Clerk puts the
organization in ``org_id`` — so switching IdP is a configuration change, and no
IdP SDK or secret is needed on the engine side, since JWKS is public.
"""

from __future__ import annotations

from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from marketing_os.errors import UnauthenticatedError
from marketing_os.schemas import VerifiedIdentity

_ALGORITHMS = ["RS256"]

# Clerk's session token v2 nests organization claims under a compact ``o``
# object (``{id, slg, rol, per, fpm}``); v1 spelled them out as ``org_id`` /
# ``org_slug``. Both are read so the verifier works against either, and
# ``tenant_id`` covers a non-Clerk IdP configured with an explicit claim.
_ORGANIZATION_CLAIM = "o"
_TENANT_CLAIMS = ("org_id", "tenant_id")
_TENANT_SUBCLAIMS = ("id",)
_BUSINESS_NAME_CLAIMS = ("org_name", "org_slug", "business_name")
_BUSINESS_NAME_SUBCLAIMS = ("nam", "slg")


class SigningKeyClient(Protocol):
    """The slice of ``PyJWKClient`` this adapter needs, so tests can substitute it."""

    def get_signing_key_from_jwt(self, token: str) -> Any:
        """Return the signing key matching a token's ``kid`` header.

        Args:
            token: The raw bearer token.

        Returns:
            An object exposing the public key as ``.key``.
        """
        ...


def _first_claim(claims: dict[str, Any], names: tuple[str, ...]) -> str | None:
    """Return the first non-empty string among the named claims.

    Args:
        claims: The verified token payload.
        names: The claim names to try, in priority order.

    Returns:
        The first present, non-empty claim value, or ``None`` if none match.
    """
    for name in names:
        value = claims.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _organization_claim(
    claims: dict[str, Any], subclaims: tuple[str, ...], flat_names: tuple[str, ...]
) -> str | None:
    """Read a value from the nested organization claim, then the flat fallbacks.

    Session token v2 nests organization data under ``o``; v1 used flat
    ``org_*`` names. Reading the nested form first means a current Clerk
    instance works untouched, while an older token or another IdP still resolves.

    Args:
        claims: The verified token payload.
        subclaims: Keys to try inside the ``o`` object, in priority order.
        flat_names: Top-level claim names to fall back to, in priority order.

    Returns:
        The first non-empty value found, or ``None``.
    """
    organization = claims.get(_ORGANIZATION_CLAIM)
    if isinstance(organization, dict):
        nested = _first_claim(organization, subclaims)
        if nested is not None:
            return nested
    return _first_claim(claims, flat_names)


class JwksTokenVerifier:
    """Verifies RS256 bearer tokens against an OIDC issuer's published JWKS.

    The tenant is read from the token's organization claim, never from the
    subject: one tenant is one business, and a business may have more than one
    signed-in person. A token carrying no organization has no tenant to act for
    and is refused rather than silently falling back to the user id, which would
    weld a business to a single login and make tenancy unmigratable later.
    """

    def __init__(
        self,
        *,
        issuer: str,
        audience: str | None = None,
        jwks_url: str | None = None,
        jwks_client: SigningKeyClient | None = None,
    ) -> None:
        """Initialise the verifier.

        Args:
            issuer: The expected ``iss`` claim, and the base for JWKS discovery.
            audience: The expected ``aud`` claim, or ``None`` to skip the check
                when the IdP does not set one.
            jwks_url: An explicit JWKS endpoint; defaults to the issuer's
                standard ``/.well-known/jwks.json``.
            jwks_client: A pre-built key client, used by tests to avoid a network
                fetch; defaults to a caching :class:`PyJWKClient`.
        """
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_url = jwks_url or f"{self.issuer}/.well-known/jwks.json"
        self._jwks_client: SigningKeyClient = jwks_client or PyJWKClient(
            self.jwks_url, cache_keys=True
        )

    def verify(self, token: str) -> VerifiedIdentity:
        """Verify a bearer token and resolve the identity it carries.

        Args:
            token: The raw bearer token, without its ``Bearer `` prefix.

        Returns:
            The verified identity, with the tenant derived from the
            organization claim.

        Raises:
            UnauthenticatedError: If the token fails any verification step or
                carries no tenant claim. The reason is not disclosed to the
                caller, so a probe learns nothing from the refusal.
        """
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=_ALGORITHMS,
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["exp", "iat", "iss", "sub"],
                    "verify_aud": self.audience is not None,
                },
            )
        except Exception as exc:
            raise UnauthenticatedError("Sign in to continue.") from exc

        tenant_id = _organization_claim(claims, _TENANT_SUBCLAIMS, _TENANT_CLAIMS)
        subject = claims.get("sub")
        if not tenant_id or not isinstance(subject, str):
            raise UnauthenticatedError("Sign in to continue.")

        return VerifiedIdentity(
            user_id=subject,
            tenant_id=tenant_id,
            email=_first_claim(claims, ("email",)),
            business_name=_organization_claim(
                claims, _BUSINESS_NAME_SUBCLAIMS, _BUSINESS_NAME_CLAIMS
            ),
        )
