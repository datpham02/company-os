# Animation and Body-Mechanics Fundamentals for Code-Driven 2D Skeletal Animation

> **Status:** `PROPOSED` (Knowledge base for AI agents (body mechanics and animation craft)). Compiled 2026-11-22 by a Claude Code research agent for the Board in the studio's own words, with source links and an evidence tag per rule; thresholds tagged *derived* are starting points to tune, not facts. Reviewed by the Board operator for structure and quoting; content review by `director` pending.


Research date: 2026-11-22. Audience: agents and engineers who author or validate 2D skeletal animation (Spine/Godot-style bone rigs) in code.

## How to read this document

- **Evidence labels.** Each rule is tagged where it matters:
  - `[clinical]`: a measured or clinical reference value from a source I read.
  - `[sport-biomech]`: sports or occupational biomechanics research. Some of it comes from abstracts or search snippets only, and those rules say so.
  - `[anim-craft]`: an animation-craft convention from a secondary source I read.
  - `[game-practice]`: a published game-dev rule of thumb. These are not science.
  - `[derived]`: my own engineering recommendation, built from the sources above. Treat these as starting thresholds to tune, not facts.
- **Source access was limited.** All five Animation Mentor articles returned HTTP 403, and YouTube returned only the page title. PMC/PubMed pages hit a bot check. The craft content here therefore leans on Wikipedia (summarising *The Illusion of Life*), Animator Island, Game Developer, Human Kinetics, SLYNYRD, MocapOnline, Aztez and Esoteric Software (Spine), plus CDC and WikEM for clinical numbers. The full source list at the end says what was and wasn't read.
- **2D conventions used in validation methods.**
  - Angles are in degrees.
  - A "joint angle" is the signed angle between the parent bone vector and the child bone vector in world space. Positive means counter-clockwise; define the sign per rig.
  - "Flexion angle" means the deviation from straight. 0 is a fully straight limb, and 140 is an elbow bent 140 degrees.
  - Most checks assume a side or three-quarter view. Out-of-plane motion (rotation toward the camera) is invisible in 2D, so ROM checks only constrain the in-plane component.
  - Frame rates: 30 fps or 60 fps are noted where given.

---

## 1. The twelve principles of animation

**Concept.** Disney animators Frank Thomas and Ollie Johnston set out twelve principles in *The Illusion of Life* (1981). They are squash and stretch, anticipation, staging, straight-ahead vs pose-to-pose, follow-through and overlapping action, slow in/slow out, arcs, secondary action, timing, exaggeration, solid drawing and appeal. John Lasseter's 1987 SIGGRAPH paper carried them into computer animation. Together they are the common vocabulary for judging whether motion reads as alive and physically believable. (Secondary: Wikipedia; Alan Becker's series could not be read.)

**Practical rules (mapped to code-checkable form).**

- **Squash and stretch.** Keep volume roughly constant: if a part scales up on one axis, scale it down on the other (scaleX × scaleY ≈ 1). For limbs on realistic characters, keep bone length scale near 1.0. `[anim-craft]` + `[derived]: |scale−1| ≤ 0.05 for realistic limbs; larger only for stylised squash on torso/head`.
- **Anticipation.** Before a major action, add a smaller movement in the opposite direction (see section 11).
- **Staging.** Silhouette the key pose: the weapon and the striking limb should not hide behind the torso at the key frames. In 2D, check that their screen-space bounds overlap the torso as little as possible.
- **Straight ahead vs pose to pose.** Code-driven rigs are naturally pose-to-pose: keyframes plus interpolation. Simulate loose parts (cloth, hair, chains) straight-ahead, as physics or spring follow-through (see sections 12 and 13).
- **Follow-through, overlap and drag.** Loose and fleshy parts keep moving after the body stops, start late, and settle late (sections 12 and 13).
- **Slow in / slow out.** More frames sit near the extremes and fewer in the middle. Velocity is low at the key poses and high between them.
- **Arcs.** Natural motion follows curves, because limbs rotate about joints and thrown objects follow parabolas. Only mechanical motion moves in straight lines. Faster motion gives flatter arcs.
- **Secondary action.** It supports the main action and must not compete with it. During a fast move, put facial or secondary changes at the start or end, not the middle.
- **Timing.** The frame count sets speed and implies mass: lighter objects react faster.
- **Exaggeration.** Push poses, but keep them coherent (section 19).
- **Solid drawing.** Avoid "twins", where left and right limbs mirror each other. In code, symmetric limbs should not share identical angle curves.
- **Appeal.** Poses should read clearly and look interesting.

**Common mistakes.** Linear (constant-speed) tweens between all keys; symmetric "twinned" arm poses; no anticipation before big actions; everything stopping on the same frame.

**Example.** For an overhead smash: the anticipation is a dip and lift, the key poses are top-of-windup and impact, there is slow-out from the top and maximum speed just before contact, the weapon head travels on an arc, and the cloth sash overlaps.

**Validation methods.**
- **Ease.** For each key interval, compute per-frame speed of the controlled bone tip. Flag intervals where the speed coefficient of variation is below 0.1, meaning near-linear motion with no easing `[derived]`.
- **Twins.** Compute the correlation of the left and right limb angle curves. Flag a correlation above 0.98 combined with a near-zero time offset `[derived]`.
- **Arcs.** See section 9.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://www.youtube.com/watch?v=uDqjIdI4bF4 (title only).

**Exceptions / limitations.** Mechanical characters, such as robots, may legitimately move linearly and on constant timing. Snappy pixel-art games often skip easing frames on purpose. These principles are craft heuristics, not physics.

---

## 2. Functional anatomy (arm, shoulder girdle including the scapula, spine, hip, knee)

**Concept.** A rig's bones stand in for real joints, and each real joint has a characteristic motion. The elbow is a hinge. The shoulder is a ball-and-socket joint (glenohumeral) that rides on a mobile scapula and clavicle (the shoulder girdle). The spine is many small joints whose motion adds up. The hip is a deep, stable ball-and-socket. The knee is mostly a hinge. Most "wrong-looking" arms in 2D come from treating the shoulder as a fixed pin on the ribcage instead of a joint on a moving scapula.

**Practical rules.**

- **Scapulohumeral rhythm.**
  - Arm elevation is shared between the glenohumeral joint and scapular upward rotation in an overall ratio of about 2:1 `[clinical]`. At 90 degrees of elevation that is roughly 60 degrees from the glenohumeral joint and 30 from the scapula.
  - The first ~30 degrees is a "setting phase" that is mostly glenohumeral. After that, both joints move together.
  - Measured ratios vary between about 1.7:1 and 2.7:1 depending on plane, direction and person (Scibek & Carcia; Braman et al.; McClure et al., via search abstracts).
  - Rig implication: when the arm goes above about 90 degrees, the shoulder pivot (clavicle/scapula bone) must rise and rotate. The top of the shoulder moves up toward the ear.
- **Elbow.**
  - It is a hinge: flexion 0 to about 140-150 degrees, extension about 0 (a few degrees of hyperextension is normal, especially in women; see section 3).
  - Forearm pronation and supination (about 80 degrees each) happen in the forearm, not at the elbow hinge. In 2D you see them as a change in hand or weapon orientation, or as a sprite swap, not as elbow bend.
- **Wrist.** It flexes and extends about 60 degrees each way, with radial deviation (thumb side) about 20 and ulnar deviation (pinky side) about 30. Hammering uses a diagonal path that couples extension with radial deviation (cocked) and flexion with ulnar deviation (strike) `[sport-biomech, abstract/snippet only]`.
- **Spine.**
  - Lumbar-thoracic flexion is only about 45-50 degrees, extension about 25, lateral flexion about 25 and rotation about 30 `[clinical: Luttgens & Hamilton via WikEM]`.
  - The neck (cervical spine) has much more: flexion about 60, extension about 75, rotation about 80.
  - Big forward bends are mostly hip flexion plus spine flexion, never spine alone.
- **Hip.** Flexion is about 100 degrees with the knee straight. The CDC measured about 127-134 degrees, likely with the knee bent. Extension is about 15-30 degrees. Hip extension is small, so a "leaning back" pose must come from the spine and from the knees moving forward, not from the hip alone.
- **Knee.** Flexion is about 133-150 degrees and extension about 0. It is a hinge that bends only backward. A knee that bends the wrong way (kneecap pointing backward, shin folding forward toward the toes) is always a rig error for humans.

**Common mistakes.**
- A fixed shoulder pivot during overhead motion, so the arm "pops" out of the torso silhouette.
- Elbow or knee hyperextension, or bending the wrong way.
- All trunk bend placed in one spine bone, which gives a "hinge" at the waist.
- Head and neck frozen relative to the torso, so the eyes leave the target.

**Example.** For an arm raised overhead to 170 degrees: about 110-115 degrees comes from the glenohumeral joint and about 55-60 from scapular rotation (2:1). The clavicle and scapula bone rotates up roughly 20-30 degrees in screen space, and the top of the shoulder rises.

