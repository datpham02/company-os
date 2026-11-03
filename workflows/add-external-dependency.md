# Workflow: Add a New External Dependency

- **ID:** `add-external-dependency` · **Owner:** requesting agent or Board Operator · **Board gate:** yes

## Trigger
An agent or the Board identifies a tool, skill pack, MCP server, or service the studio should use.

## Required inputs
Official repository/docs URL; intended use; which roles/projects need it.

## Actors
Requester; `producer` (evaluation owner); Board Operator.

## Preconditions
Not already in [../dependencies/registry.yaml](../dependencies/registry.yaml) (if present as `candidate`, start at step 3).

## Steps
1. **Requester** opens a PR to the framework repository adding a registry entry with `integrationStatus: candidate` and all required fields ([dependency-system.md §2](../docs/design/dependency-system.md#2-entry-fields)). Board merges (low risk: data only).
2. **`producer`** creates an evaluation Task (`integrationStatus: evaluating`).
3. **Evaluator** (agent with suitable role) verifies from official sources: license, maintenance activity, install method, required permissions/credentials, supported providers, security concerns (network access, data sent to third parties). It tests in a scratch directory outside all repositories if installation is local and harmless. Otherwise it describes the planned test.
4. **Evaluator** writes findings into the Task and updates the entry (`verifiedVersion`, `compatibility`, `notes`) via PR.
5. **`producer`** requests Board approval with the evaluation.
6. **Board Operator** approves or rejects. Rejected → entry `rejected` with reason.
7. **Board Operator** installs following the official instructions (system-level installs are never done by agents, R4) and records the exact command in [installation.md](../docs/operations/installation.md) or the integration doc.
8. Entry set to `integrated` via PR; roles' `tools`/`skills` lists updated if needed.

## Expected outputs
Registry entry with final status; installation documented; role definitions updated.

## Approval requirements
Step 6. Upgrades of `required` dependencies follow the same gate.

## Failure cases
| Failure | Response |
|---|---|
| License unknown or incompatible | Reject or Board-level exception recorded in `notes` |
| Requires vendoring source | Not allowed (ADR-007); find alternative or fork as separate repository |
| Breaks an existing integration | Roll back; entry `evaluating`; record compatibility note |

## Related
[../docs/design/dependency-system.md](../docs/design/dependency-system.md) · [../docs/decisions/ADR-007-external-dependency-registry.md](../docs/decisions/ADR-007-external-dependency-registry.md)
