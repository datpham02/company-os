# Provider Allocation

- **Status:** `PROPOSED` ([ADR-015](../../../docs/decisions/ADR-015-provider-allocation.md))
- **Scope:** which AI provider runs each Agent Instance, for however many providers the Board has.

Provider is configuration, not identity ([ADR-008](../../../docs/decisions/ADR-008-provider-abstraction.md)). Moving a role to another provider never requires rewriting its instructions.

## 1. Current state (2026-11-04)

| Provider | Paperclip adapter | Status | Agents today |
|---|---|---|---|
| Claude Code | `claude_local` | Connected | 7 of 8 (all except QA) |
| Cursor CLI (`gpt-5.3-codex`) | `cursor` | Connected | `qa` |
| Gemini CLI | `gemini_local` | Tried 2026-11-04; login failed; uninstalled | — |
| Codex CLI | `codex_local` | Not installed (OQ-009) | — |

Nearly all work draws on the Claude quota, and Cursor runs only reviews, which often end without a recorded decision (E5 in [task-contract.md](../standards/task-contract.md)).

## 2. Inputs

**Provider list.** Local, per machine and account, never committed. Example in [../../config/providers.example.yaml](../../../config/providers.example.yaml):

| Field | Meaning |
|---|---|
| `id`, `adapter`, `model` | Paperclip adapter and model |
| `capacity` | Board's estimate of the share of work this subscription can carry (e.g. 2:1) |
| `confinement` | `allowlist` (Claude CLI engine), `classifier` (Cursor `--auto-review`), `sandbox`, or `none` (e.g. an adapter that forces `--approval-mode yolo`) |
| `supportsClaudeSkills` | Whether Claude Code skills load (needed by `ui-designer`) |
| `fit` | 0–3 per kind of work: `planning`, `implementation`, `review`, `ui-design`, `docs`, `long-context` |

**Role metadata** (`metadata.gameStudio.allocation` in each `knowledge/company/agents/<id>/AGENTS.md`): `workType` (main kind of work first), `workload` (implementer 3, designer 2, reviewer 2, game designer 1, planner 1), `writesCode`, `requires`, `reviews`, optional `pinnedProvider`.

**Fit is evidence-based.** Start from the Board's estimates; update monthly from the triage record (Tasks sent back by review, blocked by tooling, failed runs per provider and kind of work). Current estimates and evidence:

| Provider | Estimate | Evidence |
|---|---|---|
| Claude Code | 3 across the board, `long-context` 2 | All Stage 1 planning, design and code (GAM-1 to GAM-46); follows the reporting rule and allowlists |
| Cursor | `implementation` 3, `planning`/`docs`/`long-context` 2, `review` 1, `ui-design` 1 | Review decisions often not recorded (GAM-45) |

## 3. Rule

Applied in this order. With a handful of roles the allocation can simply try every assignment and keep the best one.

1. **Hard constraints.** The provider meets the role's `requires`, and its `fit` for the role's main `workType` is at least 2. A `writesCode` role goes to a provider weaker than `allowlist` only if the target repository has branch protection on `main` and the agent has a fine-grained `GH_TOKEN` for that repository. Confinement `none` means the `bypass` profile: Board approval per agent and no push-capable token (C-002). `pinnedProvider` wins.
2. **Reviewer independence.** Minimise reviewed workload whose reviewer shares the author's provider (`qa` → implementers, `director` → `game-designer`, `web-engineer` → `ui-designer`).
3. **Balance by workload, not head count.** Minimise the highest load ÷ capacity.
4. **Overload cap.** If a provider ends above 125 % of its fair share, give up rule 2 one pair at a time, lightest first, while that lowers the overload.
5. **Ties.** Higher `fit` first; then read-only planners on the weaker-confinement provider and code writers on the stronger one; then the provider listed first.

**Output for the Board:** role, provider, profile, load and % of fair share per provider, same-provider review pairs, and the adapter blocks for the import package ([company-bootstrap.md](../../../docs/operations/company-bootstrap.md)).

**Change:** adding or removing a provider, or changing `capacity` or `fit`, means rerun the rule, Board approves, update the changed agents. **Fallback:** a provider out of quota or down for a working day is marked unavailable and the rule is rerun.

## 4. Worked examples (today's 8 roles, total workload 14)

**One provider.** Everything on it. No review is cross-provider; Board approval is the only independent check.

**Two providers, equal capacity (Claude Code + Cursor): proposed allocation.**

| Provider | Roles | Load |
|---|---|---|
| Claude Code | `ui-designer`, `qa`, `game-designer`, `producer`, `project-manager` | 7 |
| Cursor | `gameplay-programmer`, `web-engineer`, `director` | 7 |

Every review is cross-provider. Changes from today: `qa` moves to Claude Code (Cursor's review fit is 1); `gameplay-programmer`, `web-engineer` and `director` move to Cursor.

**Two providers, capacity 2:1 for Claude Code.** Cursor would be at 150 % of its fair share; rule 4 moves `web-engineer` back: Claude Code 10, Cursor 4. `web-engineer`'s code and its review of `ui-designer` become same-provider.

**Three providers.** The same rule. Example with a third provider X that has `implementation` fit ≥ 2 and allowlist-level confinement: `gameplay-programmer` on Cursor, `web-engineer` on X, `qa` on Claude Code, so every code review is cross-provider.

## 5. Rollout preconditions (Cursor code roles)

1. Branch protection on the target repository's `main` (`lamplight-vigil` has it; check `soucean-game`).
2. A fine-grained `GH_TOKEN` for that repository bound to the agent.
3. Switch one role at a time, `gameplay-programmer` first; one trial Task reviewed by `qa` on Claude Code.
4. Record the result here and in [../ORGANIZATION.md](../ORGANIZATION.md).

## Related documents
[../../../docs/decisions/ADR-008-provider-abstraction.md](../../../docs/decisions/ADR-008-provider-abstraction.md) · [../../../docs/integrations/cursor-integration.md](../../../docs/integrations/cursor-integration.md) · [../../../docs/architecture/security-architecture.md](../../../docs/architecture/security-architecture.md) · [agent-system.md](../../../docs/design/agent-system.md)