**Validation methods.**
- **Shoulder-girdle coupling.** Whenever upper-arm elevation relative to the torso exceeds 90 degrees, require the clavicle/scapula bone rotation (or shoulder pivot rise) to exceed a threshold. `[derived]`: scapular contribution ≥ 0.25 × (elevation − 30) for elevation > 30.
- **Spine distribution.** With N spine bones, flag any single bone that carries more than 60% of the total trunk bend `[derived]`.
- **Hinge direction.** The sign of the elbow and knee joint angle must stay on the anatomical side for every frame (see section 16).

**Sources.** https://ouhsc.edu/bserdac/dthompso/web/namics/scapryme.htm ; https://wikem.org/wiki/Joint_ROM_(Table) ; https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html ; scapulohumeral rhythm ratios from PMC3377910 / PMC2841046 / McClure 2001 (search abstracts only).

**Exceptions / limitations.** Creatures and quadrupeds have different joint layouts. Digitigrade legs have a backward-bending "ankle" that looks like a reversed knee. Cartoon rubber-hose limbs ignore hinges by design. 2D hides rotation toward the camera, so a pronated forearm is not visible as an angle.

---

## 3. Joint movement and limits (range of motion)

**Concept.** Range of motion (ROM) is how far a joint can move, measured clinically with a goniometer from a neutral anatomical pose. ROM values differ between sources, by age and by sex, so use them as plausibility bounds rather than exact limits. For animation, the useful numbers are *active* ROM. A heavy attack may briefly approach the end of range, but it should not exceed it.

**Reference table (degrees).** Each value cites its source. "L&H" is Luttgens & Hamilton (1997) as tabulated by WikEM. "CDC" is the CDC Joint ROM Study (general population, 2003-2006, more than 600 people), adult means for men and women aged 20-44.

| Joint | Motion | L&H typical | CDC adult mean (F / M, 20-44) |
|---|---|---|---|
| Neck (cervical) | Flexion / extension | 60 / 75 | n/a |
| Neck | Lateral flexion / rotation | 45 / 80 | n/a |
| Trunk (thoraco-lumbar) | Flexion | 45-50 | n/a |
| Trunk | Extension (hyperext.) | 25 | n/a |
| Trunk | Lateral flexion / rotation | 25 / 30 | n/a |
| Shoulder | Flexion (raise forward) | 180 | 172.0 / 168.8 |
| Shoulder | Extension (behind body) | 50 | n/a |
| Shoulder | Abduction | 180 | n/a |
| Shoulder | Internal / external rotation (arm abducted) | 90 / 90 | n/a |
| Elbow | Flexion | 140 | 150.0 / 144.6 |
| Elbow | Extension (past straight) | 0 | 4.7 / 0.8 |
| Forearm | Pronation / supination | 80 / 80 | 82.0 / 76.9 and 90.6 / 85.0 |
| Wrist | Flexion / extension | 60 / 60 | n/a |
| Wrist | Radial / ulnar deviation | 20 / 30 | n/a |
| Hip | Flexion | 100 | 133.8 / 130.4 |
| Hip | Extension | 30 | 18.1 / 17.4 |
| Hip | Abduction / adduction | 40 / 20 | n/a |
| Hip | Internal / external rotation | 40 / 50 | n/a |
| Knee | Flexion | 150 | 141.9 / 137.7 |
| Knee | Extension (past straight) | 0 (not listed) | 1.6 / 1.0 |
| Ankle | Plantarflexion / dorsiflexion | 20 / 30 as listed (common clinical tables give ~50 / ~20; treat with care) | n/a |

The CDC values for men and women aged 45-69 are 2-5 degrees lower for most motions. Shoulder flexion there is 168.1 / 164.0.

**Practical rules.**
- **Hard error bounds** `[derived]` (flag as errors):
  - Elbow outside [−10, 150]
  - Knee outside [−5, 150]
  - Shoulder flexion > 180
  - Shoulder extension > 60
  - Wrist flexion or extension > 75
  - Trunk extension per whole spine chain > 35
  - Neck rotation is not visible in 2D, but neck flexion or extension > 75
- **Soft warning bounds** `[derived]` (realistic characters): any joint within 10 degrees of its limit for more than 6 frames at 30 fps. Real people rarely hold end-range positions.
- **Lower bounds in a hip-plus-knee pose.** The CDC hip flexion (about 130) is larger than L&H (100), likely because of different test positions such as the knee bent. Use about 120 as the hip-flexion warning bound when the knee is bent and about 90 when the knee is straight. Hamstrings limit hip flexion with a straight knee; that is a well-known clinical effect, not measured here.

**Common mistakes.** Ignoring the shoulder's dependence on the scapula: 180 degrees of "shoulder flexion" is a whole-girdle number. Treating elbow hyperextension as free. Spine bones that each rotate 30 degrees, so the sum is far beyond 50.

**Example.** A rig's upper arm is at 175 degrees relative to the torso, but the scapula bone has not moved. The total is plausible, but the glenohumeral share (175 degrees) is far beyond about 120, so it fails the girdle-coupling check.

**Validation methods.**
- For each frame and each joint, compute the in-plane joint angle relative to the rig's neutral (bind) pose, then compare it to the table, mapped through a per-rig sign table.
- For each chain (spine, neck), sum the bone-relative angles.
- Report: max |angle|, frames over the soft bound, and frames over the hard bound.

**Sources.** https://wikem.org/wiki/Joint_ROM_(Table) ; https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html. Physio-pedia "Range of Motion Normative Values" returned 403. A PMC normative table (PMC9218764) was blocked by a bot check, and its figures appeared only in a search snippet (elbow 0-140, wrist ±60, shoulder flexion up to 180).

**Exceptions / limitations.** Values are clinical, from slow goniometer measurements. Ballistic motion can briefly exceed the active range because of soft-tissue give, but not by much. Children, the elderly, gymnasts and creatures differ. 2D projection makes foreshortened limbs look more bent than they are.

---

## 4. Body mechanics

**Concept.** "Body mechanics" in animation means motion that obeys the physics of a body with mass. Weight is supported by the ground through the feet. Force comes from pushing against the ground. Momentum carries through the body. Balance is maintained or deliberately lost. It is the overlap of sections 5-8 applied to whole-body actions (lifts, pushes, jumps, attacks).

**Practical rules.**
- **Ground force.** Every big action begins at the ground: feet push, legs and hips generate, the trunk transmits, and the arms deliver (section 8) `[sport-biomech]`.
- **Supported weight.** If a foot is planted, it must not slide. If weight is on a leg, that leg's knee shows load (some flexion) unless the leg is deliberately locked. The hip rises and the shoulder drops on the weight-bearing side (contrapposto) `[anim-craft, Animator Island]`.
- **Heavy objects.**
  - Keep the object close to the body, because that keeps the combined centre of mass over the feet.
  - A heavy load makes the body lean in the opposite direction, to counterbalance.
  - Lifting something quickly makes balance harder `[anim-craft, Animator Island]`.
- **Push and pull.**
  - Lean the centre of mass toward the push, outside the feet if needed, so that the ground force line passes through the contact point.
  - Widen the base of support along the direction of force; bigger forces need a wider stance `[sport-biomech, Human Kinetics]`.
- **Readability.** Well-animated weight should read even in a waist-up crop, from the shoulders and hips alone `[anim-craft, Animator Island]`.

**Common mistakes.** Arms-only actions with static legs; floating feet; bodies leaning without a counter-balance; no settle after landing.

**Example.** For a push against a heavy crate: the back foot is planted far behind, the body is a straight diagonal from the back heel through the shoulders to the hands, and the front knee is bent. The push starts with the back leg extending, and the hips drive forward before the arms extend.

**Validation methods.** These are combinations of the checks in sections 5-8:
- Foot-lock check: planted foot world position drift < 2 px or < 1% of body height per frame while flagged as planted `[derived]`.
- CoM-in-support check.
- Proximal-to-distal peak ordering.

**Sources.** https://www.animatorisland.com/principles-of-animation-physics-part-4/ ; https://us.humankinetics.com/blogs/excerpt/factors-affecting-stability. The Animation Mentor body-mechanics, lifting, pushing/pulling and weight articles were all HTTP 403, not read.

**Exceptions / limitations.** Flying and floating characters, magic-assisted moves and stylised cartoon physics are exempt from ground-force rules, but they should still show a reaction (recoil) to big forces.

---

## 5. Balance and centre of mass (CoM)

**Concept.** The CoM is the mass-weighted average position of all body parts. In a standing human it sits around the lower abdomen, a little above half of body height, and it moves with every pose change (Oba; Animator Island). Static balance holds when a vertical line dropped from the CoM lands inside the base of support, which is the area spanned by the contact points (in 2D, the x-interval between the supporting feet). Stability rises with a wider base, a lower CoM, a CoM nearer the middle of the base, and more mass (Human Kinetics).

