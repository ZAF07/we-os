# Next.js frontend and BFF in the monolith

The product needs an operator UI (the "Cadence" mockup). We add it as a single Next.js (App Router, TypeScript) application at `web/` in this repo — sibling to `agent-harness/` — that carries both the frontend and its backend-for-frontend (BFF route handlers), rather than a separate repo or an `apps/` monorepo reshuffle. The Python `agent-harness/` remains the domain engine (LangGraph + the existing FastAPI in `entrypoints/api/`); the intended long-term seam is BFF route handlers calling that FastAPI over HTTP. Both stacks live in one monolith so the FE/BFF ship and version together with the governance markdown they present.

Milestone 1 is a **faithful static clone** of the six designed screens (Home, Campaigns, Workspace, Calendar, Brand, Performance) plus onboarding and new-campaign wizards designed in the same visual language, driven entirely by hardcoded mock fixtures (Fernway) with a client store — **no backend calls**. Wiring the BFF to the FastAPI engine is a later milestone once flows and APIs are settled.

## Considered options

- **`web/` at repo root (chosen)** — smallest disruption, clean Python-engine / Node-UI split inside one monolith.
- **Separate frontend repo** — rejected: breaks the "ship and version together" monolith intent and splits governance markdown from the UI that renders it.
- **`apps/` monorepo (move `agent-harness/` under `apps/`)** — rejected for now: a larger reshuffle of existing paths than M1 warrants; revisit if more apps appear.
- **Wire to FastAPI in M1** — rejected: flows/APIs are undetermined; a static clone gets a faithful, reviewable design in front of the user fastest.

## Stack choices

- **shadcn/ui + Tailwind**, re-themed to the mockup's tokens (indigo `#4F46E5`, slate scale, Instrument Sans). Chosen over hand-rolled primitives for a11y-correct interactive parts.
- **Zustand** client store, seeded from the mock fixtures and persisted to `sessionStorage`, to preserve the prototype's cross-screen reactivity (e.g. "Approve" in Workspace updates the Home queue and campaign statuses).
- **Real App Router routes** per view (`/`, `/campaigns`, `/campaigns/[slug]` = Workspace, `/calendar`, `/brand`, `/performance`), not the prototype's single-page state switching.
- **Responsive** from the start (the mockup is desktop-only, so mobile/tablet behavior is invented, not specified).
- **Gate**: TypeScript strict + ESLint/Prettier + a thin Playwright smoke suite; no exhaustive unit tests for presentational UI.

## Consequences

- **Stage-vocabulary divergence (open).** The mockup's Workspace names 8 operator stages — `Brief · Research · Strategy · Plan · Produce · Approve · Publish · Measure` — which do not line up with the engine pipeline in `CONTEXT.md` (`Research → Brand Strategy → Campaign Strategy → Creative Brief → Asset Prompts → Performance Plan`). M1 uses the mockup names against mock data; the FE↔engine stage mapping must be resolved before wiring. Until then, no FE UI terms are added to the `CONTEXT.md` glossary (flows/APIs are still undetermined).
- The repo now carries a Node toolchain (pnpm) alongside `uv`; contributors need both.
- "Cadence" in the mockup is a wireframe placeholder; the shipped product name is **Marketing OS**.
