# simple-memory

Significance-based **auto-compaction** of the `notes` values in the
[agenticAwareness](../agenticAwareness) data files. It is deliberately small:
for now it runs **once after the last user input**, after a set idle pause
(default **15 minutes**), and asks the agent to find low-value notes to compact.

Two rules it is built on:
- **Idle pause only gates *when* we ask.** It never deletes on a timer.
- **Removal is by significance, not time.** Old != low-value.

## How it plugs into agenticAwareness

```mermaid
graph LR
  U[User input] -->|touch| MK[input marker file]
  MK --> W[Watcher]
  W -->|idle >= 15min AND<br/>marker newer than last run| C[Compaction pass]
  C -->|reads/writes via strict schema| KB[(agenticAwareness<br/>hosts/entities/personas)]
```

## The one-pass lifecycle

```mermaid
sequenceDiagram
  participant U as User turn
  participant M as input marker
  participant W as Watcher (poll)
  participant R as Reviewer (significance)
  participant D as agenticAwareness YAML
  U->>M: touch (records last-input time)
  loop every interval
    W->>M: read mtime
    W->>W: due? (idle>=15min AND mtime newer than last_run)
  end
  W->>D: load via schema
  W->>R: collect_notes() -> candidates
  R-->>W: decisions (keep/drop/rewrite)
  W->>D: apply_decisions() + dump
  W->>W: touch last_run (so it runs once per input)
```

## Significance, not time

```mermaid
graph LR
  N[Notes across data<br/>+ old chat logs] --> Q[Reviewer judges<br/>significance]
  Q -->|high value| K[Keep]
  Q -->|low value| X[Compact / drop]
  T[Age / idle time] -.only triggers the review.-> Q
```

## Default reviewer

Without an LLM wired in, `default_reviewer = keep_all` — safe, nothing is
dropped. Plug in an LLM-backed reviewer later to actually judge low-value notes.

## Run it

```sh
# one evaluation
python -m simple_memory --input-marker ~/.local/share/last-user-input --once

# continuous watcher (poll every 60s)
python -m simple_memory --input-marker ~/.local/share/last-user-input
```

`--kb` defaults to `~/repos/agenticAwareness`; `AGENTICAWARENESS_ROOT` overrides.
`--idle` sets the pause (default 15). The watcher triggers once per user input
via an `input-marker` file you touch on every user turn.

## Status

Minimal by design. The reviewer, chat-log source, and scheduling are stubs to
build on later.