**Practical rules.**
- **Static balance.** In any held pose, including holds, the impact pose and the end of recovery, the CoM's ground projection must lie within the feet's x-range. Add a margin `[derived]`: at least 10% of foot-span inside the edge for a "stable" pose.
- **Dynamic balance.** During motion the CoM may leave the base briefly, but the next contact (a step) must catch it. A character whose CoM sits outside the base with no step coming must be falling.
- **Load counter-balance.** When the character holds a heavy object, compute a *combined* CoM (body plus weapon) and apply the same rule. Hammers carry their CoM toward the head end `[anim-craft, Animator Island]`.
- **Braced stance.**
  - Widen the stance along the direction of the force (forward and back for an overhead smash).
  - Lower the CoM (bend the knees) before receiving or delivering big forces `[sport-biomech, Human Kinetics]`.
- **CoM is a guide, not a control.** Animate the root/hips, then *check* the CoM. Don't drive the CoM directly. For flips, rotate around the CoM, not the hip bone, or the motion wobbles `[game-practice, Oba]`.
- **Ballistic phases.** When airborne, the CoM follows a parabola whatever the limbs do (y = ½gt²). Missing acceleration looks "floaty" (Oba).

**Common mistakes.** A pose that leans far forward with nothing in the opposite direction; a jump whose hip path is not a parabola; ignoring the weapon's mass in the CoM.

**Example.** At the top of a sledgehammer windup the hammer head is behind and above the head. The body CoM shifts slightly forward (the hips come forward, the chest arches) so that the combined CoM stays over the feet.

**Validation methods.** Approximate the 2D CoM as a weighted sum of segment midpoints. Typical segment mass fractions:

| Segment | Share of body mass |
|---|---|
| Head and neck | about 8% |
| Trunk | about 50% |
| Upper arm | about 3% each |
| Forearm | about 1.6% each |
| Hand | about 0.6% each |
| Thigh | about 10% each |
| Shank | about 4.7% each |
| Foot | about 1.5% each |

These are the classic Dempster/Winter anthropometric values from my background knowledge; they were not verified from a source in this session, so treat them as approximate.

Add the weapon mass, a design parameter, at its own CoM. Then:
- Flag held frames (speed below a threshold for 3 or more frames) where the CoM x lies outside [min foot x, max foot x].
- For airborne frames, fit a parabola to the CoM y. A residual above 2% of body height suggests wrong ballistic motion `[derived]`.

**Sources.** https://www.animatorisland.com/principles-of-animation-physics-part-4/ ; https://us.humankinetics.com/blogs/excerpt/factors-affecting-stability ; https://gamedeveloper.com/design/center-of-mass-tools-and-techniques-for-animating-natural-human-movement.

**Exceptions / limitations.** Stylised characters with huge heads or hands have a different CoM distribution. Use per-rig mass fractions. Creatures with tails use the tail as a counterweight. 2D ignores side-to-side balance in a pure side view.

---

## 6. Weight transfer

