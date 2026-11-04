# OpenSpec Integration

**Verified against:** OpenSpec repository [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) (MIT) at commit `2bd5bc3` (2026-11-02), and the locally installed CLI **1.11.0** (`openspec --help`). Latest npm: `@fission-ai/openspec` 1.16.0. Integration status: `candidate` in the dependency registry.

## 1. What OpenSpec does (its own capabilities, `VERIFIED`)

OpenSpec is an "AI-native system for spec-driven development". In a project it maintains:

```text
openspec/
├── specs/                      Source of truth: current agreed behaviour (requirements + scenarios)
└── changes/
    ├── <change-name>/          A proposed change
    │   ├── proposal.md         Why and what
    │   ├── design.md           Technical approach
    │   ├── tasks.md            Implementation checklist
    │   └── specs/…             Spec deltas (ADDED / MODIFIED / REMOVED requirements)
    └── archive/<date>-<name>/  Completed changes, merged into specs/
```

- **CLI** (`VERIFIED` commands in 1.11.0): `init`, `update`, `list`, `view`, `change`, `archive`, `spec`, `validate`, `show`, `status`, `instructions`, `config`, `schema`, `store`, `doctor`, `context`, `workset`, `templates`.
- **AI slash commands** installed into the chosen coding tools by `openspec init`: `/opsx:explore`, `/opsx:propose <name>`, `/opsx:apply`, `/opsx:archive` (default profile). Spelling varies per tool; for Codex it is `$openspec-propose` style (`VERIFIED`, README). `openspec init` prints the right form for the tools you pick.
- Requires Node.js 22.12.0+ for npm installation (`VERIFIED`).

## 2. What Game Studio does (orchestration, `PROPOSED`)

OpenSpec manages *spec artefacts inside one repository*. It does not assign work, gate approvals, or know about agents. Game Studio maps its workflow onto Paperclip tasks:

| Step | Actor | OpenSpec action | Paperclip / Game Studio action |
|---|---|---|---|
| 1. Explore an idea | `game-designer` | `/opsx:explore` | Task "Explore: <feature>"; findings in comment |
| 2. Propose a change | `game-designer` (design) or `gameplay-programmer` (technical) | `/opsx:propose <change>` creates `openspec/changes/<change>/` on a Task Branch | Task → `in_review`; review by `director` or `project-manager` |
| 3. Validate | proposer | `openspec validate <change>` | Must pass before review |
| 4. Approve proposal | `director` / Board for pillar-affecting changes | — | Execution-policy approval stage |
| 5. Break down | `project-manager` | reads `tasks.md` | Creates Paperclip sub-tasks, one per task group |
| 6. Implement | implementers | `/opsx:apply` on the change | development-cycle per sub-task |
| 7. Archive | `project-manager` after merge | `/opsx:archive <change>` merges deltas into `specs/` | Separate small Task and PR |

Rules:
- OpenSpec files live in the **Game Repository** (`openspec/`), never in this repository (OQ-020). The Framework Repository MAY adopt OpenSpec later for Runtime development.
- Spec changes go through Task Branches and PRs like code (ADR-009).
- OpenSpec does not replace Paperclip tasks. `tasks.md` is a checklist inside a change, and Paperclip issues remain the unit of assignment.

## 3. Setup per Game Project (`PROPOSED`)

Run in the Game Repository on an initialization Task Branch, after the dependency is approved:

```bash
openspec init     # interactive: select Claude Code and Codex as tools
```

Then record `specs.tool: openspec` in the project's registry entry. The flags for non-interactive init were not verified. Check `openspec init --help` before scripting it.

## 4. Version note

Installed 1.11.0 is older than the latest 1.16.0. Pin a version in the registry before adoption and run `openspec update` in each Game Repository after upgrading (`update` refreshes instruction files, `VERIFIED` help text).

## Related documents
- [../design/dependency-system.md](../design/dependency-system.md) · [../../knowledge/company/workflows/development-cycle.md](../../knowledge/company/workflows/development-cycle.md) · [../../knowledge/departments/game/agents/game-designer/AGENTS.md](../../knowledge/departments/game/agents/game-designer/AGENTS.md)
