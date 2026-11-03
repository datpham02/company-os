# Organization

Instance of [../docs/design/company-design.md](../docs/design/company-design.md). If this file and the design document disagree, the design document wins.

## Org chart

```text
Board Operator (human)
└── game-director
    ├── game-designer
    └── producer
        └── project-manager
            ├── gameplay-programmer
            ├── ui-designer
            └── qa
```

## Roster

| Agent ID | Title | Reports to | Definition | Default Provider (Stage 1) | Permission profile |
|---|---|---|---|---|---|
| `game-director` | Game Director | Board Operator (Paperclip root/CEO) | [AGENTS.md](../agents/game-director/AGENTS.md) | `claude_local` | read-only |
| `producer` | Producer | `game-director` | [AGENTS.md](../agents/producer/AGENTS.md) | `claude_local` | read-only |
| `project-manager` | Project Manager | `producer` | [AGENTS.md](../agents/project-manager/AGENTS.md) | `claude_local` | read-only |
| `game-designer` | Game Designer | `game-director` | [AGENTS.md](../agents/game-designer/AGENTS.md) | `claude_local` | workspace-write |
| `gameplay-programmer` | Gameplay Programmer | `project-manager` | [AGENTS.md](../agents/gameplay-programmer/AGENTS.md) | `claude_local` or `codex_local` | workspace-write |
| `ui-designer` | UI Designer | `project-manager` | [AGENTS.md](../agents/ui-designer/AGENTS.md) | `claude_local` | workspace-write |
| `qa` | QA Engineer | `project-manager` | [AGENTS.md](../agents/qa/AGENTS.md) | `codex_local` | workspace-write |

"Default Provider" is a starting suggestion for Agent Instance registration, not a property of the role (ADR-008). Mixing providers lets the studio compare them and gives `qa` an independent provider from most implementers.

## Planned roles (not defined yet)
Candidates when workload requires them, each via [agent-onboarding.md](../workflows/agent-onboarding.md): `technical-director`, `engine-programmer`, `artist` / `art-director`, `audio-designer`, `narrative-designer`, `release-manager`.

## Change control
Adding, removing, or changing a role's reporting line requires Board approval and an update to this file and [../docs/design/agent-system.md §6](../docs/design/agent-system.md#6-defined-roles-v1).
