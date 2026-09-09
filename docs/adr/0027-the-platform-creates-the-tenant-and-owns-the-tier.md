# The platform creates the tenant, and owns the tier

A business picks its **tier** before it has an account, and we-OS — not the
identity provider — decides when a tenant comes into being.

Until now Clerk was configured to create an Organization during its own hosted
sign-up. That made the IdP the author of a business: a person who reached the
sign-up form by any route — the generic "Get started", the "Sign up" link
inside the sign-in widget, or the address bar — ended up with an Organization,
a tenant on first engine call, and full access to the product, having chosen
nothing. There was no tier on the tenant row and no moment at which one could
be asked for, because by the time control returned to our code the account
already existed.

Two decisions follow, and they are one decision seen from two sides.

**Org creation moves into the app.** Clerk creates the *user*; we-OS creates
the *business*. A new sign-up lands authenticated with no organization claim —
a **Tenantless Session** — and may reach only the Welcome page, which names the
business, creates the Organization, activates it on the session, and records
the tier. Ordering matters and is fixed: the Organization must exist before the
session can carry `org_id`, and the session must carry `org_id` before the
engine can mint the tenant the tier attaches to.

**The tier is ours, mirrored from nobody.** It is a column on `tenants`, set
through `PUT /tenant/tier`, and it is what business logic reads. Clerk's
organization metadata may hold a copy for a cheap gate, but a copy is what it
is: the platform's row is the record. Keeping the tier only in the IdP would
put a fact the product will bill on inside a vendor we have already decided to
be able to swap (ADR-0013), and would leave no place to express a rule about a
business that the IdP has no concept of.

The tier is **set once**. A second call naming a different tier is refused with
409, because changing a tier is a billing event and billing does not exist yet.
When Stripe lands, the change arrives on a webhook, not on a call the signed-in
person can make about their own account.

## Considered options

- **Gate after authentication, in the app, with the platform creating the org
  (chosen)** — the only option that makes the rule true rather than suggested.
  Costs: a third route group, org-creation code, and a fixture change in the
  browser suite.
- **Route the buttons at a tier page and leave sign-up alone** — rejected: a
  suggestion, not a gate. The exact path complained about (reach `/sign-up`
  directly, get an account with no tier) stays open, and a green suite would
  say otherwise.
- **Keep Clerk creating the org; gate the app on a tier recorded afterwards** —
  rejected: a half-formed business sits in the IdP before anyone chose
  anything, and the product's notion of "a business exists" would be something
  the IdP decided on its own schedule.
- **Tier travels in the JWT claim** — rejected: recorded only when a token
  happens to arrive, absent-tolerant everywhere it is read, and stale until the
  next refresh. A field billing will depend on should be written deliberately.
- **Clerk webhook creates the tenant** — rejected for now: a public endpoint,
  signature verification and retry handling, to arrive at a state the app
  already knows the moment it creates the org.

## Consequences

- **The tenant row is still minted implicitly**, by the first authenticated
  engine call — which is now the tier call. There is no "create tenant"
  endpoint, and `TenantDirectory.resolve` remains the only thing that brings a
  tenant into being.
- **A window exists** between activating the organization and recording the
  tier, in which a tenant has no tier. It is closed by a check on Home, which
  sends a tierless tenant back to finish: to Get Started to choose, from where
  Launch leads to Welcome, which records the tier for a session that already
  has a business. Home cannot send it to bare Welcome, because Welcome sends a
  session with a business and no tier to Home. This is why the tier call must
  be safe to repeat.
- **Tier names live in two languages** — TypeScript for the web app (with
  prices and credits) and a Python literal for validation. Only the names are
  duplicated; each list points at the other. Serving the list from the engine
  was rejected because the pages that show tiers are public and make no engine
  call, a property ADR-0012's public half depends on.
- **Existing tenants are backfilled** to `strategist` by a guarded update.
  Nothing yet distinguishes the tiers, so a default costs nothing and is
  corrected when billing arrives. The guard is on the column's absence, not
  on empty values: the backfill runs once, when the column is first added, so
  a later `init-db` never quietly defaults a business that is mid-way through
  choosing — Home sends that business back to finish instead.
- **The browser suite's users have organizations**, so they never walk this
  path; a dedicated tenantless user covers it and deletes the organization it
  creates, so the fixture stays tenantless for the next run.
- **The redirect is a convenience, not the boundary.** The engine already
  refuses a token with no organization claim (`NO_ORGANIZATION`, 401), and that
  remains what actually protects tenant data (ADR-0013).
