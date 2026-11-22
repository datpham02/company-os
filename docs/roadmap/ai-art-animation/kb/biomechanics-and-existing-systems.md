# Functional Anatomy & Biomechanics System: existing knowledge and systems

> **Status:** `PROPOSED` (Biomechanics, kinesiology and existing systems (licences)). Compiled 2026-11-22 by a Claude Code research agent for the Board in the studio's own words, with sources and read status; claims not confirmed on a page are tagged. Content review by `director` pending (K4).


Research date: 2026-11-22. Scope: 2D code-driven rigging and animation by AI agents (skeleton JSON, FK/IK, retargeting from mocap, automated pose/motion QA).

Method: pages were read with WebFetch. Nothing was downloaded or installed. Where a page failed or did not contain the claim, that is marked. Statements tagged **[GK]** are general engineering knowledge that I did not verify against a page in this session. Treat them as hypotheses until checked.

Licence notes are summaries of what the pages say, not legal advice.

---

## Part 1: Biomechanics for animation (practical models + validation signals)

Each topic gives: the idea, a **2D-computable model**, and a **validation signal** our QA could compute from a skeleton pose sequence.

### 1.1 Kinetic chains and proximal-to-distal sequencing

- **Idea.** In fast throws, strikes and swings, motion starts in the big proximal segments (legs, hips, trunk) and flows outwards (shoulder, elbow, wrist). Each more distal segment starts its main motion around when the previous segment reaches peak speed, and endpoint speed grows down the chain. Ellenbecker & Aoki (2020) report hip and trunk supply about half the energy in throwing, and that a 20% loss of hip/trunk energy would need about 34% more shoulder rotation speed to compensate. They also note exceptions: shoulder internal rotation and forearm pronation peak late, so the rule is a strong tendency, not a law.
- **2D model.** For a chain list (e.g. `pelvis → chest → upperArm → foreArm → hand → tool`), compute angular velocity of each segment per frame (finite differences of world angle). Find the frame of peak |ω| for each segment within the action window.
- **Validation signal.** `sequence_ok = peak_frame[i] <= peak_frame[i+1]` for each adjacent pair (allow a tolerance, e.g. 1 to 2 frames at 24 fps; whitelist known exceptions such as forearm pronation). Also check `peak_endpoint_speed` increases distally. Flag "arm-only" swings where the pelvis/chest peak is missing or after the hand.

### 1.2 Joint coordination

- **Idea.** Joints in one limb move with stable phase relationships (hip-knee-ankle in gait, shoulder-elbow in reaching). Overlapping action in animation (one part lags another) is the art-side name for the same thing (Twelve principles of animation, Wikipedia).
- **2D model.** Store per-motion "coupling rules" as offsets: e.g. knee flexion peak lags hip flexion peak by a fraction of the cycle; elbow extension follows shoulder flexion. Represent as `(jointA, jointB, expected_phase_lag, tolerance)`.
- **Validation signal.** Cross-correlation lag between joint angle curves vs expected lag; flag "all joints hit keyframes on the same frame" (zero lag everywhere = robotic).

### 1.3 Centre of mass, balance, support polygon, ZMP

