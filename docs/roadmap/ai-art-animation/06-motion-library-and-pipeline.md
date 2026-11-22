# Motion Library, Reference-driven Pipeline and Motion QA

- **Status:** `PROPOSED`, R&D. Responds to the Board directive "Animation Knowledge & Motion Reference System" (2026-11-22).
- **Builds on:** [04-animation-methodology.md](04-animation-methodology.md) (structure and motion data, solver),
  [kb/animation-fundamentals.md](kb/animation-fundamentals.md), [kb/animation-workflow-spine-godot.md](kb/animation-workflow-spine-godot.md),
  [05-motion-reference-and-licensing.md](05-motion-reference-and-licensing.md).
- **Scope:** studio level, every current and future game. Characters and projects are validation cases only.

## 1. Existing capabilities checked first

| Capability | Exists | Gap |
|---|---|---|
| Skeleton + motion data, deterministic solver, checks, QA renders | `spikes/motion/motion.py` (structure.v2, motion.v2), 20 checks | humanoid arm/leg chain types only; no creature chain library yet |
| Engine compile | S2 Godot builder (`rig.v0` / `clip.v0`), S4 Godot scenes | needs a `motion.v2` → Godot adapter (bake IK/constraints into FK keys, per kb/animation-workflow) |
| Art for rigs | `comfy-edit matte`, `comfy-draft`, `comfy-edit` | layered parts with completed occlusion (initiative Phase 3) |
| Motion reference | none | data source (CMU, CC0 packs), ASF/AMC/BVH reader, projection, retargeting |
| Agents | `game-artist`, `director` (review) | no animation role (D7 decides later; no new agent proposed here) |

## 2. Reference-driven pipeline

```
motion request (intent, character structure, gameplay events)
 -> reference selection      library search by category/tags; licence must be "production-ok"
 -> extraction               ASF/AMC/BVH parse -> per-joint 3D positions per frame (own numpy reader, no new dependency)
 -> analysis                 phases from wrist/weapon speed and height extrema; contact detection (foot height+speed)
 -> key pose identification  extrema + phase boundaries -> candidate keys (blocking set)
 -> skeleton mapping         source joints -> target joints (map per character type, stored with the motion)
 -> 3D -> 2D projection      orthographic camera ~30-35 deg off profile, 10-15 deg down; depth kept for draw order
 -> retargeting              keep each bone's DIRECTION, use the target's bone LENGTHS; feet/hands pinned by IK;
                             result baked to FK offsets of the target structure (motion.v2)
 -> character adjustment     proportions, weapon mass (timing scale), joint limits of the target, weapon attachment
 -> stylisation              stronger anticipation, held impact, exaggerated arcs - within the KB stylisation rules
 -> render + motion QA       same checks and evidence as hand-authored motion
 -> approval                 director (craft), Board (gate) -> approved motion library entry
```
Agents author original or procedural motion only when no suitable reference exists (and say so in the entry).

## 3. Motion library architecture

One entry per motion, engine-neutral, stored as data next to its evidence:

```json
{
 "schema": "motion-library-entry.v1",
 "id": "overhead_swing.heavy.two_hand.v1",
 "category": "overhead_swing",
 "tags": ["heavy", "two-handed", "weapon:hammer|axe|club"],
 "source": {"kind": "mocap|cc0-pack|authored|procedural", "origin": "CMU 79_01 chopping wood",
            "licence": "CMU: free for all uses; no resale of the data", "licence_checked": "2026-11-22",
            "production_ok": true, "attribution": "mocap.cs.cmu.edu (optional)"},
 "skeleton": {"type": "biped.humanoid.v1", "joints": ["..."], "source_skeleton": "cmu-asf"},
 "motion": "motion.v2 file (FK offsets from the type's rest pose, keys, curves, breaks)",
 "timing": {"fps": 60, "frames": 120, "phases": [["windup", 18, 46], ["swing", 46, 56]]},
 "contacts": [{"joint": "ankle_f", "frames": [[0, 50], [56, 98]]}],
 "direction": "+x", "root_motion": {"dx": 34, "dy": 0},
 "trajectory": {"weapon_head": "trajectory png + sampled points"},
 "events": [{"frame": 56, "name": "impact", "hitstop_frames": 4}],
 "retargeting": {"requires": ["two arms", "weapon attachment on hand"], "limits": "target joint_limits apply",
                 "scales": {"timing_by_weapon_mass": true}},
 "supports": ["biped humanoid", "big biped (brute)"],
 "not_for": ["quadruped", "serpent", "flying"],
 "validation": {"status": "draft|checked|director-approved|board-approved", "checks": "checks.json", "reviews": []}
}
```
Categories (Board list): idle, walk, run, jump, light attack, heavy attack, overhead swing, horizontal swing, thrust,
cast, throw, defend, dodge, hit reaction, knockback, death, creature-specific. **No motion is assumed to fit every
character:** an entry lists the skeleton types it supports, and retargeting fails loudly when the target lacks a
required chain or breaks a joint limit.

**Library rules:** raw third-party data is never committed or redistributed (CMU: no resale even converted;
Mixamo/Rokoko: no redistribution); the library stores the studio's derived `motion.v2` keys plus a pointer to the
source trial and its licence check. A source whose licence is not "production-ok" may be used for R&D only.

## 4. Motion QA: hard, soft and artistic

