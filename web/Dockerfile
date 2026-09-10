# The Next.js app, for the compose stacks.
#
# Two stages in one file, so the two ways the app is served cannot drift:
#
#   - `dependencies` is what the development stacks run (`make dev`, and the
#     e2e fast loop's `make e2e-up`): `next dev` over a bind mount of the
#     working tree, so a frontend edit is live with no rebuild. This stage
#     carries **dependencies only, never source** — the stack mounts the
#     working tree over /app, so any source copied in here would be hidden the
#     moment the container started. What it is genuinely for is the installed
#     `node_modules`, which the stack keeps as the container's own volume
#     because the host's are built for a different platform.
#
#   - `production` is what the e2e gate runs (`make test-e2e`): the source
#     copied in and built with `next build`, served by `next start`. Every
#     route is compiled before the first request and there is no dev cache to
#     write, so no spec ever pays a compile inside an assertion. It costs a
#     rebuild per edit, which the gate always does.
#
# Compose picks the stage with `build.target`. The last stage is the default,
# so a service that wants the dev server must say `target: dependencies`.
FROM node:22-slim AS dependencies

RUN corepack enable

WORKDIR /app

# pnpm refuses to purge a modules directory without a TTY; the container has
# none, and there is nothing to purge anyway.
ENV CI=true

# The only thing that should ever invalidate this stage is a dependency change.
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


FROM dependencies AS production

# `NEXT_PUBLIC_*` values are inlined into the client bundle at build time, so
# they arrive as build arguments — the compose stack reads them from the same
# web/.env.local the runtime environment already comes from. The secret key is
# runtime-only and never enters an image; .dockerignore keeps every .env file
# out of the build context for the same reason.
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
ARG NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \
    NEXT_PUBLIC_CLERK_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_URL \
    NEXT_PUBLIC_CLERK_SIGN_UP_URL=$NEXT_PUBLIC_CLERK_SIGN_UP_URL \
    NEXT_TELEMETRY_DISABLED=1

# The working tree, minus what .dockerignore keeps out: the host's
# dependencies, old build output, saved browser sessions, and every .env file.
COPY . .
RUN pnpm build

CMD ["pnpm", "start", "--port", "3000", "--hostname", "0.0.0.0"]
