# 02 — Log why a bearer token was refused, without telling the caller

Status: ready-for-agent
Type: task

## Parent

[01 — The e2e suite fails a shifting handful of campaign-creating specs](01-campaign-creating-specs-fail-under-parallel-workers.md) · [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)

## What to build

Today every way a bearer token can fail at the engine — no header, expired,
not yet valid, bad signature, wrong issuer or audience, no organization
claim — collapses into the same 401 "Sign in to continue." and nothing is
written to the engine log. That opacity is deliberate for the caller (a probe
must learn nothing from a refusal, ADR-0013) but it was never meant for the
operator: diagnosing issue 01 took twelve suite runs and a hand-patched
container because the log could not say *why* the engine said no.

Keep the response exactly as it is and add one server-side log line per
refusal, under the `marketing_os` logger namespace like every other engine
event, naming the failure class and the facts an operator needs to place it:
the request path, the failure class (missing header, expired, not yet valid,
signature, issuer, audience, no organization), and for a decodable token its
`iat` and `exp` relative to the engine clock so a skew or expiry window is
visible at a glance. Never log the token itself. At INFO, since a refusal is
an event worth seeing in the default configuration, not a debug detail.

## Acceptance criteria

- [ ] Each distinct refusal path emits exactly one log line under the
      `marketing_os` namespace naming its failure class and the request path;
      an expired token's line also carries its `exp` and `iat` offsets from
      the engine clock in seconds.
- [ ] The HTTP response for every refusal is byte-for-byte what it was:
      status 401 and the same "Sign in to continue." detail, asserted by the
      existing tests.
- [ ] No log line contains the raw token or any of its claims beyond the two
      timestamps; a test asserts the token string is absent from the captured
      log.
- [ ] Unit tests at the verifier seam use `caplog` to assert the line for at
      least the expired, signature and missing-organization cases.
- [ ] `make check` and `make test-postgres` pass.

## Blocked by

None - can start immediately.
