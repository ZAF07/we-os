# The creative unit is the approvable asset

A **creative unit** — headline, primary text, CTA, one generated still image, and a named placement (Meta feed 1:1, Meta story 9:16, TikTok 9:16) — is the thing a client reviews, approves, or sends back. Not a lone image: what gets published to Meta or TikTok is an ad, and modelling the asset as a bare picture would be wrong at integration time. Copy comes from the chat model already in use; images come from one image model behind a new `ImageGenerator` port, consistent with the ports-and-adapters shape in [ADR-0001](0001-ports-and-adapters-architecture.md).

The Asset Prompts stage therefore stops emitting one `asset-prompts.md` blob and emits **N creative-unit records**, each individually approvable and individually re-iterable with its own version chain ([ADR-0015](0015-human-approval-gates-and-versioned-deliverables.md)).

**No video in v1.** Video generation is slow, expensive per attempt, and unpredictable in quality — a revision loop over video burns real money and patience.

## Considered options

- **Copy only, visuals later** — rejected: nearly free and arguably the higher-value output for small businesses, but the review experience is thin and it isn't what "AI generates your creative" promises.
- **Copy + stills + short video** — rejected for v1 on cost and iteration latency; revisit once the still-image loop is proven.
