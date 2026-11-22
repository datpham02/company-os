# Spike results

One page per spike (initiative package 03 §3; Board decision D1): question, method, n, median and worst, repair cost, artefacts, verdict. Engine spikes run in the R&D area `~/game-studio-workspace/rnd/` (outside every repository); the scripts that reproduce them are kept here (`s1_spike_insert.py`, `s2/`, `s3/`). **S1 ran on the production ComfyUI server** with its already-installed SDXL base (no install; before the R&D ComfyUI of decision D2 exists); its temporary input folder `ComfyUI/input/spike/<run>/` and outputs were deleted after the run. From tier 1 on, model spikes run only in the R&D ComfyUI.

**Review status (decision D1):** `director`: changes requested, then **accepted** (SOU-80, 2026-11-22). The S2 follow-ups below go into the S8–S10 Task descriptions when they are written. `gameplay-programmer` review of S2 is still open and is due before S8 starts.

| Spike | Date | Verdict |
|---|---|---|
| [S1 object insertion with SDXL base](#s1--object-insertion-with-sdxl-base) | 2026-11-22 | **Failed** (Verified negative, one input) |
| [S2 scripted Godot rig from JSON](#s2--scripted-godot-rig-from-json) | 2026-11-22 | **Passed (mechanics)**; engine-vs-reference numeric match not measured |
| [S3 engine capture with alpha](#s3--engine-capture-with-alpha) | 2026-11-22 | **Passed windowed; headless (dummy renderer) crashes** |
| [S5 insertion, SDXL + Fooocus patch](#s5--object-insertion-sdxl--fooocus-inpaint-patch-rd-only) | 2026-11-22 | **Failed** (open 1/12; next 1/4 and 3/4 on two valid subjects; visible seams; R&D only) |
| [S6 FLUX.2 klein 4B](#s6--flux2-klein-4b-fit-insertion-completion-identity) | 2026-11-22 | Fit **passed**; insertion **failed**; completion **partial** (confounded); identity attacker 4/5, frayer 4/5, **Scrivener 2/5** (`director`) |
| [S7 cut-out: key vs BiRefNet vs ToonOut](#s7--cut-out-colour-key-vs-birefnet-vs-toonout) | 2026-11-22 | **BiRefNet passed** (leftover backdrop 0.03% median vs 2.95%) |

## S1 — Object insertion with SDXL base
- **Question:** can SDXL base add a new object (a lantern) **next to the figure, at the cloak edge**, with ComfyUI core inpaint conditioning? (Placement in open backdrop was not tested.)
- **Method:** `s1_spike_insert.py` (ComfyUI API on the production server, temporary input folder removed after the run). Input: SOU-64 run 2 master `m3` (832×1216), feathered rectangular mask at the left cloak edge, prompt for a lantern on a hook. Variant A: latent noise mask (today's `comfy-edit` template). Variant B: `InpaintModelConditioning` (noise mask) + `DifferentialDiffusion`. SDXL base, 30 steps, cfg 7, denoise 1.0, seeds 21 and 22.
- **n:** 1 subject × 2 seeds × 2 variants = 4 (plus SOU-64 run 2's 6 attempts with the same model).
- **Result:** 0/4 contain a lantern; the model extends the cloak or leaves the backdrop. Together with SOU-64 run 2: 0/10. About 21 s per image on the RTX 3060.
- **Median and worst:** n/a (binary outcome, 0 of 4 on one subject).
- **Artefacts:** none retained (the 4 outputs were deleted with the run's temporary folders); reproducible with `s1_spike_insert.py` and the SOU-64 run 2 master `art_src/characters/char_scrivener/work/m3.png` (deckbound branch `SOU-64-deckbound-m1-t18b-art-slice-the-scrivener`). The SOU-64 run 2 attempts are committed there as `inpaint_lantern_attempt1.png` and `inpaint_lantern_attempt2.png`.
- **Repair cost:** n/a (no usable output).
- **Verdict:** **Failed** for this placement: SDXL base did not insert the object next to the figure with either conditioning; changing the conditioning node is not enough there. This closes the SDXL-base insertion path (no more conditioning variants). S5 (Fooocus inpaint patch, R&D only) and S6 (FLUX.2 klein 4B) test two subjects with masks both in open backdrop and next to the figure, reported per placement.

## S3 — Engine capture with alpha
- **Question:** does Godot 4.6.3 Movie Maker capture deterministic frames with a transparent background on the studio PC, windowed and headless?
- **Method:** R&D Godot project (`s3/project.godot`: `viewport/transparent_background=true`, `window/per_pixel_transparency/allowed=true`, Compatibility renderer); a keyed Scrivener sprite swaying (`s3/s3_capture.gd`, `s3/s3_capture.tscn`); `godot --path . --write-movie out/f.png --fixed-fps 30 --quit-after 30`, run twice; then the same with `--headless`.
- **n:** 2 windowed runs × 30 PNG frames (Movie Maker also writes an audio `.wav`); 1 headless run.
- **Result:** windowed: **30/30 PNG frames byte-identical** between the two runs; RGBA, background alpha 0 (155,483 of 252,928 px transparent in the middle frame), sprite alpha intact. Headless: **segmentation fault before any image frame was written** (only Movie Maker's audio file was created; the dummy renderer cannot capture).
- **Repair cost:** none.
- **Median and worst:** n/a (deterministic comparison; one sprite, two runs, a thin sample).
- **Not checked:** partial-alpha edge pixels (a transparent Compatibility viewport may return premultiplied edges) and a minimised window; both go into the next engine spike.
- **Artefacts:** `~/game-studio-workspace/rnd/godot-spikes/out/a/`, `out/b/` (30 PNG + audio each), `out/h.log` (headless crash log); project files in `s3/`.
- **Verdict:** **Passed for windowed capture** (deterministic, correct background alpha). Headless capture with the dummy renderer crashes; a virtual-display route (software OpenGL) is untested, so capture runs windowed on the studio PC for now.

## S2 — Scripted Godot rig from JSON
- **Question:** can a script build a weighted Godot 4.6 rig (Skeleton2D, Bone2D, skinned Polygon2D, AnimationPlayer) from engine-neutral JSON and render it?
- **Method:**
  1. Parts: three rough parts cut from the keyed Scrivener master with `art-ops mask` + `compose` (head, front arm with book, cloak with the other two removed); full-canvas RGBA, so all share one assembly origin. No occlusion completion (that is Phase 3).
  2. `s2/make_rig.py` writes `rig.json` (schema `rig.v0`: 4 bones with pivots; per part a grid mesh over its alpha and per-bone weights; the cloak blends Root → Torso by height) and `clip_sway.json` (`clip.v0`: 2.0 s loop, eased rotation keys on Torso, Head, ArmFront), and checks every triangle at every frame with a CPU linear-blend-skinning reference.
  3. `s2/build_rig.gd` (headless `godot --script`) builds the scene from the JSON and saves `s2_rig.tscn`; a view scene instances it and the clip is rendered with Movie Maker (60 frames).
- **n:** 1 subject, 1 clip, 60 rendered PNG frames.
- **Result:** build OK (4 bones, 3 parts: cloak 639 vertices / 1,116 triangles weighted to 2 bones; arm 139/232; head 123/200). CPU reference: **no flipped triangles**. Rendered frames show the cloak bending with the torso and the head and arm rotating about their joints. Visible defects all come from the test parts, not the rig: rectangular cut edges, holes where the arm and head were removed (no occlusion completion), the baked ground shadow stretching with the cloak.
- **Median and worst:** per-frame minimum triangle area ratio over the 61 clip frames sampled by the CPU check (0 to 2.0 s inclusive; the render has 60): median 0.960, worst 0.938 (cloak); 1.0 means undistorted, ≤ 0 a flip.
- **Not measured:** numeric agreement between the engine's skinning and the CPU reference (the CPU check interpolates keys linearly, the Godot track is cubic, so it is a sanity check of the mesh and weights, not of the engine); a CDT mesh (S10) instead of the grid; exit-time resource-leak warnings from the headless builder (harmless here, to clean up later).
- **Artefacts:** `s2/rig.json`, `s2/clip_sway.json` (committed next to the scripts); `~/game-studio-workspace/rnd/godot-spikes/s2_rig.tscn` (generated) and `out/s2/` (60 PNG frames); the test parts are in `rnd/godot-spikes/art_src/parts/`.
- **Follow-ups (from review):** use linear track interpolation (or a cubic CPU reference) in S8–S10 so the engine can be measured; clean the builder's exit-time leak warnings when S8–S10 touch it; write the Phase 3 input requirements this spike surfaced (clean contours, completed occlusion, no baked shadow) into the acceptance criteria of the spike that produces parts.
- **Repair cost:** none for the pipeline; the art defects are Phase 3 input requirements (clean contours, completed occlusion, no baked shadow).
- **Verdict:** **Passed (mechanics).** An agent-writable JSON rig and clip compile to a working Godot 4.6 rig without the editor. `rig.v0`/`clip.v0` are recorded in `s2/make_rig.py`; they will be revised from S8–S10 output.

## Tier-1 environment (S5–S7)
**Review status (D1):** `director` accepted the S5–S7 results (SOU-82, 2026-11-22) and scored S6 identity; the wording fixes it asked for are applied below.
R&D ComfyUI `~/game-studio-workspace/rnd/ComfyUI_rnd` (port 8189, `--offline`, models in `rnd/models/`; registry entries `comfyui-rnd`, `flux2-klein-4b`, `qwen3-4b-text-encoder`, `birefnet`, `toonout`, `fooocus-inpaint-patch`, `comfyui-inpaint-nodes`; company-os PR #103). Scripts in `s5-s7/`: `download_tier1.sh` (SHA256-checked downloads), `smoke_tier1.py`, `s7_matting.py`, `s56_insert.py`. Review sheets in `s5-s7/img/`.
**Inputs (all spikes below):** the 11 house-style images approved in SOU-81 (FLUX schnell, A Ink Cel): Scrivener 6101–6104, attacker 6111, 6114, 6115, 6116, frayer 6123, 6124, 6127 (deckbound `docs/art/directions/style.md`). S5/S6 use one image per subject: Scrivener 6102, attacker 6115, frayer 6127, with 4 seeds (31–34) each.

## S7 — Cut-out: colour key vs BiRefNet vs ToonOut
- **Question:** can a matting model replace `art-ops key` (which leaves baked foot shadows and enclosed backdrop fragments, SOU-79/SOU-81)?
- **Method:** `s5-s7/s7_matting.py`: each of the 11 inputs cut out three ways: `art-ops key --tolerance 35 --soft 8` (as the agents use it), BiRefNet and ToonOut (core `RemoveBackground`). Metrics per cut-out: *leftover backdrop* = opaque pixels within 40 of the backdrop colour (% of opaque pixels); interior alpha distribution; a *shadow band* heuristic; plus a visual sheet on `#1B2026` (`img/s7_compare.png`: Scrivener 6102, attacker 6115, frayer 6127).
- **n:** 3 subjects, 11 images (frayer 3), 3 methods.
- **Result:**

  | Method | Leftover backdrop median | worst | Visual (sheet) |
  |---|---|---|---|
  | `art-ops key` | 2.95% | 24.76% (frayer 6127) | foot shadows and large white fragments kept |
  | **BiRefNet** | **0.03%** | **0.14%** | clean: no shadow, no fragments |
  | ToonOut | 0.05% | 1.17% (Scrivener 6102) | clean except a pale patch kept beside the Scrivener's book |

  Interior alpha of both models is not a hard 255 (median 254; 1st percentile 229–248 on the three images checked, 6101–6103): the figure is about 1% translucent unless alpha ≥ 250 is snapped to 255. The *shadow band* metric is **not reliable** (it also counts the grey hems and grey feet as "shadow"); shadows were judged on the sheet.
- **Median and worst:** above (leftover backdrop); visual judgement on 3 of 11 images.
- **Repair cost:** none; ~4 s (BiRefNet), ~2 s (ToonOut) per image.
- **Verdict:** **BiRefNet passed**: on the leftover-backdrop metric for all 11 images and, by eye, on the 3 sheet images it removes the foot shadows and enclosed fragments that `key` leaves. It closes the SOU-64/79/81 "tool capability failure (cut-out)" **once a matte tool with the alpha snap exists** for agents. It needs an alpha snap (≥ 250 → 255) before production. ToonOut is no better than BiRefNet on this style and is R&D-only by licence: **not taken further**. Production use of BiRefNet needs a Board decision (a CLI around it for agents).

## S5 — Object insertion: SDXL + Fooocus inpaint patch (R&D only)
- **Question:** does SDXL with the Fooocus inpaint patch (grey pre-fill, VAE-encode-for-inpaint, denoise 1.0) insert an object, in open backdrop and next to the figure?
- **Method:** `s5-s7/s56_insert.py s5`. Masks from each figure's BiRefNet alpha: *open* = 200×280 box on the backdrop, clear of the figure; *next* = 180×260 box on the figure's left edge at mid height. Prompt: a small iron lantern, A Ink Cel style words. 24 steps, cfg 7; result composited back through the feathered mask (exact outside it).
- **n:** 3 subjects × 2 placements × 4 seeds = 24.
- **Result** (lantern present and on-style, judged on `img/s56_fooocus_*.png`):

  | Subject | open | next |
  |---|---|---|
  | Scrivener | 0/4 (one dark blob) | **invalid test**: the *next* box covered the Scrivener's existing lantern, so the model repainted that lantern |
  | attacker | 0/4 | 1/4 |
  | frayer | 1/4 | 3/4 (+1 shape without detail) |

  In open backdrop the patch leaves a **visible lighter rectangle** (the repainted backdrop does not match the original's tone) on most seeds. ~24 s per image.
- **Median and worst:** open 0/4 median over 3 subjects (worst 0/4; best 1/4); next: 1/4 (attacker) and 3/4 (frayer), n = 2 valid subjects, no median.
- **Repair cost:** n/a (failed).
- **Verdict:** **Failed** the S6/S5 bar (insertion median ≥ 3/4). Better than SDXL base next to a figure (S1: 0/10), but unusable in open backdrop and with visible seams. R&D only by licence anyway.

## S6 — FLUX.2 klein 4B: fit, insertion, completion, identity
- **Question:** does klein 4B run on 12 GB VRAM / 16 GB RAM, and how well does it insert, complete hidden areas and keep identity? (three results reported separately, per the director's amendment)
- **Method:** `s5-s7/s56_insert.py s6`, R&D ComfyUI, 4 steps, cfg 1, euler/simple. *Insert* and *complete*: the input image as a `ReferenceLatent`, the VAE-encoded input with a latent noise mask, instruction prompt; result composited back through the mask. *Identity*: no mask; the input as `ReferenceLatent` and a prompt for a new pose of "the same character".
- **Licence:** FLUX.2 klein 4B and the FLUX.2 VAE Apache-2.0, Qwen3-4B text encoder Apache-2.0, as recorded in the `flux2-klein-4b` and `qwen3-4b-text-encoder` registry entries (company-os PR #103).
- **Fit:** **passed** (peak VRAM and RAM were not measured, so the margin to 12 GB / 16 GB is unknown): 40 klein generations at 832×1216 (24 insertion, 4 completion, 12 identity) without out-of-memory; ~17 s per image (warm). (The 64 images of S5 and S6 together include S5's 24 SDXL runs.)
- **Insertion** (`img/s56_klein_*.png`), n = 3 × 2 × 4:

  | Subject | open | next |
  |---|---|---|
  | Scrivener | 0/4 | invalid test (same mask problem as S5) |
  | attacker | 0/4 | 2/4 (+1 hook without lantern) |
  | frayer | 0/4 | 4/4 (one seed drew two lanterns) |

  In open backdrop klein leaves the backdrop unchanged and **seamless** (no rectangle), but adds nothing. Open 0/4 on all 3 subjects; next 2/4 (attacker) and 4/4 (frayer), n = 2 valid subjects, no median. **Failed** the bar overall; **next to the figure it works on one subject of two**.
- **Completion** (`img/s56_complete.png`), Scrivener, n = 4: remove the held book and hand and paint the cloak behind. The mask (derived from the brightest pale block) also covered the lantern, so the lantern is removed too (**mask design error**). Cloak repainted plausibly on 4/4; nearly clean on 1/4 (s31, a faint chain stub remains); a leftover hand on 2/4 and a dark slab on 1/4. **Partial on cloak repaint (1–2 of 4 usable); the intended test (book and hand only, lantern untouched) was not run.**
- **Identity / new pose** (`img/s56_identity.png`), n = 3 subjects × 4 seeds:
  - attacker 4/4 and frayer 4/4 keep the design (shapes, colours, seal, apron, robe, tail) and the A Ink Cel style in a clearly new pose (mallet swung down; crouching with hands forward);
  - Scrivener 4/4 keep the hooded cloak, teal cords and style with the book raised, **but** turn to a front view with a visible face, lose the lantern, and draw **text-like marks on the open book pages** (fails the no-text rule).
  - **`director` score (Gate A, against the SOU-81 house-style images; provisional until the sheets are seen in a deckbound Task):** attacker **4/5**, frayer **4/5**, Scrivener **2/5** (the character is faceless with a visible chin only; the lantern is a silhouette accent; text on pages breaks the no-text rule). Median 4/5, worst 2/5. One target pose per subject only.
  - **Repair cost (identity):** Scrivener outputs would need re-facing, the lantern re-added and page marks removed; attacker and frayer none.
- **Verdict:** fit **passed**; insertion **failed** with this method (masked latent noise + reference); completion **partial** (confounded by the mask); identity: **the first tool tested that keeps design and style in a new pose for the attacker and frayer (4/5)**; it **fails Gate A for the Scrivener (2/5)** and is blocked for Scrivener assets until a re-test passes ("facing right, hood hiding the face, pale chin only", "lantern on a hook in the back hand", "closed contract book", a no-text check per output).
- **Not tested (next variant):** klein **instruction edit on the whole image** (no latent noise mask) then the exact outside-mask restore; collage-then-harmonise (paste a separately generated object, then a low-denoise pass over the seam).

## Consequences
(Revised with the `director`'s SOU-82 conditions.)
1. **Cut-out:** BiRefNet replaces colour keying for figures. **Approved by the Board 2026-11-22 and built as `comfy-edit.py matte`** (company-os PR for the matte template). Was proposed, **recommended by `director` for Board approval**: a `matte` CLI for agents (Phase 2B-style tool) with the alpha snap built in (threshold as a flag), the leftover-backdrop metric run inside the tool and failing loudly, the enclosed-backdrop case (SOU-81 lantern halo) in its tests, `key` kept for flat non-figure assets, and the licence from the `birefnet` registry entry.
2. **Insertion:** neither tool inserts reliably in open backdrop; next to a figure klein reaches 4/4 on one subject. Rig objects are separate parts, so open-backdrop insertion matters little; **first** run the completion re-test (book and hand only, lantern untouched, two subjects, 4 seeds), then the two untested insertion variants, with masks validated against the image, the bar stated before the run and at least three valid subjects.
3. **Identity:** klein reference editing feeds S4 and Phase 3 only with these gates: at least three poses per subject and a measure of pose-instruction adherence; the Scrivener re-test; a per-image no-text check; S4 tests frame-to-frame coherence (a different question from one new pose). The reveal-area use rests on the identity result, not on the partial completion result. klein for production is a later Board decision after the Scrivener re-test.
4. **Experiment design errors to avoid next time:** check each mask against what is already in the image (the Scrivener *next* box sat on its lantern; the completion mask covered the lantern); state each bar before the run; two subjects give no median.
5. **Licences:** S5's Fooocus patch and ToonOut stay R&D only; nothing from S5 is a production candidate.
