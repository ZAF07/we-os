"""Tests for JWT verification and tenant derivation.

No test contacts a live IdP: a throwaway RS256 keypair is generated per session
and served through a fake JWKS client, so the verifier is exercised over real
signatures without a network.
"""

from __future__ import annotations

import logging
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


def test_accepts_a_token_the_bff_still_forwards_just_past_expiry(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """A token 5 s past ``exp`` verifies: the BFF forwards up to 5 s past it."""
    private_key, _ = keypair
    identity = verifier.verify(make_token(private_key, expires_in=-5))
    assert identity.organization_id == "org_coast"


def test_rejects_a_token_past_the_clock_skew_tolerance(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """The tolerance is a few seconds, not a second life for the token."""
    private_key, _ = keypair
    with pytest.raises(UnauthenticatedError):
        verifier.verify(make_token(private_key, expires_in=-15))


def test_accepts_a_token_issued_a_few_seconds_ahead_of_this_clock(
    verifier: JwksTokenVerifier, keypair: tuple[Any, Any]
) -> None:
    """An ``iat`` slightly in the future is clock skew, not forgery."""
    private_key, _ = keypair
    identity = verifier.verify(make_token(private_key, iat=int(time.time()) + 3))
    assert identity.organization_id == "org_coast"


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


def _refusal_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return the messages logged under the refusal logger, at INFO or above."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("marketing_os") and record.levelno >= logging.INFO
    ]


def test_logs_the_failure_class_and_path_when_a_token_has_expired(
    verifier: JwksTokenVerifier,
    keypair: tuple[Any, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An expired token's line names the class, the path and the clock offsets."""
    private_key, _ = keypair
    token = make_token(private_key, expires_in=-60)
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        with pytest.raises(UnauthenticatedError):
            verifier.verify(token, request_path="/campaigns")
    lines = _refusal_lines(caplog)
    assert len(lines) == 1
    assert "expired" in lines[0]
    assert "/campaigns" in lines[0]
    assert "exp=-60s" in lines[0]
    assert "iat=+0s" in lines[0]


def test_logs_a_signature_failure_without_the_token(
    verifier: JwksTokenVerifier, caplog: pytest.LogCaptureFixture
) -> None:
    """A token signed by the wrong key is logged as a signature failure."""
    impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(impostor)
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        with pytest.raises(UnauthenticatedError):
            verifier.verify(token, request_path="/campaigns/spring-launch")
    lines = _refusal_lines(caplog)
    assert len(lines) == 1
    assert "signature" in lines[0]
    assert token not in lines[0]


def test_logs_a_missing_organization_claim(
    verifier: JwksTokenVerifier,
    keypair: tuple[Any, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A token that verifies but names no business is its own failure class."""
    private_key, _ = keypair
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        with pytest.raises(UnauthenticatedError):
            verifier.verify(make_token(private_key, org_id=None), request_path="/dna")
    lines = _refusal_lines(caplog)
    assert len(lines) == 1
    assert "no organization" in lines[0]
    assert "/dna" in lines[0]


def test_logs_a_not_yet_valid_token_apart_from_an_expired_one(
    verifier: JwksTokenVerifier,
    keypair: tuple[Any, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``nbf`` far ahead of this clock is its own failure class, not expiry."""
    private_key, _ = keypair
    now = int(time.time())
    token = make_token(private_key, nbf=now + 300)
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        with pytest.raises(UnauthenticatedError):
            verifier.verify(token, request_path="/campaigns")
    lines = _refusal_lines(caplog)
    assert len(lines) == 1
    assert "not yet valid" in lines[0]


def test_logs_the_issuer_and_audience_classes_apart(
    verifier: JwksTokenVerifier,
    keypair: tuple[Any, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Wrong issuer and wrong audience are distinguishable in the log."""
    private_key, _ = keypair
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        with pytest.raises(UnauthenticatedError):
            verifier.verify(make_token(private_key, issuer="https://evil.example"))
        with pytest.raises(UnauthenticatedError):
            verifier.verify(make_token(private_key, audience="someone-else"))
    lines = _refusal_lines(caplog)
    assert len(lines) == 2
    assert "issuer" in lines[0]
    assert "audience" in lines[1]


def test_no_refusal_line_contains_the_raw_token(
    verifier: JwksTokenVerifier,
    keypair: tuple[Any, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every refusal class is logged, and none of them echo the token back."""
    private_key, _ = keypair
    tokens = [
        make_token(private_key, expires_in=-60),
        make_token(private_key, issuer="https://evil.example"),
        make_token(private_key, audience="someone-else"),
        make_token(private_key, org_id=None),
        "not-a-jwt",
    ]
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        for token in tokens:
            with pytest.raises(UnauthenticatedError):
                verifier.verify(token, request_path="/campaigns")
    logged = "\n".join(_refusal_lines(caplog))
    assert len(_refusal_lines(caplog)) == len(tokens)
    for token in tokens:
        assert token not in logged
    assert "sam@coastcoffee.example" not in logged
    assert "org_coast" not in logged


def test_a_verified_token_logs_nothing(
    verifier: JwksTokenVerifier,
    keypair: tuple[Any, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The line records a refusal, so a token that verifies writes none."""
    private_key, _ = keypair
    with caplog.at_level(logging.INFO, logger="marketing_os"):
        verifier.verify(make_token(private_key), request_path="/campaigns")
    assert _refusal_lines(caplog) == []
