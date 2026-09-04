COMPOSE = docker compose --env-file web/.env.local -f docker-compose.e2e.yml

# Bring up Postgres, the engine and the web app, seed the test tenant, and run
# the browser suite against them. One command from a clean checkout — the only
# prerequisite is web/.env.local, which holds the shared test instance's Clerk
# credentials (see web/.env.local.example).
#
# The stack is torn down whether the suite passes or fails, so a red run never
# leaves containers holding ports.
test-e2e:
	$(COMPOSE) up --build --wait engine web
	cd web && E2E_STACK=compose pnpm test; \
		status=$$?; \
		cd .. && $(COMPOSE) down -v; \
		exit $$status

# The same stack, left running — for driving the app by hand or re-running the
# suite without paying the startup cost each time. Run the suite against it with
# `cd web && E2E_STACK=compose pnpm test`.
e2e-up:
	$(COMPOSE) up --build --wait engine web

e2e-down:
	$(COMPOSE) down -v

e2e-logs:
	$(COMPOSE) logs -f

.PHONY: test-e2e e2e-up e2e-down e2e-logs
