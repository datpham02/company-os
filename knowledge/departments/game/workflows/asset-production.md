# Workflow: Asset Production

- **ID:** `asset-production` · **Status:** `PROPOSED` (2026-11-21) · **Owner:** `project-manager` · **Board gate:** yes, through [code-review-and-merge.md](../../../company/workflows/code-review-and-merge.md)
- **Extends:** the company workflows [task-delegation.md](../../../company/workflows/task-delegation.md), [development-cycle.md](../../../company/workflows/development-cycle.md) and [code-review-and-merge.md](../../../company/workflows/code-review-and-merge.md). It adds the asset handoffs; it never replaces their steps, statuses or approval gates.

Agents cannot read this repository at run time. The parts `game-artist` and `gameplay-programmer` need are repeated in their role files ([game-artist](../agents/game-artist/AGENTS.md), [gameplay-programmer](../agents/gameplay-programmer/AGENTS.md)). The role files of `game-designer`, `project-manager` and `qa` do not carry these steps (Board decision, 2026-11-21): whoever writes an asset Task puts the asset request fields (step 1) and the routing of findings (step 8) in its description. Ownership: [game-rules.md §6](../domain/game-rules.md#6-art-assets-and-technical-art).

## Trigger
A milestone, design document, defect or Board request needs a visual asset made, changed or integrated in a game project.

## Required inputs
The asset request (step 1); the project's art references named in its `AGENTS.md` (art bible, render standards, palette, asset specs, licensing rule), when the project has them.

## Actors
| Role | Part |
|---|---|
| `game-designer` (or the Board, or `producer` for non-design requests) | Writes the asset request: gameplay purpose, readability, acceptance criteria |
| `project-manager` | Turns the request into Tasks, assigns, sets review and approval stages, routes rework |
| `game-artist` | Visual planning, asset creation, self-check, handoff |
| `gameplay-programmer` | Engine-side integration and all technical-art implementation |
| `qa` | Independent review against the acceptance criteria; files defects |
| Board Operator | Approval and merge (ADR-009) |

## Preconditions
- The project is a game project and `game-artist` is an enabled role for it.
- The project's licensing rule for assets is known (its `AGENTS.md`). Without one, production art does not start: the step 1 actor stops and asks the Board for the rule.
- `game-artist` is listed in the project's `agents` in [registry.yaml](../../../projects/registry.yaml). Adding it is a registry change the Board approves (on 2026-11-21 no project lists it).

## Steps
1. **Asset request.** `game-designer` writes, in a design document or in the Task description, for each asset:
   - gameplay purpose and where it appears in play;
   - visual intent and readability requirements (what the player must notice, at what size and speed);
   - target dimensions, frame counts, animation states and variants, when known;
   - references and style constraints;
   - priority and acceptance criteria;
   - open questions that need art-direction input.
   Output: the request, persisted in the Task or the game repository.
2. **Task breakdown.** `project-manager` creates the Tasks under the [task contract](../../../company/standards/task-contract.md#2-task-contract):
   - an **art Task** for `game-artist`: write set = the asset files, their provenance records and, if the project has one, the asset registry or spec entries;
   - when the asset must be wired into the game, a separate **integration Task** for `gameplay-programmer`, blocked by the art Task (a Paperclip blocker relation);
   - both with a `review` stage for `qa` and an `approval` stage for the Board Operator.
   Output: Tasks in `backlog` with intended assignee, write set, acceptance criteria and reviewer.
3. **Visual planning.** `game-artist` reads the request and the project's references and posts a short plan as a Task comment: visual interpretation, references used, constraints, the list of deliverables (files, sizes, frames, variants), and any source library it intends to use (for example PixelFX, only under the conditions below). If the request conflicts with the references or cannot be read clearly at the required size, it asks `game-designer` in a comment and does not change the gameplay requirement itself. Output: the plan comment.
4. **Asset creation.** `game-artist` creates or revises the source artwork, sprites, sprite sheets, animation frames and art-side metadata on the Task Branch, inside the write set. Output: commits.
5. **Artist self-check.** `game-artist` checks, and lists the result in its Run summary:
   - dimensions, frame count and frame order;
   - consistency with the references: style, scale, outline, lighting;
   - palette and render standards;
   - naming and directory layout;
   - transparency and edges;
   - every required variant present;
   - provenance recorded for every new or changed asset.
   This is not an approval. Output: the checklist in the Run summary.
6. **Asset handoff.** `game-artist` updates the project's existing asset registry or spec fields (only where they exist; it never changes their schema), pushes the branch, opens the PR and posts the handoff:
   - the files and where they are;
   - preview evidence (a contact sheet or screenshot where its tools allow it, otherwise each file with its dimensions and what it shows);
   - frame timing intent and pivot or origin, for animated assets;
   - known limitations;
   - handoff status: `ready for integration` or `art only`.
   It moves the Task to `in_review`. Output: the PR and the handoff comment.
7. **Technical integration.** After the art Task is merged, `gameplay-programmer` runs the integration Task: engine import settings and resource configuration, animation state machine and runtime logic, shaders, materials and runtime VFX, asset pipeline scripts, technical validation and in-engine performance. When a technical constraint needs a source-art change or a visual trade-off, it comments to `game-artist` (and to `game-designer` if gameplay readability is affected) instead of redrawing the asset. Output: the integration PR.
8. **QA and acceptance.** `qa` reviews each PR under [code-review-and-merge.md](../../../company/workflows/code-review-and-merge.md) against the Task's acceptance criteria, and records the decision. Routing of findings:
   - wrong look, size, frames, palette, provenance → art Task, `game-artist`;
   - wrong in-game behaviour, import, timing logic, shader, performance → integration Task, `gameplay-programmer`;
   - the requirement itself is unclear or wrong → `game-designer`.
   "Changes requested" returns the Task to its author on the same branch. A defect found after merge: `qa` files a new Task in `backlog` with the intended assignee from this routing.
9. **Approval and closeout.** The Board Operator approves and merges each PR (ADR-009). Nobody approves their own asset or integration. `project-manager` closes the request when both Tasks are `done`.

## Using PixelFX (optional source library)
[PixelFX](https://github.com/patch-gg/pixelfx) is `approved` in [dependencies/registry.yaml](../../../../dependencies/registry.yaml) (Board, 2026-11-21, after a security review at commit 5294518). Installed by the Board at `$HOME/tools/pixelfx` (registry entry `integrated`). `game-artist`'s allowlist allows only its `list.mjs` and `render.mjs` from there. Rules:
- `game-artist` may search and preview effects during visual planning (step 3), and decides to use, adapt or reject each one against the request and the project's references;
- it exports only the effects the Task needs, as sprite sheets, never the whole library, and never adds PixelFX as a package of the game;
- each exported effect gets a provenance record: PixelFX, the reviewed commit, the effect path, the licence (MIT; some effects carry the Sprite Fusion notice in `NOTICE.md`), and the changes made;
- the bundled Patch Pixel font is never used (it is not under the MIT licence);
- it is used only in a project whose licensing rule allows MIT assets with attribution. Lamplight Vigil's rule allows only original work or CC0, so PixelFX output cannot go into it unless the Board changes that rule;
- engine import of the sheet (frame rects, durations, pivot, loop) is the integration Task (step 7);
- review and approval do not change: `qa` review, then the Board.

## Expected outputs
Merged asset PR with provenance; merged integration PR when needed; registry or spec entries updated where the project has them; Tasks `done`.

## Approval requirements
Board approval and merge of every PR (ADR-009), recorded in Paperclip and GitHub. `qa` review is required and never replaced by the creator's self-check. Changing the project's art direction follows [game-rules.md §2](../domain/game-rules.md#2-design-authority).

## Failure cases
| Failure | Detection | Response |
|---|---|---|
| Request lacks purpose, size or acceptance criteria | `game-artist` at step 3 | Comment the exact question; `blocked` (type `decision`, owner `game-designer`) |
| The project has no art references | `game-artist` at step 3 | `blocked` (type `decision`, owner `project-manager`); a reference Task first, approved as in game-rules §2 |
| Licence of a source asset unknown or not allowed by the project | `game-artist` or `qa` | Do not add the asset; `blocked` (type `decision`, owner Board) |
| The asset needs a technical change (import, shader, pipeline) | `game-artist` | Hand off to the integration Task; do not implement it |
| Engine constraint makes the art unusable | `gameplay-programmer` at step 7 | Comment to `game-artist` with the constraint; a follow-up art Task |
| Registry schema cannot hold a needed field | Any | Write a proposal; schema changes need the Board's approval and a `gameplay-programmer` Task |

## Related
[../README.md](../README.md) · [../domain/game-rules.md](../domain/game-rules.md) · [new-game-concept.md](new-game-concept.md) · [../../../company/standards/task-contract.md](../../../company/standards/task-contract.md)
