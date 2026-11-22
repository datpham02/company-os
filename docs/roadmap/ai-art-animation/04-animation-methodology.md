# Animation Production Methodology (Board direction correction, 2026-11-22)

- **Status:** `PROPOSED`, R&D. Responds to the Board review "Animation R&D Direction Correction" (2026-11-22).
- **Prepared by:** Claude Code for the Board (decision D1: Claude Code runs the R&D, `director` reviews and presents).
- **Scope:** a studio-level animation capability. The hammer-wielding attacker (Deckbound SOU-81 image 6115) is only
  the technical benchmark: nothing here is hardcoded to that character or project.

## 1. Root cause analysis

What spike S4 did, in order, and why each round failed the Board's bar:

| Round | Method | What failed | Root cause |
|---|---|---|---|
| v1–v2 | one skinned mesh over the whole drawing, bone rotations | arm folded into the head, shoulder triangles flipped | a single drawing has no joints and no drawn anatomy for any new pose; deforming it can only bend, not articulate |
| v3–v5 | the arm cut into 2–3 rigid parts, kinetic-chain timing, a shoulder bone | still read as "an arm swinging on its own"; ragged cut edges | the parts were cut from the same single pose: no completed occlusion, no joint overlap drawn, the torso cannot turn or bend because its other views do not exist |
| beat v1 | lunge, slash effect, number, target flash | staging worked, the strike pose was still the bent drawing | staging cannot fix a missing pose |
| pose-snap | key poses generated per pose with klein reference editing | wind-up ≈ reference; weak impact pose; one seed drew a second hammer; hand–weapon relation not controlled; no in-betweens, no temporal consistency | **geometry, timing, object continuity and attachments were delegated to an image model**, which has no notion of a skeleton, a rigid object, or time |

**Root cause:** the pipeline had no motion design layer and no structural model of the character. Every attempt
started from pixels (deform them, cut them, or regenerate them) instead of from a specification of the movement and a
character structure that code can hold constant. The image model was asked to solve problems that are deterministic
(where the hand is, that there is one hammer, how long the wind-up lasts), so it solved them inconsistently.

## 2. Current pipeline limitations

1. **No motion specification.** Timing, arcs, centre of mass, contacts and events existed only inside ad-hoc code.
2. **No character structure.** No locked proportions, joint positions, hierarchy, pivots or attachment points.
3. **Weapons are pixels of the body.** The hammer is painted into every image, so it can change shape, count and grip.
4. **Art supply is one pose.** All art is a single front-three-quarter drawing; there are no layered parts with
   completed occlusion (initiative Phase 3 / M2 has not started).
5. **QA proved images, not motion.** Pose sheets were the evidence; there was no trajectory, contact, attachment or
   timing check.

## 3. Revised methodology

**Animation = a controlled transformation of a character structure over time. Generative models make artwork; code
makes motion.**

```
1. Motion design      motion spec (intent, phases, key poses, timing curves, COM, contacts, arcs, events)
2. Structure          structure spec (skeleton, proportions, pivots, attachments, contacts) - locked
3. Blocking           deterministic solver poses a proxy skeleton from 1+2; automatic checks; QA renders
                      -> the Board/director judge MOTION here, before any new artwork exists
4. Art supply         artwork for the structure: layered body parts with completed occlusion, one master asset
                      per rigid object (generation + repair tools, Phase 3 tools)
5. Skinning/binding   art bound to the same structure (rigid parts, partial mesh deformation where it helps)
6. Polish             secondary motion, effects, smears, staging (beat: lunge, hit-stop, target reaction)
7. Runtime            engine adapter (Godot first) from the same motion data; QA on engine renders
```

