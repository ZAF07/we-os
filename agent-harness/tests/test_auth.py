"""Tests for JWT verification and tenant derivation.

No test contacts a live IdP: a throwaway RS256 keypair is generated per session
and served through a fake JWKS client, so the verifier is exercised over real
signatures without a network.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from marketing_os.adapters.auth import JwksTokenVerifier
from marketing_os.errors import UnauthenticatedError

ISSUER = "https://example.clerk.accounts.dev"
AUDIENCE = "we-os"


@pytest.fixture(scope="module")
def keypair() -> tuple[Any, Any]:
    """Generate a throwaway RS256 keypair for signing test tokens."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


class FakeJwksClient:
    """Stands in for ``PyJWKClient``, returning a fixed public key."""

    def __init__(self, public_key: Any) -> None:
        """Initialise the client.

        Args:
            public_key: The public key every lookup resolves to.
        """
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> Any:
        """Return the signing key for a token, ignoring its ``kid``.

        Args:
            token: The raw bearer token (unused; one key serves every token).

        Returns:
            An object exposing the public key as ``.key``.
        """

        class _Key:
            key = self._public_key

        return _Key()


@pytest.fixture
def verifier(keypair: tuple[Any, Any]) -> JwksTokenVerifier:
    """Build a verifier wired to the throwaway keypair."""
    _, public_key = keypair
    return JwksTokenVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_client=FakeJwksClient(public_key),
    )


def make_token(
    private_key: Any,
    *,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    expires_in: int = 3600,
    **claims: Any,
) -> str:
    """Sign a token with the given claims, defaulting to a valid Clerk-shaped one."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": "usr_9f2c",
        "org_id": "org_coast",
        "email": "sam@coastcoffee.example",
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_verifies_a_valid_token_and_derives_the_organization_from_org_id(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    private_key, _ = keypair
    identity = verifier.verify(make_token(private_key))
    assert identity.organization_id == "org_coast"
    assert identity.user_id == "usr_9f2c"
    assert identity.email == "sam@coastcoffee.example"


def test_rejects_an_expired_token(verifier: JwksTokenVerifier, keypair: tuple[Any, Any]) -> None:
    private_key, _ = keypair
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(private_key, expires_in=-60))


def test_rejects_a_token_signed_by_a_different_key(verifier: JwksTokenVerifier) -> None:
    impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(impostor))


def test_rejects_a_token_from_another_issuer(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    private_key, _ = keypair
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(private_key, issuer="https://evil.example"))


def test_rejects_a_token_for_another_audience(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    private_key, _ = keypair
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(private_key, audience="someone-else"))


def test_derives_the_organization_from_a_v2_session_token(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """Clerk's current token nests the organization under a compact ``o`` claim."""
    private_key, _ = keypair
    token = make_token(
        private_key,
        org_id=None,
        o={"id": "org_coast", "slg": "coast-coffee", "rol": "admin"},
    )
    identity = verifier.verify(token)
    assert identity.organization_id == "org_coast"
    assert identity.business_name == "coast-coffee"


def test_the_nested_organization_claim_wins_over_the_legacy_one(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    private_key, _ = keypair
    token = make_token(private_key, org_id="org_stale", o={"id": "org_current"})
    assert verifier.verify(token).organization_id == "org_current"


def test_rejects_a_v2_token_whose_organization_claim_is_empty(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """No active organization means no tenant to act for, so the token is refused."""
    private_key, _ = keypair
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(private_key, org_id=None, o={}))


def test_rejects_a_token_carrying_no_organization(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """A token with no ``org_id`` has no tenant to derive, so it is refused."""
    private_key, _ = keypair
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(private_key, org_id=None))


def test_rejects_a_malformed_token(verifier: JwksTokenVerifier) -> None:
    with pytest.raises(UnauthenticatedError):
        verifier.verify("not-a-jwt")


def test_rejects_an_unsigned_token_claiming_none_algorithm(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """An ``alg: none`` token must never be accepted, even with valid claims."""
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "usr_9f2c",
            "org_id": "org_coast",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + 3600,
        },
        key="",
        algorithm="none",
    )
    with pytest.raises(UnauthenticatedError):
        verifier.verify(token)
