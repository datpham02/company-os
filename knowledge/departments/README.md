# Departments

A **department** is an enduring part of the company with its own specialists, rules and knowledge (brief v5 §4.2). A **project** is a product; it belongs to one department and may have contributing departments ([../projects/README.md](../projects/README.md)).

| Department | Charter | Roles of its own | Head |
|---|---|---|---|
| Game | [game/README.md](game/README.md) | `game-designer`, `gameplay-programmer` | `director` |
| Web | [web/README.md](web/README.md) | `web-engineer` | `director` |

Marketing and Operations have no folder yet. A department folder is created with its first role.

## What a department owns
- Its charter (`README.md`): mission, scope, roles, review gates, projects.
- Roles used only by this department (`agents/<id>/AGENTS.md`).
- Workflows that extend company workflows (`workflows/`). A department workflow adds steps; it never replaces a company workflow.
- Domain knowledge and rules (`domain/`).

Everything a second department would follow unchanged belongs in [../company/README.md](../company/README.md) instead.

## Adding a department
1. The Board decides it (ADR or a recorded decision).
2. Create `departments/<id>/README.md` from the charter structure above, and its first role through [agent-onboarding.md](../company/workflows/agent-onboarding.md).
3. Add the department to [../company/ORGANIZATION.md](../company/ORGANIZATION.md) and to `config/paperclip/agents.json` (`department` of each role).
4. Tag the dependencies it uses in `dependencies/registry.yaml` (`departments`).

## Placement rules
1. Rules, roles, workflows, standards and charters go in `knowledge/`. Engineering documentation of Company OS goes in `docs/`.
2. Followed unchanged by a second department → `knowledge/company/`. Only one department → `knowledge/departments/<id>/`.
3. Contracts between departments → `knowledge/company/shared/`, with one owner.
4. Project documents stay in the project's repository.
