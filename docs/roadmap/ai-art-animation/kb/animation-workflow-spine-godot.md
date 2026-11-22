# Professional 2D skeletal animation workflow -> data-driven pipeline (Godot 4.6)

> **Status:** `PROPOSED` (Professional 2D workflow mapped to the studio's data model). Compiled 2026-11-22 by a Claude Code research agent for the Board in the studio's own words, with source links and an evidence tag per rule; thresholds tagged *derived* are starting points to tune, not facts. Reviewed by the Board operator for structure and quoting; content review by `director` pending.


Research date: 2026-11-22. Main sources: Esoteric Software (Spine) user guide, Godot stable docs. The stable Godot docs are currently **4.7**; class pages for the 2D skeleton APIs read the same as the 4.0–4.3 versioned pages, so the 4.6 behaviour is assumed to match. A 4.6.2 forum thread also confirms `SkeletonModificationStack2D` is still in use in 4.6. Everything below is paraphrased. Items marked **[inference]** are my synthesis, not a source claim.

---

## 1. The professional workflow

### 1.1 Setup (rig) mode vs animate mode
- Spine separates **setup mode**, where you build the bone hierarchy, attachments, slots, draw order, constraints and weights and define the *setup pose*, from **animate mode**, where you only create keys. Keys can only be made in animate mode with an animation active.
- **Bone transform keys are stored relative to the setup pose.** If you change the setup pose, every animation changes with it. Unkeyed property values fall back to the setup pose.
- Moving mesh vertices in setup mode changes the base shape. Moving them in animate mode creates deform keys, so the mode decides what an edit means.
- Weight testing should be done by posing bones in *animate* mode, so the setup is not changed by accident.
- Rigging notes (spine-bones): there is one root bone, and scaling it scales the whole skeleton. A new bone created from a parent starts at the parent's tip. Bone length only matters for IK, path constraints and auto-weights. Per-bone inherit flags (rotation, scale, reflection) exist, but bones under an IK constraint cannot turn inheritance off. Non-uniform parent scale can still change a child's angle. Negative scale is used for flipping, and a per-bone "reflection" flag controls whether the bone mirrors.
- Two-handed weapon rig (Spine blog): the `weapon` bone is parented to **root**, not to the body, so the weapon moves on its own path and the hands follow it, not the other way round.

### 1.2 Keying approaches (spine-animating)
Spine describes four approaches:
- **Straight ahead**: key frame after frame in order. Best for path-like motion such as an effect trail or a falling leaf. It is easy to lose control of timing.
- **Pose to pose (blocking)**: set the major poses first, then fix timing, then fill in the in-betweens. Early changes are cheap. Previewing with *stepped* playback (no tweening) shows only the key poses.
- **Layered**: animate a few parts per pass with the rest hidden, e.g. **hips + torso first, then legs, then arms**. It needs body-mechanics knowledge, and the parts can feel disconnected.
- **Combined**, which is what professionals usually do: block the poses that must read, then make layered straight-ahead passes on subsets of parts.

### 1.3 Blocking -> splining -> polish (industry pipeline; Spine tools map onto it)
1. **Blocking**: key the extremes and contact poses on all major bones, with curves set to **stepped**. Use "Key Shown" (key every visible channel) so each pose is a full snapshot. Timing is rough.
2. **Breakdowns**: add the poses that show *how* the body gets from A to B (arcs, lead/follow). Spine's graph has a **favor slider** for this: it blends between the neighbouring keys, and dragging past the end of the slider gives overshoot.
3. **Splining**: switch the keys to **bezier**. Start with *Automatic* handles (computed from neighbouring keys) and fix individual keys only where needed. Use *Flat* on holds and extremes, *Separate/Bounce* for sharp direction changes (a cusp at impact), and *Ease in/out* for settles.
4. **Polish**: offset timing between parts for overlap and follow-through (secondary bones lag by a frame or two), add settle and overshoot keys, and check loops with the graph's *Repeat* view (curves drawn faintly before and after the loop). Remove redundant keys ("Clean Up"), but not in layered animations, where keys equal to the setup pose may be needed to override lower tracks.
- **Which bones first**: root/hips (centre of mass, weight shift, bob), then torso/chest, then legs/feet contacts, then arms, then head, then secondary bones (hair, cloth, weapon trails). This follows Spine's layered example and standard practice.
- Linear timing everywhere looks robotic. The variety of curves is what makes motion feel alive (spine-animating).

### 1.4 Graph editor and ghosting
- The dopesheet is for **timing** (move or scale keys in time). The graph is for **values and curve shape** (spine-graph tip).
- Curve types per key: **stepped** (hold until next key; used for visibility/attachment swaps), **linear**, and **bezier** (handles). A new key inserted between bezier keys keeps the existing curve shape.
- Channels can be **separated** (translate X and Y, colour RGB vs alpha) so each has its own keys and curve. Rotation is in local axes and translation is in parent axes.
- Timing-only edits can keep either the curve's value extremes or its shape.
- **Store/Swap** keeps a reference copy of the curves so you can A/B compare a revision.
- **Ghosting (onion skin)** shows poses before and after the current frame, every N frames or only on key frames. **Motion vectors** show the speed of vertices. A key professional use is checking **foot sliding**: set the ghost X-offset to the character's runtime speed (px/frame) and the planted foot should land in the same place in every ghost.
- Looping: the first and last keys must match. Spine's *Offset* tool rotates keys around the loop point. Keys at fractional frames (e.g. 30 and 30.01) give an instant jump.
- Auto-key is convenient but creates unwanted keys. Pros key explicitly ("Key edited" or "Key shown").

### 1.5 Common tips
- Default to Automatic bezier handles. Keep stepped curves for anything discrete.
- Key complete poses while blocking. Thin out the keys later.
- Build a "range of motion" test animation that moves every bone through its full range; use it while weighting meshes and tuning constraints.
- Hide attachments while blocking the body to cut visual noise.
- Hide parts by keying the slot's **attachment to none**, not alpha 0: transparent images still cost fill-rate, and a hidden visibility dot is not keyable.

---

## 2. IK in 2D

- **One-bone IK** turns a bone to point at a target. It can **compress** (shorten) when the target is closer than the bone's length.
- **Two-bone IK** places the child's tip on the target. Parent and child must be direct parent/child. Chains of three or more bones are not supported: use several constraints or FK.
- **Bend direction**: two-bone IK in 2D has exactly two solutions. Spine exposes this as a boolean `bendPositive` (child rotates counter-clockwise relative to the parent when true). **It is keyable**, and flipping the elbow or knee means keying this flag, never dragging the target across the line between root and target. Godot's equivalent is `flip_bend_direction` on `SkeletonModification2DTwoBoneIK` (true = bend outward when contracting).
- **Mix (FK/IK blend, 0–100)**: used briefly to hand off into or out of IK, or to layer IK on top of FK motion. **Flip hazard**: at a partial mix, moving the target can make the blended rotation suddenly go the other way, because the blend takes the shortest rotation path. Spine's mitigation is to keep partial mixes short and transitional. **[inference]** Our pipeline should also keep unwrapped angles and blend on the continuous angle.
- **Softness**: the bones slow down as they near full extension, which avoids the "snap" just before the limb straightens. The value is how far past maximum reach the slowdown starts. Stretch is not applied while softness is above 0.
- **Stretch / Compress / Uniform**: scale bones to reach targets that are too far or too close. Stretch and Compress are keyable. Uniform scales both axes.
- **Avoiding flips in practice** (Spine + general practice): (a) set the bend direction explicitly per pose; (b) keep the target inside the reachable annulus, which softness helps with; (c) don't partially mix while the target sweeps past the root–target line; (d) don't put a target under the bones it constrains (Spine forbids it); (e) mirroring the character with negative scale also mirrors the bend sign. A Godot 4.6.2 user hit legs twisting when flipping via `scale.x = -1` with a 2D IK stack, and fixed it by rebuilding the rig and rest pose.
- **Feet on ground**: IK target bones for the feet are parented to **root**, not to the hips. The hips bob with FK keys, and the feet stay planted because their targets don't move. Targets can be adjusted at runtime for uneven terrain (spine-ik-constraints). Check for sliding with ghosting.
- **Arms holding a weapon** (Spine "Holding a two-handed weapon"): the weapon bone sits under root. `hand-on-weapon-l/r` bones are children of the weapon. A two-bone IK on each arm targets them, and a **transform constraint** on each hand copies the weapon's rotation (with an offset). All mixes are **0 in setup** and are **keyed to 100** while the character holds the weapon, then back to 0 to let go. One rig then works for pistol, spear, shotgun and so on. Trade-off: driving both hands from one constraint is simpler but you cannot release one hand.

## 3. Attachments, weapons and draw order

- **Slot** = a depth-ordered container parented to a bone. It shows **one** attachment (or none) at a time. Slots of the same kind are grouped: a `weapon` slot holds the knife, sword or axe.
- **Weapons are rigid region images** in a weapon slot on a weapon/hand bone. A mid-animation swap is a **stepped attachment key** on the slot.
- **Skins / placeholders**: animations key a *placeholder* name (e.g. `weapon`), and the active skin supplies the real image. That keeps animations independent of which weapon is equipped. Skins can be mixed and matched (one per item). Skins can also add bones and constraints that exist only while the skin is active.
- **Draw order** is the list of slots. **It is keyable**, e.g. the weapon swings behind the body during wind-up and passes in front on the strike, or the far arm crosses in front. Keeping weapons in one slot keeps the draw order manageable.
- **Slot colour** is keyable (tint, fade before hiding). Blend modes other than normal (additive etc.) may add draw calls. Good for slash flashes.
- Transform constraints also cover "pick up / equip / throw" (a bone follows another bone), and "place a bone at X% between two bones".

## 4. Mesh deformation and weights

- **When to use**: parts that must bend (torsos, sleeves, tails, faces, squash/stretch), or to trim transparent space for fill-rate. Rigid parts such as weapons, armour plates and most hands stay as plain regions.
- **Weights**: each vertex's bone influences sum to 100%. Auto-weights use mesh topology, Smooth spreads weights, and **Prune** caps bones per vertex and drops tiny weights, because every influence costs a vertex transform each frame.
- **Prefer weights over deform (per-vertex) keys.** Deform keys move vertices in straight lines, are heavy, and are wiped by mesh edits.
- **Pitfalls**: weights must be bound in the setup/bind pose; editing weights after bones were rotated moves vertices ("Update bindings" re-binds). Regenerating or retracing the mesh **deletes all weights and deform keys**. Holes are not supported. A hull that cuts through opaque pixels gives jagged edges. Too many vertices cost CPU. Unwanted bending happens where there are no internal vertices. Godot's tutorial has the same advice: add internal vertices where bending should happen, and weight them too.
- **Godot**: `Polygon2D` with `skeleton` set, a bone list (`add_bone(path, weights)`, one weight per vertex) and `internal_vertex_count`. The bone list is **synced by hand** ("Sync Bones to Polygon") and must be re-synced when bones are added, removed or renamed. Weights are per-vertex floats per bone; white = 1, black = 0.

## 5. Godot 4.6 specifics

| Area | What exists / how it behaves |
|---|---|
| `Skeleton2D` | Container. Bones are indexed depth-first. `set_bone_local_pose_override(idx, xform, strength, persistent)`, `set_modification_stack()`, `execute_modifications(delta, mode)`. Not marked experimental. |
| `Bone2D` | A `Node2D` with `rest` (a Transform2D relative to its parent), `apply_rest()`, `length`, `bone_angle`, `autocalculate_length_and_angle` (computed from the first Bone2D child, so **leaf bones need an explicit length and angle**). Bones point along +X by default. |
| Rest pose | Editor: Skeleton2D menu > "Overwrite Rest Pose". Bones show a warning until it is set, and it must be redone when bones are added or removed. In code, set `rest` on each bone yourself. |
| Skinning | `Polygon2D.skeleton` plus per-bone weight arrays, `polygons` (triangulation index arrays), `uv`, `internal_vertex_count`. The arrays return copies, so reassign them after editing. |
| 2D IK | **Exists but experimental** ("may be changed or removed"): `SkeletonModificationStack2D` (enabled, strength, modification_count; **order matters**, e.g. spine before arms) and `SkeletonModification2D` subclasses **TwoBoneIK, CCDIK, FABRIK, LookAt, Jiggle, PhysicalBones, StackHolder**. TwoBoneIK uses the law of cosines on exactly two bones, with `target_nodepath`, `flip_bend_direction`, `target_minimum_distance`, `target_maximum_distance`, and joints set through setters (`set_joint_one_bone2d_node` / `..._idx`). `clamp_angle` is available for limits. Godot 4.3+ added the new `SkeletonModifier3D` system for **3D only**; 2D did not get an equivalent. |
| Driving bones | AnimationPlayer **value tracks** on `Bone2D:position`, `:rotation`, `:scale` (paths like `Skeleton2D/hip/torso:rotation`). Keys are **absolute local values, not offsets from rest** (unlike Spine). Interpolation types: NEAREST, LINEAR, CUBIC, **LINEAR_ANGLE / CUBIC_ANGLE** (shortest-path rotation; the output is normalized). Update modes: CONTINUOUS, DISCRETE, CAPTURE. Loop modes: none, linear, ping-pong. `track_set_interpolation_loop_wrap`. |
| Bezier tracks | `TYPE_BEZIER` with per-key in/out handles (`bezier_track_insert_key(track, t, value, in_handle, out_handle)`), and can target sub-properties. **Not blendable in AnimationPlayer/AnimationTree**, so they are a poor fit for characters that crossfade. |
| Events | `TYPE_METHOD` call-method tracks (don't fire in the editor preview), audio tracks, animation tracks. |
| Attachments / draw order | No slot concept. A weapon is a `Sprite2D` child of a Bone2D. A swap is a DISCRETE value track on `texture`/`visible`/`frame`. Draw order is a DISCRETE track on `z_index` (or `show_behind_parent`), or a CanvasGroup reorder. |
| Limitations | Modification stack is experimental and only lightly maintained. Mirroring via negative scale can twist IK legs (4.6.2 report). Rest pose and polygon bone sync are manual steps. Bezier tracks don't blend. There is no built-in physics constraint (Jiggle is the nearest). The 2D skeletons tutorial page itself says it is not updated for 4.7. **[inference]** Whether the IK stack previews in the editor during AnimationPlayer scrubbing has to be tested on 4.6 before we rely on it. |

**[inference] Recommended Godot strategy:** bake IK into FK keys at compile time for authored animation, and use runtime 2D IK only for procedural adjustments such as foot planting on slopes or aim. This removes the dependency on an experimental API for the core content.

## 6. Mapping table: concept -> data -> Godot adapter

| Professional concept | Structure JSON (rig) | Motion JSON (anim) | Godot 4.6 adapter emits |
|---|---|---|---|
| Root bone | `joints[0]` named `root`, no parent, at the ground contact point | root translate keys only for in-place vs root-motion choice | `Skeleton2D` > `Bone2D root` |
| Setup / rest pose | per joint `rest: {x,y,rot,scale}` in parent space, `length`, `angle` | keys are **deltas from rest** (Spine convention) | `Bone2D.rest` = rest; `transform` = rest; explicit `length`/`bone_angle` (autocalc off); a `RESET` animation holding rest |
| Hierarchy (hips first) | `parent` per joint; hips is the parent of torso and both thighs | key order and blocking pass recorded as metadata only | node tree that mirrors `parent` |
| Joint limits | `limits: {rot_min, rot_max}` | n/a (validated) | compile-time clamp + lint error; optional `clamp_angle` in runtime IK |
| FK keys | — | `tracks[joint].rotate/translate/scale: [{t, v, curve}]`, channels separable (x/y) | value tracks `Bone2D:rotation` (CUBIC_ANGLE or LINEAR_ANGLE), `:position`, `:scale`; value = rest + delta |
| Curves (stepped/linear/bezier/presets) | — | `curve: "stepped" \| "linear" \| "auto" \| "flat" \| "ease_in" \| "ease_out" \| [cx1,cy1,cx2,cy2]` | stepped -> NEAREST; linear -> LINEAR; others -> **resample into dense LINEAR/ANGLE keys** at e.g. 30–60 fps (keeps blendability), or CUBIC for `auto` |
| Rotation continuity | — | angles stored **unwrapped** (may exceed ±180) | LINEAR/CUBIC (not _ANGLE) when the author spins >180°, else _ANGLE; compiler decides per segment |
| IK chain | `chains: [{name, bones:[upper,lower], target, bend:+1/-1, softness, stretch:false}]` | `ik: {chain: [{t, target:{x,y}, mix, bend}]}` | **default: solve at compile time and bake rotations into FK tracks**; optional runtime: `SkeletonModificationStack2D` + `TwoBoneIK(flip_bend_direction = bend<0)` for procedural use |
| IK target bones | targets are joints parented to `root` (feet) or `weapon` (hands) | target keys in the target's parent space | Bone2D/Node2D targets; baked when compiling |
| FK/IK mix | `chains[].mix_default` (0 in setup) | keyed `mix` 0..1 (stepped or short ramps) | baked: per-frame blend of FK and IK solutions on unwrapped angles |
| Bend flip | `bend` default | keyed `bend` (stepped only) | baked; runtime: discrete track on `flip_bend_direction` |
| Transform constraint (hand follows weapon) | `constraints: [{type:"follow", bone, target, channels, offset}]` | keyed `mix` | baked into FK; runtime: RemoteTransform2D (rot/pos/scale flags) |
| Physics / secondary | `secondary: [{bone, inertia, strength, damping}]` | optional `mix` keys | baked overlap pass at compile time, or runtime `SkeletonModification2DJiggle` |
| Attachment / slot | `slots: [{name, bone, z, default, attachments:{name: {image, offset, pivot, rot}}}]` | `attachments: [{t, slot, name\|null}]` (always stepped) | Sprite2D per attachment under the Bone2D; DISCRETE `visible` tracks (or one Sprite2D with DISCRETE `texture`) |
| Skins / weapon placeholders | `skins: {name: {slot.placeholder: image}}` | keys reference **placeholder names** | adapter resolves the skin at build time or exposes `set_skin()` that swaps textures |
| Draw order | `slots[].z` setup order | `draw_order: [{t, slot, z}]` (stepped) | DISCRETE `z_index` tracks (z relative); `z_as_relative` kept true |
| Slot colour / flash | `slots[].color` | `color: [{t, rgba, curve}]` | value track `modulate` / `self_modulate` |
| Mesh + weights | `meshes: [{slot, image, vertices, uvs, triangles, internal_count, weights:[{bone, w[]}]}]`, max 4 bones per vertex, normalized | prefer bones over deform keys; `deform` keys discouraged | Polygon2D with `skeleton`, `polygon`, `uv`, `polygons`, `internal_vertex_count`, `add_bone(path, PackedFloat32Array)` in skeleton bone order |
| Events | — | `events: [{t, name, args}]` (hit frames, footsteps, SFX) | METHOD track calling e.g. `_on_anim_event(name, args)`; AUDIO track for sounds |
| Loop | — | `loop: true`, first key == last key enforced | `loop_mode = LOOP_LINEAR`; loop_wrap on |
| Ghosting / foot-slide check | `ground_y`, `move_speed_px_per_s` | — | (tooling) compiler renders onion-skin contact sheet + foot-slide metric |
| Facing/mirroring | `mirror: {axis:"x"}` | — | flip by `scale.x = -1` on a parent Node2D; runtime IK must invert bend; prefer baked IK |

## 7. Concrete recommendations for our pipeline

1. **Store motion keys as deltas from the rig's rest pose** (Spine model). The Godot adapter writes `rest + delta`, because Godot keys are absolute. Rig tweaks then carry into every animation, matching artist expectations.
2. **Always emit a `RESET` animation and set `Bone2D.rest`** from the structure JSON. Set explicit `length`/`bone_angle` and turn autocalculate off so leaf bones (hands, head, weapon) are deterministic.
3. **Bake IK and constraints to FK at compile time** by default: solve two-bone IK analytically (law of cosines) with the keyed `bend` sign, softness and limits, then write plain rotation tracks. Reserve Godot's experimental `SkeletonModificationStack2D`/`TwoBoneIK` for an opt-in runtime layer (slope foot-planting, aiming) behind a feature flag, with its own test scene on 4.6.
4. **Make bend direction explicit and stepped** on every IK chain and every pose. Lint-fail any partial-mix (0<mix<1) segment where the target crosses the chain's root–target line or where the solution's bend sign would flip.
5. **Keep angles unwrapped in the motion JSON** and choose the Godot interpolation per track: `_ANGLE` types only when no segment exceeds 180°, otherwise LINEAR/CUBIC on unwrapped values. Add a lint for >180° jumps between neighbouring keys.
6. **Support curve presets (`stepped`, `linear`, `auto`, `flat`, `ease_in`, `ease_out`, explicit bezier)** in the motion JSON, and compile non-linear curves by **resampling to dense keys** on blendable value tracks. Do not use Godot Bezier tracks for character animation, because they cannot blend in AnimationTree.
7. **Write authoring agents' instructions to follow blocking -> breakdowns -> splining -> polish**: pass 1 stepped full-pose keys (root/hips, torso, legs, arms, head) on contact/extreme frames; pass 2 breakdowns; pass 3 switch to `auto` curves; pass 4 offset secondary bones by 1–3 frames for overlap and add settle/overshoot. Store `pass` metadata so reviewers can check each stage.
8. **Parent foot IK targets and weapon to `root`**, not to hips or hands. Hands follow the weapon through `hand_on_weapon_l/r` target joints with IK + follow constraints whose `mix` is 0 in rest and keyed to 1 while the weapon is held (Spine's two-handed weapon pattern).
9. **Model weapons as slot attachments** (rigid Sprite2D on the hand/weapon bone) with placeholder names resolved by skins, so one attack animation works for any weapon of the same class. Attachment, draw-order and bend keys are always stepped.
10. **Key draw order explicitly in attacks** (`draw_order` track -> DISCRETE `z_index`), e.g. weapon behind body on wind-up and in front on the strike. Lint for slot z collisions.
11. **Emit gameplay events (`hit`, `footstep`, `sfx`) as METHOD tracks** with a single dispatcher method, so gameplay timing lives in the animation data and stays in sync with the frames.
12. **Enforce loop closure** (first key == last key per channel for looping clips) and build a **foot-slide check**: the compiler samples the planted foot's world X over a cycle, subtracts `move_speed`, and fails if drift exceeds N px. This is the automated version of Spine's ghost-offset trick.
13. **Generate onion-skin contact sheets** (every N frames plus the keyed frames, before/after tinting) as review artefacts, so human and agent reviewers judge arcs and spacing without opening Godot.
14. **Meshes only where bending is needed**, max 4 influences per vertex, weights normalized and pruned below a threshold. Bind in rest pose. Require internal vertices at joints. The adapter writes Polygon2D bone arrays in skeleton order and re-syncs on every build, never by hand. Disallow per-vertex deform keys at first.
15. **Mirror by flipping a parent Node2D, not the Skeleton2D or bones**, and test mirrored playback of every IK-using clip. If runtime IK is used, invert `flip_bend_direction` when mirrored (the 4.6.2 forum report shows twisting otherwise).
16. **Add a "range of motion" clip** per rig, generated from joint limits, used to QA weights, limits and IK before any real animation is authored.
17. **Secondary motion (hair, cloth, tails)**: bake a simple spring/lag pass at compile time from `secondary` parameters (inertia/strength/damping, as in Spine physics constraints), or opt into runtime `SkeletonModification2DJiggle`. Keep it out of hand-authored keys.

---

## Sources

| URL | Contributed | Status |
|---|---|---|
| https://esotericsoftware.com/spine-animating | Straight-ahead / pose-to-pose / layered / combined approaches; hips+torso -> legs -> arms layering; stepped preview; curves vs robotic motion | Read OK (short page) |
| https://esotericsoftware.com/spine-graph | Curve types, handle presets, separate channels, favor slider (breakdowns), store/swap, repeat view, dopesheet-for-timing tip | Read OK |
| https://esotericsoftware.com/spine-ik-constraints | One/two-bone IK, bend positive (keyable), mix and flip hazard, softness, stretch/compress/uniform, limitations | Read OK |
| https://esotericsoftware.com/spine-tips | Nothing: tips load dynamically, so only the intro text came back | **Failed (no content)** |
| https://docs.godotengine.org/en/stable/tutorials/animation/2d_skeletons.html | Skeleton2D/Bone2D setup, rest pose, Polygon2D skinning, internal vertices; no IK on the page; page says not updated for 4.7 | Read OK |
| https://esotericsoftware.com/spine-keys | Setup vs animate mode, keys relative to setup pose, auto key, separate channels, clean-up and layering, loop offset | Read OK |
| https://esotericsoftware.com/spine-ghosting | Onion skin options, motion vectors, foot-slide check via ghost offset | Read OK |
| https://esotericsoftware.com/spine-bones | Root bone, inheritance flags, bone length, reflection | Read OK |
| https://esotericsoftware.com/spine-slots | Slots, one attachment per slot, keyable draw order, attachment keys vs alpha, slot colour, blend modes, weapon slot | Read OK |
| https://esotericsoftware.com/spine-skins | Skins, placeholders, skin bones/constraints, mix-and-match | Read OK |
| https://esotericsoftware.com/spine-transform-constraints | Copying a target's transform, mixes, offsets, local/relative | Read OK |
| https://esotericsoftware.com/spine-path-constraints | Bones along paths (treads, rope) | Read OK |
| https://esotericsoftware.com/spine-physics-constraints | Inertia/strength/damping/mass, runtime-only, deterministic mode | Read OK |
| https://esotericsoftware.com/spine-weights | Weights, auto/smooth/prune, bind pose pitfalls, ROM test animation | Read OK |
| https://esotericsoftware.com/spine-meshes | When to use meshes, vertex cost, deform keys discouraged, edit-mode pitfalls | Read OK |
| https://eu.esotericsoftware.com/blog/Holding-a-two-handed-weapon | Weapon-under-root rig, hand target bones, IK + transform constraints, mix 0 in setup and keyed to 100 | Read OK |
| https://docs.godotengine.org/en/stable/classes/class_skeleton2d.html | Skeleton2D methods (pose override, modification stack) | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/classes/class_bone2d.html | rest, apply_rest, length/angle, autocalculate | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/classes/class_skeletonmodificationstack2d.html | Experimental, strength, order matters | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/classes/class_skeletonmodification2d.html | Experimental base class, clamp_angle, list of 2D modification subclasses | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/classes/class_skeletonmodification2dtwoboneik.html | flip_bend_direction, min/max distance, joint setters, experimental | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/classes/class_polygon2d.html | Skinning properties and bone-weight methods | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/classes/class_animation.html | Interpolation (incl. _ANGLE), update modes, loop modes, track types, bezier key API | Read OK (4.7 docs) |
| https://docs.godotengine.org/en/stable/tutorials/animation/animation_track_types.html | Bezier tracks not blendable; method tracks don't fire in editor preview | Read OK |
| https://forum.godotengine.org/t/ik-2d-issue-when-mirroring-a-character-skeletonmodificationstack2d/136656 | 4.6.2 report: 2D IK legs twist when mirrored via negative scale; fixed by rebuilding the rig and rest pose | Read OK |
| Web search (Godot 2D IK status; Spine IK flip / two-hand weapon) | Confirmed the experimental label across 4.0–4.x docs; found the two-handed weapon blog | OK |
