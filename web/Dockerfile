# The Next.js app, for the end-to-end test stack.
#
# Test-only: it runs `next dev` rather than a production build, because the
# suite wants the same code paths a developer sees, and because a production
# build would bake in build-time environment the tests then could not vary.
#
# The image carries **dependencies only, never source**. The compose stack bind
# mounts the working tree over /app, so any source copied in here would be
# immediately hidden — it would cost a rebuild on every edit while changing
# nothing that runs. What the image is genuinely for is the installed
# `node_modules`, which the stack keeps as its own volume because the host's are
# built for a different platform.
FROM node:22-slim

RUN corepack enable

WORKDIR /app

# pnpm refuses to purge a modules directory without a TTY; the container has
# none, and there is nothing to purge anyway.
ENV CI=true

# The only thing that should ever invalidate this image is a dependency change.
#
# The store and the download cache are build-time artefacts: `node_modules` is
# what the container runs, and pnpm hard-links into it from the store, so
# keeping both doubles the image for nothing. Cleared in the same layer that
# creates them — a later `rm` would only hide them behind an earlier layer that
# still carries the weight.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile \
    && rm -rf /root/.cache/node /root/.local/share/pnpm/store

EXPOSE 3000

CMD ["pnpm", "dev", "--port", "3000", "--hostname", "0.0.0.0"]
