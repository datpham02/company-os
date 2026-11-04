# ADR-015: Provider Allocation by Fit, Reviewer Independence and Workload

- **Status:** Proposed
- **Date:** 2026-11-04
- **Deciders:** Board Operator
- **Related:** ADR-008, C-002, OQ-033, [provider-allocation.md](../design/provider-allocation.md)

## Context
ADR-008 makes the provider a property of the Agent Instance, not of the role, but says nothing about how to choose it. On 2026-11-04, 7 of 8 agents ran on Claude Code and only `qa` on Cursor, so one quota carried almost all the work. Cursor reviews often ended without a recorded decision, which Paperclip turns into `blocked` (GAM-45). The Board's set of AI subscriptions will change over time (Gemini CLI was tried and dropped the same day).

## Decision
- The Board declares its providers in a local provider list (capacity, confinement, Claude-skill support, fit per kind of work). Roles declare `allocation` metadata (work types, workload, writes code, requirements, whom they review).
- Agents are placed by the rule in [provider-allocation.md §3](../design/provider-allocation.md#3-rule): hard constraints (requirements, minimum fit 2, confinement for code writers) → reviewer on a different provider from its author → balance load against capacity → overload cap → ties by fit.
- Fit numbers start as Board estimates and change only from recorded evidence (triage records), with Board approval.
- A code-writing role MAY run on a provider weaker than an allowlist only with branch protection on the target repository and a repository-scoped `GH_TOKEN`. A provider with no confinement runs under the `bypass` profile (C-002).
- Allocation changes are Board-approved configuration changes, rolled out one role at a time with a cross-provider trial Task.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Fixed table per provider pair | Breaks whenever the Board adds or drops a subscription |
| Balance by head count | Implementers use far more tokens than planners; head count hides the real load |
| Everything on the strongest provider | One quota limit stops the whole studio; reviews lose model diversity |

## Consequences
- With today's two providers the proposed allocation moves `qa` to Claude Code and the two implementers plus `game-director` to Cursor (Claude 7, Cursor 7 workload units).
- Code roles on Cursor rely on Cursor's classifier instead of an allowlist; branch protection becomes a hard precondition (check `soucean-game`).
- `preferredProviders` in role files becomes redundant once this ADR is accepted.

## Reconsider when
A provider gains or loses allowlist-level confinement, fit evidence contradicts the estimates, or the Runtime (Stage 2) takes over provider selection.
