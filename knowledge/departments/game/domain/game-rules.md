# Game Rules

- **Status:** `APPROVED`. Moved from company rule R7.1 and the former game studio design documents on 2026-11-05 ([ADR-019](../../../../docs/decisions/ADR-019-knowledge-tree-and-departments.md)).
- **Applies to:** every Task in a project with `type: game`.

Agents cannot read this repository at run time, so each game role file repeats the rules that it needs.

## 1. Originality
1. Build original games. Do not recreate a specific existing commercial game, even renamed: not its name, characters, art, music, levels or look.
2. Genres, mechanics and conventions are free to use. A concept that is "game X with new art" is not.

## 2. Design authority
| Decision | Proposes | Decides |
|---|---|---|
| Which games to make | `director` | Board Operator |
| Game vision and pillars | `game-designer` | `director` (Board review recommended) |
| Design documents, mechanics, balance | `game-designer` | `game-designer`, within the pillars |
| Tuning values in data files | `game-designer` | `game-designer`; only in files the game's `AGENTS.md` designates for tuning |
| Scope cuts that affect pillars | `producer` | `director` |

## 3. Default hotspot files
Files that only one Task may change at a time ([task-contract.md §3](../../../company/standards/task-contract.md#3-splitting-work)). Each game's `AGENTS.md` lists its real hotspots; for a Phaser + TypeScript game the defaults are:
- the main game scene (for example `src/scenes/*Scene.ts` that wires systems together);
- game configuration and tuning tables (for example `src/config/*`);
- `package.json` and lock files;
- shared types used by most systems.

## 4. Testability
Every design document contains acceptance criteria that `qa` can test. Balance changes come with a simulation or a reproducible play check when the game has one (for example `npm run sim`).

## 5. Platform boundary
Games never depend on a platform's source code, never contain ads or ad hooks, and use only the published [game platform contract](../../../company/shared/game-platform-contract.md).