| Validator | Class | Applies to | Notes |
|---|---|---|---|
| Bone length consistency | hard | all rigid skeletons | FK by construction; still checked |
| Joint angle limits | hard (per structure) | per joint, per character | limits come from the structure file, never a global human table |
| Elbow/knee bend direction, IK flipping | hard where IK is used | IK chains | bend sign is a keyed channel; a flip without a key fails |
| Foot contact / foot sliding | hard | planted contacts | tolerance per contact |
| Weapon attachment (grip error) | hard | attachments | grip = hand joint |
| Rigid object geometry, single instance | hard | rigid objects | transform-only |
| Velocity continuity (pops) | hard | weapon head, hands, root | broken-tangent keys exempt by design (impacts) |
| Acceleration continuity | soft | same | flags, reviewer decides |
| Self-intersection (forearm through the face zone in held poses) | soft | humanoids | passing in front during a fast swing is allowed |
| Centre of mass inside support | soft (hard for held poses) | bipeds | lunges and jumps marked in the spec are exempt |
| Weight transfer (COM back in wind-up, forward at impact) | soft | attacks | thresholds per category |
| Timing ratios (wind-up : swing : recovery) | soft | attacks | KB rule 8 ranges; weapon mass scales them |
| Contact speed ≥ 80 % of peak | soft | strikes | KB rule 8 |
| Motion arcs (no reversal inside the swing) | soft | strikes | |
| Silhouette change at key poses | soft | all | readability at 270 px |
| Appeal, intent, style | artistic judgement | all | `director`, on real-time + slow-motion previews, never on stills alone |

**Non-humanoids:** a creature structure declares its own chains, limits, contacts and mass model; human anatomy
rules (scapula ratio, elbow ranges, face zone) apply only when the structure declares the matching chain type.

## 5. Spike results (A / B / C, same character, intent and acceptance; 2026-11-22)

Evidence per method (rnd/motion/review, review_B, review_C): real-time and slow GIF, sequential sheet, key sheet,
trajectories, joint-angle graph with limit bands, skeleton overlay, checks.json; plus a phase-matched comparison
sheet `review_C/compare_A_B_C.png`. Checks are the v2 set (20 checks incl. KB rules).

| Method | How | Checks | Main result |
|---|---|---|---|
| A | hand-authored keys, arm IK (v1) | v1: 13/13 (v2 set not applicable: no wrist, no limits) | **rejected by the Board**: forearm across the face, elbow kept bent, arm-only swing |
| B | knowledge-guided FK keys, kinetic chain, PCHIP, broken tangent at contact, KB rules | **20/20** | intent met: extended arm at impact (172°), contact speed 0.97 of peak, wind-up elbow 124°, weight back 65 px / forward 103 px; poses still found by iteration |
| C | CMU 79_01 "chopping wood" (2nd chop) → 3D FK → orthographic 3/4 projection (yaw 25°) → retarget (target bone lengths, chest-frame arm directions, clavicle → shoulder shift) → contact cleanup + hip clamp → KB wrist rule | 15/20 | most natural body: deep back arch and coil in the wind-up (COM 102 px back), whole-body drive, contact at full speed; **fails the intent**: a chop lands at chest/waist height with bent arms (impact elbow interior 105°, COM not forward), 2D projection produces impossible-looking back-arm elbow angles, and the clip does not start from the character's idle |

| Criterion (Board list) | A | B | C |
|---|---|---|---|
| Naturalness | 1 | 3 | **4** (body), 2 (impact) |
| Anatomy | 1 | 4 | 3 (projection artefacts on the far arm) |
| Weight | 2 | 3 | **4** |
| Anticipation | 2 | 3 | **5** |
| Arm extension at impact | 1 | **5** | 2 (source is a waist-height chop) |
| Weapon trajectory | 3 | **4** | 3 (wrist by rule; source has no usable hand data) |
| Ground contact | 4 | 5 | 5 (after cleanup) |
| Impact | 2 | **4** | 2 |
| Recovery | 2 | 4 | 3 |
| Automation effort | low (but wrong) | high (per-pose design by iteration) | **low per clip once the reader/retarget exist**; reference selection is the expensive step |
| Reusability | none | medium (KB rules + spec are reusable; poses are not) | **high** (map file per character type + clip; same code) |
Scores are the Board operator's first assessment on the rendered previews; `director` scores them in review.

**Findings**
1. Reference-driven motion gives the body mechanics that hand-authored keys lacked (coil, arch, timing), at low
   cost per clip - but **the reference must match the intent**: "chopping wood" is not a "ground smash". Reference
   selection is a first-class step with its own acceptance (target height, arm extension, weapon grip).
2. Mocap does not supply everything: CMU has no hand rotation and two-handed sources hide the weapon axis, so wrist
   and weapon orientation come from KB rules - the hybrid is necessary, not optional.
3. 3D → 2D projection needs cleanup (far-arm elbow flips, depth for draw order) and a transition from the
   character's idle into the clip.
4. The QA set caught every problem it was built for in all three methods; the artistic verdict still needs the
   previews.

**Recommendation:** the studio method is **C + B as a hybrid**: reference-driven body and timing (C) from a clip that
matches the intent, character-specific adjustment by KB rules where the reference is silent or mismatched (B: wrist,
weapon, impact extension, weight-forward at contact), the same QA. Next step: search a better-matching commercially
usable reference (a downward strike to the ground; CC0 packs, other CMU trials) and add the "adjustment" layer
(per-phase blend toward B's impact pose; idle-to-clip transition).
