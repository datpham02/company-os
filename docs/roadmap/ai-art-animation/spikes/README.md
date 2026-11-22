# Spike results

One page per spike (initiative package 03 §3; Board decision D1): question, method, n, median and worst, repair cost, artefacts, verdict. Engine spikes run in the R&D area `~/game-studio-workspace/rnd/` (outside every repository); the scripts that reproduce them are kept here (`s1_spike_insert.py`, `s2/`, `s3/`). **S1 ran on the production ComfyUI server** with its already-installed SDXL base (no install; before the R&D ComfyUI of decision D2 exists); its temporary input folder `ComfyUI/input/spike/<run>/` and outputs were deleted after the run. From tier 1 on, model spikes run only in the R&D ComfyUI.

**Review status (decision D1):** `director`: changes requested, then **accepted** (SOU-80, 2026-11-22). The S2 follow-ups below go into the S8–S10 Task descriptions when they are written. `gameplay-programmer` review of S2 is still open and is due before S8 starts.

| Spike | Date | Verdict |
|---|---|---|
| [S1 object insertion with SDXL base](#s1--object-insertion-with-sdxl-base) | 2026-11-22 | **Failed** (Verified negative, one input) |
| [S2 scripted Godot rig from JSON](#s2--scripted-godot-rig-from-json) | 2026-11-22 | **Passed (mechanics)**; engine-vs-reference numeric match not measured |
| [S3 engine capture with alpha](#s3--engine-capture-with-alpha) | 2026-11-22 | **Passed windowed; headless (dummy renderer) crashes** |

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
