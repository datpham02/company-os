# ADR-017: Task Contract, WIP Limit, Blocker Protocol and Daily Triage

- **Status:** Proposed
- **Date:** 2026-11-04
- **Deciders:** Board Operator
- **Related:** ADR-004, ADR-006, G-8, G-9, G-10, OQ-041, [task-contract.md](../design/task-contract.md), [daily-triage.md](../../workflows/daily-triage.md)

## Context
In the first two days of Stage 1, parallel Tasks conflicted on the same file because the overlap check ignored Tasks in review (GAM-44/45). One agent ran two Tasks at once (GAM-25/45). Planned Tasks landed on the read-only planner (GAM-21). Blocked Tasks waited with no named owner (GAM-6). Nothing revisits blocked work, because heartbeats are disabled and wakes are event-driven only. Paperclip never resolves a cancelled blocker. Evidence is in [task-contract.md §1](../design/task-contract.md#1-why).

## Decision
- Every Task carries the task contract: goal, acceptance criteria, **write set**, read set, blocker relations, assignee, reviewer, Board approval for code, and a size within one PR. Tasks missing a write set or stages are not released.
- Parallel safety is checked against every unmerged Task, not only `in_progress` ones. Hotspot files are changed by one Task at a time.
- WIP is one `in_progress` Task per Agent Instance.
- A blocked Task always names its type, its unblock owner, the exact ask and the next check. Dependencies are blocker relations. Cancelling a Task repairs the relations that point at it.
- A daily triage, run by the Board through the Paperclip skill and acted on by `project-manager`, lists the Board queue, blocked Tasks without owners, stalled reviews, quiet Tasks, ready backlog and WIP breaches, with time limits for escalation.
- Because agents cannot read this repository at run time, each role file repeats the agent-side rules in a `## Task hygiene` section.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Enable periodic heartbeats on every agent | Spends quota on idle wakes; agents still cannot see other issues (G-8) |
| Rely on Paperclip's blocker wakes only | Do not cover missing owners, cancelled blockers, Board queues or stalled reviews |
| Lock files through Git | Git has no locks for this workflow; planning-time write sets prevent the conflict earlier |

## Consequences
- Planning takes slightly longer (write sets, relations); merge conflicts and forgotten Tasks should drop.
- `pc.py triage` and release checks are added to the Paperclip skill. Enforcing WIP in Paperclip (`maxConcurrentRuns: 1`) waits for OQ-041.
- Paperclip's own issue monitor and blocker-attention fields (`monitorNextCheckAt`, `blockerAttention`, seen in the API) may replace part of the triage later (`UNVERIFIED`).

## Reconsider when
Paperclip lets agents read sibling issues, offers native stale-work alerts, or the Stage 2 Runtime takes over task scheduling.
