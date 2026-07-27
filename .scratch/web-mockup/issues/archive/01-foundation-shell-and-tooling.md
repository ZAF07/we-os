# 01 — Foundation: scaffold, shell, tokens, store, test gate

Status: completed
Type: task

## Parent

[PRD: Marketing OS web frontend — Milestone 1](../PRD.md) · [ADR-0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md)

## What to build

The tracer-bullet foundation the whole frontend hangs off. A single Next.js app at `web/` (App Router, TypeScript strict, pnpm) that boots, renders the persistent nav-rail shell, and can reach every route as a stub page — with the design system, client store, mock-data module, and test/quality gate all wired.

End-to-end behavior: the operator opens the app, sees the left nav rail (Home, Campaigns, Calendar, Brand, Performance) with the "Marketing OS" mark, and can navigate to each route (stub content for now). The active nav item highlights; Workspace highlights Campaigns. Below desktop width the nav collapses to a drawer and content reflows.

Scope of this slice:
- Next.js App Router + TS strict + ESLint/Prettier; pnpm.
- Tailwind + shadcn/ui, re-themed to the mockup's tokens: indigo `#4F46E5`, the slate scale, status colors, radii; Instrument Sans via `next/font/google`; `lucide-react` for icons.
- App shell: `layout` with the nav rail + content area; real routes `/`, `/campaigns`, `/campaigns/[slug]`, `/calendar`, `/brand`, `/performance`, `/onboarding`, `/campaigns/new` (all stubs).
- Zustand store persisted to `sessionStorage`, holding the demo state and seeded fixtures. The **status taxonomy** is defined once here and every status pill will read it. From the prototype:

  ```
  state = { stage: 2, approved: false, calMode: 'calendar',
            calSelIdx: 0, brandIdx: 0, aiKey: null, rightTab: 'evidence' }
  ST = { Draft:['#F1F5F9','#475569'], 'Needs input':['#FEF3C7','#B45309'],
         'In progress':['#E0E7FF','#4338CA'], 'Ready for review':['#EDE9FE','#6D28D9'],
         Approved:['#D1FAE5','#047857'], Scheduled:['#E0F2FE','#0369A1'],
         Published:['#F1F5F9','#334155'], 'Needs attention':['#FEE2E2','#B91C1C'],
         'Not started':['#F8FAFC','#94A3B8'] }   // status -> [bg, fg]
  ```

- `lib/mock-data` module skeleton (fixtures filled per-screen in later slices), sourced verbatim from the prototype's `renderVals()`.
- Playwright configured against the running app with one smoke test; `pnpm` scripts for `typecheck`, `lint`, `test`.

No backend calls. "Marketing OS" is the product name ("Cadence" in the mockup is a placeholder).

## Acceptance criteria

- [x] `web/` app boots with `pnpm dev`; `tsc --noEmit` (strict), ESLint, and Prettier pass.
- [x] Nav rail renders with all five primary items + the Marketing OS mark; clicking each navigates to its route and marks it active; Workspace route highlights Campaigns.
- [x] All eight routes resolve to a stub page (no 404s).
- [x] Below a mobile breakpoint the nav collapses to a drawer and content reflows without horizontal overflow.
- [x] Design tokens (indigo, slate, status colors, Instrument Sans) are applied via the Tailwind theme; no ad-hoc color literals in components.
- [x] Zustand store persists demo state across a page refresh within a session; the status-taxonomy map lives in one place.
- [x] Playwright is configured and one smoke test (app boots + nav reaches all routes) passes; `pnpm test`, `pnpm typecheck`, `pnpm lint` scripts exist.

## Blocked by

None - can start immediately.

## Completion

- Completed: 2026-07-16
- Commit: <to be filled in manually>
