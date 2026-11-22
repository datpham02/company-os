# Spike results

One page per spike (initiative package 03 §3; Board decision D1): question, method, n, median and worst, repair cost, artefacts, verdict. Spikes run in the R&D area `~/game-studio-workspace/rnd/` (outside every repository and outside the production ComfyUI tree); the scripts that reproduce them are kept here.

| Spike | Date | Verdict |
|---|---|---|
| [S1 object insertion with SDXL base](#s1--object-insertion-with-sdxl-base) | 2026-11-22 | **Failed** (Verified negative, one input) |
| [S3 engine capture with alpha](#s3--engine-capture-with-alpha) | 2026-11-22 | **Passed windowed; headless crashes** |
| [S2 scripted Godot rig from JSON](#s2--scripted-godot-rig-from-json) | 2026-11-22 | **Passed (mechanics)**; engine-vs-reference numeric match not measured |

## S1 — Object insertion with SDXL base
- **Question:** can SDXL base add a new object (a lantern) into empty background with ComfyUI core inpaint conditioning?
- **Method:** `s1_spike_insert.py` (ComfyUI API, R&D input folder removed after the run). Input: SOU-64 run 2 master `m3` (832×1216), feathered rectangular mask at the left cloak edge, prompt for a lantern on a hook. Variant A: latent noise mask (today's `comfy-edit` template). Variant B: `InpaintModelConditioning` (noise mask) + `DifferentialDiffusion`. SDXL base, 30 steps, cfg 7, denoise 1.0, seeds 21 and 22.
- **n:** 1 subject × 2 seeds × 2 variants = 4 (plus SOU-64 run 2's 6 attempts with the same model).
- **Result:** 0/4 contain a lantern; the model extends the cloak or leaves the backdrop. Together with SOU-64 run 2: 0/10. About 21 s per image on the RTX 3060.
- **Repair cost:** n/a (no usable output).
- **Verdict:** **Failed.** SDXL base is not an inpainting model; changing the conditioning node is not enough. Next: S5 (Fooocus inpaint patch, R&D only) and S6 (FLUX.2 klein 4B).

## S3 — Engine capture with alpha
- **Question:** does Godot 4.6.3 Movie Maker capture deterministic frames with a transparent background on the studio PC, windowed and headless?
- **Method:** R&D Godot project (`project.godot`: `viewport/transparent_background=true`, `window/per_pixel_transparency/allowed=true`, Compatibility renderer); a keyed Scrivener sprite swaying (`s2/s3_capture.gd`); `godot --path . --write-movie out/f.png --fixed-fps 30 --quit-after 30`, run twice; then the same with `--headless`.
- **n:** 2 windowed runs × 31 frames; 1 headless run.
- **Result:** windowed: **31/31 frames byte-identical** between the two runs; RGBA, background alpha 0 (155,483 of 252,928 px transparent in the middle frame), sprite alpha intact. Headless: **segmentation fault** after the first frame (the dummy renderer cannot capture).
- **Repair cost:** none.
- **Verdict:** **Passed for windowed capture** (deterministic, correct alpha). Rendering and QA capture need a windowed run on the studio PC (minimised is untested); CI cannot capture frames headless.

## S2 — Scripted Godot rig from JSON
- **Question:** can a script build a weighted Godot 4.6 rig (Skeleton2D, Bone2D, skinned Polygon2D, AnimationPlayer) from engine-neutral JSON and render it?
- **Method:**
  1. Parts: three rough parts cut from the keyed Scrivener master with `art-ops mask` + `compose` (head, front arm with book, cloak with the other two removed); full-canvas RGBA, so all share one assembly origin. No occlusion completion (that is Phase 3).
  2. `s2/make_rig.py` writes `rig.json` (schema `rig.v0`: 4 bones with pivots; per part a grid mesh over its alpha and per-bone weights; the cloak blends Root → Torso by height) and `clip_sway.json` (`clip.v0`: 2.0 s loop, eased rotation keys on Torso, Head, ArmFront), and checks every triangle at every frame with a CPU linear-blend-skinning reference.
  3. `s2/build_rig.gd` (headless `godot --script`) builds the scene from the JSON and saves `s2_rig.tscn`; a view scene instances it and the clip is rendered with Movie Maker (60 frames).
- **n:** 1 subject, 1 clip, 61 rendered frames.
- **Result:** build OK (4 bones, 3 parts: cloak 639 vertices / 1,116 triangles weighted to 2 bones; arm 139/232; head 123/200). CPU reference: **no flipped triangles** (minimum area ratio 0.938 on the cloak). Rendered frames show the cloak bending with the torso and the head and arm rotating about their joints. Visible defects all come from the test parts, not the rig: rectangular cut edges, holes where the arm and head were removed (no occlusion completion), the baked ground shadow stretching with the cloak.
- **Not measured:** numeric agreement between the engine's skinning and the CPU reference; a CDT mesh (S10) instead of the grid; exit-time resource-leak warnings from the headless builder (harmless here, to clean up later).
- **Repair cost:** none for the pipeline; the art defects are Phase 3 input requirements (clean contours, completed occlusion, no baked shadow).
- **Verdict:** **Passed (mechanics).** An agent-writable JSON rig and clip compile to a working Godot 4.6 rig without the editor. `rig.v0`/`clip.v0` are recorded in `s2/make_rig.py`; they will be revised from S8–S10 output.
