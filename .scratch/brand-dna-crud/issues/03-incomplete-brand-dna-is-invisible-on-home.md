Status: ready-for-agent

# Incomplete Brand DNA is invisible on Home and in the side nav

## Symptom

A signed-in business whose Brand DNA is missing Required fields — never filled in at
all, or filled in partially — gets no indication of it anywhere on Home. Nothing in
the shell or on the screen says the Brand section is unfinished, so the tenant has to
already know to click into Brand and scroll to find out.

Two places are missing it:

- **Side nav** — the Brand item in `NAV_ITEMS` renders as a plain label with no badge
  or count, identical whether the DNA is complete or empty.
- **Action queue** — `toQueue()` builds the queue purely from campaigns
  (`blocked_reason`), so an incomplete Brand DNA never becomes an item. When a new
  business has no campaigns yet, Home reads "Nothing is waiting on you" and the queue
  shows its empty state, which is wrong: a complete Brand DNA gates all campaign work
  (`.claude/rules/brand-dna.md`), so it is the one thing actually waiting on them.

Impact: no crash. A new tenant is left at a dead end on Home — the gate that blocks
every downstream stage is invisible until they happen to visit the Brand page.

## Repro

Deterministic.

1. Sign in as a business whose Brand DNA is missing or partially answered
   (`GET /brand-dna/completeness` returns `complete: false` with a non-empty
   `missing[]`).
2. Open `/home`.
3. Observe: Brand in the left nav carries no badge; the Action queue shows no Brand
   item (and with no campaigns, shows its empty state).
4. `/brand` does show the incomplete state — only Home and the nav don't.

## What to build

**Badge.** A count of `missing.length` on the Brand nav item, shown on every route
(the gate applies everywhere, not just Home). Hidden entirely when `complete` is true.

**Action queue item.** One item, sorted after `Decision` but before `Stale` — it
blocks everything, but a campaign already at an approval gate is the more immediate
ask. Needs a third `QueueTag` (`"Setup"`) with its own entry in `TAG_CLASSES`.

Copy, matching Home's existing plain voice:

- Title: `Your Brand DNA is not filled in yet` when `required_answered` is 0,
  otherwise `N answers still needed in your Brand DNA`
- Meta: the first two or three `missing[].label` values, comma-separated, with
  `+N more` when the list is longer
- Button: `Fill it in`, linking to `/brand`

The point of the meta line is that the tenant learns *what* is missing without
leaving Home. Better answers here mean better campaign runs, so the copy should read
as useful rather than nagging — no exclamation marks, no "action required".

## Suspected location

The data already exists and is simply never read by Home or the shell:

- `web/src/lib/engine.ts:253` — `DnaCompleteness` (`complete`, `required_total`,
  `required_answered`, `missing[]`), fetched by `getBrandDnaCompleteness()` at
  `web/src/lib/engine.ts:273`. `MissingField` carries `question_id`, `field`, `label`.
- `web/src/app/(app)/home/actions.ts` — `loadHome()` fetches campaigns and usage;
  add completeness to the same `Promise.all`.
- `web/src/lib/home.ts` — `toQueue()` takes only `CampaignSummary[]`; it needs the
  completeness report as a second argument to emit the Setup item. `QueueTag` is
  `"Decision" | "Stale"` and gains `"Setup"`.
- `web/src/app/(app)/home/page.tsx:27` — `TAG_CLASSES` needs a `Setup` class.
- `web/src/components/shell/app-shell.tsx:34-39` — `NAV_ITEMS` and `NavLinks()`.

**Seam for the badge.** `app-shell.tsx` is a client component (`usePathname`,
`useUser`), so it cannot fetch. `web/src/app/(app)/layout.tsx` is a server component
that today only wraps `AppShell` — fetch completeness there and pass the count into
`AppShell` as a prop, so the badge works on every route without a client-side fetch.
That means two callers of `getBrandDnaCompleteness()` (the layout and `loadHome()`);
that duplicate read is acceptable and preferable to threading it up from Home.

**Failure handling.** A completeness read that throws `EngineError` degrades the same
way `getUsage()` already does in `loadHome()` — it costs the badge and the queue item,
not the screen. In the layout, a failed read means no badge; the layout must not throw.

## Acceptance criteria

- [ ] With an incomplete Brand DNA, the Brand item in the side nav shows the count of
      missing Required fields, on every signed-in route
- [ ] With an incomplete Brand DNA, the Action queue contains a `Setup` item using the
      copy above, with a `Fill it in` button linking to `/brand`
- [ ] The Setup item sorts after `Decision` items and before `Stale` items
- [ ] Home's header count ("N things need you") includes the Setup item
- [ ] Both the badge and the queue item disappear once completeness reports `complete`
- [ ] A completeness read that fails costs the badge and the queue item only — Home
      and the shell still render
- [ ] Unit tests cover `toQueue()` with complete / partially complete / empty DNA,
      including the sort position and the `+N more` meta truncation
- [ ] A Playwright spec covers incomplete vs. complete Brand DNA on Home
- [ ] Quality gates pass, run from `web/`: `pnpm lint`, `pnpm typecheck`,
      `pnpm test:unit` (vitest), `pnpm test` (playwright), `pnpm format:check`
