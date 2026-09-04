COMPOSE = docker compose --env-file web/.env.local -f docker-compose.e2e.yml

# Bring up Postgres, the engine and the web app, seed the test tenant, and run
# the browser suite against them. One command from a clean checkout — the only
# prerequisite is web/.env.local, which holds the shared test instance's Clerk
# credentials (see web/.env.local.example).
#
# The stack is torn down whether the suite passes or fails, so a red run never
# leaves containers holding ports — nor an image nobody will use again.
test-e2e:
	$(COMPOSE) up --build --wait engine web
	cd web && E2E_STACK=compose pnpm test; \
		status=$$?; \
		cd .. && $(MAKE) e2e-down; \
		exit $$status

# The same stack, left running — for driving the app by hand or re-running the
# suite without paying the startup cost each time. Run the suite against it with
# `cd web && E2E_STACK=compose pnpm test`.
e2e-up:
	$(COMPOSE) up --build --wait engine web

# Remove everything this stack created: containers, networks, volumes, and the
# images any rebuild orphaned.
#
# Scoped deliberately. A blanket `docker system prune` would take other
# projects' images and build cache with it, and this machine runs several — so
# the dangling images are filtered to the ones this stack's builds produced,
# by the label Compose stamps on them. Everything else is left alone.
e2e-down:
	$(COMPOSE) down -v --remove-orphans
	@orphans=$$(docker images -q --filter dangling=true \
		--filter label=com.docker.compose.project=we-os-e2e); \
	if [ -n "$$orphans" ]; then \
		echo "$$orphans" | xargs docker rmi >/dev/null 2>&1 || true; \
		echo "Removed $$(echo "$$orphans" | wc -l | tr -d ' ') orphaned e2e image(s)."; \
	fi

e2e-logs:
	$(COMPOSE) logs -f

.PHONY: test-e2e e2e-up e2e-down e2e-logs
