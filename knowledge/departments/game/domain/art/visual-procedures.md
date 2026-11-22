# Visual Procedures: Research, Exploration, Critique and Refinement

- **Status:** `PROPOSED` (2026-11-22, Art Production v2, Phase 1).
- **Used by:** `game-artist` (the role file carries the compact version), `ui-designer` (§7), reviewers through the [rubric](quality-rubric.md).
- **Tools:** only those the role file and the permission layer allow. §8 maps each step to the tools that exist today and lists the gaps; a gap is not permission to improvise a tool.

These are the internal phases of one art Task (steps 3–6 of [asset-production.md](../../workflows/asset-production.md#steps)). Their depth depends on the [lane](complexity-lanes.md).

## 1. Visual research (before any candidate)
1. Read the references the Task's `## Read set` names: the project's art bible, render standards, palette, asset specs, approved golden references and existing assets of the same family. Read the licence rule in the project's `AGENTS.md`.
2. Write down 3–5 **concrete** traits the new asset must share with them, each one observable: for example "2 px dark outline, no inner outlines", "light from top-left, one shadow tone", "head is 1/3 of height", "warm palette ramp of 4 values", "silhouette readable as a single dark shape at 32 px". "Same style" is not a trait.
3. Write down the constraints: target display size and background, camera and angle, scale against the player character or tile grid, frame count, states, budget.
4. Record where each reference came from (project file path, or `original`). External images are mood only: describe what they show in words, never copy, trace, or feed them to a generator, and never name another game, studio, artist or character in a prompt.
5. Missing or contradictory direction: stop, ask in a comment, and set the Task `blocked` (type `decision`, owner `game-designer`; owner `project-manager` when the project has no art references at all, which needs a reference Task first).

## 2. Concept exploration (L1, L2)
1. Make candidates that differ in a way that matters: silhouette, proportion, shape language, value structure, or layout. Two colour swaps of one drawing are one candidate.
2. Judge every candidate **at target display size, on the target background**, and, for L2, in a representative composition (next to the player character, on the real tile set, in the HUD). Enlarged views find craft defects; they do not prove readability.
3. Quick checks at target size: is the silhouette identifiable as a flat dark shape? Is the focal point where the gameplay purpose needs the eye? Do the values separate it from the background? Does it read as the same family as its neighbours?
4. Keep raw candidates in the staging folder, outside the repository; commit only the review sheets built from them ([where evidence lives](handoff-templates.md#review-evidence-where-it-lives-and-how-reviewers-open-it)).

## 3. Selection
1. Choose by, in order: gameplay purpose and readability, consistency with the traits from §1, craft, technical feasibility (frames, size, budget).
2. Record the choice and one line per rejected candidate saying why it fails. "I like it more" is not a reason.
3. A candidate outside the approved direction is not chosen by the artist: it goes to the design authority ([game-rules.md §2](../game-rules.md#2-design-authority)) as an L2 decision.

## 4. Production
1. Use the method that fits: an approved generator for organic forms and lighting; deterministic operations (crop, trim, canvas, sheet, key, grade) for exact geometry, alignment and repetition; an approved library (PixelFX, where the licence allows it) for effects; project-owned sources.
2. Do not use a generator for exact UI text, icons on a strict grid or repeated variants when a deterministic method gives the exact result.
3. Record for every output: tool, model, prompt, seed, size, operations applied and their arguments. The draft tool writes this provenance; copy it into the project's asset spec or provenance record.

## 5. Art critique and targeted refinement
Critique the **actual image**, not the prompt or the intent. Open the file (Read) and look.
1. **Inspect** at target size and, for craft, enlarged. Compare side by side with the references and with the previous round.
2. **List issues** precisely, most important first. Each issue has: location (region, frame, layer), what is wrong, why it matters visually or for gameplay, and the expected correction. For example: "frame 3, left hand: merges with the sword hilt at 64 px; separate by one value step". Not "make it better".
3. **Fix the listed issues only.** Preserve what was approved: identity, silhouette, palette, everything not named in an issue. Prefer the smallest change that fixes the issue (regenerate with the same seed and an adjusted prompt, crop, re-key, trim, grade, re-assemble) over starting again.
4. **Compare before and after** at target size. A fix that introduces a new defect, or drifts the identity, is a regression: revert to the previous version.
5. **Stop** when the acceptance criteria and the rubric's hard gates are met, or when the iteration budget is spent. Report what remains. Never call your own work approved.

## 6. Technical preflight (before handoff)
Check and list in the Run summary, with the command output where a command exists:
- dimensions, frame count and order, cell size, padding;
- transparency: a real alpha channel, clean edges with no backdrop halo, nothing unwanted outside the alpha bounding box;
- palette and render standard, when the project defines them;
- naming, directory layout, every required variant and state;
- pivot or origin and frame timing intent, for animated assets;
- provenance record complete for every new or changed file;
- every file inside the write set (`git status --short`).

A check that cannot run with the available tools is written as `UNVERIFIED: <check> — <why>`, never as passed. If it blocks acceptance, use the blocker protocol.

## 7. Game UI visual workflow (`ui-designer`)
1. Start from the player's goal on the screen, the information priority, the interaction flow and the target device and input.
2. Read the approved art direction and design tokens (`DESIGN.md` where the project keeps one) before choosing a style.
3. New screen: a simple wireframe, then 2–3 layout options compared at the target resolution; routine screens reuse the existing components.
4. Build reusable components with the approved tokens and every interactive state (normal, hover or focus, pressed, disabled, selected, error).
5. Check readability, text overflow, safe areas, aspect ratios, input methods and accessibility as the Task requires.
6. Inspect the actual engine screenshots at each required size and state before the PR; fix hierarchy, spacing, contrast and alignment problems you see. An uninspected render is not evidence.
7. Visual-language decisions are coordinated with `game-artist`; gameplay meaning with `game-designer`. New illustrated art is a `game-artist` Task, not a UI permission.

## 8. Playbooks by asset family
Each line is the order of decisions; do not polish a later step before the earlier one reads correctly.

| Family | Order |
|---|---|
| Character and creature | silhouette → proportion and value → colour → turnaround or model sheet → sprite → poses and animation consistency |
| Environment and tiles | composition → scale against the player → modular grammar (edges, corners, transitions) → material → seams and tiling → test in a scene |
| UI and iconography | user task → wireframe → hierarchy and tokens → component and states → screenshot review |
| Animation and VFX | gameplay cue → key poses or beats → anticipation, impact, recovery → timing → visibility against busy backgrounds → performance budget (with `gameplay-programmer`) |
| Art critique | inspect native and enlarged → compare with references and states → prioritised issues → targeted edit → regression check |
| Asset preflight | files → technical contract → export → provenance → preview |

## 9. Tools today and known gaps
| Step | Available to `game-artist` today | Gap (proposal only, [OQ-049](../../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)) |
|---|---|---|
| Candidates | `comfy-draft.py`: text-to-image, two approved models, 1–8 candidates, no input image | No reference image, img2img or inpainting: a targeted edit of one region is not possible with an approved tool |
| Operations | `art-ops.py`: `info`, `crop`, `resize` (`--filter lanczos\|nearest`), `key`, `trim`, `canvas`, `sheet`, `grade`, `contact` (`--bg`); `mask` (rectangles, ellipses, polygons, from alpha or a colour; grow, shrink, invert, feather), `compose` (alpha over at a position, opacity, through a mask: exact base outside the mask), `diff` (heat map, changed pixels, per-channel delta, changes outside a mask) | No palette quantise or palette report; no byte-budget export |
| Target-size review | `art-ops.py resize` to the display size, then `contact --cell W H` with the cell at least that size (contact only shrinks, never enlarges); `--bg R G B` for a flat target background | No compositing over a textured or in-scene background: needs an engine frame, else `UNVERIFIED` |
| Enlarged review | `resize --filter nearest` (pixel art) or the default Lanczos (painted art) | — |
| Before/after | `contact` with both versions side by side | No pixel diff |
| In-engine | The five Godot commands of the role file; Deckbound's screenshot runner | Other resolutions and states need a project fixture or Board evidence |
| Effects | PixelFX `list.mjs`, `render.mjs`, where the project licence allows MIT with attribution | — |
