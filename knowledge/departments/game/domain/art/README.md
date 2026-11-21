# Game Art Production Knowledge

- **Status:** `PROPOSED` (2026-11-22, Art Production v2, Phase 1). Process guidance only: no new role, status, permission, tool or review bypass.
- **Scope: Board-assisted pilot.** Phase 1 is not ready for autonomous production. Every art, integration and game-UI Task of the pilot is written by the Board Operator from [asset-task-template.md](asset-task-template.md), because no Board-approved way yet puts the template where `project-manager` and `game-designer` can read it. Autonomous planning of asset Tasks waits for that mechanism ([OQ-049](../../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)).
- **Applies to:** every art, art-integration and game-UI Task in a project with `type: game`.
- **Owner:** `project-manager` (process); content of each procedure: `game-artist`. Authority for art direction stays in [game-rules.md §2](../game-rules.md#2-design-authority).

## Contents
| Document | Use it for |
|---|---|
| [complexity-lanes.md](complexity-lanes.md) | Choosing L0, L1 or L2 for an asset and what each lane requires |
| [visual-procedures.md](visual-procedures.md) | Visual research, concept exploration, selection, art critique, targeted refinement, preflight; per-family playbooks |
| [quality-rubric.md](quality-rubric.md) | Hard gates and the 0–2 rubric for self-check and review |
| [asset-task-template.md](asset-task-template.md) | Copy-ready art Task, integration Task and game-UI Task descriptions |
| [handoff-templates.md](handoff-templates.md) | Plan comment, art handoff, integration handoff and review verdict formats |

The process itself is [asset-production.md](../../workflows/asset-production.md).

## How agents get this text (delivery map)

Agents cannot read Company OS at run time. Paperclip receives exactly one file per role, the role file's body, through [sync-instructions.py](../../../../../scripts/setup/sync-instructions.py) (`PUT /api/agents/{id}/instructions-bundle/file`); nothing in this folder reaches an agent by itself. A cross-reference to this folder is not an instruction.

| Role | What it needs at run time | How it gets it |
|---|---|---|
| `game-artist` | Lanes, research, exploration, critique, refinement, preflight, evidence | Its role file, section "Visual design and refinement" (a compact copy of [complexity-lanes.md](complexity-lanes.md) and [visual-procedures.md](visual-procedures.md) §1–§6) |
| `gameplay-programmer` | Integration evidence and the routing back to the artist | Its role file (asset integration bullet) |
| `ui-designer` | Game UI visual workflow | Its role file, section "Game UI visual workflow (game projects)" |
| `game-designer`, `project-manager`, `qa` | Brief fields, lane, rubric, routing | **The Task description**, written from [asset-task-template.md](asset-task-template.md). Their role files stay unchanged (Board decision 2026-11-21) |
| Any role | Project art references, art bible, asset specs, licence rule | The project repository, named in the Task's `## Read set` |

Who writes the Task description in Phase 1: **only** the Board Operator, through the Paperclip skill (`pc.py create --desc-file <filled template>`), which can read this folder. `project-manager` and `game-designer` cannot read this folder; in the pilot they propose asset work in a comment or a design document, and the Board turns it into Tasks. An asset Task that reaches `game-artist` without the brief fields (lane, target size and background, reference traits, acceptance criteria, rubric) is set `blocked` (type `context`, owner `project-manager`) instead of guessed. A project-local copy of the template is a later, Board-approved step ([OQ-049](../../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)).

Deployment after a merge (tools, permissions, dependencies, instructions, drift, smoke test): the checklist in [runtime-management.md §1.0](../../../../../docs/operations/runtime-management.md#10-comfyui-draft-script-and-art-ops-d1-2026-11-22).

## What this folder does not change
- Review and approval: `qa` review, extra review stages the Task names, Board approval and merge (ADR-009). Nobody approves their own work.
- Ownership: the interim technical-art split in the [game-artist role](../../agents/game-artist/AGENTS.md#ownership-with-gameplay-programmer-interim).
- Tools and permissions: only those in [agents.json](../../../../../config/paperclip/agents.json) and the role files. Tools named here as gaps are proposals, not approvals.
- Paperclip statuses: the phases in these documents are internal steps of one Task, not statuses or separate issues.

## Sources
Company-owned, original guidance. It names no other game, studio or artist as a style to imitate. Do not copy paid educational material or third-party art into a game repository.
