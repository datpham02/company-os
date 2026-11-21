# Organization

Instance of [company-design.md](../../docs/design/company-design.md). If this file and the design document disagree, the design document wins.

## Org chart

```text
Board Operator (human)
└── director                         Company · root agent · head of every department
    ├── game-designer                Game
    └── producer                     Company (shared)
        └── project-manager          Company (shared)
            ├── gameplay-programmer  Game
            ├── game-artist          Game
            ├── web-engineer         Web
            ├── ui-designer          Company (shared: Game and Web)
            └── qa                   Company (shared: Game and Web)
```

## Roster

Providers are those of the live company **Soucean** (`SOU`, imported 2026-11-05 from [config/paperclip/agents.json](../../config/paperclip/agents.json)). The allocation rule is in [policies/provider-allocation.md](policies/provider-allocation.md) (ADR-015, proposed).

| Agent ID | Scope | Reports to | Definition | Provider | Permission profile |
|---|---|---|---|---|---|
| `director` | Company | Board Operator (Paperclip root) | [AGENTS.md](agents/director/AGENTS.md) | `claude_local` | read-only |
| `producer` | Company | `director` | [AGENTS.md](agents/producer/AGENTS.md) | `claude_local` | read-only |
| `project-manager` | Company | `producer` | [AGENTS.md](agents/project-manager/AGENTS.md) | `claude_local` | read-only |
| `ui-designer` | Company (Game, Web) | `project-manager` | [AGENTS.md](agents/ui-designer/AGENTS.md) | `claude_local` | workspace-write |
| `qa` (`qa-engineer` in Paperclip) | Company (Game, Web) | `project-manager` | [AGENTS.md](agents/qa/AGENTS.md) | `claude_local` | workspace-write |
| `code-reviewer` | Company (Review Package pilot, `PROPOSED`) | Board Operator (no agent manages it) | [AGENTS.md](agents/code-reviewer/AGENTS.md) | `claude_local` | reviewer-strict (Read, Grep, Glob only; not in the live company until P6-B) |
| `game-designer` | Game | `director` | [AGENTS.md](../departments/game/agents/game-designer/AGENTS.md) | `claude_local` | workspace-write |
| `gameplay-programmer` | Game | `project-manager` | [AGENTS.md](../departments/game/agents/gameplay-programmer/AGENTS.md) | `cursor` | workspace-write |
| `game-artist` | Game | `project-manager` | [AGENTS.md](../departments/game/agents/game-artist/AGENTS.md) | `claude_local` | workspace-write (asset files only; created in Soucean 2026-11-21, idle, not run yet) |
| `web-engineer` | Web | `project-manager` | [AGENTS.md](../departments/web/agents/web-engineer/AGENTS.md) | `cursor` | workspace-write (dev/test environments only, ADR-014) |

Provider is a property of the Agent Instance, not of the role (ADR-008).

## Planned roles (not defined yet)
Each via [agent-onboarding.md](workflows/agent-onboarding.md), when workload requires it:
- Company: `release-manager`; a department lead under `director` when a department has three or more roles of its own.
- Game: `technical-director`, `engine-programmer`, `art-director`, `technical-artist` (only on the evidence in [game-rules.md §6](../departments/game/domain/game-rules.md#6-art-assets-and-technical-art)), `audio-designer`, `narrative-designer`.
- Web: `devops-engineer` (more than one platform or self-hosted infrastructure, ADR-014).

## Change control
Adding, removing or changing a role's reporting line requires Board approval and an update to this file, the department charter and [agent-system.md §6](../../docs/design/agent-system.md#6-defined-roles-v1).
