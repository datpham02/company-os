# ADR-005: Independent Game Repositories

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-001, ADR-006, [project-system.md](../design/project-system.md)

## Context
The studio will build several unrelated games, e.g. `node-arena` and `card-battle`. Each has its own engine, history, releases, and possibly collaborators.

## Decision
- Each game MUST have its own Git repository, e.g. `datpham02/node-arena`.
- Game source code and assets MUST live only in that game's repository.
- The Framework Repository references games only through [projects/project-registry.yaml](../../projects/project-registry.yaml).
- An agent working on one Game Project MUST NOT read from or write to another Game Project's repository unless the Task explicitly requires it and the Board Operator approves.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Monorepo of all games | Coupled history and permissions; large clones; cross-game leakage. |
| Games as subdirectories of the framework | Violates ADR-001. |
| Git submodules of games in the framework | Couples framework commits to game commits; confusing for agents. |

## Consequences
- The Runtime must resolve a Project ID to a repository and local path.
- Each repository needs its own access credentials and branch protection.
- Cross-game shared code, if ever needed, must become its own library repository and be registered as a Dependency.

## Reconsider when
- Games start sharing substantial code that cannot be extracted into a library.
