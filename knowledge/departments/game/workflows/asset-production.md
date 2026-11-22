# Workflow: Asset Production

- **ID:** `asset-production` · **Status:** `PROPOSED` (2026-11-21) · **Owner:** `project-manager` · **Board gate:** yes, through [code-review-and-merge.md](../../../company/workflows/code-review-and-merge.md)
- **Version:** v2 (Art Production v2, Phase 1, 2026-11-22, `PROPOSED`, **Board-assisted pilot**: the Board writes every asset Task from the template until a Board-approved distribution to the project exists): complexity lanes, visual research, exploration, critique and targeted refinement inside steps 3–7, the rubric and the templates in [../domain/art/](../domain/art/README.md). Statuses, gates, ownership and permissions are unchanged.
- **Extends:** the company workflows [task-delegation.md](../../../company/workflows/task-delegation.md), [development-cycle.md](../../../company/workflows/development-cycle.md) and [code-review-and-merge.md](../../../company/workflows/code-review-and-merge.md). It adds the asset handoffs; it never replaces their steps, statuses or approval gates.

Agents cannot read this repository at run time. The parts `game-artist` and `gameplay-programmer` need are repeated in their role files ([game-artist](../agents/game-artist/AGENTS.md), [gameplay-programmer](../agents/gameplay-programmer/AGENTS.md)). The role files of `game-designer`, `project-manager` and `qa` do not carry these steps (Board decision, 2026-11-21): whoever writes an asset Task puts the asset request fields (step 1), the rubric and the routing of findings (step 9) in its description, from [asset-task-template.md](../domain/art/asset-task-template.md). Which role gets which text, and how: [delivery map](../domain/art/README.md#how-agents-get-this-text-delivery-map). Ownership: [game-rules.md §6](../domain/game-rules.md#6-art-assets-and-technical-art).

## Trigger
A milestone, design document, defect or Board request needs a visual asset made, changed or integrated in a game project.

## Required inputs
The asset request (step 1) with its proposed [lane](../domain/art/complexity-lanes.md); the project's art references named in its `AGENTS.md` (art bible, render standards, palette, asset specs, licensing rule), when the project has them.

## Actors
| Role | Part |
|---|---|
| `game-designer` (or the Board, or `producer` for non-design requests) | Writes the asset request: gameplay purpose, readability, acceptance criteria, proposed lane; decides an L2 direction ([game-rules.md §2](../domain/game-rules.md#2-design-authority)) |
| `project-manager` | Turns the request into Tasks, assigns, sets review and approval stages, routes rework |
| `game-artist` | Research, exploration, selection, production, critique and refinement, preflight, handoff |
| `gameplay-programmer` | Engine-side integration and technical-art implementation: engine-side work and shared pipeline code (artwork production scripts for the Task's own assets are `game-artist` art work, inside its write set) |
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
   - open questions that need art-direction input;
   - the proposed lane (L0 fix or variant, L1 new asset, L2 new visual direction) and why ([complexity-lanes.md](../domain/art/complexity-lanes.md));
   - target display size, background, camera and states; the identity invariants, the pose-specific properties the Task may change and any representation being replaced; 3–5 observable reference traits;
   - the iteration budget (default 2 critique-and-refine rounds).
   Output: the request, persisted in the Task or the game repository. Format: [asset-task-template.md](../domain/art/asset-task-template.md) §1.
2. **Task breakdown.** `project-manager` creates the Tasks under the [task contract](../../../company/standards/task-contract.md#2-task-contract):
   - an **art Task** for `game-artist`: write set = the asset files, their provenance records and, if the project has one, the asset registry or spec entries;
   - when the asset must be wired into the game, a separate **integration Task** for `gameplay-programmer`, blocked by the art Task (a Paperclip blocker relation);
   - both with a `review` stage for `qa` and an `approval` stage for the Board Operator. Every other reviewer the Task names (`game-designer` for readability, `director` where the project's art pipeline requires it) is its own Paperclip review stage; a role that is not a stage participant is never asked to review;
   - an L2 direction gets its own Task only when an approval decision gates later production; the internal phases of steps 3–7 are never split into separate issues; a coherent asset family is batched into one Task within the size limit.
   Output: Tasks in `backlog` with intended assignee, write set, acceptance criteria, rubric, routing and reviewers, written from [asset-task-template.md](../domain/art/asset-task-template.md).
3. **Visual research and planning.** `game-artist` reads the request and the project's references, extracts 3–5 observable reference traits and the constraints ([visual-procedures.md §1](../domain/art/visual-procedures.md#1-visual-research-before-any-candidate)), confirms or contests the lane, and posts the plan comment ([handoff-templates.md §1](../domain/art/handoff-templates.md#1-plan-comment-game-artist-before-any-file-is-written)): visual interpretation, references used, constraints, the list of deliverables (files, sizes, frames, variants), method and tools, and any source library it intends to use (for example PixelFX, only under the conditions below). If the request conflicts with the references or cannot be read clearly at the required size, it asks `game-designer` in a comment and does not change the gameplay requirement itself. Output: the plan comment.
4. **Exploration, selection and production.** By lane: L0 reuses the family's proven pattern; L1 compares 2–3 distinct candidates at the target size and on the target background and records why the others fail; L2 compares 3–4 directions at the target size and in a representative composition, and the design authority decides the direction before production, through a direction Task with a `game-designer` review stage (a choice other than the artist's recommendation comes back as `changes_requested` naming it; the artist updates the direction record and resubmits) or, when nothing else waits on it, a `decision` blocker on the same Task ([L2 decision handoff](../domain/art/complexity-lanes.md#l2-decision-handoff), [visual-procedures.md §2–§4](../domain/art/visual-procedures.md#2-concept-exploration-l1-l2)). Candidates stay in the staging folder outside the repository. `game-artist` then creates or revises the source artwork, sprites, sprite sheets, animation frames and art-side metadata on the Task Branch, inside the write set, recording tools and settings. Output: the selection record and commits.
5. **Critique and targeted refinement.** `game-artist` opens the actual images and critiques them at target size and enlarged against the references: each issue located, explained and given an expected correction; only the listed issues fixed, the entity's identity invariants preserved (a targeted refinement also keeps what no issue names, including the silhouette; a new pose, view, state or rig-ready art follows the Task's pose requirement instead of the source silhouette); before and after compared at target size; a fix that breaks an identity invariant is reverted. It stops when the acceptance criteria and hard gates are met or the iteration budget is spent, and reports what remains ([visual-procedures.md §5](../domain/art/visual-procedures.md#5-art-critique-and-targeted-refinement)). Output: before/after evidence and the remaining-issue list.
6. **Preflight and artist self-check.** `game-artist` checks, and lists the result in its Run summary with command output where a command exists, scoring itself against the [rubric](../domain/art/quality-rubric.md):
   - dimensions, frame count and frame order;
   - consistency with the references: style, scale, outline, lighting;
   - palette and render standards;
   - naming and directory layout;
   - transparency and edges;
   - every required variant present;
   - provenance recorded for every new or changed asset;
   - only files in the write set changed.
   A check that cannot run is written `UNVERIFIED`, never passed. This is not an approval. Output: the checklist in the Run summary.
7. **Asset handoff.** `game-artist` updates the project's existing asset registry or spec fields (only where they exist; it never changes their schema), pushes the branch, opens the PR and posts the handoff:
   - the files and where they are;
   - preview evidence for its lane ([complexity-lanes.md](../domain/art/complexity-lanes.md)): at least the selected asset at target size; for L1 and L2 the candidate contact sheet and the reason for the choice; before/after of each refinement round; for L2 the representative scene. Evidence is committed under `art_src/review/<TASK-KEY>/` (or the project's evidence folder) and cited by repository-relative path, so reviewers can open it in the Task Workspace ([where evidence lives](../domain/art/handoff-templates.md#review-evidence-where-it-lives-and-how-reviewers-open-it)); staging paths and written descriptions are not visual evidence: where a preview cannot be made, the handoff says `UNVERIFIED` and why;
   - frame timing intent and pivot or origin, for animated assets;
   - known limitations;
   - handoff status: `ready for integration` or `art only`.
   Format: [handoff-templates.md §2](../domain/art/handoff-templates.md#2-art-handoff-game-artist-with-the-pr). It moves the Task to `in_review`. Output: the PR and the handoff comment.
8. **Technical integration.** After the art Task is merged, `gameplay-programmer` runs the integration Task: engine import settings and resource configuration, animation state machine and runtime logic, shaders, materials and runtime VFX, shared asset pipeline code, technical validation and in-engine performance. When a technical constraint needs a source-art change or a visual trade-off, it comments to `game-artist` (and to `game-designer` if gameplay readability is affected) instead of redrawing the asset. Its handoff cites in-engine screenshots, or frames for motion, at every preview state and resolution the integration Task lists, committed under `art_src/review/<TASK-KEY>/` (game-UI Tasks: frames left in the Task Workspace, see the evidence table) ([handoff-templates.md §3](../domain/art/handoff-templates.md#3-integration-handoff-gameplay-programmer)). Output: the integration PR.
9. **QA and acceptance.** Acceptance has three stages with their own hard gates: art-ready (art Task), integration-ready (integration Task) and verified; only in-context checks may be deferred, each to a named integration Task, and stay `UNVERIFIED` until it validates them ([quality-rubric.md, acceptance stages](../domain/art/quality-rubric.md#acceptance-stages)). `qa` reviews each PR under [code-review-and-merge.md](../../../company/workflows/code-review-and-merge.md) against the Task's acceptance criteria and the rubric copied into the Task description (hard gates first; missing evidence is `UNVERIFIED`, not a pass; a 0 in art direction, craft or coherence also means changes requested unless the design authority records an exception, [quality-rubric.md §2](../domain/art/quality-rubric.md#2-scored-categories-02)), at the required sizes and states, and records the decision. Findings carry location, expected, actual, severity, evidence and owner ([quality-rubric.md §3](../domain/art/quality-rubric.md#3-writing-a-finding)). Routing of findings:
   - wrong look, size, frames, palette, provenance → art Task, `game-artist`;
   - wrong in-game behaviour, import, timing logic, shader, performance → integration Task, `gameplay-programmer`;
   - the requirement itself is unclear or wrong → `game-designer`.
   "Changes requested" returns the Task to its author on the same branch. A defect found after merge: `qa` files a new Task in `backlog` with the intended assignee from this routing.
10. **Approval and closeout.** The Board Operator approves and merges each PR (ADR-009). Nobody approves their own asset or integration. `project-manager` closes the request when both Tasks are `done`.

## Generated art (Board decisions D1 and 2026-11-22)
- `comfy-draft.py` makes text-to-image candidates with the two approved models only, no input images, into the staging folder outside the repository (D1, [security-architecture.md §4](../../../../docs/architecture/security-architecture.md#4-agent-permissions-provider-level)). Since 2026-11-22 the Board accepts AI-made final art: a candidate becomes final art through selection, regeneration for consistency and the approved `art-ops.py` operations, then the review stages and Board approval (recorded in the [game-artist role](../agents/game-artist/AGENTS.md#tools-and-skills)). Each project's licensing rule still decides whether AI-made art may enter it.
- Editing our own art (Board decision 2026-11-22, Phase 2A stage 1): `comfy-edit.py img2img` (SDXL or FLUX, denoise 0.15–0.75) and `inpaint` (SDXL only, through an `art-ops mask`; pixels outside the mask restored exactly), on the project's own art only. Cut-outs (Board decision 2026-11-22, after spike S7): `comfy-edit.py matte` cuts figures out with BiRefNet. All three are installed and allowed for `game-artist` ([security-architecture.md §4](../../../../docs/architecture/security-architecture.md#4-agent-permissions-provider-level), [game-artist role](../agents/game-artist/AGENTS.md#tools-and-skills)). Not approved: reference images from outside the project, image-prompt adapters, LoRA, ControlNet, FLUX inpainting. Targeted refinement therefore means the smallest change that fixes the issue: the deterministic `art-ops.py` operations, `inpaint` for one region, `img2img` at low denoise for family consistency, or regeneration. A new tool needs its own registry entry, review and Board approval ([visual-procedures.md §9](../domain/art/visual-procedures.md#9-tools-today-and-known-gaps), [OQ-049](../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)).

## Using PixelFX (optional source library)
[PixelFX](https://github.com/patch-gg/pixelfx) is `approved` in [dependencies/registry.yaml](../../../../dependencies/registry.yaml) (Board, 2026-11-21, after a security review at commit 5294518). Installed by the Board at `$HOME/tools/pixelfx` (registry entry `integrated`). `game-artist`'s allowlist allows only its `list.mjs` and `render.mjs` from there. Rules:
- `game-artist` may search and preview effects during visual planning (step 3), and decides to use, adapt or reject each one against the request and the project's references;
- it exports only the effects the Task needs, as sprite sheets, never the whole library, and never adds PixelFX as a package of the game;
- each exported effect gets a provenance record: PixelFX, the reviewed commit, the effect path, the licence (MIT; some effects carry the Sprite Fusion notice in `NOTICE.md`), and the changes made;
- the bundled Patch Pixel font is never used (it is not under the MIT licence);
- it is used only in a project whose licensing rule allows MIT assets with attribution. Lamplight Vigil's rule allows only original work or CC0, so PixelFX output cannot go into it unless the Board changes that rule;
- engine import of the sheet (frame rects, durations, pivot, loop) is the integration Task (step 8);
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
| The asset needs a technical change (import, shader, shared pipeline code) | `game-artist` | Hand off to the integration Task; do not implement it |
| Engine constraint makes the art unusable | `gameplay-programmer` at step 8 | Comment to `game-artist` with the constraint; a follow-up art Task |
| Registry schema cannot hold a needed field | Any | Write a proposal; schema changes need the Board's approval and a `gameplay-programmer` Task |
| The best candidate is outside the approved direction | `game-artist` at step 4 | Do not produce it; propose it as an L2 decision to `game-designer` (`director` when it changes vision or pillars) |
| Iteration budget spent with defects left | `game-artist` at step 5 | Hand off with the defects listed; if one fails a hard gate, `blocked` (type `decision`, owner `project-manager`) |
| A required visual check cannot run with the approved tools | Any | Report it `UNVERIFIED` with the reason; `blocked` (type `environment`, owner Board) when it prevents acceptance |
| The work outgrows its lane | `game-artist` | Comment, and continue only on the new lane's requirements ([complexity-lanes.md](../domain/art/complexity-lanes.md) rule 3) |

## Pilot and measurement
v2 is a Board-assisted pilot until the Board accepts it: the Board writes the asset Tasks, so the pilot measures art quality and review flow, not autonomous planning. Run it on one project with a small representative set (a character or prop, a tile or environment piece, a UI screen, an effect), with the same brief, references and budget as a comparable earlier Task where one exists. Record per accepted asset: first-pass acceptance, reasons for rejection, refinement rounds, run time and spend, in-engine defects and integration rework, and the sample size. Success: no hard-gate regression, and fewer review rounds or less rework at an acceptable cost. Do not claim an improvement before it is measured. Lane sizes, the iteration budget and the rubric are recalibrated from the result. Pilot project, readiness items and the Phase 1 exit gate G8 (metrics for every Task, including failed ones, reported to the Board to order Phase 2): [art-production-v2-pilot.md](../../../../docs/roadmap/art-production-v2-pilot.md).

## Related
[../README.md](../README.md) · [../domain/game-rules.md](../domain/game-rules.md) · [../domain/art/](../domain/art/README.md) · [new-game-concept.md](new-game-concept.md) · [../../../company/standards/task-contract.md](../../../company/standards/task-contract.md)
