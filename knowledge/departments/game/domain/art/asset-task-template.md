# Asset Task Templates

- **Status:** `PROPOSED` (2026-11-22).
- **Who uses it:** in the Phase 1 pilot, only the Board Operator, through `pc.py create --desc-file <file>` ([scope](README.md)). `game-designer` and `project-manager` cannot read it yet ([delivery map](README.md#how-agents-get-this-text-delivery-map)).

Why the text is long: `game-designer`, `project-manager` and `qa` do not carry the asset steps in their role files (Board decision 2026-11-21), and no agent can read this repository. The Task description is the only place they find the brief, the rubric and the routing. Keep the blocks below whole; delete only lines that do not apply.

Rules for every filled template:
- It satisfies the [task contract](../../../../company/standards/task-contract.md#2-task-contract): one outcome, exactly one `## Acceptance criteria` and one `## Write set`, each write-set item one path in backticks relative to the project repository, a `## Read set` the assignee can actually open.
- Every reviewer it names is a Paperclip review stage on the Task (`pc.py create --review qa --review game-designer …`). A role that is not a stage participant must not be asked to review: its wake is cancelled.
- Integration Tasks get a Paperclip blocker relation on the art Task, not only a sentence.
- Text the assignee cannot reach (other issues, chat) is pasted in or committed to the project repository first (G-8).

## 1. Art Task

```md
# [ART] <asset family>: <one outcome>

Intended assignee: game-artist
Reviewers (Paperclip review stages): qa<, game-designer when readability is at stake><, director when the project's art pipeline requires it> · Approval: Board

## Goal
<One outcome. Where the asset appears in play and what the player must understand from it.>

## Read set
- `AGENTS.md` (asset rules, licensing rule, directories)
- `<approved art bible / render standard / palette>`
- `<asset spec or registry entry>`
- `<golden reference or existing assets of this family>`
- `<design document section>`

## Write set
- `<asset folder or files>`
- `<provenance record or asset spec entry, only where the project has one>`
- `art_src/review/<TASK-KEY>/` (review evidence; or the folder the project's `AGENTS.md` names)

## Asset brief
- Lane: <L0 fix or variant | L1 new asset | L2 new direction>, because <reason>.
- Gameplay role and information priority: <what the player must notice first, second>
- Target display size, background, camera and angle: <e.g. 64x64 px on the forest tile set, side view>
- States and variants: <idle, hit, disabled …>
- Identity that must not change: <traits, colours, proportions>
- Reference traits to match (3–5, observable): <e.g. 2 px dark outline; light from top-left; 4-value palette ramp>
- Output: <format, dimensions, frames, cell size, pivot, loop, file naming>
- Budget: <file size, texture size, frame count>
- Licence rule: <project rule, e.g. original or CC0 only; AI-made art allowed under the Board decision of 2026-11-22>
- Approved tools for this Task: <comfy-draft.py, art-ops.py, PixelFX (licence permitting), Godot capture>
- Iteration budget: <default 2 critique-and-refine rounds>
- Integration Task for in-context checks: <Task key, or none — then nothing may be deferred and the asset can reach art-ready only>
- Open questions for art direction: <or none>

## Procedure (game-artist)
1. Post the plan comment: lane, reference traits, constraints, deliverables, tools.
2. Research the references. L1: compare 2–3 distinct candidates at the target size and record why the others fail. L2: compare 3–4 directions at the target size and in a representative scene; the design authority decides before production (see the L2 decision rule in the workflow).
3. Produce, then critique the actual image: located issues, targeted fixes, before/after at target size, within the iteration budget.
4. Preflight and hand off with the evidence below. The self-check is not an approval.

## Acceptance criteria
- [ ] Purpose and silhouette read at the target size, on the target background, in every listed state.
- [ ] Matches the named reference traits; no identity or style drift from the approved references.
- [ ] Output matches the technical spec: dimensions, frames, alpha, naming, directory, every variant.
- [ ] Every new or changed file has a provenance record the licence rule allows; no third-party or traced art.
- [ ] Evidence attached as listed below; limitations and unverified checks stated explicitly.
- [ ] Acceptance stage reached: **art-ready**. In-context checks not judged here are written `UNVERIFIED — deferred to <integration Task key>: <check>`; nothing else is deferred. The asset is not production-accepted until the integration Task verifies them.

## Evidence required in the handoff
<L0: before/after at target size. L1: candidate contact sheet at target size and why others fail; selected asset; before/after of each refinement round. L2: as L1, plus the representative scene and the decision record.> Always: preflight results with command output, provenance, pivot and timing for animated assets, known limitations, `ready for integration` or `art only`. Every image is committed under `art_src/review/<TASK-KEY>/` and cited by repository-relative path; target-background previews use `art-ops.py contact --bg <R G B>`. Staging paths, uncommitted files and descriptions are not evidence (reviewers mark them UNVERIFIED).

## Review rubric (for every reviewer)
Hard gates at this stage (art-ready; any failure or missing evidence = changes requested): licence and provenance · originality · technical contract of the files · critical readability at target size on the target background colour, in every listed state · required evidence · write set only. Only in-context checks (readability over the real background or scene, in-engine scale against other assets, animation and VFX timing in context, UI legibility in place) may be deferred, each written `UNVERIFIED — deferred to <integration Task key>: <check>`; a deferral without that key = changes requested. Approving this Task makes the asset art-ready, not production-accepted; it stays UNVERIFIED for the deferred checks until the integration Task validates them.
Score each that applies 0 (fails), 1 (partly), 2 (meets, with evidence) and write the observation: readability · art direction · craft · coherence · production · evidence. Scores never override a hard gate. A 0 in art direction, craft or coherence = changes requested even when every hard gate passes, unless game-designer (director for vision or pillars) records an explicit exception in this Task naming the category, what is accepted and why; a 1 there is a finding, approvable only as minor with a follow-up Task or that exception. Taste questions without a named reference trait go to the design authority.
Findings: location (file, frame, region), expected, actual, severity (blocker / major / minor), evidence, owner. Routing: look, size, frames, palette, provenance → this Task, game-artist · in-game behaviour, import, timing logic, shader, performance → the integration Task, gameplay-programmer · unclear or wrong requirement → game-designer.
Reviewers never edit, commit or push this branch; record approve or changes requested in Paperclip.
```

## 2. Integration Task

```md
# [INTEGRATE] <asset family> in <scene or system>

Intended assignee: gameplay-programmer
Blocked by: <art Task key> (Paperclip blocker relation)
Reviewers (Paperclip review stages): qa<, game-artist for the visual result when the look can change in engine> · Approval: Board

## Goal
<The merged asset working in the game: where, which states.>

## Read set
- `AGENTS.md`
- `<merged asset files and their spec / provenance>`
- `<art handoff: pivot, frame timing intent, loop, limitations>` (pasted here or committed)

## Write set
- `<scene, resource, import, animation or shader files>`
- `art_src/review/<TASK-KEY>/` (in-engine evidence; or the folder the project's `AGENTS.md` names)

## Integration brief
- Import settings, filtering and compression expected: <e.g. nearest filtering for pixel art>
- Animation states and timing: <from the art handoff>
- Preview states and resolutions to capture: <e.g. idle and hit, at 1920x1080 and 2400x1080>
- Performance budget: <draw calls, texture memory, particle count>

## Deferred checks to validate
<Copied from each art handoff and verdict: `<art Task key> · <asset> · <check>`. Every one must be validated here.>

## Acceptance criteria
- [ ] Every deferred check listed above passes, each with a committed in-engine screenshot or frame strip cited by path; a failing check is a finding routed to a new art fix Task, which blocks verification of that asset.
- [ ] The asset appears in <scene> in every listed state, with the pivot, timing and loop from the art handoff.
- [ ] In-engine screenshots (or frames for motion) at each listed resolution and state are copied to `art_src/review/<TASK-KEY>/`, committed, cited by path and inspected.
- [ ] The source art was not redrawn; any needed art change was requested from game-artist in a comment.
- [ ] Performance budget met, with the measurement stated.
- [ ] Smoke check passes; CI green.

## Review routing
Import, behaviour, timing logic, shader, performance → this Task, gameplay-programmer · source look, frames, palette → a new art Task for game-artist · requirement → game-designer.

## Review rules (for every reviewer)
Hard gates at this stage (integration-ready): technical contract in the engine (import, filtering, pivot, frame timing, loop) · every deferred check above validated with committed in-engine evidence · performance budget · evidence · write set only. Nothing may be deferred further. qa's verdict lists each integrated asset as `verified` or names the open check; only verified assets are production-accepted. Reviewers never edit, commit or push this branch; record approve or changes requested in Paperclip.
```

## 3. Game UI Task

```md
# [UI] <screen or component>: <one outcome>

Intended assignee: ui-designer
Reviewers (Paperclip review stages): qa<, game-designer when gameplay information changes> · Approval: Board

## Goal
<Player goal on this screen and the information it must show first.>

## Read set
- `AGENTS.md`
- `<DESIGN.md or UI style guide, approved art direction>`
- `<design document section, existing components>`

## Write set
- `<UI scenes, components, theme or token files>`

## Evidence (not in the write set)
Engine frames captured with the allowed Godot commands stay in the Task Workspace (`.godot/<name>*.png`; Deckbound: `.godot/qa/main-<W>x<H>.png`) and are listed by path in the handoff. `qa` recaptures them with the same commands.

## UI brief
- Information priority and interaction flow: <…>
- Target resolutions, aspect ratios, safe areas, input methods: <…>
- States to show: <normal, focus, pressed, disabled, selected, error, empty, overflow>
- Accessibility requirements: <contrast, text size, focus order>
- New illustrated art needed: <none | separate game-artist Task KEY>

## Acceptance criteria
- [ ] New screen: wireframe and 2–3 layout options compared; chosen option and reason recorded. Routine screen: existing components reused.
- [ ] Built with the approved tokens; every listed state implemented.
- [ ] Engine frames at every listed resolution and state captured in the Task Workspace, listed by path and inspected; hierarchy, spacing, contrast, alignment and overflow issues fixed. A size or state the allowed commands cannot capture is stated as UNVERIFIED.
- [ ] Accessibility and input requirements checked, or each unverified check stated.
- [ ] No third-party UI asset or font without a recorded licence.
```
