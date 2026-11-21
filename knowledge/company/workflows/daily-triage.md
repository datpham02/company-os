# Workflow: Daily Triage

- **ID:** `daily-triage` · **Owner:** `project-manager` (agent part), Board Operator (Board queue) · **Board gate:** no
- **Status:** `PROPOSED` ([ADR-017](../../../docs/decisions/ADR-017-task-contract-and-liveness.md))

## Trigger
Once per working day per active project, and after the Board approves or merges a batch of work.

## Required inputs
All open issues of the project with status, assignee, blockers, execution stage, last comment and last run.

## Actors
Board Operator (runs `pc.py triage`), `project-manager` (acts on the agent items), owners named in blocked comments.

## Preconditions
Paperclip reachable. Agents cannot list other issues (G-8), so the sweep itself runs as the Board through the Paperclip skill. Running it as a Paperclip routine or scheduled heartbeat is `UNVERIFIED` and stays a later option.

## Steps
1. **Board Operator** runs `python -I .claude/skills/paperclip/scripts/pc.py triage` (or asks Claude: "triage the studio"). It prints, oldest first:
   - **Needs the Board:** issues assigned to the Board, pending Board approval stages, Paperclip recoveries handed to the Board (OQ-048), and Board Tasks for environment fixes;
   - **Blocked:** age, last comment, and whether the comment names an unblock owner ([task-contract.md §6](../standards/task-contract.md#6-blocker-protocol)); blocked issues whose blockers are all `done` or include a `cancelled` one;
   - **Review stalled:** `in_review` issues on an agent with no run since the stage started;
   - **Quiet:** `in_progress` issues with no update for a working day;
   - **Ready to release:** `backlog` issues whose blockers are all `done`;
   - **WIP:** agents with more than one `in_progress` issue.
2. **Board Operator** clears "Needs the Board": approve, request changes, answer, or reassign.
3. **Board Operator** posts the remaining agent items as one comment on the project's planning issue and wakes the `project-manager` on it (or acts directly through the skill).
4. **`project-manager`**, for each agent item: wakes the unblock owner with the `Ask`; escalates items older than the limits in [task-contract.md §7](../standards/task-contract.md#7-liveness-nothing-is-forgotten); fixes cancelled-blocker relations (or asks the Board to); proposes which ready Tasks to release next, respecting WIP and write-set overlap.
5. **Board Operator** releases the proposed Tasks.

## Expected outputs
An empty "Needs the Board" list, every blocked issue with a named owner and a next check, and a release proposal.

## Approval requirements
Releases and cancellations stay Board decisions.

## Failure cases
| Failure | Response |
|---|---|
| The same blocker type recurs | `producer` opens a process or tooling Task |
| An owner does not respond after escalation | Board reassigns the Task |

## Related
[task-failure-handling.md](task-failure-handling.md) · [parallel-tasks.md](parallel-tasks.md) · [../standards/task-contract.md](../standards/task-contract.md)
