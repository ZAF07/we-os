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

import time
from enum import StrEnum
from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from marketing_os.adapters.observability import get_logger
from marketing_os.errors import UnauthenticatedError
from marketing_os.schemas import VerifiedClaims

_LOGGER = get_logger("marketing_os.auth")

_ALGORITHMS = ["RS256"]

# How far the IdP's clock and ours may disagree before a token is refused.
#
# A session token reaches the engine second-hand: the BFF accepts it under its
# own skew allowance (Clerk's default is 5 seconds past ``exp``) and forwards it
# as-is, so this tolerance must cover the BFF's plus the hop in between. Clerk
# itself dates ``nbf`` 10 seconds before ``iat``; that is the tolerance the IdP
# asks for, so it is the one honoured here — on ``exp``, ``nbf`` and ``iat``
# alike, since the same skew moves all three.
_CLOCK_SKEW_LEEWAY_SECONDS = 10

# Clerk's session token v2 nests organization claims under a compact ``o``
# object (``{id, slg, rol, per, fpm}``); v1 spelled them out as ``org_id`` /
# ``org_slug``. Both are read so the verifier works against either, and
# ``tenant_id`` covers a non-Clerk IdP configured with an explicit claim.
_ORGANIZATION_CLAIM = "o"
_ORGANIZATION_ID_CLAIMS = ("org_id", "tenant_id")
_ORGANIZATION_ID_SUBCLAIMS = ("id",)
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


class RefusalClass(StrEnum):
    """Why the engine refused a bearer token, for the operator's log only.

    A closed set rather than free text, so a refusal cannot be logged under a
    name nothing else uses. None of these ever reaches the caller: every one of
    them answers the same 401 (ADR-0013), and the distinction exists so an
    operator can tell a clock-skew refusal from a forged one.
    """

    MISSING_HEADER = "missing header"
    EXPIRED = "expired"
    NOT_YET_VALID = "not yet valid"
    SIGNATURE = "signature"
    ISSUER = "issuer"
    AUDIENCE = "audience"
    NO_ORGANIZATION = "no organization"
    MALFORMED = "malformed"


def _failure_class(exc: Exception) -> RefusalClass:
    """Name the class of a PyJWT decode failure for the refusal log.

    Args:
        exc: The exception ``jwt.decode`` (or the key lookup) raised.

    Returns:
        The matching refusal class, defaulting to
        :attr:`RefusalClass.MALFORMED` for anything unrecognised.
    """
    by_type: list[tuple[type[Exception], RefusalClass]] = [
        (jwt.ExpiredSignatureError, RefusalClass.EXPIRED),
        (jwt.ImmatureSignatureError, RefusalClass.NOT_YET_VALID),
        (jwt.InvalidIssuerError, RefusalClass.ISSUER),
        (jwt.InvalidAudienceError, RefusalClass.AUDIENCE),
        (jwt.InvalidSignatureError, RefusalClass.SIGNATURE),
        (jwt.InvalidKeyError, RefusalClass.SIGNATURE),
        (jwt.PyJWKClientError, RefusalClass.SIGNATURE),
    ]
    for exception_type, failure_class in by_type:
        if isinstance(exc, exception_type):
            return failure_class
    return RefusalClass.MALFORMED


def _clock_offsets(token: str) -> str:
    """Describe a token's ``exp`` and ``iat`` relative to this engine's clock.

    Read without verifying, since the point is to explain a token that failed
    verification. Only the two timestamps are read; no other claim is touched,
    so nothing identifying can reach the log.

    Args:
        token: The raw bearer token.

    Returns:
        A fragment like ``" exp=-60s iat=-3660s"``, or an empty string if the
        token does not decode or carries neither timestamp.
    """
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return ""
    now = time.time()
    offsets = [
        f"{name}={int(claims[name] - now):+d}s"
        for name in ("exp", "iat")
        if isinstance(claims.get(name), int | float)
    ]
    return f" {' '.join(offsets)}" if offsets else ""


def log_refusal(
    failure_class: RefusalClass, request_path: str | None, *, token: str | None = None
) -> None:
    """Record why a bearer token was refused, for the operator only.

    The caller's 401 stays uniform (ADR-0013); this is the other half of that
    contract — the engine log names the failure so a refusal is diagnosable
    without patching a running container. The token is never logged, and no
    claim beyond ``exp`` and ``iat`` is read.

    Args:
        failure_class: Why the token was refused.
        request_path: The path the token was presented on, if known.
        token: The refused token, read only for its clock offsets; omit it when
            there is no token to read, as for a missing header.
    """
    _LOGGER.info(
        "token refused: %s path=%s%s",
        failure_class.value,
        request_path or "unknown",
        _clock_offsets(token) if token else "",
    )


class JwksTokenVerifier:
    """Verifies RS256 bearer tokens against an OIDC issuer's published JWKS.

    The business is read from the token's organization claim, never from the
    subject: one tenant is one business, and a business may have more than one
    signed-in person. A token carrying no organization has no business to act
    for and is refused rather than silently falling back to the user id, which
    would weld a business to a single login and make tenancy unmigratable later.
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

    def verify(self, token: str, request_path: str | None = None) -> VerifiedClaims:
        """Verify a bearer token and return the claims it carries.

        Args:
            token: The raw bearer token, without its ``Bearer `` prefix.
            request_path: The path the token was presented on, recorded in the
                refusal log so an operator can place a failure.

        Returns:
            The verified claims, naming the person and the IdP organization
            they act for. Turning that organization into a platform tenant is
            the :class:`~marketing_os.ports.TenantDirectory`'s job, not this
            adapter's.

        Raises:
            UnauthenticatedError: If the token fails any verification step or
                carries no organization claim. The reason is not disclosed to
                the caller, so a probe learns nothing from the refusal — it is
                written to the engine log instead.
        """
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=_ALGORITHMS,
                issuer=self.issuer,
                audience=self.audience,
                leeway=_CLOCK_SKEW_LEEWAY_SECONDS,
                options={
                    "require": ["exp", "iat", "iss", "sub"],
                    "verify_aud": self.audience is not None,
                },
            )
        except Exception as exc:
            log_refusal(_failure_class(exc), request_path, token=token)
            raise UnauthenticatedError("Sign in to continue.") from exc

        organization_id = _organization_claim(
            claims, _ORGANIZATION_ID_SUBCLAIMS, _ORGANIZATION_ID_CLAIMS
        )
        subject = claims.get("sub")
        if not organization_id or not isinstance(subject, str):
            log_refusal(RefusalClass.NO_ORGANIZATION, request_path, token=token)
            raise UnauthenticatedError("Sign in to continue.")

        return VerifiedClaims(
            user_id=subject,
            organization_id=organization_id,
            email=_first_claim(claims, ("email",)),
            business_name=_organization_claim(
                claims, _BUSINESS_NAME_SUBCLAIMS, _BUSINESS_NAME_CLAIMS
            ),
        )