**Concept.** Weight transfer is moving the CoM from one support to another, such as back foot to front foot or one leg to two. It is how a body converts leg drive into motion. Small lateral CoM shifts produce large changes in how weight is shared between the feet (Animator Island's scale example), so the shift does not need to be large to read.

**Practical rules.**
- **Order.** The hips (pelvis/root) lead the weight shift. The shoulders and arms follow. The weight shift for a strike starts *before* the arms commit `[sport-biomech + anim-craft]`.
- **Visible signals of loading a leg.**
  - That knee flexes slightly, then extends as it drives.
  - The pelvis tilts up on that side and the shoulder line counter-tilts (contrapposto).
- **Unloading.** The unloaded foot can lift its heel or slide. The loaded foot must stay locked.
- **Heavy loads.** Heavier loads mean slower, deeper weight transfer. The body sinks (the knees bend more) before shifting `[anim-craft]` `[derived]`.

**Common mistakes.** The weight shift happens at the same frame as the arm strike, or after it; hips static while the upper body swings; both knees identical at all times.

**Example.** For an overhead hammer smash in a staggered stance: the windup holds the weight about 55-65% on the rear foot, and the swing transfers it to about 60-70% on the front foot by impact. These percentages are `[derived]` illustrative targets, not measured values.

**Validation methods.**
- **Weight-share proxy.** Compute the CoM x as a fraction between the rear foot x and the front foot x. That fraction should move rear-to-front, monotonically within tolerance, between the windup top and impact.
- **Pelvis-first.** The pelvis x-velocity peak should precede the hand-speed peak.
- **Leg loading.** The front knee should show its peak flexion near impact.

**Sources.** https://www.animatorisland.com/principles-of-animation-physics-part-4/ ; https://us.humankinetics.com/blogs/excerpt/factors-affecting-stability.

**Exceptions / limitations.** Characters that are rooted (turrets, plants) or levitating don't transfer weight. Some stylised attacks are deliberately "planted" for gameplay readability; they still need hips that move.

---

## 7. Force and momentum

**Concept.** Momentum is mass times velocity. Heavy things take longer to start and longer to stop, and they keep going after the driving force ends. Force is how momentum changes over time. A hard stop over a few frames reads as a big impact, while a gradual stop reads as soft. In animation, timing is the main signal of mass: lighter objects react faster (Wikipedia on timing).

**Practical rules.**
- **Heavy objects accelerate slowly at first.** The swing needs time to build up speed, and peak speed comes late. MocapOnline suggests the fastest point is about 60-70% through the swing arc rather than at the endpoint `[game-practice]`.
- **Heavy objects don't stop instantly unless they hit something.**
  - After impact, show the energy going somewhere: a rebound, recoil into the arms and body, or ground penetration.
  - If the strike misses, the weapon overshoots and drags the body.
- **Action/reaction.** A heavy strike pushes back on the striker. Show a slight recoil: the elbows flex and the shoulders and torso jolt over 2-4 frames after contact `[derived]`.
- **Hit-stop.** Freeze or slow the animation 1-4 frames at contact to sell the force `[game-practice: MocapOnline]`. SLYNYRD advises keeping freezes subtle and reserving them for exaggerated actions.
- **Hold the follow-through.** Holding the follow-through a little longer than the other frames communicates weapon weight `[game-practice: SLYNYRD]`.

**Common mistakes.** Constant-speed swings; the weapon decelerating *before* contact; a dead stop at impact with no reaction; light weapons and heavy weapons timed identically.

**Example.** A 30 fps heavy smash: the last 3 frames before contact have the largest tip displacement per frame. Contact is followed by a 2-3 frame hit-stop, then 2-3 frames of small rebound and the body settling lower.

**Validation methods.**
- **Weapon tip speed.** Compute it per frame. The argmax of speed should fall in the last 25-40% of the swing phase, and the speed at the contact frame should be at least 80% of the max `[derived]`.
- **Deceleration.** After contact, the tip speed should drop by at least 70% within 3 frames, for a hit on a hard surface `[derived]`.
- **Overall pacing.** Compare total durations of light vs heavy attacks against the ranges in section 17.

**Sources.** https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide ; https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks ; https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation.

**Exceptions / limitations.** Superhuman characters can swing heavy objects fast. Sell their strength with the target's reaction and with the body bracing, not with slow timing. Comedic timing may break momentum on purpose.

---

## 8. Kinetic chains

**Concept.** In throwing, striking and swinging, speed is built in sequence from proximal (large, central) segments to distal (small, end) segments: ground, legs, hips/pelvis, trunk, shoulder girdle, upper arm, forearm, hand, implement. Each segment ideally starts to accelerate as the previous one reaches its peak, and each reaches a higher peak speed than the one before (the "summation of speed" principle). In the tennis serve, Kibler's often-cited figures attribute about 51% of kinetic energy and 54% of force to the legs, hips and trunk. Throwing literature gives about 50% for the hip-and-trunk area. The scapula is the link that passes trunk energy to the arm.

**Practical rules.**
- **Order of peak angular velocity.** Pelvis, then trunk, then upper arm, then forearm, then wrist/hand, then implement. Peaks need not be perfectly sequential. Pitching studies show some overlap, and upper-arm internal rotation peaks late, near or even after release `[sport-biomech; snippets/abstracts]`.
- **Pelvis-trunk separation.** A delay between the pelvis peak and the trunk peak was positively associated with ball speed in pitching. Practically, the hips should lead the shoulders by a few frames `[sport-biomech, abstract only]`.
- **Missing links.** An arm-only swing (no legs or trunk) loses about half of the available energy, by the ~50% figure. It *looks* weak and unnatural.
- **Hammering-specific sequence.** Shoulder and elbow extend, then the forearm rotates, then the wrist "snaps" through ulnar flexion to drive the head `[sport-biomech: PMC2901240 via search snippet; full text not readable]`.

**Common mistakes.** All joints peak on the same frame; the arm leads the hips; the wrist is locked through the whole swing; the trunk stays upright during an overhead strike.

**Example.** For a 60 fps overhead smash, a plausible peak-angular-velocity timeline before contact (illustrative, `[derived]`):

| Segment | Peak before contact |
|---|---|
| Pelvis | about 120-150 ms |
| Trunk | about 90-110 ms |
| Upper arm/shoulder | about 50-70 ms |
| Elbow extension | about 25-40 ms |
| Wrist release | 0-20 ms |

**Validation methods.**
- **Peak ordering.** Compute angular velocity per segment (world rotation or relative joint angle) across the swing phase, and take the time of the peak of |ω| for pelvis, trunk, upper arm, forearm, hand and weapon.
  - Pass if the sequence is non-decreasing in time, with a tolerance of 1 frame at 30 fps.
  - Warn if fewer than 4 of 6 pairs are ordered.
  - Fail if the hand or weapon peaks before the trunk `[derived]`.
- **Speed summation.** Each distal segment's peak linear tip speed should be at least that of the more proximal segment's tip.

**Sources.** https://dptcapstone.web.unc.edu/2014/04/22/kinetic-chain-concepts-and-exercise-progression-for-tennis-players (read; cites Kibler 1991 and Sciascia 2012). Leenen 2022, Frontiers in Sports and Active Living, DOI 10.3389/fspor.2022.1044616: only the PDF metadata and title were readable, and the findings came from search snippets. PubMed 22666599 (Sciascia, Kinetic chain rehabilitation) was blocked. PMC2901240 (hammering) was blocked by a bot check.

**Exceptions / limitations.**
- Most data come from baseball pitching and tennis serving. Overhead sledgehammer striking is a two-handed, mostly sagittal-plane motion with gravity assisting. The proximal-to-distal principle transfers, but exact timings do not.
- No measured sledgehammer kinematics study was found.
- Creatures with different body plans (for example tail strikes) still follow base-to-tip sequencing.

---

## 9. Motion arcs

**Concept.** Joints rotate, so their endpoints trace curves. The wrist circles the elbow, the elbow circles the shoulder, and a weapon head traces a combined arc. Thrown and airborne objects follow parabolas. Motion that moves in straight lines, or zig-zags between keys, looks mechanical or broken.

**Practical rules.**
- Track the arcs of: the weapon tip, the hands, the head, and the hips/root. Each should be smooth, with no kinks except at deliberate direction changes (the top of the windup, impact).
- Faster motion has flatter arcs. Turnarounds widen the arc (Wikipedia).
- **Overhead smash.** The weapon head should trace a large, near-circular arc behind and over the head, then down in front. A wide arc reads as slow but powerful (SLYNYRD).
- **Linear interpolation of positions** (IK targets) between distant keys produces straight lines. Add breakdown keys or interpolate rotations instead.

**Common mistakes.** IK hand targets tweened linearly, so the weapon moves in a straight line through the head; arcs that double back (jitter) between keys; a head bobbing on a sawtooth.

**Example.** A hammer moves from the top-of-windup key to the impact key. Linear interpolation of the hand IK target cuts a chord through the character's head region. Interpolating the shoulder and elbow rotations (FK) produces the correct arc above the head.

**Validation methods.**
- **Kinks.** Take the tip path p(t) and compute the turning angle between successive displacement vectors. Flag frames with a turning angle above 45 degrees that are not tagged key/contact frames `[derived]`.
- **Straightness.** Over windows of 5 or more frames during the swing, the ratio of chord length to path length should be below about 0.98, meaning the path is not a straight line `[derived]`.
- **Head clearance.** The tip path must not intersect the head's bounding circle, or a 2D forearm-over-face rule applies (see section 20.4).

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks ; https://www.animatorisland.com/principles-of-animation-physics-part-4/.

**Exceptions / limitations.** Mechanical motion, robotic characters, and deliberate snaps or teleport-like smears may break arcs. A single smear frame can replace an arc on purpose.

---

## 10. Timing and spacing

**Concept.** *Timing* is how many frames an action takes, which sets speed, mass and mood. *Spacing* is how far things move between frames, which sets acceleration and deceleration (ease). The same timing with different spacing reads completely differently. Richard Williams devotes a central section of *The Animator's Survival Kit* to this topic (per public table-of-contents descriptions; the book itself was not read).

**Practical rules.**
- **Light reacts fast, heavy reacts slow** (Wikipedia, on timing).
- **Spacing near the extremes** (keys) is tight, which is slow-in and slow-out. Spacing in the middle is wide.
- **Heavy weapons.**
  - Slower anticipation and recovery, longer holds (SLYNYRD).
  - Fast swing in the middle.
  - Fastest point late in the arc (MocapOnline: about 60-70%).
- **Game timing realities** `[game-practice]`.
  - The hitbox is active about 2-4 frames.
  - Wind-up plus attack lasts at least about 340 ms for a readable enemy attack. The end pose lasts at least about 170-240 ms (Dark Souls 3 analysis).
  - Players feel input latency above about 100 ms, and about 200 ms feels sluggish (Mick West, cited there).
- **Responsiveness vs weight.** Too much anticipation reads as input lag, and too much recovery feels "sticky". Allow cancel windows in the recovery (Aztez proposes a movement-cancel flag midway through; MocapOnline opens combo windows at about 70% through the recovery).

**Common mistakes.** Even spacing; the weapon's slowest frames in the middle of the swing; identical timing for weapons of different weights; long recovery with no cancel window for player characters.

**Example.** Aztez forehand slash at 60 fps: 60 frames total, about 6-7 frames anticipation, about 10 frames swing with about 5 active, and the remainder (about 43) follow-through and recovery. That is about 11% / 17% / 72%.

**Validation methods.**
- **Spacing profile.** Per phase, compute the tip displacement per frame. Expect a low-high-low profile within a swing.
- **Phase durations.** Compare against the budget tables in section 17 and section 20.1.
- **Holds.** Count frames with displacement below ε at key poses.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://www.gamedeveloper.com/game-platforms/anatomy-of-an-enemy-attack-in-dark-souls-3 ; https://aztez.com/blog/2012/05/24/the-amalur-problem/ ; https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide ; https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks ; https://en.wikipedia.org/wiki/The_Animator%27s_Survival_Kit (book metadata only).

**Exceptions / limitations.** Pixel art at low frame counts uses holds and smears instead of smooth spacing. Fighting games trade fidelity for frame-exact readability.

---

## 11. Anticipation

**Concept.** Anticipation is a preparatory move, usually opposite to the main action, that stores energy and tells the viewer what is coming. Examples are a pitcher winding back or a jumper bending their knees (Wikipedia). In games it is also the *telegraph* that gives players a reaction window (the Dark Souls 3 analysis names "opening pose" and "attack signal" phases).

**Practical rules.**
- **Opposite direction.** Before an overhead downward smash, the body first rises and arches back, and the hammer goes up and back.
- **Size scales with the action and the weight.**
  - Heavy attacks need an obvious wind-up.
  - Light attacks get only a small coil of about 0.1-0.2 s (MocapOnline).
- **Enemy vs player.**
  - Enemy telegraphs need at least about 340 ms of wind-up plus attack to be reactable (DS3 analysis).
  - Player attacks should keep anticipation short (Aztez: about 6-7 of 60 frames for a slash) for responsiveness. For a heavy player attack, longer is acceptable as a deliberate risk/reward trade.
- **Small counter-move first.** Anticipation often contains a smaller pre-move: a slight dip (knees bend) before the rise. That is an anticipation of the anticipation `[anim-craft]`.

**Common mistakes.** The wind-up direction is the same as the strike; no body involvement (only the arm cocks); anticipation so long that player attacks feel laggy.

**Example.** For a heavy smash: a knee dip of 3-4 frames, then a rise and arch over 12-18 frames as the hammer moves overhead, then a 2-6 frame hold at the top.

**Validation methods.**
- **Direction reversal.** Take the dominant direction of the main action (for the smash, weapon tip velocity downward and forward). In the frames before the swing, the root and tip should have a net displacement with a negative dot product against that direction.
- **Duration.** Measure the anticipation duration and compare it to the role (enemy vs player) budgets.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide ; https://www.gamedeveloper.com/game-platforms/anatomy-of-an-enemy-attack-in-dark-souls-3 ; https://aztez.com/blog/2012/05/24/the-amalur-problem/.

**Exceptions / limitations.** Surprise or "no-tell" attacks deliberately cut anticipation. Use them sparingly and compensate with other cues (sound, VFX). A delayed attack (a held anticipation) is a legitimate difficulty tool.

---

## 12. Follow-through

**Concept.** After the main action ends, parts of the body and props keep moving because of momentum, then settle. Follow-through shows that the action carried energy and that objects have mass. The "moving hold" keeps a resting character subtly alive (Wikipedia).

**Practical rules.**
- **Weapon.** It continues past the contact point if unobstructed. On a hard surface it rebounds or embeds, and the body continues settling.
- **Swing past centre.** For a horizontal swing, carry 30-60 degrees past centre before decelerating (MocapOnline). For an overhead smash, the analogue is continuing toward the ground.
- **Order of settling.** The torso settles first, then the arms, then loose parts (hands relax, cloth, hair).
- **Hold the follow-through** slightly longer to show weight (SLYNYRD).

**Common mistakes.** Everything stops on the contact frame; the follow-through is a mirror-image reversal back to idle; loose parts settle on the same frame as the body.

**Example.** After impact: 2-3 frames of hit-stop, then the hammer bounces up about 5-10% of its swing radius while the knees continue to bend 2-4 more frames, then a hold.

**Validation methods.**
- **Stop staggering.** For each bone, find the "stop frame" (speed below ε). The spread of stop frames between the root and the leaf bones should be at least 2 frames at 30 fps `[derived]`.
- **Overshoot.** The weapon tip or a loose part should overshoot its final rest position (sign change of velocity) at least once, unless it is embedded.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide ; https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks.

**Exceptions / limitations.** Fast gameplay may cancel follow-through into the next action. Keep at least the first 2-4 frames so the hit reads.

---

## 13. Overlapping action

**Concept.** Different parts of the body move on different timings. Parts start late ("drag") when motion begins and finish late when it ends. Fleshier and looser parts lag more (Wikipedia). Overlap breaks the "one rigid block" look of keyframed rigs.

**Practical rules.**
- **Child offset.** Offset child bone rotation curves by 1-3 frames (at 30 fps) behind their parent for loose parts. Hair, cloth, belly and tails lag more, and limbs lag less `[derived]`.
- **Drag** happens at the start of a fast move. The hand trails the elbow, and the hammer head trails the hands. Then the distal part whips through (connects to the kinetic chain, section 8).
- **Don't overlap rigid connections.** Two hands gripping one handle must not drift apart.

**Common mistakes.** Every bone keyed on the same frames; overlap so large that limbs look boneless; overlap on a rigid weapon grip.

**Example.** At the top of the windup the torso has already started forward. The arms are still finishing going back and the hammer head is still rising (drag). That is the classic "stretch" moment before the whip.

**Validation methods.**
- **Lag.** For parent and child bones, cross-correlate the angular velocity curves. The lag at peak correlation should be at least 1 frame for flagged loose chains and about 0 for rigid ones.
- **Grip.** The distance between the two hand bones should vary by less than 2% of handle length on two-handed weapons.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation.

**Exceptions / limitations.** Mechanical and armoured characters have less overlap. Stylised limbs can exaggerate drag (see section 19).

---

## 14. Pose-to-pose workflow

**Concept.** The animator defines key poses first (the storytelling extremes), then breakdowns (the in-between poses that define the arcs and spacing), then lets interpolation fill the rest. It contrasts with straight-ahead animation (frame by frame in order). It suits code-driven rigs because poses are data and interpolation is automatic (Wikipedia).

**Practical rules.**
- Author keys at the storytelling extremes: idle, anticipation low, windup top, impact, follow-through extreme, recovery, return.
- Add breakdowns where interpolation gives wrong arcs or spacing. Typically, mid-swing breakdowns fix arcs, and frames near the extremes control ease.
- Use straight-ahead or simulated motion only for secondary parts (cloth, hair, chains, debris).
- Each key pose should be readable as a silhouette by itself (staging).

**Common mistakes.** Too few keys, so interpolation produces chords instead of arcs; key poses that are not physically balanced; skipping breakdowns.

**Example.** A smash with 7 keys and 3 breakdowns: one on the downswing (to keep the arc), one in anticipation (the dip), and one in recovery (the lift via the legs).

**Validation methods.**
- **Balance at keys.** Run the CoM/balance check at every key.
- **Interpolation error.** Measure the maximum arc error between keys (section 9). If the chord-to-arc deviation exceeds 10% of the arc radius, require a breakdown `[derived]`.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation.

**Exceptions / limitations.** Procedural or physics animation (ragdolls, springs) is inherently straight-ahead.

---

## 15. Animation blocking

**Concept.** Blocking is the first pass of an animation. Only the key poses and their timing are placed, usually with stepped (held) interpolation, to approve story, staging and timing before spending time on polish. In stepped mode each pose holds until the next, which exposes weak poses and bad timing early.

**Practical rules.**
- **Block first.** Block in stepped mode: keys plus rough breakdowns, then the timing review, then spline/ease. Do not polish curves before the poses and the timing are approved.
- **Blocking review checklist.**
  - Each key passes ROM and balance.
  - Phase durations fit the gameplay budget.
  - The silhouette reads.
  - The anticipation direction is correct.
- **A pipeline-friendly order for agents** `[derived]`: (1) gameplay timing budget, (2) stepped key poses, (3) validation of keys, (4) breakdowns, (5) spline plus ease, (6) overlap/secondary, (7) full validation.

**Common mistakes.** Starting in spline, so the timing looks "ok" only because it is mushy; adding overlap before the poses are approved.

**Example.** A stepped preview of the smash at 30 fps:

| Pose | Hold |
|---|---|
| Idle | 4 frames |
| Dip | 3 frames |
| Windup top | 14 frames to reach, 4 frames hold |
| Impact | 1 frame + 3 hit-stop frames |
| Follow-through | 5 frames |
| Recovery | 10 frames |
| Return | 8 frames |

**Validation methods.**
- **Stepped export.** Export a stepped version and run the key-pose checks on it.
- **Timing budget.** Verify the total frame budget against the design spec.

**Sources.** General animation practice. Blocking is described in the Animation Mentor articles, which could not be read (403). This section is `[anim-craft]` from background knowledge and should be validated by the studio's lead animator.

**Exceptions / limitations.** Procedural/runtime animation may never have a blocking pass. Its "keys" are parameters.

---

## 16. FK and IK

**Concept.** Forward kinematics (FK) rotates bones from the root outward. It is good for free-form arcs, swings and overlap. Inverse kinematics (IK) places an end target, such as a hand or foot, and solves the joint rotations. It is good for keeping contacts fixed: planted feet, hands on a fixed handle, reaching to a point. In Spine, an IK constraint covers one bone or two (parent plus direct child). Three or more bones need several constraints or FK. A "mix" value blends FK (0) and IK (100) (Esoteric Software).

**Practical rules.**
- **Use IK for:**
  - Planted feet throughout an attack.
  - The second hand on a two-handed weapon (constrain it to the handle).
  - Hands on fixed objects.
  - Runtime terrain adaptation.
- **Use FK for:**
  - The swinging arm and weapon arcs.
  - Spine and tail.
  - Follow-through and overlap.
  - Anything where the *path* matters more than the end position. The overhead hammer arc should be driven by shoulder and elbow FK rotations, with the second hand on IK to the handle.
- **Bend direction.** Two-bone IK has two solutions, elbow or knee "up" or "down". In Spine, the keyable "bend positive" flag picks the side. Set it explicitly to the anatomical side and key it if it ever needs to change. Knees bend forward and elbows bend backward and down, in human anatomy terms.
- **IK flipping.**
  - When the target passes near the root, or the limb fully straightens, the solver can snap to the other solution.
  - With mix between 0 and 100, rotations can suddenly flip because interpolation takes the shortest rotation path (Esoteric Software).
  - Mitigations: keep targets within reach; key the bend direction; use softness (Spine slows the bones as they approach full reach, avoiding the fast snap near full extension); avoid long mix transitions while the target crosses the root.
- **Stretch/compress.** Disable them for realistic characters (bones keep their length). Enable them only for stylised squash and stretch.
- **Pole vectors** (3D tools such as Blender) play the role of the bend-direction flag. Place the pole on the side the joint should point to, far enough away to stay stable. The Blender manual page could not be read in this session.

**Common mistakes.**
- An IK hand driving a big swing, so the path is a straight line.
- An elbow popping to the other side mid-swing when the hand passes close to the shoulder.
- A fully extended IK limb with no softness, which snaps.
- The second hand on FK, drifting off the handle.

**Example.** For the hammer smash: the lead arm is on FK (shoulder plus elbow rotations keyed), the rear hand is IK-constrained to the handle at a fixed offset, both feet are IK-planted, and the spine is FK. Bend direction for the rear arm is keyed so the elbow points down and back, never up through the face.

**Validation methods.**
- **IK flip.** For each two-bone chain, compute the sign of the 2D cross product of (upper bone vector, lower bone vector) per frame.
  - Any sign change not tagged in the animation metadata is a flip error.
  - Also flag a joint angle change above 60 degrees between consecutive frames at 30 fps `[derived]`.
- **Contact lock.** For IK-planted effectors, measure position drift (see section 4). For handle constraints, measure the hand-to-handle distance.
- **Bone length.** Bone length change below 1% unless stretch is intended.

**Sources.** https://en.esotericsoftware.com/spine-ik-constraints ; https://docs.blender.org/manual/en/latest/animation/armatures/posing/bone_constraints/inverse_kinematics/introduction.html (fetched, but only the navigation text was returned; content not read).

**Exceptions / limitations.** Creatures with three or more segment legs need chained IK or FK. Stylised rigs may want stretch. Godot's 2D IK (Skeleton2D modifications) has its own conventions; check the engine docs.

---

## 17. Combat animation: heavy weapon attacks

**Concept.** A game attack is a body-mechanics action constrained by gameplay. It has phases: anticipation/telegraph, an active (hitbox) window, and recovery. Its timing defines fairness and feel. Heavy attacks trade speed for reach and damage: slow start, long recovery, an obvious telegraph and a strong impact. They need visible weight (whole-body involvement, a weight shift, holds) without making a player character feel unresponsive.

**Practical rules** `[game-practice]` unless noted.
- **Phases.**
  - Anticipation: opening pose plus attack signal.
  - Active: the hitbox, about 2-4 frames in Dark Souls 3.
  - Recovery: end pose plus return/opportunity window.
- **Duration budgets.** At 30 fps, from MocapOnline:

  | Attack | Swing | Full attack | Recovery |
  |---|---|---|---|
  | Light | 6-12 frames (0.2-0.4 s) | 20-35 frames | 0.4-0.8 s (one-handed) |
  | Heavy | 12-24 frames (0.4-0.8 s) | 45-80 frames | 0.8-1.5 s (two-handed) |

- **Enemy readability.** Wind-up plus attack of at least about 340 ms. End pose at least about 170 ms (or 240 ms when used as bait) (DS3 analysis).
- **Impact.**
  - Hit-stop of 1-4 frames.
  - Optionally slow the animation for 2-4 frames around contact (MocapOnline).
  - Keep smears to a single frame and freezes subtle (SLYNYRD).
- **Weight cues for heavy weapons.** Slower anticipation and recovery, more frames or longer holds (SLYNYRD); hips lead and the body drops into the strike.
- **Cancel windows.** For player heavies, allow movement cancel late in recovery (Aztez; MocapOnline suggests about 70% into recovery for combos).
- **Recovery length matches gameplay.** The animation recovery must equal the gameplay recovery exactly, so the character is not "free" while still visibly recovering (MocapOnline).

**Common mistakes.** Hitbox frames not aligned with the visual contact; recovery animations shorter than gameplay lockout or vice versa; heavy attacks with light-attack anticipation; huge hitboxes with no visual reason.

**Example.** See section 20.

**Validation methods.**
- **Hitbox alignment.** The active-frame window from gameplay data must contain the frame where the weapon tip crosses the contact plane (ground y for a smash).
- **Budgets.** Phase durations within the budget tables.
- **Hit-stop.** The hit-stop length is within 1-4 frames.

**Sources.** https://www.gamedeveloper.com/game-platforms/anatomy-of-an-enemy-attack-in-dark-souls-3 ; https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide ; https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks ; https://aztez.com/blog/2012/05/24/the-amalur-problem/.

**Exceptions / limitations.** Fighting games and souls-likes deliberately differ: fighting games use exact frame data, and souls-likes use long commitment. Numbers are genre conventions, not physics. Calibrate them per game.

---

## 18. Creature and big-character animation

**Concept.** Size is communicated mostly through timing. Bigger bodies move with longer durations, larger arcs, more delayed overlap, and heavier settles. Gravity's effect over larger distances takes more frames: a fall from greater height lasts longer (y = ½gt², Oba). Big characters also need wider bases and lower CoM for stability (Human Kinetics). The Animation Mentor big-vs-small article was not readable, so this section relies on physics sources and general craft.

**Practical rules.**
- **Scale timing with size.** For a pendulum, the period grows with the square root of length, and a longer pendulum falls more slowly (Oba). A limb twice as long swings roughly 1.4 times slower if scaled naturally. Use this as the baseline for scaling limb-swing timing `[derived from physics]`.
- **Ground contact.** Big characters should show more ground contact, a wider stance, a slower weight transfer, and a bigger settle after impact (deeper knee bend, longer hold).
- **Overlap.** Jowls, belly, tail and armour need larger lag. Use 2-6 frames instead of 1-3 `[derived]`.
- **Exaggerated hitboxes** are common for big enemies but hurt clarity (DS3 analysis on Midir).
- **Non-human creatures.** Apply joint ranges per species or design. Keep the hinge rules: the knee/ankle bend direction must stay consistent.

**Common mistakes.** Scaling a human animation up with no timing change (it looks like a toy); big creatures with snappy, small-character spacing; no ground reaction (dust, settle) on heavy steps.

**Example.** A 3-times-height ogre doing the same overhead smash: the timing scales by about √3 ≈ 1.7. A 60-frame human attack becomes about 100 frames, the hold at the top lengthens, and the impact settle doubles.

**Validation methods.**
- **Size ratio.** For each rig, compare total duration and peak limb angular velocity against the human reference. Angular velocity should scale about 1/√(size ratio) unless the character is flagged "superhuman".
- **Stance width.** Stance width over hip height should be at least the human baseline for heavy characters.

**Sources.** https://gamedeveloper.com/design/center-of-mass-tools-and-techniques-for-animating-natural-human-movement ; https://us.humankinetics.com/blogs/excerpt/factors-affecting-stability ; https://www.gamedeveloper.com/game-platforms/anatomy-of-an-enemy-attack-in-dark-souls-3. https://www.animationmentor.com/blog/tutorial-animating-big-and-small-characters/ returned 403.

**Exceptions / limitations.** Insects and small creatures move faster than the √-scaling suggests (muscle and strength scaling differ). Magic or mechanical giants can be designed fast. The pendulum rule is a baseline, not a law of animal motion.

---

## 19. Stylisation (what can be exaggerated vs what must stay plausible)

**Concept.** Exaggeration pushes reality for clarity and appeal, but it must stay coherent so the viewer isn't confused (Wikipedia). For a game's readability, it is usually safe to exaggerate *how much* (pose extremes, timing contrast, smears, squash) but risky to break *how* (the direction of joints, the sequence of force, ground contact).

**Practical rules.**
- **May be exaggerated:**
  - Pose extremes, about 10-20% past the clinical ROM, for stylised rigs only.
  - Anticipation depth and hold length.
  - Speed contrast: slow wind-up versus a very fast swing.
  - Smear frames, which may even slightly elongate the arm or weapon at maximum extension (SLYNYRD).
  - Squash/stretch on the torso and head.
  - Hit-stop and camera shake.
  - Hitbox size, which is a gameplay choice.
- **Must stay plausible:**
  - Hinge direction (elbows, knees).
  - Planted feet that do not slide.
  - Weight shift preceding the strike.
  - Proximal-to-distal ordering.
  - CoM over the support in held poses.
  - The two-hand grip staying on the handle.
  - Arcs (no linear chords), unless it is a deliberate smear.
  - Eyes on the target.
  - Recovery that is proportional to weapon mass.
- **Be consistent.** Choose a stylisation level per project and apply it consistently. Mixing realistic and rubber-hose motion on the same character reads as an error.

**Common mistakes.** "Exaggeration" used to excuse broken mechanics (backward knees, floating feet); exaggeration inconsistent between attacks.

**Example.** A stylised hero can arch to about 35 degrees of spine extension at the top of the windup (versus about 25 clinical) and stretch the swinging arm by 5% on the smear frame. The knees, feet, weight shift and sequencing stay realistic.

**Validation methods.**
- **Profile.** Run all checks with a per-project "stylisation profile". Realistic: ROM ×1.0, stretch 0. Stylised: ROM ×1.2, stretch ≤ 10% on tagged smear frames only.
- **Never relaxed:** hinge-direction, foot-lock and peak-ordering checks.

**Sources.** https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks.

**Exceptions / limitations.** Fully cartoon (rubber-hose) styles can break hinge rules intentionally. Document such exceptions per character, not per animation.

---

## 20. Heavy overhead hammer smash: body mechanics checklist

Assumptions:
- Human character, two-handed heavy hammer (sledgehammer or maul class).
- Side or three-quarter view, with the front (lead) foot toward the target.
- The rear hand is at the end of the handle and the lead hand is nearer the head.

**Evidence caveat.** No published kinematics study of overhead sledgehammer smashes was found. This checklist combines four kinds of evidence:
- Measured ROM (sections 3-4).
- General kinetic-chain findings from throwing, serving and hammering (section 8).
- Game-timing conventions (section 17).
- Craft and lifting sense, marked `[derived]`.

Get a lead animator or a motion-capture reference to sign off on it.

### 20.1 Phases and relative timing

Suggested durations for a **player heavy attack at 30 fps, total about 60 frames (2.0 s)**. This sits within MocapOnline's 45-80-frame heavy budget. Percentages are `[derived]` from the Aztez, MocapOnline, DS3 and SLYNYRD figures.

| Phase | Frames (30 fps) | Share | Notes |
|---|---|---|---|
| Idle / ready | (loop) | – | Starts from a staggered stance |
| Anticipation (dip) | 3-5 | ~6-8% | Small knee dip, hammer lowers slightly: a pre-load |
| Windup (raise to top) | 10-16 | ~20-25% | Hammer up and back overhead; ease out of the dip, slow into the top |
| Top hold | 2-6 | ~4-8% | Longer for an enemy telegraph (enemy wind-up plus attack ≥ 340 ms) |
| Swing (downswing) | 5-8 | ~10-13% | Fastest phase; peak speed in the final third (MocapOnline: 60-70% through the arc) |
| Impact + hit-stop | 1 + 2-4 | ~5% | Hitbox active 2-4 frames around contact |
| Follow-through / settle | 4-8 | ~8-12% | Hammer rebounds or embeds; body keeps sinking 2-4 frames; hold |
| Recovery (lift) | 10-15 | ~18-25% | Lift with the legs; cancel window opens at about 70% of recovery |
| Return to idle | 6-10 | ~10-15% | Blend back to the stance |

**Rule of thumb ratios** `[derived]`:
- Anticipation plus windup plus hold ≈ 3× the swing.
- Recovery plus return ≈ 2.5-4× the swing.
- The swing is the shortest major phase.

For an **enemy heavy**: lengthen the windup and hold, so the telegraph is at least 340 ms and for a new move longer (about 600-1000 ms is common practice `[derived]`). Keep the swing fast.

**Weapon-weight effect on timing** `[derived from SLYNYRD, MocapOnline, the momentum section]`:
- Heavier means a longer windup (it takes time to lift), a longer top hold, and a *still short* swing, because gravity and the body both accelerate it.
- It also means a longer follow-through and recovery, because the weapon must be decelerated and re-lifted.
- As a starting scale, multiply windup and recovery durations by about (m/m_ref)^0.5, capped by gameplay. Keep the swing within ±25% of the reference.

### 20.2 What each body part does, phase by phase

Notation: "flex" is the amount of bend from straight. Elbow 0 is straight. Knee 0 is straight. Trunk "extension" is arching back; "flexion" is bending forward.

**Idle / ready**
- **Feet:** Staggered stance, lead foot forward. The width along the attack direction is about 1-1.5× shoulder width. Both feet planted (locked).
- **Knees:** Soft, about 10-25 degrees of flexion.
- **Hips:** Square to the target or slightly turned. CoM between the feet, slightly toward the rear.
- **Spine:** Neutral, slight forward lean.
- **Shoulder girdle:** Relaxed, scapulae neutral.
- **Shoulder:** Arms low, hammer held across the body or resting on the shoulder.
- **Elbow:** Moderately bent, about 40-90 degrees depending on the carry pose.
- **Wrist:** Neutral grip.
- **Head/eyes:** Eyes on the target.

**Anticipation (dip)**
- **Feet:** Planted.
- **Knees:** Flex further, by about 10-15 degrees more. This loads the legs.
- **Hips:** Sink, and drift slightly back.
- **Spine:** Slight flexion.
- **Shoulder girdle:** Slightly depressed.
- **Shoulder:** Hammer dips slightly or pulls back toward the rear hip. This is the counter-move.
- **Elbow:** Bends a little more.
- **Wrist:** Neutral.
- **Head/eyes:** Head steady, eyes on the target.

**Windup (raise to top)**
- **Feet:** Planted. The rear heel may stay down, and weight shifts toward the rear foot (about 55-65%) `[derived]`.
- **Knees:** Extend as the body rises (leg drive lifts the hammer). Not locked straight; about 5-15 degrees remains.
- **Hips:** Rise. The pelvis tilts back slightly and the hips drift slightly forward under the raised load to keep the combined CoM over the base.
- **Spine:** Moves into extension (arch). Within about 25 degrees of thoraco-lumbar extension for realistic rigs, up to about 35 if stylised. A slight rotation toward the rear-hand side is acceptable in three-quarter view.
- **Shoulder girdle:** Scapulae upwardly rotate and elevate as the arms go overhead. The shoulder pivot rises toward the ears (2:1 rhythm). Scapulae retract slightly.
- **Shoulder:** Flexes toward about 150-175 degrees (arms overhead). The hammer head goes behind the head.
- **Elbow:** **Bent** at the top, about 70-120 degrees of flexion, so the hammer head can drop behind the head and the arms frame the head. The elbows point forward and up, not out to the side across the face.
- **Wrist:** Cocked: extension plus radial deviation. The head of the hammer trails low behind the shoulders.
- **Head/eyes:** Head stays upright or tilts slightly back with the trunk. Eyes stay on the target; the head is *between* the arms, not hidden by a forearm.

**Top hold**
- **Feet:** Planted.
- **Knees:** Slight flex.
- **Hips:** Begin to move forward *before* the arms start down. This is the overlap and kinetic-chain lead.
- **Spine:** Peak extension; the "stretch" is at its maximum.
- **Shoulder girdle:** Fully elevated and upwardly rotated.
- **Shoulder:** Maximal flexion.
- **Elbow:** Bent, as at the top.
- **Wrist:** Fully cocked. The hammer head keeps drifting back for 1-2 frames (drag).
- **Head/eyes:** Locked on the target.

**Swing (downswing)**
- **Feet:** Planted. Weight transfers to the lead foot (about 60-70% by impact) `[derived]`. The rear heel may lift.
- **Knees:** Flex quickly. The body drops into the strike, which adds body mass behind it; the lead knee flexes about 30-60 degrees by impact `[derived]`.
- **Hips:** Hinge: hip flexion drives the trunk forward and down. Pelvis angular velocity peaks first in the chain.
- **Spine:** Travels from extension through neutral into moderate flexion. Trunk velocity peaks after the pelvis.
- **Shoulder girdle:** Scapulae depress and downwardly rotate, and protract as the arms come forward and down.
- **Shoulder:** Extends powerfully, from overhead to in front of the body at chest-to-waist height. Peaks after the trunk.
- **Elbow:** **Extends** during the downswing. It is nearly straight (about 0-20 degrees of flexion) in the last frames before impact, which maximises the radius and the head speed.
- **Wrist:** Holds the cock until late, then releases (flexion plus ulnar deviation) in the last frames. The wrist and hammer-head peak comes last.
- **Head/eyes:** Head moves down with the trunk but stays stable relative to it. Eyes on the contact point.

**Impact (contact) plus hit-stop**
- **Feet:** Planted and wide. The CoM projection is between the feet, toward the lead foot.
- **Knees:** Both bent. Lead knee about 30-60 degrees, rear knee similar or more.
- **Hips:** Flexed, about 40-70 degrees `[derived]`. The pelvis is low.
- **Spine:** Moderately flexed, but the back is long rather than collapsed. No single spine bone bends more than about 60% of the total.
- **Shoulder girdle:** Protracted and depressed.
- **Shoulder:** Arms in front, about 30-70 degrees of flexion. The hands are low, in front of the lead foot.
- **Elbow:** **Near-extended but not locked.** About 5-20 degrees of flexion absorbs the shock. Elbow angle at or past 0, meaning a locked or hyperextended elbow at impact, is an error.
- **Wrist:** Fully released, firm grip. The hammer shaft is roughly aligned with the forearms or slightly past.
- **Head/eyes:** Eyes on the impact point. The head does not snap forward beyond the trunk motion.

**Follow-through / settle**
- **Feet:** Still planted. No sliding.
- **Knees:** Continue flexing 2-4 frames after contact (they absorb the shock), then hold.
- **Hips:** Sink a little further, then stop.
- **Spine:** Slight further flexion, then hold.
- **Shoulder girdle:** Small recoil (elevation jolt).
- **Shoulder:** Small rebound upward if the surface is hard, or continuation down if it gives.
- **Elbow:** Flexes slightly with the recoil, by about 5-15 degrees more.
- **Wrist:** May extend slightly with the rebound.
- **Head/eyes:** Eyes stay on the impact point. A slight head bob that lags the trunk by 1-2 frames is acceptable.

**Recovery (lift)**
- **Feet:** Planted. Weight moves back toward the centre.
- **Knees:** Extend; the legs do the lifting.
- **Hips:** Extend to lift the trunk. The hips lead the shoulders.
- **Spine:** Returns to neutral, with the back kept long. Don't lift by curling the spine.
- **Shoulder girdle:** Returns to neutral.
- **Shoulder:** Brings the hammer up and back to the carry position. A short arc, not a straight line.
- **Elbow:** Bends, toward about 60-90 degrees.
- **Wrist:** Neutral.
- **Head/eyes:** Head rises with the trunk. Eyes can scan back to the target.

**Return to idle**
- **Feet:** Optional small foot adjustment, as a stepped key. Never a slide.
- **Knees:** Back to soft.
- **Hips:** Settle into idle.
- **Spine:** Neutral.
- **Shoulder girdle:** Neutral.
- **Shoulder:** Idle carry.
- **Elbow:** Idle carry.
- **Wrist:** Idle.
- **Head/eyes:** Settle, eyes on the target.

### 20.3 Where the elbow is bent vs extended (summary)

| Phase | Elbow |
|---|---|
| Idle | Bent, carry |
| Anticipation | Bent a little more |
| Windup top | **Most bent**, about 70-120 degrees; the hammer drops behind the head |
| Downswing | **Extending** |
| Just before and at impact | **Near straight**, about 5-20 degrees, never locked or hyperextended |
| Follow-through | Re-bends slightly (recoil) |
| Recovery | Bends to carry |

The elbow extension peak should come *after* the shoulder and trunk peaks and *before* the wrist release (section 8).

### 20.4 Common mistakes and checks

| Mistake | Why it is wrong | Check |
|---|---|---|
| **Forearm crossing the face** (front arm passes over the head or eyes at the windup top in a side view) | Real overhead swings frame the head between the arms. The elbows point forward and up. A forearm across the face hides the eyes and implies an impossible shoulder or IK flip. | Head circle (or eye point) vs the forearm segment of the near arm: no intersection on screen in frames from windup to swing, unless draw order places the forearm behind the head and the pose is a deliberate three-quarter view. Also run the elbow IK flip check. |
| **Arm-only swing** | Loses about half of the available energy (kinetic-chain data). Looks weak. | Pelvis and trunk angular-velocity peaks must exist (above a threshold) and precede the arm peaks. Hip/root vertical travel windup-top to impact of at least 5% of body height `[derived]`. |
| **No weight shift** | Force comes from the ground. A static CoM reads as weightless. | The CoM-between-feet fraction moves rear to front by at least 0.15 from windup top to impact `[derived]`. |
| **Locked or hyperextended elbows at impact** | Unrealistic and visually brittle. | Elbow flexion at the impact frame within [5, 25] degrees. |
| **Hinge flip** (elbow or knee bends the wrong way) | Anatomically impossible. | Cross-product sign is constant. |
| **Foot sliding** | Breaks ground contact; looks floaty. | Planted-foot drift below 2 px per frame. |
| **Linear weapon path / chord through the head** | IK-tweened hands. | Tip path straightness and head-clearance check (section 9). |
| **Swing slows before contact** | Wrong spacing; reads as a weak tap. | Tip speed at contact at least 80% of the swing max. |
| **No hold, or overly long hold, at the top** | Too short gives no weight; too long gives input lag. | Hold within budget: player 2-6 frames, enemy longer. |
| **Spine-only bend** (back folds while hips and knees stay straight) | Unrealistic and hurts readability. | Hip and knee flexion at impact above their minima; no spine bone over 60% of the trunk bend. |
| **Head whips around or eyes leave the target** | Loses intent and readability. | Head world angle change between consecutive frames below 15 degrees except at impact; gaze vector within 30 degrees of the target at the key frames `[derived]`. |
| **Shoulder pivot fixed while the arms go overhead** | Ignores scapulohumeral rhythm, so the arms pop out of the torso. | Scapula/clavicle bone elevation coupling (section 2). |
| **Rear hand drifts off the handle** | Breaks the rigid two-hand grip. | Hand-to-handle distance below 2% of handle length. |
| **Recovery shorter than gameplay lockout (or the reverse)** | Visual and gameplay desync. | Animation recovery frames equal the gameplay recovery frames. |
| **Identical timing for light and heavy hammers** | Mass not communicated. | Windup and recovery scale with mass (section 20.1). |

---

## Source list

| URL | What it contributed | Read? |
|---|---|---|
| https://www.animationmentor.com/blog/animation-tips-tricks-what-makes-or-breaks-a-good-body-mechanics-shot/ | Intended: body-mechanics shot criteria | **Failed (HTTP 403)** |
| https://www.animationmentor.com/blog/how-to-animate-weight-and-force-lifting-heavy-object/ | Intended: lifting weight/force | **Failed (HTTP 403; web.archive.org also not fetchable)** |
| https://www.animationmentor.com/blog/how-to-create-believable-weight-in-animation/ | Intended: weight | **Failed (HTTP 403)** |
| https://www.animationmentor.com/blog/tutorial-animating-big-and-small-characters/ | Intended: size and timing | **Failed (HTTP 403)** |
| https://www.animationmentor.com/blog/tutorial-animating-pushing-and-pulling-motions/ | Intended: push/pull | **Failed (HTTP 403)** |
| https://www.youtube.com/watch?v=uDqjIdI4bF4 | Only the title ("12 Principles of Animation (Official Full Series)"); no transcript or description | **Partial (page shell only)** |
| https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation | The 12 principles, as a secondary summary of Thomas & Johnston (*The Illusion of Life*) and Lasseter 1987 | Read |
| https://en.wikipedia.org/wiki/The_Animator%27s_Survival_Kit | Book metadata only (Williams, 2001); no technique content | Read |
| https://www.awn.com/print/animationworld/animators-survival-kit-most-valuable-how-animate-book-you-will-ever-want-own | Table-of-contents description of the Survival Kit (timing/spacing, weight, anticipation chapters) | Search snippet only |
| https://wikem.org/wiki/Joint_ROM_(Table) | ROM table for spine, neck, shoulder, elbow, forearm, wrist, hip, knee, ankle (Luttgens & Hamilton 1997) | Read |
| https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html | Measured adult ROM means by age and sex (more than 600 people, 2003-2006) | Read |
| https://www.physio-pedia.com/Range_of_Motion_Normative_Values | Intended: normative ROM | **Failed (HTTP 403)** |
| https://pmc.ncbi.nlm.nih.gov/articles/PMC9218764/table/T1 | Normative ROM table | **Failed (bot check)**; values seen only in a search snippet |
| https://ouhsc.edu/bserdac/dthompso/web/namics/scapryme.htm | Scapulohumeral rhythm: 2:1 ratio, 30-degree setting phase | Read |
| PMC3377910, PMC2841046, McClure 2001 (uoregon.edu) | Measured scapulohumeral ratios 1.7-2.7:1 | Search abstracts only |
| https://dptcapstone.web.unc.edu/2014/04/22/kinetic-chain-concepts-and-exercise-progression-for-tennis-players | Kinetic chain, proximal-to-distal, 51%/54% figure (citing Kibler 1991) | Read |
| https://pubmed.ncbi.nlm.nih.gov/22666599/ | Sciascia et al., kinetic chain rehabilitation framework | **Failed (cookie wall)** |
| https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.1044616/pdf | Leenen 2022: summation of speed, pelvis-trunk separation in pitching | PDF metadata/title only; findings from search snippets |
| https://pmc.ncbi.nlm.nih.gov/articles/PMC2901240 | Hammering sequence: shoulder/elbow extension, then supination, then wrist snap | **Failed (bot check)**; search snippet only |
| https://pmc.ncbi.nlm.nih.gov/articles/PMC3368495 and https://vivo.weill.cornell.edu/display/pubid20610055 | Wrist dart-throw path in hammering (extension+radial to flexion+ulnar, ~41 degrees off sagittal, ~71 degrees range) | Search snippet only; the Weill page redirect had no abstract |
| https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_proquest_miscellaneous_1865821442 | Heavier hammer raises joint moments, most at distal joints | Search snippet only |
| https://www.animatorisland.com/principles-of-animation-physics-part-4/ | CoG, line of gravity, base of support, contrapposto, heavy-load lean, parabolic CoG in jumps | Read |
| https://us.humankinetics.com/blogs/excerpt/factors-affecting-stability | Stability factors: base size, CoG height, line of gravity, mass, widening toward force (Burkett, *Applied Sport Mechanics*) | Read |
| https://gamedeveloper.com/design/center-of-mass-tools-and-techniques-for-animating-natural-human-movement | CoM as a guide not a control, rotation about CoM, parabolic falls, pendulum timing (Oba 2010) | Read |
| https://en.esotericsoftware.com/spine-ik-constraints | Spine IK: one/two-bone, bend direction, mix, softness, stretch, flipping, FK vs IK | Read |
| https://docs.blender.org/manual/en/latest/animation/armatures/posing/bone_constraints/inverse_kinematics/introduction.html | Intended: pole targets | **Failed (only navigation text returned)** |
| https://www.gamedeveloper.com/game-platforms/anatomy-of-an-enemy-attack-in-dark-souls-3 | Attack phases, ≥340 ms telegraph, 2-4 frame hitboxes, end-pose timings, latency thresholds (Zhang 2022) | Read |
| https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide | Light/heavy frame budgets, peak speed at 60-70% of arc, hit-stop 1-4 frames, recovery durations | Read (vendor blog: practice, not research) |
| https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks | Heavy weapons need slower anticipation and recovery and longer holds; single smear frame; arc width vs speed | Read |
| https://aztez.com/blog/2012/05/24/the-amalur-problem/ | Frame breakdown of a 60-frame slash; cancel windows vs responsiveness | Read |

Gaps worth filling later: a motion-capture or published kinematic study of overhead sledgehammer or maul strikes, a verified anthropometric segment-mass table (Winter), the Animation Mentor articles (fetch through a browser), and the Survival Kit's chapters on weight and anticipation (the physical book).
