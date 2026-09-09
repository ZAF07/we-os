# Issue tracker: Local Markdown

Issues and PRDs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The PRD is `.scratch/<feature-slug>/PRD.md`
- Implementation issues are `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

### Issue file header

An issue opens with its title as a level-one heading, then its metadata lines,
then the body. Nothing else comes before the heading:

```markdown
# 10 — Stage output shows raw markdown instead of rendered markdown

Status: ready-for-agent
Type: bug

## Symptom
...
```

- The heading is `# <NN> — <title>`, using an em dash, with `<NN>` matching the
  filename's number.
- `Status:` is the triage role, from `triage-labels.md`. It becomes `completed`
  when `/post-implement` archives the file.
- `Type:` is what kind of work the issue is:

  | `Type:`       | Meaning                                                       |
  | ------------- | ------------------------------------------------------------- |
  | `task`        | Planned work — a feature slice, a refactor, a chore            |
  | `bug`         | A defect in already-shipped code (what `/file-bug` files)      |
  | `enhancement` | An improvement to something that already works as intended     |

  Most issues are `task`. Use `bug` only for the shipped-code defects described
  in `CLAUDE.md` — not for something broken in the diff currently being written.

Some older issue files predate this header and carry no `Type:` line. Match the
convention above for new files rather than the oldest neighbours; don't
retrofit old files just to make them uniform.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`. These two vocabularies are the wayfinder's own and do **not** apply to implementation issues, which use the `Status:`/`Type:` values above. No wayfinding effort exists in this repo yet.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
