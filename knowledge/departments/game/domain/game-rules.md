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
| Art direction: look, palette, render standards (2026-11-21) | `game-artist` | `game-designer`, within the pillars; `director` when it changes the vision or pillars |

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

## 6. Art assets and technical art
- **Owners.** `game-artist` makes the visual assets and owns their visual quality. `gameplay-programmer` owns everything technical around them: integration, import settings, animation logic, shaders, runtime VFX and asset pipeline tooling. The full interim split, with handoffs, is in the [game-artist role](../agents/game-artist/AGENTS.md#ownership-with-gameplay-programmer-interim) (2026-11-21). A project's own `AGENTS.md` may name a more specific owner; it wins, and a conflict is reported to `project-manager`.
- **Art references live in the project.** Art bible, render standards, palette, asset specs, asset registry and the licensing rule are in each Game Repository, never here. A project that has none yet gets them through a Task before production art starts: `game-artist` drafts them, and they are approved as in §2.
- **Acceptance.** Assets go through the same review as any change: `qa` review on the PR, then Board approval and merge (ADR-009). `game-designer` reviews gameplay readability when the Task's review stage includes it. Nobody approves their own assets.
- **Process.** Request, art, integration, QA and approval steps and their handoffs: [asset-production.md](../workflows/asset-production.md). Lanes, visual procedures, rubric and Task templates: [art/](art/README.md) (`PROPOSED`). They change no authority in §2 and no gate in this section.
- **Technical Artist (not a role yet).** Propose a `technical-artist` role, with evidence, scope, authority and acceptance criteria, only when the interim split stops working, for example:
  - asset pipeline and validation work recurs and competes with gameplay programming;
  - shader, material or VFX implementation becomes a substantial stream of its own;
  - import settings, engine integration or performance work repeatedly block asset delivery;
  - coordination between `game-artist` and `gameplay-programmer` on technical-art Tasks becomes a bottleneck.