Rules:
- **Motion intent and constraints come before final art.** Before final artwork is produced, the motion spec records
  intent, key poses, contacts and the art requirements derived from them. The technique that produces artwork and
  motion is chosen per entity structure, art direction, motion intent and production requirements: skeletal, mesh
  deformation, pose-conditioned generation, frame-by-frame, procedural, 3D-to-2D, sprite replacement, physics or a
  hybrid (§5, [08 §5](08-universal-motion-system.md#5-motion-method-selection-criteria)). Artwork generation may run before, during or after deterministic
  blocking when the chosen technique needs it; the checks that apply to that technique still gate acceptance.
- **Locked properties are data and are checked:** bone lengths, proportions, one instance per rigid object, the grip
  transform, ground contact. A violation fails the build, not a reviewer's eye.
- **Rigid objects are independent assets** with a grip point and a pivot; they move only by transforms.
- **Generative models may produce artwork, including new poses, views and frames,** when conditioned on a structural
  input the studio controls (rig-derived pose, depth or part masks) and an identity reference. Geometry, timing and
  object continuity stay under deterministic control wherever the chosen technique needs continuity (rigged parts,
  attachments, loops). Where the technique is generative (pose-conditioned key poses, frame-by-frame, sprite
  replacement), those properties are enforced by selection gates (structure, identity, no extra or missing limbs or
  props) and measured, not assumed.
- **No technique is the studio default.** The structure and motion data are shared; each asset picks a binding
  (skeletal, partial skeletal, mesh, frame-by-frame, hybrid) by the comparison in §5.

## 4. Data model

### 4.1 Structure spec (`structure.v1`)
```json
{
  "schema": "structure.v1",
  "id": "<character id>",
  "units": "px (master canvas)",
  "joints": {"<name>": {"parent": "<name|null>", "rest": [x, y]}},
  "bones":  {"<name>": {"from": "<joint>", "to": "<joint>", "locked_length": true}},
  "masses": {"<segment>": 0.0},
  "contacts": {"<name>": {"joint": "<joint>", "ground_y": 0.0, "tolerance_px": 2}},
  "attachments": {"<object id>": {"asset": "<asset id>", "parent_joint": "<joint>",
                                  "grip": [x, y], "grip_angle": 0.0, "count": 1}},
  "objects": {"<asset id>": {"kind": "rigid", "grip_point": [x, y], "points": {"<name>": [x, y]}}}
}
```

### 4.2 Motion spec (`motion.v1`)
```json
{
  "schema": "motion.v1",
  "id": "<clip id>", "structure": "<structure id>", "fps": 60, "loop": false,
  "intent": "<one sentence: what the motion communicates in gameplay>",
  "phases": [{"name": "anticipation", "start": 6, "end": 18, "purpose": "..."}],
  "keys": [{"frame": 18, "pose": {"root": [dx, dy], "angles": {"<bone>": deg},
                                  "ik": {"<chain>": {"target": [x, y]}}},
            "ease_in": "<curve>", "ease_out": "<curve>"}],
  "curves": {"<name>": {"type": "cubic-bezier", "p": [x1, y1, x2, y2]}},
  "constraints": [{"type": "contact", "contact": "<name>", "frames": [a, b]},
                  {"type": "attachment", "object": "<id>", "frames": "all"}],
  "events": [{"frame": 42, "name": "impact", "point": "<object point>", "hitstop_frames": 6}],
  "secondary": [{"bone": "<bone>", "model": "spring", "freq": 0.0, "damping": 0.0, "driver": "<bone>"}],
  "acceptance": {"<check>": "<threshold>"}
}
```
Both are engine-neutral; adapters compile them to a Godot `AnimationPlayer` (and later Spine, initiative S13).

## 5. Technique comparison

Scale 1 (poor) to 5 (strong), for this studio (AI agents only, RTX 3060 12 GB / 16 GB RAM, 2D card-game combat).

| Technique | Quality ceiling | Determinism / continuity | Art supply needed | AI dependency | Fit for big actions | Fit for idles | Cost / complexity |
|---|---|---|---|---|---|---|---|
| Full skeletal rig (layered parts) | 4 | 5 | high: every part, completed occlusion, joint overlaps | artwork only | 4 | 5 | high once, low per clip |
| Partial skeletal (rigid limbs + body mesh) | 4 | 5 | medium | artwork only | 4 | 5 | medium |
| Mesh deformation only (one drawing) | 2 | 5 | low | none | 1 (folds, no new anatomy; S4 v1–v2) | 4 (S4 idles passed checks) | low |
| Pose-conditioned image generation | 3 | 1 (drift, extra objects; S4 pose-snap) | none | full | 2 | 1 | low per image, high review |
| Frame-by-frame (generated frames) | 5 | 1–2 | very high | full | 3 | 2 | very high |
| Procedural (springs, IK, curves) | 3 alone | 5 | none | none | 2 alone | 4 | low |
| AI motion generation (video → poses) | 3 | 2 | none | full; RAM-bound (S12) | 3 as reference only | 2 | high |
| **Hybrid: motion spec + structure + partial skeletal + rigid attachments + procedural secondary + generated artwork for parts** | **5** | **5** | medium | artwork only | **5** | **5** | medium |

**Recommendation:** no technique is the studio default. What is shared is the data and the checks (motion spec,
structure, acceptance), not a binding. The technique is selected per asset from the entity's structure, the art
direction, the motion intent and the production requirements: skeletal, mesh deformation, pose-conditioned
generation, frame-by-frame, procedural, 3D-to-2D, sprite replacement, physics or a hybrid ([08 §5](08-universal-motion-system.md#5-motion-method-selection-criteria)).
Deterministic constraints are kept where the selected technique needs geometric or object continuity. The scores
above are one operator's judgement on one character (heuristic, benchmark-specific): they inform the choice and
are not a selection rule.

## 6. Benchmark rework (hammer attacker)

One complete attack before anything else: idle → anticipation → wind-up → swing → impact → follow-through →
recovery → return to idle. No seed batches before the motion spec passes.

**Acceptance criteria (blocking pass, proxies):**
1. All 8 phases present with the durations in the spec; total length and the impact frame as specified.
2. Locked bone lengths: max deviation 0 px (FK by construction; checked).
3. One hammer, one master asset; grip error (hand joint vs hammer grip) ≤ 0.5 px on every frame.
4. Ground contact: planted feet slide ≤ 2 px while planted; lift and plant frames as specified.
5. Centre of mass: moves back during the wind-up and forward through the swing (weight transfer), and stays inside
   the support polygon except on frames the spec marks as a lunge.
6. Arcs: the hammer head path is a smooth arc (no direction reversal inside the swing; curvature continuous).
7. Anticipation and recovery: the hammer head moves opposite to the strike direction before the swing; it
   overshoots after impact and settles (follow-through), measured on the trajectory.
8. Impact readability: the impact key is held for the hit-stop frames; the silhouette at impact differs from idle
   (silhouette IoU < 0.85) and reads at 270 px.
9. Evidence: real-time and slow-motion playback, a sequential frame contact sheet, trajectory plot (hammer head,
   hand, COM), a timing graph (angles over time), contact and attachment check output.

**Art pass (after blocking approval):** body as layered parts on the same structure (generated and repaired parts with
completed occlusion), one master hammer asset with a grip point, bound to the structure; the same checks plus
silhouette comparison against the master and part identity (Gate A).

## 7. Visual QA requirements → evidence

| Requirement | Evidence (tool output) |
|---|---|
| Real-time playback | `review/*.gif` at 60 fps source, played at 30 fps |
| Slow motion | `review/*_slow.gif` (quarter speed) |
| Sequential frame contact sheet | `review/*_sheet.png`, every frame of each phase in order, phase labels |
| Motion trajectories | `review/*_trajectories.png`: hammer head, hand, COM paths with frame ticks |
| Silhouette comparison | `review/*_silhouettes.png` + IoU table (idle vs each key) |
| Weapon consistency | check: one hammer instance; hammer shape transform-only (rigid) |
| Hand-to-weapon attachment | check: grip error per frame (max) |
| Ground contact | check: foot slide per planted interval; feet plot |
| Timing | `review/*_timing.png`: joint angles and hammer angle over frames, phase bands, impact event |
| Impact readability | impact key held for hit-stop; 270 px thumbnail of the impact frame |
| Runtime performance | engine adapter: frame time and draw calls in the Godot preview (art pass) |

## 8. Deliverables status

| Deliverable | Status |
|---|---|
| Root cause analysis | §1 |
| Current pipeline limitations | §2 |
| Revised methodology | §3 |
| Motion specification schema | §4 (`structure.v1`, `motion.v1`) |
| Technical approaches + cost/complexity comparison | §5 |
| Benchmark results, rendered preview, QA findings | **blocking pass run (2026-11-22, proxies, R&D `rnd/motion/`)**: 120 frames at 60 fps, 8 phases. Technical checks: 13 of 13 passed (planar 2D proxy set of that date; it does not detect weapon-ground penetration, foreshortening or temporal coverage between key poses): bone length dev 0 px, grip error 0 px, rigid hammer dev 0 px, 1 hammer, foot slide 0 px, COM 71 px back in the wind-up and 75 px forward at impact, COM inside the support polygon on every frame, swing monotonic, wind-up opposite to the swing, follow-through overshoot 19°, no solver flags, impact silhouette IoU 0.38. Visual review: no blocking approval or visual acceptance is recorded. A pass count shows the checks ran, not that the motion is good. The checks caught two body-mechanics errors in the first spec (a rise on near-straight legs; the hips driven past the back foot: 17.7 px foot slide) and one eye-review fault each round (hammer leaving the frame; a weak horizontal wind-up). Art follows the technique chosen per §3 and §5 |
| Recommendation for a reusable implementation | §5 recommendation; tools: `motion` solver + checks + QA renderer (engine-neutral), Godot adapter |

Constraints kept: no change to budget, permissions or the agent structure; no manual art, rigging or animation by the
Board; generation only in the R&D environment until a tool passes its spike.

## 9. Knowledge and reference system (Board directive 2026-11-22, second review)

After the Board's second review (v1 forearm across the face; guesswork in poses) the R&D added: a knowledge base
([kb/](kb/)), a motion reference and licence evaluation ([05](05-motion-reference-and-licensing.md)), a motion
library, pipeline and QA design ([06](06-motion-library-and-pipeline.md)) and an Agent Skills proposal
([07](07-agent-skills-proposal.md)). Solver v2 (`spikes/motion/motion.py`): generic FK chains from `structure.v2`,
per-character joint limits, shoulder shift, PCHIP splines with broken-tangent keys, hit-stop as a runtime event.

### Recommended implementation roadmap
1. **Now:** A/B/C done (06 §5); next the hybrid C+B (a reference that matches the intent + KB adjustment layer + idle
   transition), and a `director` review of the results and of the KB content.
2. **Motion core:** ASF/AMC/BVH reader, projection and retargeting in `motion.py`; library entry format; the
   `motion.v2` → Godot adapter (bake IK and constraints into FK keys; offsets from rest; events as method tracks).
3. **Art pass on the approved motion:** layered parts with completed occlusion + the master hammer, bound to the same
   structure (initiative Phase 3 tools).
4. **Second benchmark** (a creature or a different weapon class) to prove the structure and library are not
   hammer-specific.
5. **Skills** packaged after the KB review; D7 decides who runs them.

### Required Board decisions
| # | Decision | Recommendation |
|---|---|---|
| K1 | Download CMU trials 79.asf, 79_01.amc, 80.asf, 80_71.amc (text, a few MB) into the R&D folder, parsed with own code (no new dependency) | **approved and done 2026-11-22**; method C ran (06 §5) |
| K2 | Licence policy for motion data: production use only for sources marked production-ok in 05 (CMU original data, CC0 packs); NC/research datasets R&D-only; no raw redistribution | approve |
| K3 | Mixamo: not used (Adobe ID + manual download + terms on automated access); revisit only if a Board member chooses to download clips themselves | approve |
| K4 | KB content review by `director` (craft) before it becomes agent knowledge | approve |
| K5 | Skills packaging after K4 (no new agent; D7 later decides the owner) | approve later |
