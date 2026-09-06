# Running we-OS locally

One command starts the whole platform — database, engine and web app — so you
can sign up, fill in a Brand DNA and run real campaigns on your own machine.

```bash
cp .env.example .env     # then fill it in, see below
make dev
```

Open **http://localhost:3000**.

`make dev` builds the images the first time (a few minutes) and is fast after
that. It waits until every service is healthy before returning, so when the
command finishes the app is genuinely ready.

## Filling in `.env`

Three things matter. `.env` is gitignored — never commit it.

### Clerk — required

The app is unusable without it: every route sits behind Clerk, and the engine
works out which business you are from the organization on your token
([ADR-0013](adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)). There is no
anonymous mode.

From the Clerk dashboard → **API keys**:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `MARKETING_OS_AUTH_ISSUER` — your instance's Frontend API URL,
  `https://<slug>.clerk.accounts.dev`

One-time dashboard setup: enable **Organizations** and turn on *"create an
organization on sign-up"*. One Clerk Organization is one business is one we-OS
tenant. Without an organization on your token the engine refuses the request.

### DeepSeek — required to run a campaign

`DEEPSEEK_API_KEY`. DeepSeek is the default provider
([ADR-0004](adr/0004-provider-agnostic-llm-with-deepseek-default.md)).

The stack starts happily without it and every screen works — you can sign up,
onboard, write your Brand DNA and create a campaign. Only the pipeline needs a
model, so a missing key surfaces when you press run, not at boot.

### Web search — optional

`MARKETING_OS_WEB=1` lets the research stage search the live web, and
`MARKETING_OS_TAVILY_API_KEY` makes it use Tavily rather than falling back to
scraping ([ADR-0011](adr/0011-tavily-primary-web-backend.md)). Off by default.

## First run

1. `make dev`, then open http://localhost:3000
2. **Sign up.** Create an organization when Clerk asks — that is your business.
   Your tenant is registered on your first request; nothing is seeded for you.
3. **Onboarding** walks you through the questionnaire. Your answers become your
   Brand DNA.
4. **Create a campaign.** The DNA Gate checks your Brand DNA is complete first —
   if it is not, it tells you exactly which answers are missing and stops.
5. **Run it.** Stages execute in order, pausing at each Approval Gate for you.

## Everyday commands

| Command | What it does |
| --- | --- |
| `make dev` | Start everything. Rebuilds if anything changed |
| `make dev-down` | Stop everything. **Your data is kept** |
| `make dev-logs` | Follow logs from all services |
| `make dev-reset` | Stop everything **and delete the database** — every campaign, Brand DNA and run you created locally |

## Where things are

| | URL |
| --- | --- |
| Web app | http://localhost:3000 |
| Engine | http://localhost:8001 (`/health`, `/docs`) |
| Postgres | `localhost:5436`, user/password/db all `marketing_os` |

Run traces land in `logs/<tenant>/<slug>/` in your working tree — that is what
to read when a run does something surprising.

## This is not the test stack

There are two compose files and they are for different things.

| | `make dev` | `make test-e2e` |
| --- | --- | --- |
| Model provider | **Real** (DeepSeek) | `scripted` — fabricates deliverables, spends nothing |
| Database | **Persistent** named volume | tmpfs, gone on stop |
| Tenants | **None** — you sign up | Two fixture tenants, re-seeded every start |
| Ports | 3000 / 8001 / 5436 | 3100 / 8000 |

The ports differ so both can run at once. Never point the test stack at
anything you want to keep — it purges its tenants' campaigns on every start.

## Troubleshooting

**A port is already in use.** Something else holds 3000, 8001 or 5436. Find it
with `lsof -nP -iTCP:3000 -sTCP:LISTEN`, or change the left-hand number in
`docker-compose.yml`.

**"set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY in .env".** Compose refuses to start
without the required values rather than booting a broken app. Copy
`.env.example` to `.env` and fill it in.

**A run fails immediately at the first stage.** Usually a missing or invalid
`DEEPSEEK_API_KEY`. Check with `make dev-logs`.

**Signing in works but every page errors.** Your Clerk token probably carries no
organization. Confirm Organizations are enabled in the Clerk dashboard and that
your user belongs to one.

**The engine will not start after pulling changes.** The schema is brought up to
date on every `make dev`, so this is rare — but if the engine complains about a
missing column, `make dev-reset` gives you a clean database. It also deletes
your local campaigns.

## Running without Docker

For working *on* the code rather than using it, run the two apps natively —
they pick up their own env files, `agent-harness/.env` and `web/.env.local`,
rather than the root `.env` this stack uses.

```bash
docker compose -f agent-harness/docker-compose.yml up -d   # Postgres alone
cd agent-harness && uv run uvicorn marketing_os.entrypoints.api.app:app --reload
cd web && pnpm dev
```

See [`USAGE.md`](../USAGE.md) for the Brand DNA and campaign goal the pipeline
needs, whichever way you run it.
