# Customers

One folder per customer, each holding that customer's **Customer DNA** — the stable, reusable profile the agent grounds all work in.

```
customers/
  <name>/
    dna.md        # copied from templates/customer-dna.md, then filled in
```

## How it works
- **DNA is reusable.** Fill `dna.md` once per customer; every campaign for that customer reuses it. Update it only when the business changes.
- **Humans author it.** Agents read the DNA but do not write here.
- **The agent resolves by name.** Running `/new-campaign <name>` loads `customers/<name>/dna.md`. If it is missing or incomplete, the agent stops and asks you to complete it before any campaign work begins.

See `USAGE.md` at the repo root for the full procedure.
