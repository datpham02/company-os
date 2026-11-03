# Company Design

**Contract owner for:** studio organization, hierarchy, reporting, decision authority. The concrete instance lives in [../../company/ORGANIZATION.md](../../company/ORGANIZATION.md).

## 1. Studio model

- One **Studio** = one Paperclip **company** (`PROPOSED`). All Game Projects run inside it as Paperclip projects.
- Agent Roles are studio-wide. Agent Instances are shared across Game Projects by default. A Task's project determines which repository the work touches.
- The **Board Operator** is the only human role in v1 and sits above the agent hierarchy (Paperclip's "board").

## 2. Hierarchy

```text
Board Operator (human, Paperclip board)
└── game-director            Root agent (Paperclip CEO position, OQ-006)
    ├── game-designer        Design authority
    └── producer             Delivery authority
        └── project-manager  Per-project planning and delegation
            ├── gameplay-programmer
            ├── ui-designer
            └── qa
```

Rationale:
- Paperclip requires a strict tree with exactly one root (`VERIFIED`). The root is the studio's top decision-making agent.
- **Design** (what the game is) and **delivery** (how and when it is built) are separate lines so that schedule pressure cannot silently override design intent; conflicts escalate to `game-director`.
- Implementers report to `project-manager` for work intake and escalation; they consult `game-designer` for design questions without a reporting relationship.

## 3. Decision authority

| Decision | Proposes | Decides | Approval gate (human) |
|---|---|---|---|
| Studio vision, which games to make | `game-director` | Board Operator | Yes |
| Create a new Game Project | `game-director` / `producer` | Board Operator | Yes |
| Game vision and pillars (per project) | `game-designer` | `game-director` | Board review recommended |
| Game design documents, mechanics, balance | `game-designer` | `game-designer` (within pillars) | No |
| Scope, milestones, release plan | `producer` | `producer`; scope cuts affecting pillars → `game-director` | Release: yes |
| Task breakdown and assignment | `project-manager` | `project-manager` | No |
| Technical implementation within a Task | `gameplay-programmer` / `ui-designer` | Implementer | No |
| UI/UX design | `ui-designer` | `ui-designer` (within design docs) | No |
| Quality verdict on a change | `qa` | `qa` (review stage) | — |
| Merge to Default Branch | any implementer via PR | **Board Operator** | Yes (ADR-009) |
| Release a version | `producer` | **Board Operator** | Yes |
| Add/upgrade a Dependency | any agent | **Board Operator** | Yes |
| Add an Agent Role or Instance | `game-director` / `producer` | **Board Operator** | Yes (Paperclip `hire_agent`) |
| Change studio rules or ADRs | any | **Board Operator** | Yes |

Agents MUST NOT take decisions outside their row. When unsure, escalate along the reporting line.

## 4. Ownership of artefacts

| Artefact | Owner role | Location |
|---|---|---|
| Studio definition | Board Operator | Framework Repository `company/`, `agents/` |
| Project registry entry | `producer` (maintains), Board Operator (approves) | `projects/project-registry.yaml` |
| Game design docs | `game-designer` | Game Repository (e.g. `docs/design/` or OpenSpec specs) |
| Roadmap and milestones | `producer` | Paperclip goals/projects |
| Tasks | `project-manager` | Paperclip |
| Gameplay code | `gameplay-programmer` | Game Repository |
| UI code and UI specs | `ui-designer` | Game Repository |
| Test plans, bug reports | `qa` | Game Repository / Paperclip tasks |

## 5. Escalation

1. An agent that is blocked or out of authority comments on the Task, sets it to `blocked` (Paperclip status), and @-mentions its manager. A comment mention triggers a heartbeat (`VERIFIED`).
2. The manager resolves or escalates one level up.
3. `game-director` escalates to the Board Operator through a Paperclip approval or confirmation request.
4. Disputes between design and delivery go to `game-director`.

## 6. Mapping to Paperclip

| Game Studio | Paperclip | Notes |
|---|---|---|
| Studio | Company | Goal = studio mission from [COMPANY.md](../../company/COMPANY.md) |
| Agent Role | Agent *title/role* and instructions | Instructions from `agents/<id>/AGENTS.md` |
| Agent Instance | Agent | Adapter type + config chosen per instance |
| Reporting line | `reportsTo` | |
| Game Project | Project (+ project workspace) | Registry stores Paperclip project ID |
| Milestone | Goal (`level: team`) | `PROPOSED` |
| Task | Issue | |
| Approval Gate | Approval, or execution-policy approval stage | |

## Related documents
- [agent-system.md](agent-system.md) · [../../company/ORGANIZATION.md](../../company/ORGANIZATION.md) · [../../company/RULES.md](../../company/RULES.md)
