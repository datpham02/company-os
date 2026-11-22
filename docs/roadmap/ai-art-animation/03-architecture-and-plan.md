# Architecture, Benchmarks, Spikes and Roadmap

- **Status:** `PROPOSED` (2026-11-22), revised after the `director` review (SOU-78, "approve for Board decision" with amendments; all amendments applied below). Nothing here is approved, installed or allowed. Board decisions are listed in the [README](README.md#required-board-decisions).
- Labels used for every capability: **Verified** (tested on the studio machine) · **Experimental** (a spike will test it) · **Proposed** (designed, not built) · **Unknown** (open limitation).

## 1. Proposed architecture

```
Project profile (YAML, per project)            Studio Art Platform (company-os runtime/, project-independent)
  style, palette, proportions, resolution  -->   1. Model & workflow registry   (pinned weights, licences, ComfyUI workflow templates)
  animation set, engine target, budgets         2. Tool CLIs                   (art-ops, comfy-draft, comfy-edit, + new: matte, segment,
  naming, quality gates                                                          decompose, layer-validate, mesh, rig-build, motion, render, qa)
                                                 3. Neutral data schemas        (versioned JSON: layer manifest, rig, clip, QA report, provenance)
                                                 4. Engine adapters             (Godot compiler via headless @tool scripts; Spine JSON exporter, gated)
                                                 5. Render & QA harness         (engine capture, metrics, vision rubric, structured feedback)
                                                 6. Run ledger                  (structured logs, retries, repair cost, provenance)
Project artifacts (project repository)
  source art, masks, layers, meshes, rigs, clips, sprite sheets, engine resources, QA evidence
```

Design rules (initiative §15):
- **Data is the source of truth, engines are targets.** An agent writes a layer manifest, a rig JSON and clip JSON; adapters compile them. Nothing depends on one Godot project's structure.
- **Every tool is a CLI with a fixed contract** (validated arguments, path boundary, limits, provenance output, exit codes), like `art-ops` and `comfy-edit` today. Agents get one exact allow rule per tool.
- **Workflows are templates in code or a registry**, never arbitrary ComfyUI JSON from an agent (keeps the GHSA-rvxv boundary and licence gating).
- **Two environments:** the pinned production ComfyUI (today's) and a separate R&D ComfyUI whose models live **outside the production ComfyUI tree**, so experiments never change production.
- **Bounded loops:** every generate–validate–repair loop has retry, time and cost caps and escalates to `director` with a structured failure.
- **One canonical master per character** (art-direction rule, `director`): every part is **cut from the approved master, never generated alone**; poses come from the rig; regeneration is allowed only for completed (hidden) regions and failed parts; gameplay states (for example binding states) are masked edits on the master, then re-cut. This is the lesson of SOU-64 run 1, where separately generated parts did not match.
- **Complete only what animation reveals.** Each part gets a *reveal budget* derived from the clip ranges (how far each joint moves); occlusion completion is required only inside it. Briefs carry a parts sheet or an anatomy rule for every hidden area (for the Scrivener: spec production requirement 6).

Neutral schemas: **v0 is derived from spike output** (S2, S8, S9), not designed ahead; **v1 is fixed at the M2 (layers) and M3 (rig, clip) exits**.
- `layer-manifest`: parts (id, semantic tag, PNG, bbox, assembly origin, joint point, parent, z-order, reveal budget, completed regions with the completing tool per region), source master, reassembly diff score, provenance per part.
- `rig`: bones (hierarchy, rest transform, limits), slots/attachments (rigid sprite or mesh with vertices, UVs, triangles, weights), swaps, constraints baked or runtime.
- `clip`: tracks per bone (rotate, translate, scale; Bézier or stepped), attachment swaps, events (`release`), loop flag, secondary-motion parameters.
- `qa-report`: checks (id, metric, threshold, value, pass), artefacts (frames, heat maps), rubric scores, findings with owner, **repair cost** (below).

**Repair-cost record (every spike result and every benchmark run):** attempts, parts regenerated, manual interventions (counted and named, including any mask drawn by hand), wall time, GPU hours. "Eleven regenerations and two hand-drawn masks" is a result, not an unattended run.

## 2. Benchmark suite

Same inputs and criteria for every method compared. Benchmarks are studio assets, original designs only, never another game's art.

**Sampling rule (all benchmarks and spikes with a success rate):** 3 subjects × 4 seeds per method; report the **median and the worst** result; pass on the median, and record the worst as a risk. A single subject or n = 4 is never a pass.

| ID | Group (initiative §6) | Proposed subject and style | Required layers | Animation set | Gameplay states | Key acceptance criteria |
|---|---|---|---|---|---|---|
| B1 | Humanoid, many moving parts | New original swordfighter, three-quarter view, **flat cel-shaded style** (the second painted style, initiative Gate G) | head, torso, pelvis, 2×upper/lower arm, hands, 2×thigh/shin, feet, weapon | idle, attack, hit, death | weapon swap | reassembly diff ≤ 1% changed px at rest; elbows and knees bend 90° without gaps; **facing**: one facing defined, a mirrored facing either produced or declared unsupported |
| B2 | Cloaked, mesh deformation, occlusion | **The Scrivener** (Deckbound, direction B, master s6302), painterly dark fantasy | per Deckbound spec (cloak, hood/head, arms, book, page, lantern, three bindings × 3 states) | `idle` 2.0 s loop, `action_tear_page` 0.6 s with `release` | binding intact/frayed/severed | spec production requirements; **hidden parts painted whole**, shown by a range-of-motion render; **draw order as the spec**; cloak sway without tearing; lantern reads at 270 px |
| B3 | Non-humanoid monster | Deckbound `enemy_frayer` or a new multi-limbed creature, painterly | body, 4+ limbs/tendrils, head | idle, attack windup, hit | enraged variant | tendrils animate with secondary motion; **silhouette: the flat black shape at 25% screen height is identifiable in a roster line-up** |
| B4 | Lightweight pixel art | New 64 px pixel character, **frame-based** (rotated pixels blur, so no parts rig) | frames, not parts | idle, walk, hit | — | pixel grid exact (no sub-pixel blur), palette ≤ 16 colours, frames consistent |
| B5 | Gameplay-variable accessories | New character with swappable armour pieces and a shield that can break, **flat cel-shaded** | base + 3 swappable attachments | idle, block, break | armour on/off, shield intact/broken | swaps keep pivots; no seams on swap; facing criterion as B1 (asymmetric props declared per facing) |

Per benchmark the spec records: input artwork (or brief), the **approved reference sheet** (first master + parts sheet), required layer separation and reveal budgets, animation set and timing, gameplay states, engine preview configuration (resolution, background, camera, fps), quality criteria (Gates A–E), performance limits (atlas, memory, frame time on the Deckbound target device class).

Gate G therefore needs **at least two painted styles (painterly B2/B3 and flat cel B1/B5)**; pixel art (B4) is a separate frame-based pipeline and does not count as the second style.

## 3. Technical spike plan

Small, evidence-first, in the R&D environment. Each spike ends with a **one-page result** in this folder: question, method, n (subjects × seeds), median and worst, repair cost, artefacts, verdict. **Tier 0 needs no new dependency; later tiers need the Board's install decision (README D2).**

| ID | Tier | Question | Method | Success metric | Effort | Needs |
|---|---|---|---|---|---|---|
| S1 | 0 | Can SDXL base insert a new object with core inpaint conditioning? | latent mask vs `InpaintModelConditioning` + `DifferentialDiffusion` | object present | done | — **Result: failed 0/4 (one input; 0/10 together with SOU-64 run 2's 6 attempts). Verified negative for this input only** |
| S2 | 0 | Can a script build a weighted Godot rig that deforms correctly in 4.6? | rig JSON → headless `@tool` builder → `.tscn` → Movie Maker frames, **using the Scrivener spec's part list**, so it seeds SOU-77; `gameplay-programmer` reviews | visual match, no flipped triangles | 2 d | Godot only |
| S3 | 0 | Does Movie Maker capture deterministic frames with alpha on this PC (headless vs windowed)? | `--write-movie` PNG, `transparent_bg` | identical frames on two runs; correct alpha | 0.5 d | Godot only |
| S4 | 0 | **Can agents author clips that read as good animation?** (biggest unknown; first go/no-go) | preset functions (anticipation, overshoot, follow-through, baked spring) → clip JSON → Godot; render | 4 seamless loops; Gate D rubric (below) median ≥ 4, none under 3, scored by `director` | 3 d | S2 |
| S5 | 1 | Does SDXL + Fooocus patch (grey pre-fill, VAE-encode-for-inpaint) insert objects? | sampling rule (3 subjects × 4 seeds) | insertion on median subject ≥ 3/4 | 0.5 d | node pack + patch weights; **R&D only** (licence text missing) |
| S6 | 1 | Does FLUX.2 klein 4B run on 12 GB/16 GB, and how well does it insert, complete and keep identity? | sampling rule; **three results reported separately**: insertion, occlusion completion, identity against the reference sheet | runs without OOM; insertion median ≥ 3/4; completion rubric ≥ 4/5; identity rubric ≥ 4/5 | 1.5 d | klein 4B + Qwen3-4B encoder weights |
| S7 | 1 | Can a matte replace colour keying (shadows, soft edges)? | BiRefNet (and ToonOut, R&D only) on SOU-64 masters and 2 more | no halo and no baked shadow at 270 px | 0.5 d | BiRefNet weights + node |
| S8 | 2 | Does See-through decompose our style into usable occlusion-completed layers? | Scrivener + 10 project masters; reassembly diff; per-part rubric; **completion style-drift check** (hidden regions judged against the master's style, not anime defaults; drifted parts count as repairs) | ≥ 70% parts usable without repair; reassembly ≤ 2% changed px; drift-free completions ≥ 80% | 2 d | conda env + weights; **D4 (evaluation only)** |
| S9 | 2 | Does a modular chain (matte + SAM 2.1 + depth + inpaint) meet the same bar? | same inputs, same drift check | **the same absolute thresholds as S8** (it may run without S8 if D4 excludes See-through) | 2 d | SAM 2.1, DA3 MONO-LARGE + S5/S6 editor |
| S10 | 3 | Do alpha → CDT → harmonic/BBW weights bend cleanly? | 3 part sets incl. cloak | 90° bends, no tearing; Gate C rubric ≥ 4/5 | 3 d | PythonCDT, SciPy (pip in R&D venv) |
| S11a | 2 | Do automatic checks catch **layer** defects? | inject 20 known defects (halo, baked shadow, gap, wrong z-order, drifted completion, seam) into S8/S9 outputs | recall ≥ 90%, false positives ≤ 10% | 1.5 d | scikit-image, LPIPS |
| S11b | 3 | Do automatic checks catch **mesh and motion** defects? | inject 20 known defects (flipped triangles, stretching, popping at swaps, loop seam, jitter) | recall ≥ 90%, false positives ≤ 10% | 1.5 d | S10, S4 |
| S12 | 3 | Can a video model give usable motion reference within 16 GB RAM? | Wan 2.x/LTX GGUF → pose/timing extraction | no OOM, ≤ 15 min/clip, usable timing | 2 d | video weights; **RAM decision D3** |
| S13 | 3 | Does one clip compile identically to Godot and Spine? | dual export, per-frame SSIM | SSIM ≥ 0.97 | 2 d | Spine licence; **D6** |

Order: **S2, S3 → S4 (first go/no-go on animation quality)** → S5, S6, S7 → S8, S9, S11a → S10, S11b → S12, S13 only if the Board approves their dependencies.

## 4. Implementation roadmap

| Milestone | Content | Exit evidence | Depends on |
|---|---|---|---|
| **M0 Decisions & R&D environment** | Board decisions D1–D9; R&D ComfyUI with models outside the production tree; storage plan and free-space floor; licence/provenance policy; benchmark briefs B1–B5 with reference sheets | decisions recorded; R&D env hashes; free space ≥ floor | this package |
| **M1 Spikes tier 0–1** | S2, S3, **S4**, S5, S6, S7 | one-page results; go/no-go per tool; animation go/no-go from S4 | M0 |
| **M2 Layer production prototype** (initiative Phase 3) | S8, S9, **S11a** → layer-manifest v1, `matte`, `segment`, `decompose`, `layer-validate` CLIs; B2 Scrivener and one more benchmark; **repair ceiling for Gate F set here** | Gate B on 2 benchmarks (counted only after S11a); repair cost measured | M1 |
| **M3 Rigging prototype** (Phase 4) | S10, **S11b** → `mesh`, `rig-build` CLIs, rig v1, Godot compiler; rig variants compared (full, partial, single-mesh, hybrid) | Gate C on 2 benchmarks; Rig Evaluation Report | M2 |
| **M4 Animation prototype** (Phase 5) | clip v1, `motion` CLI, motion presets, baked secondary motion (from S4); S12 if approved | Gate D on B2's set; Motion Library v0 | M3 |
| **M5 Engine preview & QA loop** (Phase 6) | S3 → `render`, `qa` CLIs, qa-report v1, bounded repair loop, `director` escalation | loop demo with caps and repair-cost ledger | M3 (parallel to M4) |
| **M6 End-to-end validation** (Phase 7) | Scrivener from brief to in-engine animation, then a second benchmark in the flat cel style (B1 or B5) | validation package (sources, manifests, rig, clips, preview video, QA report, repair-cost report, reproduction steps) | M4, M5 |
| **M7 Studio platform** (Phase 8) | project profiles, registries, docs for agents, role updates, distribution | Gate F and G evidence on ≥ 2 character types and ≥ 2 painted styles | M6 |

Effort (rough, Board operator days, excluding agent run time): M0 2–3 · M1 6–8 · M2 9–13 · M3 9–13 · M4 6–10 · M5 5–8 · M6 5–8 · M7 5–8. Total about **47–71 working days**, highly uncertain beyond M2: each milestone re-estimates from its spike results.

## 5. Agent responsibility matrix

| Responsibility (initiative §13) | Today | Proposal |
|---|---|---|
| Art direction, quality standards, art review | `director` (read-only) | Keep; `director` reviews every spike result and gate and owns the Gate D rubric scores |
| Concept, master artwork, visual iteration | `game-artist` | Keep; gains new tools only after each spike passes |
| Technical art: tool research, segmentation, reconstruction, mesh, rigging, asset pipeline, benchmark runs | **nobody**; the Board operator (Claude Code) during R&D | Board operator during M0–M3 (decision D1). **`technical-artist`** (D7), created only after two characters pass M3 and a playbook exists: owns the platform CLIs, registry entries, rig builds and benchmark runs; no masters, no art direction; script execution in the R&D environment only, one allow rule per CLI; reports to `producer`; quality verdicts stay with `director` |
| Animation: motion design, keys, timing, secondary motion | nobody | Board operator builds the motion tools (M4). **`animator`** (D7) only if M4 shows motion needs its own iteration loop; then it owns the clip schema, motion library and timing, judged at Gate D, never edits masters or rigs |
| Runtime integration, state machines, performance | `gameplay-programmer` | Keep; owns engine adapters in project repositories and reviews S2 |
| Automated validation, visual QA, benchmark execution | `qa-engineer` | Keep; gains `render`/`qa` CLIs in M5 |
| Task decomposition, budgets, milestones, risks | `producer`, `project-manager` (read-only) | Keep; tracking via Paperclip |

## 6. Dependencies

- **Hardware:** RAM (16 GB) gates S12 and Qwen 20B models; disk (85 GB free) needs a storage plan or free-space floor **before tier 1** (R10).
- **Licence/provenance policy** gates S8 (See-through training data) and any SAM 3 use.
- **Lifecycle (OQ-048):** tool failures strand Tasks; until fixed, every failing spike Task needs a Board round.
- **Deckbound:** SOU-64 is parked as benchmark B2; SOU-77 (rig) waits for M3 output and is seeded by S2; other pilot Tasks continue on today's tools.

## 7. Budget and resources (estimates)

| Item | Estimate | Type |
|---|---|---|
| Local compute | electricity only; spikes ~10–40 GPU hours | Proposed |
| Disk for R&D models | ~60–120 GB (klein 4B + encoder ~15 GB, Qwen 20B GGUF + encoder ~20 GB, See-through ~15 GB, SAM/BiRefNet/DA3 ~5 GB, one video model ~15–25 GB); tier 1 alone ~20 GB | Estimate (U); tier 1 leaves too little margin beside production on 85 GB free → storage decision before tier 1 |
| RAM upgrade 16 → 64 GB | one hardware purchase (Board to price locally) | Recommended before S12 and Qwen 20B |
| Spine Professional | USD 379 one-time per named user (V), only if S13 is approved after legal reading | Optional |
| Cloud/paid APIs | none proposed | — |
| Agent tokens | spikes are run by the Board operator; agent Tasks only from M2; tokens recorded, dollar cost often unavailable | Unknown |

## 8. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Automatic occlusion completion invents wrong anatomy that passes metrics; it shows only when a joint moves | High | High | Reveal budgets; parts sheet or anatomy rule per hidden area; Gate B reveal check (render extreme poses, heat-map revealed pixels); `director` review |
| R2 | 16 GB RAM makes 20B/14B models unusable or unstable | High | Medium | Prefer 4B models; RAM upgrade decision |
| R3 | Licence or provenance problem discovered after assets ship; completed regions carry recognisable elements of scraped designs | Medium | High | Registry review per tool; provenance policy (D4); originality check covers completed regions and swaps; completing tool recorded per region |
| R4 | Automatic skin weights never reach commercial quality without humans | Medium | High | Partial-skeletal/hybrid rigs; sprite swaps for hard cases; measure in S10 |
| R5 | Style generalisation: tools trained on anime pull hidden regions toward anime hands, faces and proportions | High | Medium | Style-drift check in S8/S9; benchmarks in two painted styles; modular chain fallback |
| R6 | Godot 2D IK and tooling stay experimental | Medium | Medium | Bake IK at authoring; Blender/glTF or Spine fallback |
| R7 | Vision-model judgements of animation are unreliable | Medium | Medium | Calibrate with seeded defects (S11a/b); `director` scores Gate D |
| R8 | Board operator becomes the bottleneck for all technical art | High | Medium | `technical-artist` after M3 evidence (D7) |
| R9 | Unbounded agent repair loops waste budget | Medium | Medium | Hard caps per loop; repair-cost ledger; escalation (M5) |
| R10 | Disk fills, breaking production ComfyUI | **High** | High | R&D models outside the production tree, on another drive or after cleanup; free-space floor checked before each install |
| R11 | Roster sameness: characters from one pipeline converge on similar silhouettes | Medium | Medium | Roster silhouette line-up at Gate A |

## 9. Quality gates (initiative §14) mapped to today's stages

A gate **counts only after its automatic checks have shown ≥ 90% recall on that defect class** (S11a for Gate B, S11b for Gates C–D); before that, gate results are recorded as provisional.

| Gate | Meaning | Evidence | Relation to Art Production v2 |
|---|---|---|---|
| A Artwork | identity and production quality. **Identity = agreement with the approved reference sheet** (first master + parts sheet); checked on the master before decomposition, then per part and per pose; roster silhouette line-up | rubric (hard gates, scores), `director` verdict | = art-ready |
| B Animation readiness | layers, overlap, completion inside the reveal budget, joint points, reassembly; no halo or baked shadow at 270 px; reveal check at extreme poses | layer-manifest validation, reassembly diff, reveal heat map, part rubric | new, before rig |
| C Rig quality | correct deformation in the required range | range-of-motion render, mesh sanity, rubric | new (SOU-77-type checks) |
| D Animation quality | **rubric on the rendered clip, 1–5 each, pass at median ≥ 4 with none under 3, scored by `director`:** key pose readable at 270 px in a one-frame hold; loop seam invisible at 60 fps; contact and weight (no floating); arcs; anticipation and recovery; secondary motion settles; no popping at swaps | rendered clips, contact sheets | new |
| E Runtime | engine import, performance budget | engine capture, frame time, memory | = integration-ready / verified |
| F Automation | rerun without human art or animation work: **manual pixel edits = 0**, repairs within the ceiling set at M2 | run ledger with repair cost, reproduction from manifests | new |
| G Reusability | ≥ 2 character types and ≥ 2 painted styles (pixel art counted separately) | M6/M7 evidence | new |

A gate passes only with recorded evidence; "runs" is not "production quality" (Gate D).
