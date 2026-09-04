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
#
# Sweeps orphans afterwards for the same reason `e2e-down` does: this target
# rebuilds too, so iterating on the engine here would otherwise strand a 577 MB
# image per change. The sweep runs after the build, so it catches the image this
# build just replaced.
e2e-up:
	$(COMPOSE) up --build --wait engine web
	@$(MAKE) --no-print-directory e2e-prune

e2e-down:
	$(COMPOSE) down -v --remove-orphans
	@$(MAKE) --no-print-directory e2e-prune

# Remove the images this stack's rebuilds orphaned.
#
# Scoped deliberately. A blanket `docker system prune` would take other
# projects' images and build cache with it, and this machine runs several — so
# the dangling images are filtered to the ones this stack's builds produced, by
# the label Compose stamps on them. Everything else is left alone.
#
# An image still referenced by a running container cannot be removed; `docker
# rmi` says so and exits non-zero, which is correct here rather than a failure —
# `e2e-up` prunes while its own containers are running — so that output is
# dropped and only what was actually removed is counted.
e2e-prune:
	@orphans=$$(docker images -q --filter dangling=true \
		--filter label=com.docker.compose.project=we-os-e2e); \
	if [ -n "$$orphans" ]; then \
		removed=$$(echo "$$orphans" | xargs docker rmi 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$removed" != "0" ]; then \
			echo "Removed $$removed orphaned e2e image layer(s)."; \
		fi; \
	fi

# Reclaim build cache this stack's *superseded recipes* left behind.
#
# Editing a Dockerfile strands the cache mount of the recipe it replaced — the
# old `pnpm install` layer sat at 890 MB long after the recipe that made it was
# gone. Those entries are never reused, but BuildKit keeps them until told
# otherwise, and unlike images they carry no Compose label to filter on.
#
# Age is the filter instead: anything untouched for a day cannot be serving the
# current recipe, since any build in that window refreshes what it uses.
# Separate from `e2e-prune` because it is shared with every other project on the
# machine — it is offered, not run automatically.
e2e-prune-cache:
	docker buildx prune --force --filter unused-for=24h

e2e-logs:
	$(COMPOSE) logs -f

.PHONY: test-e2e e2e-up e2e-down e2e-prune e2e-prune-cache e2e-logs
