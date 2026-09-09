# Auto-Growing Brand DNA Answer Boxes

The Brand screen's answer editor does not grow by itself as the answer gets longer.
It opens at a fixed height with the browser's native resize grip, and the tenant
drags it taller if they want more room. That is the intended behaviour for now.

This covers any variation on the idea: `field-sizing-content` on the Brand screen
editor, a JS auto-resize handler, or reusing the shared `ui/textarea.tsx` control
so the Brand screen matches onboarding's auto-growing box.

## Why this is out of scope

Manual resize already solves the underlying problem. The complaint behind the
original report was "I cannot see enough of my long answer at once" — and the
native grip answers that, at whatever height the tenant chooses. Auto-growth is a
nicety on top of a control that already works, not a fix for something broken.

The cost is not zero. Auto-growth on this screen needs a `max-height` too, because
the Save and Cancel buttons sit directly under the box; a box that grows without a
cap pushes the primary action off screen and trades a small annoyance for a bigger
one. That is a real design decision — how tall is too tall — and it is not worth
spending on a control the tenant can already size themselves.

Verified manually on 2026-09-09: the grip is present and drags the box larger.

## What is true today

- `web/src/components/brand/brand-screen.tsx` — a raw `<textarea>` with
  `rows={4}` (`rows={2}` for short answers) and default `resize: both`.
- `web/src/app/(app)/onboarding/page.tsx` — uses `web/src/components/ui/textarea.tsx`,
  which carries `field-sizing-content min-h-16` and does auto-grow.

The two surfaces are deliberately allowed to differ. Onboarding is a first-run flow
where the tenant writes every answer from scratch and never sees a resize grip
before they need one; the Brand screen is a return-and-edit surface where the box
opens against an answer that already exists. If the divergence later causes real
confusion, that is the signal to revisit — not the divergence on its own.

## What would change this

- Tenants report they do not find the resize grip, or ask for the box to grow.
- The Brand screen editor moves into a layout where Save/Cancel do not sit
  immediately below the box, so the `max-height` question goes away.
- A shared answer-editor component is built for another reason and the Brand screen
  adopts it, making auto-growth free rather than a deliberate spend.
