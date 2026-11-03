# ADR-001: Single Game Studio Repository

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-005, ADR-007

## Context
The studio needs one place that defines its organization, agent roles, rules, workflows, project registry, dependency registry, integrations, and Runtime. Spreading these across game repositories would duplicate the framework in every game and let definitions drift.

## Decision
- There MUST be exactly one framework repository: `datpham02/game-studio`.
- It MUST contain the studio definition (company, agents, workflows), the project registry, the dependency registry, integration contracts, documentation, and the Agent Runtime source.
- It MUST NOT contain game source code, game assets, or copies of external projects.
- Game repositories MUST NOT contain copies of the framework. They MAY contain project-local configuration and instructions (for example an `AGENTS.md`) that reference the framework.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Framework copied into each game repository | Duplication, drift, and per-game upgrades. |
| Monorepo with framework and all games | Couples unrelated games; breaks per-game access control and history (see ADR-005). |
| Framework split into several repositories | Premature for a single-operator studio; adds versioning overhead. |

## Consequences
- Framework upgrades happen in one place and apply to all games.
- Game repositories need a way to know which framework version they were set up with (see [project-system.md](../design/project-system.md)).
- The Runtime must resolve game repositories from the registry instead of assuming they are nearby.

## Reconsider when
- The Runtime grows large enough to need its own release cycle, or
- several independent studios want to share the framework with different organizations.
