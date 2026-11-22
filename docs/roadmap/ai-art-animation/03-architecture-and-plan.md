# Architecture, Benchmarks, Spikes and Roadmap

- **Status:** `PROPOSED` (2026-11-22). Nothing here is approved, installed or allowed. Board decisions are listed in the [README](README.md#required-board-decisions).
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
                                                 6. Run ledger                  (structured logs, retries, cost, provenance)
Project artifacts (project repository)
  source art, masks, layers, meshes, rigs, clips, sprite sheets, engine resources, QA evidence
```

Design rules (initiative §15):
- **Data is the source of truth, engines are targets.** An agent writes a layer manifest, a rig JSON and clip JSON; adapters compile them. Nothing depends on one Godot project's structure.
- **Every tool is a CLI with a fixed contract** (validated arguments, path boundary, limits, provenance output, exit codes), like `art-ops` and `comfy-edit` today. Agents get one exact allow rule per tool.
- **Workflows are templates in code or a registry**, never arbitrary ComfyUI JSON from an agent (keeps the GHSA-rvxv boundary and licence gating).
- **Two environments:** a pinned production ComfyUI (today's) and a separate R&D ComfyUI for spikes, so experiments never change production.
- **Bounded loops:** every generate–validate–repair loop has retry, time and cost caps and escalates to `director` with a structured failure.

Neutral schemas (Proposed, versioned):
- `layer-manifest.v1`: parts (id, semantic tag, PNG, bbox, assembly origin, joint point, parent, z-order, occlusion-completed areas), source master, reassembly diff score, provenance per part.
- `rig.v1`: bones (hierarchy, rest transform, limits), slots/attachments (rigid sprite or mesh with vertices, UVs, triangles, weights), swaps, constraints baked or runtime.
- `clip.v1`: tracks per bone (rotate, translate, scale; Bézier or stepped), attachment swaps, events (`release`), loop flag, secondary-motion parameters.
- `qa-report.v1`: checks (id, metric, threshold, value, pass), artefacts (frames, heat maps), vision rubric scores, findings with owner.

## 2. Benchmark suite

Same inputs and criteria for every method compared. Benchmarks are studio assets, stored in a benchmark repository or folder, original designs only, never another game's art.

| ID | Group (initiative §6) | Proposed subject | Required layers | Animation set | Gameplay states | Key acceptance criteria |
|---|---|---|---|---|---|---|
| B1 | Humanoid, many moving parts | New original swordfighter, three-quarter view | head, torso, pelvis, 2×upper/lower arm, hands, 2×thigh/shin, feet, weapon | idle, attack, hit, death | weapon swap | Reassembly diff ≤ 1% changed px at rest; elbows/knees bend 90° without gaps |
| B2 | Cloaked, mesh deformation, occlusion | **The Scrivener** (Deckbound, direction B, master s6302) | per Deckbound spec (cloak, hood/head, arms, book, page, lantern, three bindings × 3 states) | `idle` 2.0 s loop, `action_tear_page` 0.6 s with `release` | binding intact/frayed/severed | Spec production requirements; cloak sway without tearing; lantern reads at 270 px |
| B3 | Non-humanoid monster | Deckbound `enemy_frayer` or a new multi-limbed creature | body, 4+ limbs/tendrils, head | idle, attack windup, hit | enraged variant | Tendrils animate with secondary motion; silhouette distinct |
| B4 | Lightweight pixel art | New 64 px pixel character | 4–6 parts or frame-based | idle, walk, hit | — | Pixel grid exact (no sub-pixel blur), palette ≤ 16 colours |
| B5 | Gameplay-variable accessories | New character with swappable armour pieces and a shield that can break | base + 3 swappable attachments | idle, block, break | armour on/off, shield intact/broken | Swaps keep pivots; no seams on swap |

Per benchmark the spec records: input artwork (or brief), expected identity (reference sheet), required layer separation, animation set and timing, gameplay states, engine preview configuration (resolution, background, camera, fps), quality criteria (Gates A–E), performance limits (atlas, memory, frame time on the Deckbound target device class).

## 3. Technical spike plan

Small, evidence-first, in the R&D environment. Each spike ends with a one-page result (Verified / failed, numbers, artefacts) in this folder. **Tier 0 needs no new dependency; later tiers need the Board's install decision (README D2).**

| ID | Tier | Question | Method | Success metric | Effort | Needs |
|---|---|---|---|---|---|---|
| S1 | 0 | Can SDXL base insert a new object with core inpaint conditioning? | latent mask vs `InpaintModelConditioning` + `DifferentialDiffusion`, 2 seeds | object present | done | — **Result: failed 0/4 (Verified negative)** |
| S2 | 0 | Can a script build a weighted Godot rig that deforms correctly in 4.6? | rig JSON → headless `@tool` builder → `.tscn` → Movie Maker frames | visual match, no flipped triangles | 2 d | Godot only |
| S3 | 0 | Does Movie Maker capture deterministic frames with alpha on this PC (headless vs windowed)? | `--write-movie` PNG, `transparent_bg` | identical frames on two runs; correct alpha | 0.5 d | Godot only |
| S4 | 0 | Can agents author clips from presets that read as good animation? | preset functions (anticipation, overshoot, follow-through) → clip JSON → Godot; contact sheets | 4 seamless loops; rubric ≥ 4/5 by `director` | 3 d | S2 |
| S5 | 1 | Does SDXL + Fooocus patch (grey pre-fill, VAE-encode-for-inpaint) insert objects? | same input/mask as S1 | object present and on-style in ≥ 3/4 | 0.5 d | node pack + patch weights |
| S6 | 1 | Does FLUX.2 klein 4B run on 12 GB/16 GB and insert/complete/keep identity? | insertion, occlusion fill, multi-reference pose change on Scrivener | runs without OOM; ≥ 3/4 insertions; identity rubric ≥ 4/5 | 1.5 d | klein 4B + Qwen3-4B encoder weights |
| S7 | 1 | Can a cheap matte replace colour keying (shadows, soft edges)? | BiRefNet / ToonOut on SOU-64 run 1 masters | no halo at 270 px; shadow removed | 0.5 d | BiRefNet/ToonOut weights + node |
| S8 | 2 | Does See-through decompose our style into usable occlusion-completed layers? | Scrivener + 10 project masters; reassembly diff; per-part rubric | ≥ 70% parts usable without repair; reassembly ≤ 2% changed px | 2 d | conda env + weights; **provenance decision D4** |
| S9 | 2 | Does a modular chain (matte + SAM 2.1 + depth + inpaint) match See-through? | same inputs as S8 | within 10% of S8 on the same metrics | 2 d | SAM 2.1, DA3 MONO-LARGE + S5/S6 editor |
| S10 | 3 | Do alpha → CDT → harmonic/BBW weights bend cleanly? | 3 parts sets incl. cloak | 90° bends, no tearing; rubric ≥ 4/5 | 3 d | PythonCDT, SciPy (pip in R&D venv) |
| S11 | 3 | Do metrics + mesh checks + vision rubric catch seeded defects? | inject 20 known defects | recall ≥ 90%, low false positives | 2 d | scikit-image, LPIPS |
| S12 | 3 | Can a video model give usable motion reference within 16 GB RAM? | Wan 2.x/LTX GGUF → pose/timing extraction | no OOM, ≤ 15 min/clip, usable timing | 2 d | video weights; **RAM decision D3** |
| S13 | 3 | Does one clip compile identically to Godot and Spine? | dual export, per-frame SSIM | SSIM ≥ 0.97 | 2 d | Spine licence; **D6** |

Order: S2, S3 (no install) → S5, S6, S7 → S8, S9 → S10, S4, S11 → S12, S13 only if the Board approves their dependencies.

## 4. Implementation roadmap

| Milestone | Content | Exit evidence | Depends on |
|---|---|---|---|
| **M0 Decisions & R&D environment** | Board decisions D1–D9; R&D ComfyUI copy; licence/provenance policy; benchmark briefs B1–B5 written | decisions recorded; R&D env hashes | this package |
| **M1 Spikes tier 0–1** | S2, S3, S5, S6, S7 | spike results; go/no-go per tool | M0 |
| **M2 Layer production prototype** (initiative Phase 3) | S8, S9 → `layer-manifest.v1`, `matte`, `segment`, `decompose`, `layer-validate` CLIs; B2 Scrivener and one more benchmark | Gate B on 2 benchmarks; repair rate measured | M1 |
| **M3 Rigging prototype** (Phase 4) | S10 → `mesh`, `rig-build` CLIs, `rig.v1`, Godot compiler; rig variants compared (full, partial, single-mesh, hybrid) | Gate C on 2 benchmarks; Rig Evaluation Report | M2 |
| **M4 Animation prototype** (Phase 5) | S4 → `motion` CLI, `clip.v1`, motion presets, baked secondary motion; S12 if approved | Gate D on B2's set; Motion Library v0 | M3 |
| **M5 Engine preview & QA loop** (Phase 6) | S3, S11 → `render`, `qa` CLIs, `qa-report.v1`, bounded repair loop, Director escalation | loop demo with caps | M3 (parallel to M4) |
| **M6 End-to-end validation** (Phase 7) | Scrivener from brief to in-engine animation, then a second benchmark in another style (B4 or B1) | Validation package (sources, manifests, rig, clips, preview video, QA report, cost report, reproduction steps) | M4, M5 |
| **M7 Studio platform** (Phase 8) | project profiles, registries, docs for agents, role updates, distribution | Gate F and G evidence on ≥ 2 styles | M6 |

Effort (rough, Board operator days, excluding agent run time): M0 2–3 · M1 4–5 · M2 8–12 · M3 8–12 · M4 6–10 · M5 5–8 · M6 5–8 · M7 5–8. Total about **45–65 working days**, highly uncertain beyond M2: each milestone re-estimates from its spike results.

## 5. Agent responsibility matrix

| Responsibility (initiative §13) | Today | Proposal |
|---|---|---|
| Art direction, quality standards, art review | `director` (read-only) | Keep; `director` reviews every spike result and gate |
| Concept, master artwork, visual iteration | `game-artist` | Keep; gains new tools only after each spike passes |
| Technical art: tool research, segmentation, reconstruction, mesh, rigging, asset pipeline | **nobody**; the Board operator (Claude Code) during R&D | Board operator during M0–M2 (decision D1); propose a **`technical-artist` agent** with exact tools after M2 evidence (decision D7) |
| Animation: motion design, keys, timing, secondary motion | nobody | Board operator builds the motion tools (M4); propose an **`animator` agent** only if M4 shows clip authoring needs a dedicated role (D7) |
| Runtime integration, state machines, performance | `gameplay-programmer` | Keep; owns engine adapters in project repositories |
| Automated validation, visual QA, benchmark runs | `qa-engineer` | Keep; gains `render`/`qa` CLIs in M5 |
| Task decomposition, budgets, milestones, risks | `producer`, `project-manager` (read-only) | Keep; tracking via Paperclip |

## 6. Dependencies

- **Hardware:** RAM (16 GB) gates S12 and Qwen 20B models; disk (85 GB free) gates more than ~3–4 new model families.
- **Licence/provenance policy** gates S8 (See-through training data) and any SAM 3 use.
- **Lifecycle (OQ-048):** tool failures strand Tasks; until fixed, every failing spike Task needs a Board round.
- **Deckbound:** SOU-64 is parked as benchmark B2; SOU-77 (rig) waits for M3 output; other pilot Tasks (SOU-65, SOU-68 done, SOU-72) can continue on today's tools.

## 7. Budget and resources (estimates)

| Item | Estimate | Type |
|---|---|---|
| Local compute | electricity only; spikes ~10–40 GPU hours | Proposed |
| Disk for R&D models | ~60–120 GB (klein 4B + encoder ~15 GB, Qwen 20B GGUF + encoder ~20 GB, See-through ~15 GB, SAM/BiRefNet/DA3 ~5 GB, one video model ~15–25 GB) | Estimate (U); exceeds today's 85 GB free with margin → storage decision |
| RAM upgrade 16 → 64 GB | one hardware purchase (Board to price locally) | Recommended before S12 and Qwen 20B |
| Spine Professional | USD 379 one-time per named user (V), only if S13 is approved after legal reading | Optional |
| Cloud/paid APIs | none proposed | — |
| Agent tokens | spikes are run by the Board operator; agent Tasks only from M2; tokens recorded, dollar cost often unavailable | Unknown |

## 8. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Automatic occlusion completion invents wrong anatomy that passes metrics | High | High | Vision rubric against the design sheet; `director` review of every new character; targeted regeneration |
| R2 | 16 GB RAM makes 20B/14B models unusable or unstable | High | Medium | Prefer 4B models; RAM upgrade decision |
| R3 | Licence or provenance problem discovered after assets ship | Medium | High | Registry review per tool; provenance policy (D4); exclude non-commercial weights |
| R4 | Automatic skin weights never reach commercial quality without humans | Medium | High | Partial-skeletal/hybrid rigs; sprite swaps for hard cases; measure in S10 |
| R5 | Style generalisation: tools trained on anime fail on painterly/pixel art | High | Medium | Benchmarks in ≥ 2 styles; modular chain fallback |
| R6 | Godot 2D IK and tooling stay experimental | Medium | Medium | Bake IK at authoring; Blender/glTF or Spine fallback |
| R7 | Vision-model judgements of animation are unreliable | Medium | Medium | Calibrate with seeded defects (S11); `director` as final reviewer |
| R8 | Board operator becomes the bottleneck for all technical art | High | Medium | `technical-artist` proposal after M2 (D7) |
| R9 | Unbounded agent repair loops waste budget | Medium | Medium | Hard caps per loop; escalation (M5) |
| R10 | Disk fills, breaking production ComfyUI | Medium | High | Separate R&D model folder on another drive or after cleanup; monitor free space |

## 9. Quality gates (initiative §14) mapped to today's stages

| Gate | Meaning | Evidence | Relation to Art Production v2 |
|---|---|---|---|
| A Artwork | identity and production quality | rubric (hard gates, scores), `director` verdict | = art-ready |
| B Animation readiness | layers, overlap, completion, pivots, reassembly | `layer-manifest` validation, reassembly diff, part rubric | new, before rig |
| C Rig quality | correct deformation in the required range | range-of-motion render, mesh sanity, rubric | new (SOU-77-type checks) |
| D Animation quality | timing, weight, anticipation, follow-through, readability | rendered clips, contact sheets, rubric by `director` | new |
| E Runtime | engine import, performance budget | engine capture, frame time, memory | = integration-ready / verified |
| F Automation | rerun without human art or animation work | run ledger, reproduction from manifests | new |
| G Reusability | ≥ 2 character types and ≥ 2 styles | M6/M7 evidence | new |

A gate passes only with recorded evidence; "runs" is not "production quality" (Gate D).
