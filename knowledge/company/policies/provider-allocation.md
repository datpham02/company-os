# Provider Allocation

- **Status:** `PROPOSED` ([ADR-015](../../../docs/decisions/ADR-015-provider-allocation.md))
- **Scope:** which AI provider runs each Agent Instance, for however many providers the Board has.

Provider is configuration, not identity ([ADR-008](../../../docs/decisions/ADR-008-provider-abstraction.md)). Moving a role to another provider never requires rewriting its instructions.

## 1. Current state (2026-11-21, Soucean)

| Provider | Paperclip adapter | Status | Agents today |
|---|---|---|---|
| Claude Code | `claude_local` | Connected | 7 of 9: `director`, `producer`, `project-manager`, `game-designer`, `ui-designer`, `qa-engineer`, `game-artist` (added 2026-11-21) |
| Cursor CLI | `cursor` | Connected | `gameplay-programmer`, `web-engineer` |
| Gemini CLI | `gemini_local` | Tried 2026-11-04; login failed; uninstalled | — |
| Codex CLI | `codex_local` | Installed (0.166.0, OQ-009); no account, deferred by the Board on 2026-11-21 (OQ-010) | — |

**Models and effort (Board, 2026-11-21).** Each agent has one fixed runtime and one model; there is no automatic fallback or per-task routing. The values live per agent in `config/paperclip/agents.json` (`model`, and `effort` for `claude_local`), and `scripts/setup/check-agent-drift.py` compares them with the live company.

| Agents | Adapter | Model id | Effort |
|---|---|---|---|
| `director`, `game-designer` | `claude_local` | `claude-fable-5-1` | `effort: high` (passed as `--effort`) |
| `producer`, `project-manager`, `game-artist`, `qa-engineer`, `ui-designer` | `claude_local` | `claude-sonnet-5-5` | `effort: medium` |
| `gameplay-programmer`, `web-engineer` | `cursor` | `gpt-5.3-codex-high` | in the model id; the `cursor` adapter has no effort field |

Departures from the Board's first target, approved on 2026-11-21: Fable 5.2 is not in the Paperclip 2026.1023.0 `claude_local` catalog, so Fable 5.1 is used; the Cursor account lists no "GPT-5.6 Codex", so the Codex line stays at 5.3 with High effort; `qa-engineer` and `ui-designer` stay on Claude Code, because a switch to `cursor` drops their Claude allow and deny lists (Paperclip keeps only adapter-agnostic keys on an adapter change). Whether the account can use each model is `UNVERIFIED` until each agent's first run (OQ-047).

On 2026-11-04 (the earlier company `GAM`) Cursor ran only `qa` reviews, which often ended without a recorded decision (E5 in [task-contract.md](../standards/task-contract.md)). In Soucean, Cursor runs the two implementation roles; they have no allow list, an accepted risk until the authentication migration (implementation plan D-05).

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

## 4. Worked examples (today's 9 roles, total workload 16)

The 9 roles are the 8 original ones plus `game-artist` (workload 2, main work type `ui-design`). Cursor's `ui-design` fit is 1, so rule 1 keeps `game-artist` on Claude Code in every example below. `code-reviewer` (Phase 6 pilot) is left out until it joins the live company.

**One provider.** Everything on it. No review is cross-provider; Board approval is the only independent check.

**Two providers, equal capacity (Claude Code + Cursor): proposed allocation.**

| Provider | Roles | Load |
|---|---|---|
| Claude Code | `ui-designer`, `qa`, `game-artist`, `game-designer`, `project-manager` | 8 |
| Cursor | `gameplay-programmer`, `web-engineer`, `director`, `producer` | 8 |

Every code review is cross-provider. `qa`'s review of `game-artist`'s assets is same-provider and cannot be avoided: rule 1 keeps both on Claude Code. Changes from today: `qa` moves to Claude Code (Cursor's review fit is 1); `director` and one read-only planner move to Cursor (rule 3, then rule 5; `producer` and `project-manager` tie, `producer` shown). With 8 roles (load 14) the split was 7 / 7 and `producer` stayed on Claude Code.

**Two providers, capacity 2:1 for Claude Code.** Cursor would be at 150 % of its fair share; rule 4 moves `web-engineer` back: Claude Code 11, Cursor 5. `web-engineer`'s code and its review of `ui-designer` become same-provider.

**Three providers.** The same rule. Example with a third provider X that has `implementation` fit ≥ 2 and allowlist-level confinement: `gameplay-programmer` on Cursor, `web-engineer` on X, `qa` on Claude Code, so every code review is cross-provider.

## 5. Rollout preconditions (Cursor code roles)

1. Branch protection on the target repository's `main` (`lamplight-vigil` has it; check `soucean-game`).
2. A fine-grained `GH_TOKEN` for that repository bound to the agent.
3. Switch one role at a time, `gameplay-programmer` first; one trial Task reviewed by `qa` on Claude Code.
4. Record the result here and in [../ORGANIZATION.md](../ORGANIZATION.md).

## 6. Provider comparison protocol (Phase 4, P4-T04; `PROPOSED`)

Fit scores in §2 change only on evidence. This is how the evidence is collected.

1. **Pair:** the same Task class run once by each candidate provider:
   - a small code Task with a write set of at most 5 files;
   - or a review of the same Review Package.
   Same role file, same permission profile class, same acceptance criteria.
2. **Isolation:** a sandbox company and a throwaway repository, never a production repository. Each run needs the Board's authorization (provider quota, ADR-015).
3. **Measures, recorded per run:**
   - acceptance criteria met;
   - review findings: count and severity;
   - rework rounds until approval;
   - run time;
   - provider cost or quota used;
   - rule violations (scope, recorded decision, credential rule).
4. **Record:** one table row per run in this section's results table, with the run ids, and a dated note on any fit-score change in §2.
5. **Scope today:**
   - Claude Code (`claude_local`) and Cursor CLI (`cursor`);
   - Codex is excluded until OQ-010 is reopened (no account, Board 2026-11-21);
   - Gemini is excluded (login failed, §1).

| Date | Task class | Provider | Criteria met | Findings | Rework | Time | Cost | Violations | Runs |
|---|---|---|---|---|---|---|---|---|---|
| — | No comparison run yet | | | | | | | | |

## Related documents
[../../../docs/decisions/ADR-008-provider-abstraction.md](../../../docs/decisions/ADR-008-provider-abstraction.md) · [../../../docs/integrations/cursor-integration.md](../../../docs/integrations/cursor-integration.md) · [../../../docs/architecture/security-architecture.md](../../../docs/architecture/security-architecture.md) · [agent-system.md](../../../docs/design/agent-system.md)
