# ADR-004: Task-based Agent Execution

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-003, ADR-008, [runtime-architecture.md](../architecture/runtime-architecture.md)

## Context
Agents can run as long-lived processes or be started per unit of work. Paperclip's model is already short-lived: agents "wake up in heartbeats — short execution windows triggered by Paperclip" (verified, Paperclip docs `start/core-concepts.md`).

## Decision
- In v1 each Run MUST be one Provider CLI process started for one Task, in one assigned working directory, and terminated when that Task's work for the Run is finished, fails, times out, or is cancelled.
- Persistent (always-running) agents MUST NOT be required in v1.
- Context continuity between Runs MAY use Provider session resume (Paperclip's adapters do this) but MUST NOT depend on a process staying alive.
- All durable state (task status, results, approvals) MUST be stored outside the process: in Paperclip, in Git, or in Runtime Data.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Persistent agent daemons | Resource cost, memory leaks, harder recovery; unnecessary for v1. |
| One process per workflow (multiple tasks) | Blurs task ownership and branch mapping. |

## Consequences
- Crash recovery is simple: a Run that dies is re-run or marked failed; nothing else holds state.
- Startup cost is paid per Run.
- Long tasks must be split or given adequate timeouts.

## Reconsider when
- Startup overhead dominates Run time, or
- a workflow requires an agent to react to events in real time.
