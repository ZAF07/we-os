# The Next.js app, for the end-to-end test stack.
#
# Test-only: it runs `next dev` rather than a production build, because the
# suite wants the same code paths a developer sees, and because a production
# build would bake in build-time environment the tests then could not vary.
FROM node:22-slim

RUN corepack enable

WORKDIR /app

# pnpm refuses to purge a modules directory without a TTY; the container has
# none, and there is nothing to purge anyway.
ENV CI=true

# Dependencies resolve from the manifests alone, so this layer survives edits to
# the source underneath it.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 3000

CMD ["pnpm", "dev", "--port", "3000", "--hostname", "0.0.0.0"]
