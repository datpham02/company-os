# Game Department

- **Status:** `APPROVED` as the department for every project with `type: game`.
- **Head:** `director` (company-wide, [ADR-019](../../../docs/decisions/ADR-019-knowledge-tree-and-departments.md)). No separate department lead yet.
- **Audience:** agents and humans working on game projects. Company-wide rules in [../../company/README.md](../../company/README.md) apply first.

## Mission
Design, build and ship original games of any genre the Board approves, with every change reviewed and every release approved by the Board.

## Values (in addition to the company values)
1. **Player experience first.** Design intent beats schedule pressure; conflicts escalate to `director`.
2. **Original work only.** Never a recreation of an existing commercial game, even renamed ([game-rules.md](domain/game-rules.md)).
3. **Playable early.** Every milestone ends with something a person can play.

## Scope
- In scope: original games; prototypes; tooling and simulations that games need (for example balance simulations).
- Out of scope: game source code in the framework repository ([ADR-001](../../../docs/decisions/ADR-001-single-game-studio-repository.md), [ADR-005](../../../docs/decisions/ADR-005-independent-game-repositories.md)); ads or ad hooks inside a game ([game-platform-contract.md](../../company/shared/game-platform-contract.md)).

## Roles

| Role | Scope | Definition |
|---|---|---|
| `game-designer` | Game only | [agents/game-designer](agents/game-designer/AGENTS.md) |
| `gameplay-programmer` | Game only | [agents/gameplay-programmer](agents/gameplay-programmer/AGENTS.md) |
| `game-artist` | Game only | [agents/game-artist](agents/game-artist/AGENTS.md) |
| `director` | Company (head of this department) | [director](../../company/agents/director/AGENTS.md) |
| `producer`, `project-manager`, `ui-designer`, `qa` | Company (shared) | [company agents](../../company/agents/) |

## Workflows
- Company workflows apply to every game Task ([index](../../company/workflows/README.md)).
- [new-game-concept.md](workflows/new-game-concept.md): the game part of creating a project.
- [asset-production.md](workflows/asset-production.md): asset request, research, exploration, critique and refinement, integration, QA and approval, with complexity lanes (`PROPOSED`, v2 2026-11-22).

## Domain knowledge
- [game-rules.md](domain/game-rules.md): originality, design authority, default hotspot files, review gates, art assets and the interim technical-art split.
- [domain/art/](domain/art/README.md): art complexity lanes, visual procedures, quality rubric, asset Task and handoff templates, and the map of how each role receives them (`PROPOSED`).

## Review gates
| Work | Reviewer | Board |
|---|---|---|
| Vision and pillars | `director` | Review recommended |
| Design documents and tuning tables | `director` (design), `qa` (testability) | Approval stage on the Task |
| Code | `qa`, on a different provider from the author where possible | Approval and merge (ADR-009) |
| Art assets | `qa` (acceptance, visual defects); `game-designer` (readability) when the Task's review stage includes it | Approval and merge (ADR-009) |

## Projects
| Project | Status | Registry |
|---|---|---|
| Lamplight Vigil | active | [knowledge/projects/lamplight-vigil](../../projects/lamplight-vigil/README.md) |
| Deckbound | initializing | [knowledge/projects/deckbound](../../projects/deckbound/README.md) |

## Related
[../README.md](../README.md) · [../../company/ORGANIZATION.md](../../company/ORGANIZATION.md) · [../../company/shared/game-platform-contract.md](../../company/shared/game-platform-contract.md)
