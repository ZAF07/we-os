# 02 — Log why a bearer token was refused, without telling the caller

Status: completed
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

- [x] Each distinct refusal path emits exactly one log line under the
      `marketing_os` namespace naming its failure class and the request path;
      an expired token's line also carries its `exp` and `iat` offsets from
      the engine clock in seconds. (`marketing_os.auth`, at INFO. The classes
      are a closed `RefusalClass` enum: the seven named here plus `malformed`
      as the catch-all for anything PyJWT raises that the other seven do not
      name — without it an unrecognised failure would log nothing, which is
      the opacity this issue exists to remove.)
- [x] The HTTP response for every refusal is byte-for-byte what it was:
      status 401 and the same "Sign in to continue." detail, asserted by the
      existing tests.
- [x] No log line contains the raw token or any of its claims beyond the two
      timestamps; a test asserts the token string is absent from the captured
      log. (`test_no_refusal_line_contains_the_raw_token` walks every refusal
      class and asserts the token, the `sub` and the `org_id` are all absent.)
- [x] Unit tests at the verifier seam use `caplog` to assert the line for at
      least the expired, signature and missing-organization cases. (Those
      three, plus not-yet-valid, issuer, audience, and a test that a token
      which verifies logs nothing. The missing-header case is asserted at the
      API seam in `test_tenancy.py`, where that refusal is raised.)
- [x] `make check` and `make test-postgres` pass. (623 passed / 726 passed.)

## Blocked by

None - can start immediately.

## Completion

- Completed: 2026-09-09
- Commit: 1534f4e, with review fixes in 0624b3f
