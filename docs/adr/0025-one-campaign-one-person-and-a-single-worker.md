# One campaign, one person, one worker

Slice 05 built a shared run registry so several copies of the service could run at once, and forwarding between them so a run's trace stayed readable wherever a request landed. That machinery worked and was verified end to end. It is being removed, because it buys concurrency the product does not need yet and charges real complexity for it.

Two rules replace it.

## One campaign is run by one person at a time

The claim on a campaign now names the person holding it. While a run is in flight:

- Nobody may start a second run of that campaign — not the same person in another tab, and not a colleague at the same business.
- Only the person who started it may cancel it. To a colleague the run reads as **absent** rather than forbidden, the same 404 another business would get, so nothing about the shape of one person's work leaks to another.

A colleague trying to start one is refused with a 409 that says a colleague is running it, because "campaign busy" with no explanation is a support ticket.

This is not a permission model. Nobody owns a campaign; the lock exists only while a run is live, and the campaign is free the moment it ends. The reason is mechanical, not political: two runs write the same `campaigns/<slug>/` deliverables and would overwrite each other.

## Exactly one worker

The service runs as a single process. That is now an assumption, not a preference, and two things depend on it:

- **Startup resolves every run still marked `running` as `interrupted`.** In a single-process world nothing else could be executing them, so an unconditional sweep is correct — and it beats the heartbeat protocol it replaces, which needed a stale window during which a crashed run's campaign stayed locked.
- **A run's trace is a file on that process's disk**, which is all it needs to be. Streaming works because the process serving the stream is the one that wrote the file.

Running a second copy would be **wrong, not merely unsupported**: it would resolve the first copy's live runs on boot. Scaling out is a deliberate change, and this ADR is what a future reader should find when they consider it.

## Considered options

- **One campaign, one person, one worker (chosen)** — deletes a shared registry's heartbeat protocol, a worker-to-worker HTTP relay, four settings, and a database column, in exchange for a concurrency limit no customer is asking to lift.
- **Keep the multi-worker machinery** — rejected: it was complexity paid in advance. The relay held a connection open on two workers per live stream, required workers to reach each other on the network, and needed a heartbeat window tuned against restart latency. None of that earns its keep at one process.
- **Keep multi-worker but drop the per-user rule** — rejected: the two are independent, but the per-user rule is what a business actually notices. Two colleagues silently fighting over one campaign's deliverables is a data-loss bug; a second server is a capacity feature.
- **Make the campaign lock permanent per user** — rejected: it would turn a mechanical guard into an ownership model, and leave campaigns stranded when someone leaves.

## Consequences

- Supersedes the multi-worker parts of [ADR-0024](0024-platform-owned-tenant-ids-and-explicit-run-abandonment.md): the run store stays durable and shared-capable, but nothing depends on it being reachable from more than one process.
- `RunRecord` carries `user_id` and no longer carries `worker_id`, `worker_url` or `heartbeat_at`. `MARKETING_OS_WORKER_URL`, `MARKETING_OS_LOGS_DIR`, `MARKETING_OS_RUN_HEARTBEAT` and `MARKETING_OS_RUN_STALE_AFTER` are gone.
- **To scale out later**, three things need doing together, and the order matters: give traces a shared home (Postgres or object storage), restore a liveness signal so startup stops sweeping other processes' runs, and decide whether the per-user rule should become per-session. Restoring only the first would silently break run recovery.
