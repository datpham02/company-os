# Workflow: Onboard a New Agent

- **ID:** `agent-onboarding` · **Owner:** `director` (proposal), Board Operator (registration) · **Board gate:** yes

Covers two cases: **(A)** a new Agent Role, **(B)** a new Agent Instance of an existing role (e.g. a second `gameplay-programmer` for parallel work).

## Whole-company setup (package import)
When a whole company is created or rebuilt, its agents come from a package import, not one hire request per agent ([company-bootstrap.md](../../../docs/operations/company-bootstrap.md), ADR-016). The Board decided on 2026-11-21 that this replaces steps 1–2 and 6 below for an imported company. Steps 4 and 5 still apply through `post-import.py` and the environment test. Soucean (2026-11-05) was set up this way. This workflow covers agents added afterwards.

## Trigger
Capacity shortage or a missing skill set identified by `producer`/`project-manager`, or a Board request.

## Required inputs
(A) Role purpose, responsibilities, reporting line, permission profile. (B) Role ID, provider, budget, projects served.

## Actors
`director`, `producer`, Board Operator.

## Preconditions
(B) The role exists in `knowledge/company/agents/`.

## Steps
1. **`director`** (A) or **`producer`** (B) writes the justification and requests approval. In Paperclip this is a hire request (`POST /api/companies/{companyId}/agent-hires` → `hire_agent` approval, `VERIFIED`) with name, role, `reportsTo`, capabilities, monthly budget.
2. **Board Operator** approves or rejects.
3. (A only) **An agent or the Board** opens a PR adding `knowledge/company/agents/<agent-id>/AGENTS.md` per [agent-system.md](../../../docs/design/agent-system.md) (all required sections, frontmatter) and updating [../ORGANIZATION.md](../ORGANIZATION.md) and [agent-system.md §6](../../../docs/design/agent-system.md#6-defined-roles-v1). Board merges.
4. **Board Operator** configures the Agent Instance in Paperclip:
   - adapter type (`claude_local` / `codex_local`; `process` in Stage 2);
   - adapter config: model, timeout, permission flags from the role's `permissionProfile` ([security-architecture.md §4](../../../docs/architecture/security-architecture.md#4-agent-permissions-provider-level)); for Codex, `instructionsFilePath` pointing at the role's `AGENTS.md`, or equivalent instruction delivery (OQ-023);
   - secret bindings: `GH_TOKEN` only for code-writing roles;
   - budget.
5. **Board Operator** runs Paperclip's "Test Environment" for the agent (`VERIFIED` UI feature for local adapters).
6. **`project-manager`** assigns a small trial Task. **`qa`** reviews the outcome against the role's success criteria.
7. Agent becomes generally assignable.

## Expected outputs
Role file (A); configured, tested Agent Instance; updated org chart.

## Approval requirements
Step 2; role PR merge (A).

## Failure cases
| Failure | Response |
|---|---|
| Environment test fails | Fix credentials/CLI ([troubleshooting.md](../../../docs/operations/troubleshooting.md)) |
| Trial Task shows role confusion | Revise the role's instructions; repeat step 6 |
| Paperclip requires a root "CEO" distinct from `director` | Follow OQ-006 resolution |

## Related
[../../../docs/design/agent-system.md](../../../docs/design/agent-system.md) · [../../../docs/design/company-design.md](../../../docs/design/company-design.md)
