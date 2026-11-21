# Art Production v2 — Phase 2 Roadmap: Creative and Editing Capabilities

- **Status:** `PROPOSED` (2026-11-22). A roadmap, not an implementation: nothing here is approved, installed, enabled or allowed.
- **Starts:** after **G8**, the Phase 1 exit gate ([art-production-v2-pilot.md §7](art-production-v2-pilot.md#7-g8--phase-1-exit-gate)): a **PASS** opens Phase 2; a **CONDITIONAL** outcome allows only one narrowly scoped remediation capability the Board names, **with its minimum mandatory dependencies** from §3 (for example inpainting with the 2A prerequisites and the 2B `mask`, `compose` and `diff` subset), and is not approval of this roadmap. The pilot's tally of tool capability failures orders the workstreams within the hard dependencies of §3; §3's order is otherwise only the default.
- **Each workstream ships as its own PR(s) with its own Board decision.** No new dependency, custom node, model or permission without that decision; agents install nothing; the Board installs.
- **Unchanged:** roles (no new agent; a technical artist is decided separately, game-rules §6), review and approval gates (ADR-009), ownership (`gameplay-programmer` owns project tooling; the Board owns `runtime/tools` changes and installs), originality and licence rules, Paperclip lifecycle.

## 0. Baseline (2026-11-22)
ComfyUI v0.46.0 portable (no custom nodes), checkpoints `sd_xl_base_1.0` and `flux1-schnell-fp8` (registry, PR #88), started by `comfy-draft.py` with `--offline` on loopback, text-to-image only (D1). `art-ops.py`: info, crop, resize (lanczos, nearest), key, trim, canvas, sheet, grade, contact (`--bg`), with the path boundary and limits of security-architecture §4. ComfyUI core already contains image-to-image and masked-inpainting nodes; they are unused and not approved. Published advisory to remember: path traversal in ComfyUI's `LoadImage` via `/prompt` (GHSA-rvxv-29p8-pxgq, fixed in 0.28.0).

## 1. Common rules for every workstream
- **Security review** per [security-architecture.md §11.1](../architecture/security-architecture.md#111-studio-dependencies-registry-entries) for anything external (origin, install path, agent-facing text, runtime and network, health and advisories, trial), recorded in the registry entry as `security review: <date>, <version>, <result>`.
- **Runtime validation** repeats the pilot release gates for the changed parts: tests, install, installed-file and model hashes, permission drift, instruction sync and read-back, smoke runs with success and refusal cases.
- **Benchmark** against the G8 baseline on the same briefs: first-pass acceptance, refinement and review rounds, run time and spend per accepted asset, human interventions, integration rework, and the specific capability failure it targets.
- **Rollback**: every workstream keeps the previous path working until its own acceptance passes, and names the exact undo (restore the previous tool copy by hash, remove the allowlist rule, delete the model file, revert the role text and re-sync).

## 2. Workstreams

### 2A — Controlled image generation: reference conditioning, img2img, masked inpainting
| | |
|---|---|
| **Goal** | Fix one region without regenerating the rest; keep identity and style across an asset family |
| **Owner** | Board (`runtime/tools`, installs, decisions); implementation by Claude Code for the Board as with `comfy-draft.py`; `game-artist` is the only user |
| **Design** | A new wrapper `comfy-edit.py`, separate from `comfy-draft.py` so D1 stays exactly as approved. Fixed workflow templates only, built in code: `img2img` (denoise bounded, for example 0.15–0.75) and `inpaint` (input + mask from 2B `mask`, feather bounded). Inputs only from `staging/art/<asset_id>/` or the Task Workspace's art folders, under the art-ops path rules (canonical path, no links, no hard links, size limits), copied into a per-run ComfyUI input folder by the wrapper (never a client-supplied ComfyUI path, given GHSA-rvxv). Output to staging; provenance JSON with input and mask SHA256, model, seed, settings. Reference conditioning in stages: **(1)** img2img from the project's approved golden reference (no new model); **(2)** only if the pilot shows the need, an image-prompt adapter for SDXL (new model files and, in ComfyUI, a third-party custom node); **(3)** a per-project LoRA trained only on the project's approved art. FLUX variants for fill or redux are excluded unless their licence allows commercial use (several do not) |
| **Prerequisites (before any 2A permission)** | (1) **Server verification:** the wrappers check the running ComfyUI's `/system_stats` `argv` (`--listen 127.0.0.1`, `--offline`) and version and refuse, or restart through the wrapper, a server that differs (closes OQ-049 item 8). (2) **Input isolation:** each run copies its inputs into a fresh `ComfyUI/input/<project>/<run-id>/` folder that only that run's workflow names; no input path is taken from the client; no reads across projects or runs. (3) **Cleanup:** the run's input folder and ComfyUI output copies are deleted after success or failure; staging keeps only the outputs and provenance, with a retention rule. (4) **Model compatibility:** each template is tested per approved checkpoint, and unsupported combinations (for example a model with poor inpainting) are refused, not tried. (5) **Deterministic outside-mask preservation (masked editing only):** after inpainting, `art-ops` composites the result back onto the original through the **effective mask** (the mask after feather and grow), so every pixel whose effective-mask value is 0 is copied from the input, independent of the model. This does not apply to unrestricted full-image img2img, which changes every pixel by design and is judged by the rubric and identity against its reference instead. (6) 2B `mask`, `compose` and `diff` merged and installed |
| **Dependencies** | Stage 1: none new (requires 2B). Stage 2: adapter and CLIP-vision model files plus a custom node, each a registry entry. Stage 3: a training tool, GPU time, a training-set provenance record |
| **Security review** | Stage 1: code review of `comfy-edit.py` and its tests. Stage 2: full §11.1 review of the custom node's code (it runs arbitrary code in the ComfyUI process), pinned commit, every model file's licence and SHA256. Stage 3: training tool review and data provenance |
| **Board decisions** | (a) allow input images for generation through `comfy-edit.py`, keeping D1 for `comfy-draft.py`; (b) input rule: only project-owned images with recorded provenance, never another game's, studio's or artist's work; (c) one exact allowlist rule for `game-artist`; (d) each later stage separately |
| **Acceptance** | Tests: path and argument limits, refusal of outside inputs, provenance fields, server-verification refusal, input-folder isolation and cleanup; for masked editing, **`diff` of the final output against the input is exactly 0 wherever the effective mask is 0**, for every template and checkpoint; full-image img2img is accepted on the rubric and reference identity, not on pixel preservation; identity of a character family judged by the design authority with the rubric |
| **Runtime validation** | G3/G4 for the new wrapper; one img2img and one inpaint run per approved checkpoint; refused runs (outside input, link, oversize, bad mask, unsupported model and template, a server started without `--offline`); after each run the per-run input folder is gone; ComfyUI still `--offline` |
| **Benchmark** | Redo the pilot's region defects with `inpaint` versus full regeneration: rounds, time, review outcome |
| **Rollback** | Remove the allowlist rule and the installed wrapper; D1 path untouched. Stage 2: remove the custom node folder and model files, restart ComfyUI, verify `custom_nodes` is back to the two upstream files |

### 2B — Advanced Art Ops: compositing, masks, palette tools, pixel comparison
| | |
|---|---|
| **Goal** | Preview on the real target background, build masks for 2A, enforce palettes, compare versions objectively |
| **Owner** | Board (`runtime/tools/art-ops.py`); users `game-artist`, and the review roles through the committed outputs |
| **Design** | New `art-ops.py` commands, Pillow and NumPy only: `compose` (alpha "over" onto a background image at a position, opacity), `mask` (rectangle, ellipse, alpha threshold, colour range; invert, feather, grow, shrink), `diff` (heat map plus changed pixels, max and mean delta per channel, alpha changes), `palette` (report colours; quantise exactly to a project palette file) |
| **Dependencies** | None new (`comfyui-embedded-python`) |
| **Security review** | Code review; the existing path boundary, canonical paths, hard-link refusal and limits apply to every new input |
| **Board decisions** | Approve the commands (PR review). No allowlist change: the rule already covers the script |
| **Acceptance** | Unit tests per command: exact alpha in `compose`, palette exactness, `diff` numbers on known images, mask geometry; all existing tests pass |
| **Runtime validation** | G1, G3, G4 for `art-ops.py`; smoke run of each command, and one refused path per command |
| **Benchmark** | Pilot assets re-checked on their real backgrounds with `compose`; count of readability findings caught before review versus the pilot |
| **Rollback** | Reinstall the previous `art-ops.py` by its recorded hash; the commands are additive |

### 2C — Professional game art skills and reference knowledge
| | |
|---|---|
| **Goal** | Deeper craft for agents: shape language, value and colour, readability at size, animation principles, modular tiles, UI hierarchy, VFX timing; worked examples; a company-owned reference library |
| **Owner** | Content: Claude Code for the Board, reviewed by `director` (art direction) and `game-designer` (readability); per-project references: `game-artist` Tasks in each game repository |
| **Design** | Company-written guides extending [visual-procedures.md](../../knowledge/departments/game/domain/art/visual-procedures.md); worked examples made in-house, each with brief, candidates, critique, before/after and final; a reference library of the company's own approved art with provenance. Candidate external source: the registered skill pack `awesome-gamedev-agent-skills` (Apache-2.0, `candidate`), evaluated for its art and asset skills |
| **Dependencies** | None for company-written content; the skill pack only after evaluation, pinned, reviewed and approved |
| **Security review** | Company content: review for copied material (no paid course text, no third-party art). External pack: full §11.1, especially every `SKILL.md` for prompt injection |
| **Board decisions** | Content scope; adoption of any external pack; delivery is 2E |
| **Acceptance** | Each guide has a checkable checklist; at least one **practical worked example** per guide, produced through the real pipeline (comfy-draft, art-ops, review) in a sandbox or project Task, with brief, candidates, critique, before/after and final; examples carry provenance; a reviewer finds no copied third-party material. **Applied-skill evaluation:** the same briefs done with and without the guide, scored blind by `qa` and `director` with the rubric; adoption is claimed only after 2E delivers the guide and the evaluation shows a gain |
| **Runtime validation** | Only through 2E: the guide reaches the agent at run time and is applied (cited and followed) in a plan comment and the work; until then 2C content is not counted as adopted |
| **Benchmark** | Rubric scores and first-pass acceptance on the same briefs with and without the guide |
| **Rollback** | Remove the guide or pointer and re-sync; content is additive |

### 2D — Visual evaluation and preview automation
| | |
|---|---|
| **Goal** | Reproducible in-game checks of look, animation and readability, identical for author and `qa`; closes the game-UI evidence gap (OQ-049 item 7) |
| **Owner** | Per project: `gameplay-programmer` Tasks in the game repository (fixtures are project tooling); Board for allowlist rules |
| **Design** | A fixture scene per project that loads a named asset or screen in a fixed state, seed, camera and resolution and writes frames into the Task's evidence folder; animation strips (N frames at the game's frame rate) turned into contact sheets by `art-ops.py`; golden images for approved assets compared with 2B `diff`; a short text report. Deckbound's `qa_screenshot_runner` is the pattern. Two kinds of check: **static fixtures** (a still asset or screen in a fixed state) are compared **pixel-exact** against the golden image on the same machine, renderer and resolution; any tolerance must be justified and recorded per fixture. **Animation and VFX** are validated with **tolerances**: frame count and timing within one frame, key poses compared per frame with a recorded per-pixel threshold, particle effects seeded or compared by key frames and bounds, never by exact pixels. Automated scores (for example contrast or silhouette checks) only as advisory input to the rubric, never as approval |
| **Dependencies** | None new (Godot, art-ops) |
| **Security review** | Review of each fixture command: it runs project scripts in Godot (not a write boundary, as already recorded for the existing Godot rules) and writes only into the evidence folder |
| **Board decisions** | Per project: the fixture and one exact allowlist rule per role that needs it (`game-artist`, `ui-designer`, `qa-engineer`), as done for SOU-34 and SOU-49 |
| **Acceptance** | Static fixtures: two runs give identical frames (pixel-exact); animation fixtures: two runs within the recorded tolerances; a deliberately changed asset shows in `diff`; requires 2B `diff`; `qa` uses the fixture in one review; `ui-designer` evidence lands in a committed folder |
| **Runtime validation** | Permission drift check after the allowlist change; the fixture run by each allowed role; a refused variant (other scene or arguments) |
| **Benchmark** | In-engine defects found before versus after integration; integration rework per asset |
| **Rollback** | Remove the allowlist rules (back to the five existing Godot commands); the fixture stays in the project as plain tooling |

### 2E — Art knowledge and Task template distribution
| | |
|---|---|
| **Goal** | End the Board-assisted limitation: `project-manager` and `game-designer` can write compliant asset Tasks, and agents can read 2C content at run time |
| **Owner** | Board (mechanism and role text); `game-artist` or `project-manager`-planned Tasks in each game repository for project copies |
| **Design** | Options, tested in this order: **(1)** a project copy of the template and the art knowledge in each game repository (for example `docs/art/process/`), versioned from Company OS, readable by every role with repository access, plus a one-line pointer in the role files; **(2)** Paperclip skills attached through the package, after a sandbox test of `build-package.py` and `sync-instructions.py` with one small skill (OQ-049 item 4); **(3)** the external skill pack from 2C |
| **Dependencies** | None for (1); Paperclip skill behaviour for (2) |
| **Security review** | (2) and (3): what the agent loads automatically, and that no agent can change it |
| **Board decisions** | The mechanism; the role-text pointer for `game-designer`, `project-manager` and `qa` (this changes the 2026-11-21 decision that kept asset steps out of those role files) |
| **Acceptance** | **End-to-end autonomous planning exercise:** `project-manager` (or `game-designer`) plans one asset family from a design brief into compliant `backlog` Tasks (template fields, lanes, budgets, write sets, blocker relations requested, review stages named) using only what it can read; the Board checks them with `pc.py show` and the template rules and makes no edits; the Tasks then run through the pilot release checklist. Also: a `project-manager`-written asset Task passes the template's checks without Board edits; drift between the Company OS source and the project copies is detectable (a version line and a check) |
| **Runtime validation** | Instruction sync and read-back for any role-text pointer; one Task written by `project-manager` and one by `game-designer` reviewed by the Board against the template |
| **Benchmark** | Board interventions per asset Task (pilot baseline) versus after |
| **Rollback** | Remove the pointers and re-sync; the Board resumes writing asset Tasks |

## 3. Hard dependencies and default order
Hard dependencies hold whatever order G8 suggests, and also for a CONDITIONAL remediation: the Board approves the remediation capability together with exactly the rows below that it needs, nothing more:

| Before | Must be done first | Why |
|---|---|---|
| 2A masked inpainting | 2B `mask`, `compose`, `diff` | Masks; deterministic outside-mask restore; the outside-mask `diff` acceptance |
| 2A full-image img2img | 2B `diff` | Before/after comparison in its evaluation |
| 2A any stage | 2A prerequisites (server verification, input isolation, cleanup, model compatibility) | Image input widens the attack surface (GHSA-rvxv) and the D1 boundary |
| 2D visual regression (golden images) | 2B `diff` | The comparison itself |
| 2C counted as adopted | 2E delivery of the guide | Agents cannot use what does not reach them |
| 2E role-text pointer | Board decision changing the 2026-11-21 role-text decision | Governance |

Default order:
| Step | Workstream | Why |
|---|---|---|
| 1 | 2B Advanced Art Ops | No new dependency or permission; provides `mask` for 2A and `diff` for 2A and 2D |
| 2 | 2D Visual evaluation | Makes every later change measurable in the engine |
| 3 | 2A stage 1 (img2img, inpaint) | Needs a Board decision on input images but no new model |
| 4 | 2E Distribution, with 2C content written in parallel | Ends the Board-assisted limitation |
| 5 | 2A stages 2–3 (adapter, LoRA) | New models or custom nodes: the largest security and licence review |

## 4. Out of scope
New roles or agents; cloud generation services; model or node installs by agents; arbitrary ComfyUI workflows or a client-supplied workflow JSON; ComfyUI-Manager; changes to review or approval gates.