- **Whole-body CoM.** Weighted sum of segment CoMs using mass fractions (tables in 1.10). In 2D: `CoM = Σ m_i · p_i / Σ m_i`, where `p_i = proximal + cm_frac_i · (distal − proximal)`.
- **Support polygon.** The convex hull of all ground contact points (feet, hands, tail, tool tip on ground). In 2D side view it collapses to a **support interval** on the ground line `[x_min, x_max]`.
- **Static balance.** Holding still is balanced when the vertical projection of CoM lies inside the support polygon/interval.
- **Dynamic balance and ZMP in simple words.** When the body accelerates, gravity alone no longer decides tipping. The zero-moment point is the ground point where the combined tipping effect of gravity plus inertia cancels. If it stays inside the support polygon, the feet do not roll over an edge; if it would fall outside, the character must tip, step, or be holding something (Wikipedia, Zero moment point; Goswami 1999 also discusses the related foot-rotation indicator). 
- **2D model (cart-table / point-mass) [GK].** `x_zmp ≈ x_com − (z_com / g) · ẍ_com` (z = CoM height above ground, ẍ = horizontal CoM acceleration). The Wikipedia page gives only the general vector form; this simplified form is from the robotics literature (Kajita's cart-table model) and was not verified on a page here.
- **Validation signals.**
  - `static_balance_margin = signed distance of CoM_x to the nearest support interval edge` on frames flagged as "hold" or "still". Negative → fail.
  - `zmp_margin` on all grounded frames. Negative for more than N frames without a step, fall, or external support → fail ("leaning on air").
  - Flying phases (no contact) skip ZMP checks but must follow ballistic CoM (see 1.6).

### 1.4 Support points and contacts

- **Idea.** A contact is where force is exchanged with the world: heel, ball of foot, toe, hand on wall, knee on ground, tail, wing tip on perch, insect tarsus, serpent belly segment.
- **2D model.** Each anatomy profile lists named **contact sites** (bone + local offset + radius + type: `point|line|area`) and each motion clip carries a per-frame **contact schedule** (which sites are planted). This is also what retargeting needs to keep feet planted.
- **Validation signals.** Planted site world-velocity ≈ 0 (foot skating), height ≈ ground (floating/penetration). See Part 2 §2.10 for thresholds used in research.

### 1.5 Ground contact, foot roll, ground reaction force

- **Idea.** A walking foot rolls heel → flat → ball → toe. Vertical ground reaction force (GRF) in walking shows a two-hump curve, with peaks around body weight rising to roughly 1.5× body weight with speed; running peaks are roughly 2 to 3× body weight with a shorter contact and a different, single-hump shape. Fore-aft GRF first brakes (until about mid-stance) then propels (search-result excerpts of Nilsson & Thorstensson 1989 and a gait lecture; the PubMed page itself failed). On level ground the GRF points roughly from the contact up through or near the CoM.
- **2D model.**
  - Foot as three contact points: heel, ball (metatarsal head), toe tip. Stance phases = which of these are planted.
  - **GRF direction proxy:** vector from centre of pressure (planted points) to CoM. With a friction cone (μ ≈ 0.6 to 1.0 on dry ground [GK]) we can check whether the implied horizontal push is plausible.
  - **Vertical load proxy:** `F ≈ m (g + z̈_com)`. Peaks give "how hard did the character land".
- **Validation signals.**
  - Heel-before-toe order at contact for walking clips (unless the clip is tagged forefoot run/sneak/tiptoe).
  - `z̈_com` at landing implies `F/mg`. Flag > ~3 for a "light" step or < 1.0 at a landing that should absorb impact (no knee/hip flexion).
  - Friction: `|ẍ_com| / (g + z̈_com) > μ` while all contacts are planted → "ice skating" / impossible push.

### 1.6 Momentum, angular momentum, why arms counter-rotate

- **Idea.** With no external torque (e.g. in the air), whole-body angular momentum is conserved; limbs swung one way rotate the rest of the body the other way. In walking, the swinging legs create vertical angular momentum; the arms swing opposite and largely cancel it. Collins, Adamczyk & Kuo (2009) found that holding or binding the arms raised the peak vertical ground reaction moment by about 63%, and walking with arms in phase with legs (opposite of normal) raised it by about 83% and metabolic cost by about 26%. A passive walker model with free arms swings them naturally, so arm swing largely "comes for free".
- **2D model.** In 2D side view, compute angular momentum about the CoM: `L = Σ [ m_i (r_i × v_i) + I_i ω_i ]`, with `I_i = m_i (rg_i · length_i)^2` using radius-of-gyration fractions (tables in 1.10). Linear momentum `P = M · v_com`.
- **Validation signals.**
  - **Airborne frames:** CoM path must be a parabola (`z̈_com ≈ −g`, `ẍ_com ≈ 0`) and `L` must stay constant within tolerance. Violations mean "the character steered in mid-air" (allowed only if a tag such as `cartoon_air_control` is set).
  - **Gait:** left arm swing phase opposite to left leg (i.e. same phase as right leg). Flag same-side arm and leg swinging together ("homolateral walk") unless deliberately tagged.
  - **Take-off/landing:** momentum change must be explained by contact time and plausible GRF.

### 1.7 Weight transfer

- **Idea.** Before stepping, punching or throwing, the CoM shifts over the support foot; the unloaded foot is free to lift. Weight shift precedes lift.
- **2D model.** Per frame, compute fraction of support on each contact by CoM position within the support interval (lever rule: closer foot carries more). This is a proxy, not true force distribution.
- **Validation signal.** A foot may only lift when its load share was below a threshold (e.g. < 20%) on the previous frames, or the motion is dynamic (ZMP check passes). Flag "foot lifts while carrying most weight".

### 1.8 Force transmission

- **Idea.** Force reaches a hand or tool through the chain: ground → legs → pelvis → trunk → shoulder → arm. A strong push needs a braced base: the GRF line should point roughly through the body towards the contact being pushed.
- **2D model.** For push/pull/hit poses, draw the line from rear-foot contact to hand contact. Count how far CoM and the major joints deviate from that line (a straight, aligned chain transmits force with low joint torque) and whether the front knee/elbow is near lock or slightly bent.
- **Validation signal.** "Bracing score": angle between hand force direction and the line from support to hand; joint torque proxy `|r × F|` at the knee/hip/shoulder relative to segment strength. Flag big pushes delivered from an unbraced, off-balance stance.

### 1.9 Object interaction, grips, tool inertia

- **Power vs precision grip.** Napier (1956) split prehension into a power grip (object clamped between flexed fingers and palm, thumb as counter-pressure) and a precision grip (object pinched between finger pads and the opposed thumb, away from the palm). Later work adds hook grip and lateral pinch and notes some grasps mix both (PMC1312228 overview).
- **Two-handed tool grips [GK].** For a sword, axe, bat or spear: the rear hand (near the pommel/knob) acts as the pivot/lever, the front hand steers; hands are spaced so the tool behaves like a lever. The tool becomes an extra rigid segment closing a **loop** between two hands, which an IK solver must keep consistent (constant hand-to-hand distance along the handle).
- **Heavy tool inertia.** Swing speed tracks the tool's moment of inertia about the pivot (swing weight) more than its mass: Cross & Bower (2006) found speed essentially unchanged across masses when swing weight was held constant; Russell's bat pages report lower-MOI bats swing faster mainly in the late wrist-rotation phase.
- **2D model.**
  - Attachments: `grip sites` on the hand (palm centre for power grip, thumb-index tip for precision grip) and `handle points` on the prop.
  - Prop has mass, CoM offset, and `I_pivot = I_com + m d^2` (parallel axis) [GK].
  - Timing heuristic: wind-up and follow-through duration scale with `sqrt(I_tool + I_arm)`; heavier/longer props need more anticipation, more trunk rotation, a wider stance and a longer recovery [GK].
- **Validation signals.**
  - Hand-to-handle distance ≈ 0 on all gripped frames (no "floating prop").
  - Two-hand grips: inter-hand distance stays within handle length and both hands lie on the handle line.
  - Whole-body CoM including the prop stays within support when holding heavy props still (the character must counter-lean).
  - Swing peak angular speed should drop as prop `I` grows; flag a 20 kg hammer swung as fast as a dagger.

### 1.10 Segment mass and CoM tables (source actually read)

**Source read:** BMClab / Marcos Duarte data files on GitHub (`BSPmale_ZdeLeva.txt`, `BSPfemale_ZdeLeva.txt`, `BSP_DempsterWinter.txt`), which tabulate de Leva (1996) adjustments of Zatsiorsky-Seluyanov and Dempster's data as reported by Winter. Repository: non-software content CC BY 4.0, code MIT. I did not read the original de Leva paper or Winter's book. The ExRx segment page (403) and the Visual3D wiki (403) failed.

Values are fractions. "CM" = distance of the segment CoM from the **first** listed endpoint, as a fraction of segment length. "Rg" = radius of gyration as a fraction of length.

**Table A: de Leva (1996), joint-centre based (adults)**

| Segment | Endpoints | Mass M | Mass F | CM M | CM F | Rg sag M | Rg sag F |
|---|---|---|---|---|---|---|---|
| Head (incl. neck) | vertex → mid-gonion | 0.0694 | 0.0668 | 0.5976 | 0.5894 | 0.362 | 0.330 |
| Trunk | suprasternale → mid-hip | 0.4346 | 0.4257 | 0.4486 | 0.4151 | 0.372 | 0.357 |
| Upper trunk | suprasternale → xiphoid | 0.1596 | 0.1545 | 0.2999 | 0.2077 | 0.716 | 0.746 |
| Middle trunk | xiphoid → omphalion | 0.1633 | 0.1465 | 0.4502 | 0.4512 | 0.482 | 0.433 |
| Lower trunk | omphalion → mid-hip | 0.1117 | 0.1247 | 0.6115 | 0.4920 | 0.615 | 0.433 |
| Upper arm | shoulder JC → elbow JC | 0.0271 | 0.0255 | 0.5772 | 0.5754 | 0.285 | 0.278 |
| Forearm | elbow JC → wrist JC | 0.0162 | 0.0138 | 0.4574 | 0.4559 | 0.276 | 0.261 |
| Hand | wrist JC → 3rd metacarpal | 0.0061 | 0.0056 | 0.7900 | 0.7474 | 0.628 | 0.531 |
| Thigh | hip JC → knee JC | 0.1416 | 0.1478 | 0.4095 | 0.3612 | 0.329 | 0.369 |
| Shank | knee JC → ankle JC | 0.0433 | 0.0481 | 0.4395 | 0.4352 | 0.251 | 0.267 |
| Foot | heel → toe tip | 0.0137 | 0.0129 | 0.4415 | 0.4014 | 0.257 | 0.299 |

(Mass is per single limb segment; both arms and legs are counted separately so the total is 1.0.)

**Table B: Dempster (via Winter), as tabulated by BMClab**

| Segment | Definition | Mass | CM from proximal | Rg about CM |
|---|---|---|---|---|
| Hand | wrist JC → knuckle II | 0.006 | 0.506 | 0.297 |
| Forearm | elbow JC → ulnar styloid | 0.016 | 0.430 | 0.303 |
| Upper arm | shoulder JC → elbow JC | 0.028 | 0.436 | 0.322 |
| Forearm + hand | elbow → styloid | 0.022 | 0.682 | 0.468 |
| Total arm | shoulder → styloid | 0.050 | 0.530 | 0.368 |
| Foot | lateral malleolus → MT II | 0.0145 | 0.500 | 0.475 |
| Leg (shank) | knee JC → medial malleolus | 0.0465 | 0.433 | 0.302 |
| Thigh | greater trochanter → knee JC | 0.100 | 0.433 | 0.323 |
| Head + neck | C7-T1 → ear | 0.081 | 1.000 | 0.495 |
| Trunk | greater trochanter → shoulder JC | 0.497 | 0.500 | n/a |
| HAT (head, arms, trunk) | greater trochanter → shoulder JC | 0.678 | 0.626 | 0.496 |

**How to use in a 2D tool.** Use de Leva as the default human profile (joint-centre endpoints match skeleton bones directly). Use Dempster/Winter only as a cross-check. For stylised or heavy characters, scale mass fractions by visible volume (e.g. area of the drawn segment silhouette × assumed thickness) and renormalise, then let character overrides adjust. Caveats seen in search results: Dempster used 8 elderly male cadavers; DXA studies report de Leva trunk errors of tens of percent. Good enough for animation plausibility, not for science.

**Joint range of motion (human, passive, goniometer, ages 20 to 44)** from the CDC Joint ROM study (Soucie et al. 2011) public-use table (read on the CDC archive page; usage limited to statistical analysis, so cite values rather than redistribute the dataset):

| Motion | F mean (°) | M mean (°) |
|---|---|---|
| Hip flexion / extension | 133.8 / 18.1 | 130.4 / 17.4 |
| Knee flexion / extension | 141.9 / 1.6 | 137.7 / 1.0 |
| Ankle dorsi / plantar flexion | 13.8 / 62.1 | 12.7 / 54.6 |
| Shoulder flexion | 172.0 | 168.8 |
| Elbow flexion / extension | 150.0 / 4.7 | 144.6 / 0.8 |
| Forearm pronation / supination | 82.0 / 90.6 | 76.9 / 85.0 |

These are passive limits; active animation should usually stay a few degrees inside them. Limits also depend on pose (e.g. hip flexion is lower with a straight knee), which is what Akhter & Black's pose-conditioned limits model (see §2.9) captures.

### 1.11 Secondary motion

- **Idea.** Loose parts (hair, cloth, tails, ears, fat, straps, held chains) lag behind the driver, overshoot and settle: follow-through, overlapping action, drag (Twelve principles of animation).
- **2D model.** Damped spring per secondary bone: `θ̈ = k(θ_target − θ) − c θ̇` driven by the parent's world motion; or verlet chain. Spine 4.2 has physics constraints and VRM has spring bones for the same purpose [GK, not read].
- **Validation signals.** Lag: secondary angle peak occurs after the driver's peak by 1 to N frames. Settling: oscillation amplitude decays (no endless jitter). Energy sanity: secondary amplitude does not grow without input.

---

## Part 2: Existing systems to learn from or reuse

### 2.1 OpenSim and its musculoskeletal models

- **Provides.** A physics-based musculoskeletal simulation platform (scaling, inverse kinematics, inverse dynamics, muscle-driven simulation). Models are `.osim` XML files describing bodies with mass and inertia, joints with coordinates (each with a range), and muscles [joint-coordinate range field: GK, not visible on the pages read].
- **Models read on the OpenSim "Musculoskeletal Models" page (page truncated after the third core model):**
  - `gait2392_simbody`: lower-limb with lumped torso, 23 DOF, 92 muscle-tendon actuators, **CC BY 3.0**. Warning that accuracy drops at high knee flexion.
  - `gait2354_simbody`: same skeleton, 54 muscles, **CC BY 3.0**.
  - `gait10dof18musc`: listed, details not visible.
  - Rajagopal full-body model (SimTK `full_body`): 37 DOF, 80 lower-limb muscle-tendon units, 17 upper-body torque actuators. Licence listed as an "MIT Use Agreement"; terms not visible on the page, so commercial status is **unconfirmed**.
  - Arm26, MoBL-ARMS, Hamner, lumbar spine, animal models: **not read** (page truncated; search excerpts only name them).
- **Licence.** OpenSim core software: **Apache 2.0** (read LICENSE.txt), commercial use allowed. Model licences differ per model; CC BY 3.0 allows commercial reuse with attribution.
- **Reuse vs learn.** Reuse (with attribution) the *numbers* from CC BY models: joint coordinate ranges, segment lengths and masses for an adult reference. Learn the *structure*: joints as "coordinates" with default value, range, locked/clamped flags, and coupled coordinates (e.g. knee translation as a function of knee angle) which maps to our "coupled rules". Do not adopt the muscle layer; it is far beyond 2D animation needs.
- **Fit to our schema.** Joint hierarchy, joint types, axes, limits, mass/CoM/inertia per body, coupled rules: strong. Contacts, collision, stylised bodies, 2D: none.

### 2.2 Unity Humanoid (Mecanim) avatar muscles

- **Provides.** A fixed humanoid bone set and "muscles": each muscle is one rotational degree of freedom of one bone. `HumanLimit` stores `min`, `max` (rotation away from the initial value), `center` (default orientation), `axisLength`, and `useDefaultValues`. `HumanTrait` exposes bone count, required bones, muscle names, `MuscleFromBone(bone, dof)`, `GetMuscleDefaultMin/Max` (degrees), parent bone, and default hierarchy mass. Muscles & Settings shows an example default of −40 to 40° for head nod/tilt; translation DoF is optional and limited to a few bones. Animation is stored as normalised muscle values that map into each character's own range [mapping detail GK].
- **Licence.** Unity is proprietary; docs are readable but the engine and data are not redistributable. The concept is free to learn.
- **Reuse vs learn.** Learn: the "muscle = named DOF with min/max/center around a rest pose" model and the idea of storing retargetable motion as **normalised joint values** relative to per-character limits. This is the cleanest pattern for our stylised and heavy humanoid overrides. Do not copy default values from Unity.
- **Fit.** Joint limits, per-character overrides, required vs optional bones: strong. Mass: partial. 2D, creatures, contacts: none.

### 2.3 Unreal Engine: IK Rig, IK Retargeter, Full Body IK

- **IK Rig.** Goals on end bones with position/rotation alpha; a stack of solvers run in order (e.g. limb IK per leg).
- **Full Body IK (Control Rig / IK Rig).** Per-bone settings: rotation and position **stiffness** from 0 (free) to 1 (locked); per-axis limit mode **Free / Limited / Locked** with min/max relative to the reference pose; **preferred angles** that bias bend direction when a chain compresses (docs advise trying preferred angles before limits); root behaviour (pre-pull, pin to input, free); a global mass multiplier; iterations.
- **IK Retargeter.** Characterise both skeletons with named **retarget chains** (start bone → end bone, so bone counts can differ), a designated **pelvis/retarget root** whose motion is scaled proportionally, and an editable **retarget pose** to align A-pose vs T-pose. IK goals after retargeting fix contacts (speed planting, stride warping).
- **Licence.** Unreal Engine EULA, proprietary [GK, licence page not read]. Use as design reference only.
- **Reuse vs learn.** Learn the whole retargeting architecture: chains, retarget root, retarget pose, post-retarget IK for contacts. Adopt the per-joint triplet **stiffness + limit mode + preferred angle** into our schema directly; it is the best-designed per-joint IK hint set found.
- **Fit.** Retargeting, preferred bend direction, limits, stiffness: strong. Creature support: chains are generic, so it works for quadrupeds and multi-limbed rigs.

### 2.4 Godot: SkeletonProfileHumanoid and retargeting

- **Provides.** A read-only, standardised 56-bone humanoid profile (Root, Hips, Spine, Chest, UpperChest, Neck, Head, Jaw, Eyes, legs to Toes, Shoulder to Hand, full fingers) in groups Body/Face/LeftHand/RightHand; `root_bone = Root`, `scale_base_bone = Hips`. Retargeting uses a `BoneMap` from model bones to profile names (auto-mapped by name patterns). Reference pose rules: T-pose, facing +Z, right-handed Y-up, **+Y points from parent joint to child**, **+X rotation bends a joint like a contracting muscle**. Rest Fixer options: apply node transform, normalise position tracks by hip height (reduces foot sliding across heights), overwrite axis, fix silhouette (for A-pose).
- **Licence.** Godot is **MIT**; commercial use allowed with attribution when shipping the engine.
- **Reuse vs learn.** **Reuse** the bone names and the axis conventions (+Y along bone, +X = flexion) as our humanoid canonical naming; reuse the idea of normalising root translation by hip height for retargeting. Godot is also the studio's game engine for Deckbound, so matching its humanoid profile lowers integration cost.
- **Fit.** Hierarchy, naming, axis conventions, retarget scaling: strong. Limits, mass, contacts: none.

### 2.5 Blender Rigify metarigs

- **Provides.** Template "metarigs" that generate full control rigs. Bone positioning guide: limbs placed in a straight line with a slight elbow/knee bend, because (since Rigify 0.5) roll is derived from the **bend axis**; fingers use X as bend axis with rolls recalculated to global −Z, thumb to global +Y; a heel bone spans the foot width at the ground; one spine bone for rigid regions, two for flexible ones. Rigify ships animal metarigs (cat, horse, wolf, bird, shark) and paw/limb rig types [GK, metarigs page failed to show content].
- **Licence.** Rigify is part of Blender (GPL) [GK, not read]. Generated rigs and our own data are not affected, but copying Rigify code would be.
- **Reuse vs learn.** Learn: "a slight rest bend defines the preferred bend direction" is a robust, tool-independent rule we should adopt for 2D (store the rest bend sign). Learn the animal metarig topology as a source for quadruped/bird profiles.
- **Fit.** Bend direction, creature topologies: medium. Limits, mass: none.

### 2.6 Spine and DragonBones (2D)

- **Spine JSON.** Bones ordered parent-first with `x, y, rotation, scaleX/Y, shearX/Y`, `length`, and a `transform` inheritance mode. IK constraints over one or two bones with `target`, `mix`, `softness`, **`bendPositive`** (bend direction), `compress`, `stretch`, `uniform`. Transform and path constraints with mix values. The format docs page does not cover physics constraints.
- **Spine licence.** Runtimes may be integrated, but each user of the product needs their own Spine Editor licence, and products may not replace the editor for creating or editing skeletons/animations. Copyright Esoteric Software. **Risk:** an AI agent tool that authors Spine skeletons/animations might count as an editor substitute. Check with counsel before targeting Spine output.
- **DragonBones.** JSON format with bones and an `ik` array (`bone`, `target`, optional `bendPositive` default true, `chain`, `weight`). DragonBonesJS runtime is **MIT** (read on GitHub); maintenance status unclear.
- **Reuse vs learn.** Adopt the 2D bone transform vocabulary (local x/y/rotation/scale/shear, inheritance modes) and `bendPositive` as our 2D preferred-bend field; it is the 2D equivalent of Unreal's preferred angle. Export to DragonBones (MIT) or to our own format freely; treat Spine export as a licensed integration.
- **Fit.** 2D bones, IK bend direction, constraint mixing: strong. Limits, mass, contacts: none (neither format stores joint limits).

### 2.7 Mixamo skeleton naming

- **Provides.** A de facto humanoid naming with prefix `mixamorig:`: Hips, Spine, Spine1, Spine2, Neck, Head, HeadTop_End; LeftShoulder, LeftArm, LeftForeArm, LeftHand, fingers; LeftUpLeg, LeftLeg, LeftFoot, LeftToeBase, LeftToe_End (from search excerpts of third-party mapping tables; no official Adobe bone list read).
- **Licence.** Adobe FAQ (search excerpt; the FAQ page returned 403): characters and animations royalty-free for personal, commercial and non-profit projects including games; community FAQ says raw files must not be redistributed and content must not be used to train ML models. Auto-rigger is bipedal humanoid only.
- **Reuse vs learn.** Reuse: a **name alias table** (Mixamo ↔ our canonical ↔ Godot ↔ VRM ↔ BVH/CMU) so the retargeter can ingest Mixamo clips. Do not use Mixamo clips to train models.

### 2.8 BVH and ASF/AMC

- **BVH.** `HIERARCHY` with `ROOT`/`JOINT`/`End Site`, per-joint `OFFSET` (relative to parent) and `CHANNELS` (root: 3 translation + 3 rotation, others: 3 rotation; order declared per joint, often Z X Y); `MOTION` with `Frames` and `Frame Time`. No limits, no mass, no axis/rest-pose standard; offsets double as bone lengths.
- **ASF/AMC (Acclaim).** ASF skeleton with `:units`, `:root`, `:bonedata` (per bone `direction`, `length`, `axis`, `dof`, `limits` per dof) and `:hierarchy`; AMC stores per-frame values. The `limits` field is informational for editors and does not constrain the motion data.
- **CMU mocap database** (ASF/AMC, plus BVH conversions): official page failed (TLS certificate error). Search excerpts of the official wording say it is free for all uses including commercial products, but may not be resold directly even in converted form. A 4TU FBX conversion is CC BY-NC 4.0, so pick the original files.
- **Reuse.** Write a BVH importer (it is simple and universal) as the mocap entry point; read ASF `limits`/`axis` as hints only. Use CMU as the default commercially usable mocap source after re-checking the terms page.

### 2.9 VRM humanoid

- **Provides.** VRM 1.0 humanoid: 15 required bones (hips, spine, head, upper/lower leg, foot, upper/lower arm, hand), optional chest, upperChest, neck, eyes, jaw, toes, shoulders, fingers; fixed parent chain (arms hang from upperChest through shoulders; legs from hips); non-humanoid nodes may sit between humanoid bones; `upperChest` requires `chest`. T-pose rules: +Z forward, X lateral with symmetry at X = 0, soles at Y = 0, arms along X, palms facing −Y, thumbs 45° between X and +Z. `VRMC_node_constraint` adds roll, aim and rotation constraints with weight (useful for twist bones).
- **Licence.** The spec pages and repo show no licence file (checked README, repo root; LICENSE path 404). UniVRM (reference implementation) is **MIT**. A secondary blog says the spec is MIT; **unconfirmed**. Per-model VRM licence metadata is separate from the spec.
- **Reuse vs learn.** Reuse the required/optional bone split as our "minimum viable humanoid" rule (a character is valid humanoid if the 15 required bones map). Reuse roll-constraint semantics for 2D twist/fore-shortening helper bones.

### 2.10 SMPL and research joint-limit datasets

- **SMPL.** Licence read: free only for non-commercial research, education or artistic projects; commercial use prohibited (commercial licence via Meshcapade); no training of networks for commercial use; no redistribution. **Do not use** in the product or as training data. Learn from papers only.
- **Akhter & Black 2015 PosePrior (pose-conditioned joint angle limits).** Licence read: non-commercial only, no redistribution, no training of commercial models. **Do not use** the data; the *idea* (limits of a joint depend on the parent pose, e.g. hip flexion depends on knee angle) is reusable as a schema feature ("conditional limits").
- **CDC Joint ROM (Soucie 2011).** Human normal ROM by sex and age (read; see 1.10). Public-use, restricted to statistical analysis: use derived summary values with citation; do not repackage the dataset.
- **OpenSim CC BY models.** Commercially reusable joint ranges with attribution (see 2.1).

### 2.11 Creature anatomy references for profiles

- **Plantigrade / digitigrade / unguligrade (Wikipedia, Digitigrade).** Plantigrade (humans, bears) walk on the whole sole; digitigrade (cats, dogs, birds) on the toes with heel raised; unguligrade (horses, cattle) on the tips of the digits. In digitigrade and unguligrade legs, long tarsals/carpals lift the ankle high, so the "backwards knee" is really the ankle and the leg reads as having an extra segment. **Profile impact:** legs are 4-segment chains (thigh, shin, metatarsus, toes) with alternating bend directions (knee forward, ankle backward); 2-bone IK is not enough, use 3-bone IK or 2-bone + driven metatarsus.
- **Quadruped gallop (U. Minnesota veterinary anatomy, rotary gallop page).** Rotary gallop is four-beat with two suspension phases per stride (extended after hind push-off, gathered/collected after forelimbs). Carnivores flex the spine to bring the hind feet ahead of the fore-prints and extend it during hind push-off to reach further; horses rely less on spine motion. Cheetah modelling (PMC8099890 search excerpt; arXiv 2604.00329, preprint) links speed to the timing of spine extension after hind lift-off and flexion after fore lift-off. **Profile impact:** spine as a multi-bone chain with a "flex/extend" coupled rule tied to gait phase; per-species `spine_flex_range`.
- **Birds and flying creatures (Wikipedia, Bird flight).** Wing skeleton = humerus, radius/ulna, reduced hand (carpometacarpus, digits); alula on the first digit; primaries on the hand, secondaries on the ulna. Wings fold partly on the upstroke to save energy; small birds fold wings fully in bounding flight. Downstroke gives most thrust. **Profile impact:** wing as a 3-segment chain (shoulder, elbow, wrist) with a coupled fold rule (elbow and wrist flex together, as in real birds [GK]); feather fan as attachment bones; contacts for perching.
- **Insects and arachnids (Wikipedia, Arthropod leg).** Insect leg: coxa, trochanter, femur, tibia, tarsus (+ pretarsus claws); arachnid leg: 7 segments (adds patella and metatarsus). Each joint is a hinge bending in one plane, so many segments replace a ball joint. **Gaits (search results incl. Nature Comms, JEB, Frontiers in Zoology):** fast insects use the alternating tripod gait (three legs in stance, three in swing), medium speeds tetrapod, slow speeds wave/metachronal gaits (one leg swings at a time). **Profile impact:** many 1-DOF hinge joints with per-joint plane; gait schedules as phase offsets per leg (tripod = legs L1, R2, L3 in phase, others +0.5); support polygon must contain CoM at all times for slow gaits (statically stable).
- **Serpents (Wikipedia, Undulatory locomotion).** Modes: lateral undulation, sidewinding, concertina, rectilinear, slide-pushing; lateral undulation sends bending waves head-to-tail and pushes against surface irregularities. Only lateral undulation is described in detail on the page. **Profile impact:** long uniform chain, contacts = moving set of body segments; motion as a travelling wave `θ_i(t) = A sin(ωt − k i)`; validation: contact segments should not slide backwards relative to ground (they push).

### 2.12 Pose and motion validation in research

- **Foot skating.** NVIDIA Kimodo benchmark (read): `foot_skate_from_height` (mean toe velocity when toe height < 0.05 m), `foot_skate_max_vel`, `foot_skate_ratio` (fraction of ground-contact frames with toe speed > 0.2 m/s; contact = below 0.05 m on this and next frame), `foot_contact_consistency` (heuristic detector at 0.15 m/s and 0.10 m). Also constraint-following errors (end effector distance at constrained frames, keyframe joint error, root 2D error and its 95th percentile).
- **Floating and penetration** (search excerpts of HIPC, CleanMDM, PhyMotion preprints): clearance above floor for planted feet; penetration depth over violating frames (1 cm or 5 cm thresholds); contact labels taken from the reference motion so a clip cannot score well by dropping contact. A motion-generation survey notes there is no standard plausibility metric; thresholds vary per paper.
- **Physics-based plausibility.** PhysDiff (ICCV 2023) projects motion through a physics-simulated imitation to remove floating, foot sliding and penetration (abstract read; metric definitions not read).
- **Joint limit violation [GK].** Common practice: fraction of frames with any joint outside limits, and mean exceedance in degrees. Combine with conditional limits from 2.10.
- **Reuse.** Adopt Kimodo-style metric names and thresholds, scaled to character height (e.g. thresholds as fraction of leg length, since 2D characters have arbitrary units). These are definitions, not code, so no licence issue.

---

## (a) Recommended anatomy-profile schema outline

Units: lengths in "character units" with `unit_scale` to metres; angles in degrees; 2D plane = XY with +Y up, +X facing right in the rest pose (store `facing`). Fields marked *(from X)* show where the convention comes from.

```yaml
profile:
  id: human_adult_v1
  body_type: human | stylised_humanoid | heavy_humanoid | quadruped | flying | multi_limbed | serpent | custom
  extends: null                     # inherit from another profile, then override
  unit_scale: 0.01                  # metres per unit
  rest_pose: { kind: T|A|natural_2d, facing: +X }
  canonical_names: godot_humanoid   # alias tables: mixamo, vrm, bvh_cmu, unity  (from Godot/VRM/Mixamo)
  required_bones: [...]             # minimum set for this body type (from VRM/Unity required bones)

  bones:                            # ordered parent-first (from Spine)
    - name: LeftLowerLeg
      parent: LeftUpperLeg
      length: 42.0                  # also proportion: fraction of total height
      rest: { x, y, rotation }      # local, 2D (from Spine/DragonBones)
      inherit: normal | onlyTranslation | noRotation | noScale   # (from Spine)
      mass_frac: 0.0433             # (from de Leva)
      com_frac: 0.4395              # along bone from proximal
      rg_frac: 0.251                # radius of gyration
      collision: { shape: capsule, radius: 5.0 }   # 2D capsule per bone
      tags: [leg, left, deform]

  joints:                           # one per non-root bone
    - bone: LeftLowerLeg
      type: hinge | ball2d | slider | fixed | spline_segment   # 2D: hinge = 1 rot DOF
      dofs:
        - axis: flex                # semantic axis; +flex = "contracting" direction (from Godot)
          limit: { mode: limited, min: -1, max: 140 }          # (Free/Limited/Locked from Unreal FBIK; values from CDC ROM / OpenSim)
          soft_margin: 5            # warn inside this band
          conditional_limits:       # (idea from Akhter & Black)
            - when: { joint: LeftUpperLeg, dof: flex, range: [90, 140] }
              max: 150
      preferred_bend: positive      # (bendPositive from Spine/DragonBones; preferred angles from Unreal)
      stiffness: 0.0                # 0 free .. 1 locked (from Unreal FBIK)
      center: 0                     # (Unity HumanLimit.center)

  chains:                           # retarget/IK chains (from Unreal IK Retargeter)
    - { name: LeftLeg, start: LeftUpperLeg, end: LeftFoot, ik: two_bone|three_bone|fabrik, goal: LeftFootContact }
  retarget_root: Hips               # (Unreal pelvis / Godot scale_base_bone)
  scale_base_height: 95.0           # normalise root translation (Godot)

  contacts:                         # support points
    - { name: LeftHeel, bone: LeftFoot, offset: [-4, -2], radius: 1.5, type: point, friction: 0.8 }
    - { name: LeftBall, bone: LeftFoot, offset: [8, -2] }
    - { name: LeftToeTip, bone: LeftToes, offset: [3, 0] }
  foot_roll_order: [LeftHeel, LeftBall, LeftToeTip]

  attachments:                      # grips and props
    - { name: RightPowerGrip, bone: RightHand, offset: [6, 0], grip: power }
    - { name: RightPinch, bone: RightHand, offset: [9, 1], grip: precision }

  coupled_rules:                    # (OpenSim coupled coordinates, Unity/VRM roll constraints, Rigify bend axis)
    - { kind: phase_lag, a: LeftUpperLeg.flex, b: LeftLowerLeg.flex, lag: 0.1 }
    - { kind: gear, driver: Chest.twist, driven: Spine.twist, ratio: 0.5 }
    - { kind: gait_phase, legs: [L1, R2, L3], offset: 0.0 }   # tripod
    - { kind: wing_fold, driver: LeftWingElbow.flex, driven: LeftWingWrist.flex, ratio: 1.0 }

  reach:                            # derived, cached; recompute on override
    - { chain: LeftArm, max_reach: 64.0, min_reach: 12.0, workspace: annulus_2d }

  secondary:                        # spring chains (follow-through)
    - { chain: Tail, stiffness: 0.3, damping: 0.6 }

  validation:                       # thresholds scaled by leg length
    foot_skate_speed: 0.10          # leg-lengths per second
    contact_height: 0.03
    zmp_margin_min: 0.0
    limit_violation_frames_max: 0

  overrides: {}                     # per-character: lengths, mass_frac, limits, preferred_bend
```

Design notes:

- Keep **limits per semantic DOF** (flex, abduct, twist) instead of per raw axis. 2D needs mostly `flex`, but fake-3D turns (profile vs 3/4 view) need `twist` and `abduct` as visual proxies.
- Store retargetable motion as **normalised joint values** within each character's limits (Unity idea) plus **contact schedules** (Unreal post-retarget IK). Normalised values carry style across body types; contacts carry physics.
- Body types are **profile templates**. Stylised/heavy humanoids = human profile + overrides (shorter limbs, bigger mass in trunk, smaller ROM at hips for heavy). Quadruped/flying/multi-limbed/serpent = separate templates from §2.11.

## (b) Things we should NOT build ourselves

1. **Humanoid bone naming and hierarchy.** Use Godot SkeletonProfileHumanoid names (MIT) with VRM required/optional split, plus alias tables for Mixamo, Unity and CMU/BVH.
2. **Axis conventions.** Use Godot's "+Y along the bone, +X rotation = flexion" and Rigify's "rest bend defines bend direction" rules.
3. **Segment mass, CoM and radius-of-gyration fractions.** Use de Leva (1996) via the CC BY 4.0 BMClab tables, with citation.
4. **Human joint ranges.** Use CDC Joint ROM summary values and CC BY 3.0 OpenSim model coordinate ranges, with citation.
5. **Mocap interchange.** Use BVH (and ASF/AMC reading) rather than a new mocap format.
6. **Retargeting architecture.** Copy the Unreal pattern (chains, retarget root, retarget pose, post-retarget IK for contacts) and Godot's hip-height motion scaling instead of inventing one.
7. **Per-joint IK hints.** Use the Unreal FBIK triplet (stiffness, Free/Limited/Locked limits, preferred angles) and Spine/DragonBones `bendPositive`.
8. **2D bone transform vocabulary.** Use Spine/DragonBones local transform fields and inheritance modes; target DragonBones (MIT) or our own JSON for export.
9. **Motion QA metric definitions.** Use Kimodo-style foot-skating, contact and constraint metrics, scaled to character size.
10. **Grasp vocabulary.** Use Napier's power/precision (+ hook, lateral pinch) grip types.
11. **A biomechanical simulator.** Do not build muscle simulation; if needed for research, OpenSim (Apache 2.0) exists. For games, point-mass CoM/ZMP and momentum checks are enough.

What we **must** build (no existing 2D equivalent found): the unified profile schema itself, 2D creature templates (digitigrade, wing, hexapod, serpent), conditional/coupled rules engine, contact-schedule-aware 2D IK, and the 2D QA metrics (CoM/ZMP margin, airborne ballistic and angular-momentum checks, sequencing checks).

## (c) Source list

| # | URL | Licence (as seen) | Read |
|---|---|---|---|
| 1 | https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53090607/Musculoskeletal%20Models | Models: gait2392/2354 CC BY 3.0 | Partial (truncated after 3 models) |
| 2 | https://github.com/opensim-org/opensim-core/blob/main/LICENSE.txt | Apache 2.0 | OK |
| 3 | https://simtk.org/projects/full_body | "MIT Use Agreement" (terms not shown) | OK (terms not visible) |
| 4 | https://opensimconfluence.atlassian.net/wiki/x/GnoqAw | n/a | Failed (empty) |
| 5 | https://docs.unity3d.com/Manual/MuscleDefinitions.html → docs.unity.com muscle-definitions | Unity docs, proprietary | OK (via redirect) |
| 6 | https://docs.unity.com/en-us/engine/current/script-reference/unityengine/humanlimit | Unity docs | OK |
| 7 | https://docs.unity.com/en-us/engine/current/script-reference/unityengine/humantrait | Unity docs | OK |
| 8 | https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-retargeting-in-unreal-engine | Epic docs | Failed (no content) |
| 9 | https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-in-unreal-engine | Epic docs | OK |
| 10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/control-rig-full-body-ik-in-unreal-engine | Epic docs | OK |
| 11 | https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine | Epic docs | OK |
| 12 | https://docs.godotengine.org/en/stable/classes/class_skeletonprofilehumanoid.html | Godot docs (CC BY 3.0 [GK]); engine MIT | OK |
| 13 | https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/retargeting_3d_skeletons.html | as above | OK (stable/ and animation/ paths 404) |
| 14 | https://godotengine.org/license/ | MIT | OK |
| 15 | https://docs.blender.org/manual/en/3.0/addons/rigging/rigify/bone_positioning.html | Blender manual (CC BY-SA [GK]) | OK |
| 16 | https://docs.blender.org/manual/en/latest/addons/rigging/rigify/metarigs.html, /index.html, 4.1 metarigs, 5.0 basics | n/a | Failed (404 or navigation only) |
| 17 | https://esotericsoftware.com/spine-json-format | © Esoteric Software | OK |
| 18 | https://esotericsoftware.com/spine-runtimes-license | Spine Runtimes License (each user needs Editor licence) | OK |
| 19 | https://github.com/DragonBones/DragonBonesJS | MIT | OK |
| 20 | https://h1ve2.github.io/pixi-dragonbones-runtime/guide/dataformat ; dragonbones-tools 5.5 doc | n/a | Search excerpt only |
| 21 | https://research.cs.wisc.edu/graphics/Courses/cs-838-1999/Jeff/BVH.html | course page | OK |
| 22 | https://research.cs.wisc.edu/graphics/Courses/cs-838-1999/Jeff/ASF-AMC.html | course page | OK |
| 23 | http://mocap.cs.cmu.edu/faqs.php and https://mocap.cs.cmu.edu/resources.php | "free for all uses", no direct resale (search excerpt) | Failed (TLS certificate) |
| 24 | https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md | No licence shown | OK |
| 25 | https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/tpose.md | No licence shown | OK |
| 26 | https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_node_constraint-1.0/README.md | No licence shown | OK |
| 27 | https://github.com/vrm-c/vrm-specification (and /README.md; /LICENSE 404) | Not found | OK (no licence file) |
| 28 | https://github.com/vrm-c/UniVRM | MIT | OK |
| 29 | https://vrm.dev/en/licenses/ | n/a | Failed (404) |
| 30 | https://smpl.is.tue.mpg.de/modellicense.html | Non-commercial only | OK |
| 31 | https://poseprior.is.tue.mpg.de/ and /license.html | Non-commercial only | OK |
| 32 | https://helpx.adobe.com/au/creative-cloud/faq/mixamo-faq.html | Royalty-free incl. commercial (search excerpt) | Failed (403) |
| 33 | Mixamo naming: help.wonderdynamics.com/?p=589, cascadeur.com/help/using_mixamo_rig_in_cascadeur | n/a | Search excerpts only |
| 34 | https://raw.githubusercontent.com/BMClab/BMC/master/data/BSPmale_ZdeLeva.txt | CC BY 4.0 (content) | OK |
| 35 | https://raw.githubusercontent.com/BMClab/BMC/master/data/BSPfemale_ZdeLeva.txt | CC BY 4.0 | OK |
| 36 | https://raw.githubusercontent.com/BMClab/BMC/master/data/BSP_DempsterWinter.txt | CC BY 4.0 | OK |
| 37 | https://github.com/BMClab/BMC | CC BY 4.0 content, MIT code | OK |
| 38 | https://nbviewer.org/github/BMClab/BMC/blob/master/notebooks/BodySegmentParameters.ipynb | n/a | Failed (429) |
| 39 | https://exrx.net/Kinesiology/Segments | n/a | Failed (403) |
| 40 | https://wiki.has-motion.com/Adjusted_Zatsiorsky-Seluyanov%27s_segment_inertia_parameters | n/a | Failed (403) |
| 41 | https://bionumbers.hms.harvard.edu/bionumber.aspx?id=109721 | n/a | OK (no values on page) |
| 42 | https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html | Public-use, statistical analysis only | OK |
| 43 | https://pmc.ncbi.nlm.nih.gov/articles/PMC2817299 (Collins et al. 2009) | © Royal Society | OK |
| 44 | https://pmc.ncbi.nlm.nih.gov/articles/PMC7174497 (Ellenbecker & Aoki 2020) | © Springer | OK |
| 45 | https://en.wikipedia.org/wiki/Zero_moment_point | CC BY-SA | OK |
| 46 | https://pmc.ncbi.nlm.nih.gov/articles/PMC1312228 (grasp history, Napier) | © Baylor | OK |
| 47 | https://en.wikipedia.org/wiki/Ground_reaction_force | CC BY-SA | OK (general only) |
| 48 | https://pubmed.ncbi.nlm.nih.gov/2782094/ (Nilsson & Thorstensson 1989) | n/a | Failed (cookie wall); values from search excerpt |
| 49 | https://www.acs.psu.edu/drussell/bats/bat-moi.html | © D. Russell | OK |
| 50 | Cross & Bower 2006 (people.stfx.ca PDF) | n/a | Search excerpt only |
| 51 | https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation | CC BY-SA | OK |
| 52 | https://en.wikipedia.org/wiki/Digitigrade | CC BY-SA | OK |
| 53 | https://en.wikipedia.org/wiki/Arthropod_leg | CC BY-SA | OK |
| 54 | https://en.wikipedia.org/wiki/Insect_locomotion | n/a | Failed (404); gaits from search excerpts (Nature Comms ncomms14494, JEB, Frontiers in Zoology) |
| 55 | https://en.wikipedia.org/wiki/Bird_flight | CC BY-SA | OK (first 100k chars) |
| 56 | https://en.wikipedia.org/wiki/Gallop | CC BY-SA | OK (lacks spine detail) |
| 57 | https://vanat.ahc.umn.edu/gaits/rotGallop.html | No licence shown | OK |
| 58 | https://en.wikipedia.org/wiki/Undulatory_locomotion | CC BY-SA | OK |
| 59 | https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html | © NVIDIA | OK |
| 60 | https://arxiv.org/abs/2307.10894 (motion generation survey) | arXiv non-exclusive | OK (abstract only) |
| 61 | https://arxiv.org/abs/2212.02500 (PhysDiff) | arXiv | OK (abstract only) |

Not read at all (stated from general knowledge, marked [GK] above): Unreal Engine EULA, Blender/Rigify GPL status, Spine physics constraints, VRM spring bones, Kajita cart-table ZMP formula, parallel-axis theorem, friction coefficients.
