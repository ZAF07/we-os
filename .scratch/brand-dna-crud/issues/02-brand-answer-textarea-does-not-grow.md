Status: ready-for-agent

# Brand DNA answer textarea does not grow with the answer

## Symptom

When a tenant types a long answer to a Brand DNA question, the text box keeps its
fixed height instead of growing with the content. Only a couple of paragraphs are
visible at a time, so writing or reviewing a detailed description (e.g. "what your
company is about") means scrolling inside a small box. No crash and no error — the
answer saves correctly; this is a usability defect in shipped UI.

Expected: the box grows as the answer gets longer, so the tenant can see what they
have written, with a sensible cap before it starts scrolling.

Confirmed by the reporter as the **Brand screen** (editing an existing answer), not
the onboarding wizard. Two surfaces render Brand DNA answers and they have diverged:

- `web/src/components/brand/brand-screen.tsx:253` — a raw `<textarea>` with a fixed
  `rows={4}` (`rows={2}` for non-textarea inputs) and no auto-grow. **This is the one
  that reproduces.**
- `web/src/app/(app)/onboarding/page.tsx:69` — uses the shared
  `web/src/components/ui/textarea.tsx`, which already carries `field-sizing-content`
  and `min-h-16`, so it does auto-grow. It is the reference behaviour to match.

## Repro

Deterministic.

1. Run the web app (`pnpm dev` from `web/`) and sign in as a tenant with a Brand DNA.
2. Go to the Brand screen and click to edit a long-form question (a `textarea`
   `input_type`, e.g. the company description).
3. Paste or type three or more paragraphs.
4. The box stays 4 rows tall; the content scrolls inside it.

## Suspected location

- `web/src/components/brand/brand-screen.tsx:253-258` — fixed `rows`, no
  `field-sizing-content` or auto-resize in the className.
- Fix likely means reusing `web/src/components/ui/textarea.tsx` (already auto-grows)
  rather than the hand-rolled element, keeping the existing `text-[13px]` styling.

## Acceptance criteria

- [ ] A long answer expands the box as it is typed, on the Brand screen edit control
- [ ] A maximum height is applied so a very long answer scrolls rather than pushing
      the Save/Cancel buttons off screen
- [ ] Onboarding and Brand screen use the same textarea control
- [ ] A test covers the fixed behaviour
- [ ] Quality gates pass: `pnpm lint`, `pnpm typecheck`, `pnpm test` from `web/`
