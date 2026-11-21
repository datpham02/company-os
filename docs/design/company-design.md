# Company Design

**Contract owner for:** company organization, departments, hierarchy, reporting, decision authority. The concrete instance lives in [../../knowledge/company/ORGANIZATION.md](../../knowledge/company/ORGANIZATION.md).

## 1. Company model

- One **Company** = one Paperclip **company**. Every project, of every department, runs inside it as a Paperclip project.
- **Departments** (Game, Web) own their specialist roles, rules and knowledge ([../../knowledge/departments/README.md](../../knowledge/departments/README.md)). Company Core owns everything shared ([../../knowledge/company/README.md](../../knowledge/company/README.md)).
- Company roles serve every department; department roles serve their department's projects. Agent Instances are shared across projects by default. A Task's project determines which repository the work touches.
- The **Board Operator** is the only human role in v1 and sits above the agent hierarchy (Paperclip's "board").

## 2. Hierarchy

```text
Board Operator (human, Paperclip board)
└── director                 Root agent, head of every department (ADR-019)
    ├── game-designer        Design authority for games
    └── producer             Delivery authority
        └── project-manager  Per-project planning and delegation
            ├── gameplay-programmer   Game
            ├── game-artist           Game
            ├── web-engineer          Web
            ├── ui-designer           Game and Web
            └── qa                    Game and Web
```

Rationale:
- Paperclip requires a strict tree with exactly one root (`VERIFIED`). The root is the company's top decision-making agent and leads every department until a department gets its own lead.
- **Design** (what the product is) and **delivery** (how and when it is built) are separate lines so that schedule pressure cannot silently override design intent; conflicts escalate to `director`.
- Implementers report to `project-manager` for work intake and escalation; they consult `game-designer` for design questions without a reporting relationship.

## 3. Decision authority

| Decision | Proposes | Decides | Approval gate (human) |
|---|---|---|---|
| Company vision, which products to make | `director` | Board Operator | Yes |
| Create a new project | `director` / `producer` | Board Operator | Yes |
| Department-specific design decisions | see the charter | [Game](../../knowledge/departments/game/domain/game-rules.md#2-design-authority), [Web](../../knowledge/departments/web/README.md) | — |
| Scope, milestones, release plan | `producer` | `producer`; scope cuts affecting pillars → `director` | Release: yes |
| Task breakdown and assignment | `project-manager` | `project-manager` | No |
| Technical implementation within a Task | `gameplay-programmer` / `ui-designer` | Implementer | No |
| UI/UX design | `ui-designer` | `ui-designer` (within design docs) | No |
| Look of a game asset | `game-artist` | `game-artist` (within the project's art direction); art direction → `game-designer`, or `director` when it changes the pillars | No |
| Quality verdict on a change | `qa` | `qa` (review stage) | — |
| Merge to Default Branch | any implementer via PR | **Board Operator** | Yes (ADR-009) |
| Release a version | `producer` | **Board Operator** | Yes |
| Add/upgrade a Dependency | any agent | **Board Operator** | Yes |
| Add an Agent Role or Instance | `director` / `producer` | **Board Operator** | Yes (Paperclip `hire_agent`) |
| Change company rules or ADRs | any | **Board Operator** | Yes |

Agents MUST NOT take decisions outside their row. When unsure, escalate along the reporting line.

## 4. Ownership of artefacts

| Artefact | Owner role | Location |
|---|---|---|
| Studio definition | Board Operator | Framework Repository `knowledge/company/`, `knowledge/company/agents/` |
| Project registry entry | `producer` (maintains), Board Operator (approves) | `knowledge/projects/registry.yaml` |
| Game design docs | `game-designer` | Game Repository (e.g. `docs/design/` or OpenSpec specs) |
| Roadmap and milestones | `producer` | Paperclip goals/projects |
| Tasks | `project-manager` | Paperclip |
| Gameplay code | `gameplay-programmer` | Game Repository |
| UI code and UI specs | `ui-designer` | Game Repository |
| Visual assets and their provenance | `game-artist` | Game Repository |
| Test plans, bug reports | `qa` | Game Repository / Paperclip tasks |

## 5. Escalation

1. An agent that is blocked or out of authority comments on the Task, sets it to `blocked` (Paperclip status), and @-mentions its manager. A comment mention triggers a heartbeat (`VERIFIED`).
2. The manager resolves or escalates one level up.
3. `director` escalates to the Board Operator through a Paperclip approval or confirmation request.
4. Disputes between design and delivery go to `director`.

## 6. Mapping to Paperclip

| Game Studio | Paperclip | Notes |
|---|---|---|
| Studio | Company | Goal = studio mission from [COMPANY.md](../../knowledge/company/COMPANY.md) |
| Agent Role | Agent *title/role* and instructions | Instructions from `knowledge/company/agents/<id>/AGENTS.md` |
| Agent Instance | Agent | Adapter type + config chosen per instance |
| Reporting line | `reportsTo` | |
| Game Project | Project (+ project workspace) | Registry stores Paperclip project ID |
| Milestone | Goal (`level: team`) | `PROPOSED` |
| Task | Issue | |
| Approval Gate | Approval, or execution-policy approval stage | |

## Related documents
- [agent-system.md](agent-system.md) · [../../knowledge/company/ORGANIZATION.md](../../knowledge/company/ORGANIZATION.md) · [../../knowledge/company/policies/rules.md](../../knowledge/company/policies/rules.md)
