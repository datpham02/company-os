# Game Art Production Knowledge

- **Status:** `PROPOSED` (2026-11-22, Art Production v2, Phase 1). Process guidance only: no new role, status, permission, tool or review bypass.
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

Who writes the Task description today: the Board Operator through the Paperclip skill (`pc.py create --desc-file <filled template>`), which can read this folder. A `project-manager` or `game-designer` that writes an asset Task cannot read this folder; until a project keeps its own copy of the template (see [OQ-049](../../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)), the Board fills the template or pastes it into the planning issue.

After a merge that changes a role file, the Board runs `python -I scripts/setup/sync-instructions.py --company Soucean --dry-run`, then without `--dry-run`, then `check-agent-drift.py` ([company-bootstrap.md](../../../../../docs/operations/company-bootstrap.md)).

## What this folder does not change
- Review and approval: `qa` review, extra review stages the Task names, Board approval and merge (ADR-009). Nobody approves their own work.
- Ownership: the interim technical-art split in the [game-artist role](../../agents/game-artist/AGENTS.md#ownership-with-gameplay-programmer-interim).
- Tools and permissions: only those in [agents.json](../../../../../config/paperclip/agents.json) and the role files. Tools named here as gaps are proposals, not approvals.
- Paperclip statuses: the phases in these documents are internal steps of one Task, not statuses or separate issues.

## Sources
Company-owned, original guidance. It names no other game, studio or artist as a style to imitate. Do not copy paid educational material or third-party art into a game repository.
