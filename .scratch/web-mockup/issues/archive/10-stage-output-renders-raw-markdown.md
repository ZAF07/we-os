# 10 — Stage output shows raw markdown instead of rendered markdown

Status: completed
Type: bug

## Symptom

Specialists write each stage's deliverable as markdown, but the workspace shows it
as plain text. The reader sees the markdown source characters — `#`, `##`, `###`,
`*`, `**`, `>`, `-`, table pipes — instead of headings, bold text, blockquotes,
lists and tables.

Expected: the deliverable renders as formatted markdown, so headings look like
headings and emphasis looks like emphasis.

Impact: no crash. The gate screens are hard to read, which matters because the
workspace exists so the business owner can read the whole document before
approving a stage.

## Repro

Deterministic — it is how the component is written, not data-dependent.

1. `pnpm dev` from `web/`.
2. Open a campaign workspace with a completed stage (research or brand).
3. The deliverable body shows literal `##`, `**`, `>` characters.

## Location

[web/src/components/workspace/deliverable-view.tsx:17-26](web/src/components/workspace/deliverable-view.tsx#L17-L26) —
`DeliverableContent` puts `{content}` straight into a `whitespace-pre-wrap`
article, so the markdown source is shown verbatim. Two call sites, both in
`workspace.tsx`: [line 394](web/src/components/workspace/workspace.tsx#L394)
(an older version being viewed) and
[line 397](web/src/components/workspace/workspace.tsx#L397) (the current one).

This is the whole bug. Two nearby things were checked and are **not** in scope:

- [web/src/lib/deliverable.ts](web/src/lib/deliverable.ts) — the Performance screen's
  `toSections`/`plainText`/`isBullet` path. It is not a failed renderer; it
  deliberately splits the plan into headings the screen lays out itself, and it
  already strips emphasis and detects bullets. It renders correctly. Leave it.
  (Replacing it with structured engine output is deferred separately — issue 16
  under `.scratch/saas-foundation/`.)
- [web/src/components/brand/brand-screen.tsx:279](web/src/components/brand/brand-screen.tsx#L279) —
  echoes a human-typed answer back from a textarea. That is plain text by nature,
  not markdown. `whitespace-pre-wrap` is correct there.

## Notes for implementation

`web/` has no markdown renderer today, and Tailwind v4 rules out
`@tailwindcss/typography` as a drop-in. Adding a dependency is expected here;
pick a renderer that does not evaluate raw HTML in the markdown source (or
sanitize it), since deliverable content is model-written. Style the output
explicitly rather than relying on a prose plugin.

## Acceptance criteria

- [x] Stage deliverables render as formatted markdown — headings, bold/italic,
      lists, blockquotes, links, code and tables — with no raw markdown characters
      visible in the workspace
- [x] Both `DeliverableContent` call sites are covered (current version and an
      older version viewed from history)
- [x] Raw HTML embedded in deliverable markdown is not evaluated
- [x] A unit test asserts a heading renders as a heading element rather than as
      literal `##` text
- [x] Quality gates pass from `web/`: `pnpm lint`, `pnpm typecheck`,
      `pnpm test:unit`, `pnpm format:check`

## Completion

- Completed: 2026-09-09
- Commits: 7a5e29c (render the markdown), a6e24f0 (fenced code block fix from review)

Rendered with `react-markdown` + `remark-gfm`, each element styled explicitly
because Tailwind v4 rules out `@tailwindcss/typography` as a drop-in. No
`rehype-raw` is configured, so HTML in model-written deliverables stays inert
text rather than becoming markup.

Both call sites in `workspace.tsx` (394, 397) go through `DeliverableContent`,
so the fix inside that component covers the current version and an older version
viewed from history.

Verified in the running app, not only in tests: the deliverable rendered with
headings, bold/italic, blockquote, bullets, a GFM table, a link and inline code,
and `<img src=x onerror=alert(1)>` showed as text with no `img` element.

Two defects found during the work and fixed:
- The renderer passes each component the syntax-tree node it came from, which
  was being spread onto the element as a literal `node="[object Object]"`.
  `withoutNode` drops it in one place.
- The `code` component applied the inline pill unconditionally, so a fenced
  block drew a chip inside the `pre` panel and lost its `language-*` class.

Unit tests moved to a jsdom environment so a component that renders a document
can be asserted on as elements. Gates from `web/`: `pnpm lint`, `pnpm typecheck`,
`pnpm test:unit` (108 passing), `pnpm format:check` all pass.
