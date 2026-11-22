# Universal Motion & Animation Knowledge System — research notes

> **Status:** `PROPOSED` (Universal motion: comparative anatomy, locomotion, physical motion, components, technology evaluation). Compiled 2026-11-22 by a Claude Code research agent for the Board in the studio's own words, with sources and read status; claims not confirmed on a page are tagged. Content review by `director` pending (K4).


Date: 2026-11-22. Scope: knowledge an AI agent needs to animate any 2D game entity by code, organised as an
**Entity Motion Profile** composed of reusable **motion components**. Target: Godot 4.6, one Windows PC
(RTX 3060 12 GB, 16 GB RAM), agents that have **no web access** at run time (so everything they need must be
written down locally: formulas, parameter tables, validation checks).

Method: pages were read with WebFetch / WebSearch on 2026-11-22. Nothing was downloaded or installed, no accounts
were created. Where a fact comes from my own background knowledge rather than a page read today, it is marked
**[background]**. Where a page could not be read, it is marked **[not verified]**.

Important version note: the Godot "stable" docs read today are **4.7**; several pages carry a "may be outdated for
4.7" banner. The studio targets 4.6. Class names below exist in both, but anything marked experimental may differ.

---

## 0. Verification of the Board starting points

| # | Source | What it actually is | Licence / status | Hardware | Automation | Fit for us |
|---|---|---|---|---|---|---|
| 1 | Goldfinger, *Animal Anatomy for Artists: The Elements of Form* (OUP; print 2004, Oxford Scholarship Online edition 2020) | Artist's atlas: skeleton + superficial muscle side views of horse, dog, cat, cow, pig, squirrel, rabbit, lion, giraffe, deer, hippo, rhino, elephant, gorilla, sea lion, bear; a birds chapter (skeleton, muscles, feather tracts); limb-variation chapter | Copyrighted; paywalled (institution / purchase; PDF subscribers only) | None (a book) | None — humans read it; we may write **our own** proportion notes from it, never copy plates | Good human reference for limb segment ratios and joint placement; cannot be fed to agents verbatim |
| 2 | Muybridge, *Animal Locomotion* (1887), UPenn Archives collection UPT 50 M993 | 781 collotype plates of people and animals (horses, dogs, cats, zoo animals) in sequential photos; the UPenn page is a finding aid for the physical archive | UPenn page gives **no** reuse terms. Other holders: Library of Congress files on Wikimedia Commons are tagged public domain in the US (published before 1929, "no known restrictions"); Smithsonian marks a plate public domain; Wellcome uses the Public Domain Mark; Brooklyn Museum is more cautious ("may be" PD). Plates carry an 1887 "All rights reserved" legend, which has long expired in the US. Non-US reuse of museum *reproductions* can differ | None | Frame sequences can be traced/measured by hand or with a pose model | **Best free animal gait reference.** Use LoC / Smithsonian / Wellcome copies, record the source record per plate |
| 3 | DeepLabCut (Mathis lab) | Markerless pose estimation from video; "SuperAnimal" pretrained models: Quadruped (39 keypoints, side view), TopViewMouse (27), Human (17) | Code **LGPL-3.0**. SuperAnimal weights: "Modified MIT", **academic / non-commercial only**, commercial use needs a separate EPFL licence. Logo/images copyrighted | Python 3.10–3.12, PyTorch; NVIDIA GPU, ≥8 GB VRAM "ideal" → RTX 3060 fits. Windows supported (TensorFlow GPU on Windows needs WSL; PyTorch path fine) | Fully scriptable (headless pip install, Python API) | Code usable; **SuperAnimal weights not usable for a commercial game pipeline**. Would require training our own model on our own labels. Overkill for 2D sprite work; only worth it for measuring reference video |
| 4 | Kirin (Zhao, Pan, Rehg, Wu, Wu — ECCV 2026) | Diffusion model generating **3D quadruped** motion from text + image; trained on AiM3D (23 species, 876 GB) reconstructed from internet video; auto-rigs a mesh from an image-to-3D model | Code **MIT** (per repo). Dataset licence **not stated**; it is derived from internet video (unclear provenance). Depends on gated Hugging Face weights (SAM3, DINOv3 — need `hf auth login`), an AniMer checkpoint from Google Drive, and a **Rodin API key** (third-party paid service) | VRAM not stated; PyTorch3D built from source with CUDA 12.4 | Scriptable, but needs accounts and API keys | **Reject for now**: violates our no-account rule, dataset rights unclear, output is 3D joints that would need 2D projection. Track as research only |
| 5 | Abdul Karim et al., *Procedural Locomotion of Multi-Legged Characters in Dynamic Environments* (Computer Animation and Virtual Worlds, Wiley; 2012/2013) | Fully procedural, no motion data: character controller → gait/tempo manager → footprint planner → foot & pelvis trajectory builder; level-of-detail for dozens of creatures; arachnids, insects, n-legged robots | Paper; **no code** listed | n/a | Algorithm description only | **Directly the architecture we want** for the multi-legged gait component (we re-implement the idea, in 2D) |
| 6 | Raibert & Hodgins, *Animation of Dynamic Legged Locomotion*, SIGGRAPH 1991 | Physics controllers (speed, leg sequencing, balance) for biped, quadruped robot and kangaroo; run, trot, bound, gallop, hop | Paper; no code | n/a | Concepts only; authors say controllers were hand-tuned per creature | Background for "hop / bound" and spring-leg body bounce; full physics control is **not** something we should build |
| 7 | Blender physics manual | Rigid body, cloth, soft body, fluid, particles, dynamic paint, collision, explode, ocean | Blender is GPL **[background]**: output you create is yours | Runs fine on the stated PC | Scriptable with `bpy`, can run headless (`blender -b`) **[background — the manual page read did not confirm headless baking]** | Useful **offline** for baking cloth/fluid/smoke flipbooks to sprites; not a runtime |
| 8 | Godot physics introduction (4.7 docs) | Area2D, StaticBody2D, RigidBody2D, CharacterBody2D; 32 collision layers; fixed 60 Hz physics tick by default | Godot is MIT **[background]** | Trivial | Fully scriptable | Runtime base for anything physical |
| 9 | Godot 2D particle systems (4.7 docs, banner: not yet updated) | GPUParticles2D (recommended) vs CPUParticles2D (near parity, no trails, no new features); lifetime, one-shot, preprocess, explosiveness, randomness, fixed FPS; flipbook via CanvasItemMaterial Particle Animation | MIT | GPU particles fine on 3060 | Scriptable; ParticleProcessMaterial is a Resource → agents can write `.tres` | Runtime for fire/smoke/energy/magic |

---

## 1. Knowledge domains

Each domain: key concepts → simplified 2D model a tool can compute → validation signals → sources.

### 1.1 Comparative anatomy (limbs, wings, segments)

**Key concepts**
- **Foot posture.** Plantigrade (whole sole down: humans, bears), digitigrade (on the toes: dogs, cats, birds),
  unguligrade (on hoof tips: horses, cattle). In digitigrade and unguligrade animals the metacarpals/metatarsals are
  long, so the joint that looks like a "backwards knee" is the **ankle (hock)**; the true knee sits high, near the belly.
- **Mammal limb chain (side view).** Hind: hip → femur → knee → tibia → ankle/hock → metatarsus → toes. Fore:
  shoulder blade (slides on the ribcage; no collarbone in many quadrupeds **[background]**) → humerus → elbow → radius/ulna
  → wrist → metacarpus → toes. Fore elbow points back, hind knee points forward, hock points back.
- **Bird wing.** Humerus, radius + ulna, reduced 3-digit hand carrying the primaries; secondaries on the ulna;
  the alula (first digit) helps at low speed. Bird hind limb is digitigrade; the visible "knee" is the ankle.
- **Bat wing.** A forelimb with hugely elongated finger bones; membrane (patagium) in sections: between fingers
  (dactylopatagium), finger-to-body (plagiopatagium), between legs/tail (uropatagium). Membrane is elastic, so the
  wing is a deformable surface spanning a skeleton, not a stack of feathers.
- **Arthropod legs.** Insect: coxa, trochanter, femur, tibia, tarsus (sub-segments) + pretarsus claws — 5 main
  segments. Spider: 7 segments (adds patella and metatarsus). For 2D animation, 3 visible segments (coxa+femur,
  tibia, tarsus) are usually enough **[background]**.

**Simplified 2D model**
- A limb = ordered list of segments `{length, rest_angle, min_angle, max_angle, bend_sign}`. `bend_sign` encodes
  which way the joint folds (fore elbow +1, hind knee −1, hock +1...). Foot posture is just which segment touches
  ground and its rest angle.
- Proportions as ratios of leg length so one table drives many species, e.g. `{femur: .30, tibia: .32, metatarsus: .25,
  toes: .13}`. Values must be written by us from reference observation; no copied plates.

**Validation signals**: bone lengths constant across frames (tolerance < 0.5 px); joint angles inside limits; each
joint bends only in its declared direction (sign of cross product of adjacent segments never flips); foot posture
segment is the one in ground contact during stance.

**Sources**: Wikipedia *Digitigrade*; *Bird flight*; *Bat flight*; *Arthropod leg*; Goldfinger (human reference, paid).

### 1.2 Terrestrial gaits (bipeds, quadrupeds, hexapods, octopods)

**Key concepts**
- **Stance / swing.** Each foot alternates between ground contact (stance) and air (swing). Hildebrand's gait
  diagrams describe a gait by when each foot's stance begins and ends relative to a reference foot (usually left hind).
- **Duty factor β** = fraction of the cycle a foot is on the ground. β > 0.5 → walk; β < 0.5 → run. Usually equal
  for fore and hind except when accelerating.
- **Phase offset φᵢ** of each foot relative to the reference foot (0–1 of a cycle).
- **Symmetric gaits** (left/right of a pair half a cycle apart): walk, trot, pace, amble. **Asymmetric** (pairs move
  together, suspended phase, needs a flexible spine): canter, gallop, bound, half-bound.
- **Horse reference speeds**: walk 4-beat ~7 km/h; trot 2-beat diagonal pairs ~13 km/h; canter 3-beat with a
  leading leg 16–27 km/h; gallop 4-beat with a suspension phase 40–48 km/h; pace = 2-beat same-side pairs.
- **Walking is a vaulting inverted pendulum** (body highest at mid-stance); **running is a spring-mass bounce**
  (body lowest at mid-stance). Energy fluctuations are out of phase in walking, in phase in running.
- **Dynamic similarity**: Froude number `Fr = v² / (g · L_leg)`; animals of different size move alike at equal Fr.
  Walk→run transition is widely cited near Fr ≈ 0.5 **[background]**.
- **Hexapods**: alternating **tripod** (L1, R2, L3 vs R1, L2, R3) at speed; tetrapod coordination (4 down, diagonal
  pairs swing) at medium speed; **metachronal wave** (one leg at a time, back to front) when slow.
- **Spiders**: **alternating tetrapod** — sets {L1, R2, L3, R4} and {R1, L2, R3, L4}; the eight-legged analogue of
  the tripod. Speed rises with both stride frequency and stride length. Coordination is looser than in insects.
- **Procedural multi-leg pipeline** (Abdul Karim et al.): controller → gait/tempo → footprint planner → foot and
  pelvis trajectories; no motion data needed.

**Simplified 2D model (gait scheduler)**
```
cycle phase  p(t) = frac(t * f)                      # f = stride frequency (Hz)
foot i       pᵢ   = frac(p + φᵢ)
stance       if pᵢ < β: foot locked at its world plant point
swing        s = (pᵢ - β) / (1 - β); foot moves from lift point to next plant point
             x = lerp(lift, plant, ease(s)); y = ground - h_step * sin(π s)
plant point  = hip_world_x_at_touchdown + stride_len/2 (+ terrain raycast)
stride_len   = v / f
body height  walk: y_body = base + a·cos(2π·pᵢ_mid)  (high at mid-stance)
             run:  low at mid-stance, airborne when no foot in stance
leg pose     2-bone analytic IK (law of cosines) or FABRIK for 3+ segments, bend_sign fixed per joint
```
Starting phase tables (φ relative to LH; **approximate starting values for tuning, not measurements**):

| Gait | LH | LF | RH | RF | β |
|---|---|---|---|---|---|
| Walk (lateral sequence) | 0 | 0.25 | 0.5 | 0.75 | 0.6–0.75 |
| Trot | 0 | 0.5 | 0.5 | 0 | 0.35–0.5 |
| Pace | 0 | 0 | 0.5 | 0.5 | 0.35–0.5 |
| Canter (right lead) | 0 | 0.3 | 0.3 | 0.6 | ~0.4 |
| Transverse gallop | 0 | 0.5 | 0.1 | 0.6 | 0.2–0.35 |
| Bound | 0 | 0.5 | 0 | 0.5 | ~0.3 |

| Gait | Leg groups (same phase) | β |
|---|---|---|
| Insect tripod | {L1,R2,L3}=0, {R1,L2,R3}=0.5 | 0.5–0.6 |
| Insect metachronal | L3=0, L2=1/6, L1=2/6, R3=.5, R2=4/6, R1=5/6 | ~0.8 |
| Spider tetrapod | {L1,R2,L3,R4}=0, {R1,L2,R3,L4}=0.5 | 0.5–0.65 |

Gait selection: pick gait from Fr (or speed / leg length) with hysteresis so the creature does not flicker between gaits.

**Validation signals**
- **Foot slip**: world-space speed of a stance foot ≈ 0 (e.g. < 0.5 px/frame).
- **Ground penetration**: no foot below the ground line; swing clearance > 0.
- **Measured β and φ** from the rendered frames match the profile within ±0.05.
- **Static stability (walk)**: at least 3 feet down for a quadruped walk, at least 3 for hexapod tripod.
- **Seamless loop**: pose(0) == pose(1 cycle) within tolerance.
- **Speed coherence**: stride_len × f equals body velocity (otherwise feet skate).

**Sources**: Wikipedia *Gait*, *Horse gait*; Alexander 1984 (IJRR) and Alexander & Jayes 1983 via secondary
sources (Froude); spider gait literature (J. Exp. Biol. limb-loss study, doi 10.1242/jeb.174268); Abdul Karim et al.;
Raibert & Hodgins 1991; Muybridge plates for visual checks.

### 1.3 Flight

**Key concepts**
- Downstroke makes most lift and thrust; on the upstroke the wing partly **folds** (shorter span) to cut cost.
- Angle of attack changes continuously through the stroke.
- Gliding: no flapping, slow sink or rising air (soaring in thermals).
- True hovering (hummingbirds) uses a near-horizontal figure-8 stroke with lift on both strokes; kestrels "hover"
  by flying into a headwind.
- Wingbeat frequency falls with size: hummingbirds ~40–80 Hz; large birds a few Hz **[background for large birds]**.
- Takeoff: small birds jump; large birds run, face the wind or drop. Landing: aim low, flare up at the end.
- **Strouhal number** `St = f · A / U` (frequency × stroke amplitude / forward speed): cruising fliers and swimmers
  sit roughly in **0.2–0.4** (Taylor, Nudds & Thomas, Nature 2003; later work debates the reason, not the range).
- Bat wings: skeleton plus elastic membrane; membrane billows and the wing folds strongly on the upstroke.
- Insects: very high frequency → in 2D, typically drawn as a blurred wing or a 2–4 frame flicker **[background]**.

**Simplified 2D model**
```
θ_shoulder(t) = θ_mid + A·shape(p)          # p = frac(t·f)
shape(p): downstroke for p < d (d ≈ 0.55–0.6, slower, power), upstroke after (faster)
fold(p)   = span scale: 1.0 on downstroke, 0.6–0.8 at mid-upstroke (elbow/wrist flex)
body bob  = −k · lift(p)   # body rises on downstroke, sinks on upstroke, slight lag
choose f, A from desired speed so that f·A/U ∈ [0.2, 0.4]
glide: θ fixed, small slow oscillation; tail/feathers jiggle via spring
```

**Validation signals**: St in band at cruise; wingtip path closed loop; span on upstroke < span on downstroke;
body bob phase opposite to wing; no self-intersection of wing over body in silhouette.

**Sources**: Wikipedia *Bird flight*, *Bat flight*; Taylor/Nudds/Thomas 2003 (via Oxford abstracts).

### 1.4 Swimming

**Key concepts (body–caudal fin modes)**
- **Anguilliform** (eels): wave of roughly constant amplitude along a slender body.
- **Subcarangiform** (trout): amplitude grows toward the rear half.
- **Carangiform**: motion concentrated in rear body and tail; stiffer, faster.
- **Thunniform** (tuna, lamnid sharks): almost only the tail and peduncle move; crescent tail.
- **Ostraciiform**: rigid body, only the tail fin oscillates.
- **Median/paired fin modes**: rajiform (rays undulate large pectoral fins), labriform (wrasses row/flap pectorals).
- Strouhal band 0.2–0.4 applies to cruising swimmers too.

**Simplified 2D model (travelling wave)**
```
lateral offset y(x, t) = A(x) · sin(2π (x/λ − f t))     # x = 0 head … L tail, wave travels head→tail
A(x) by mode:  anguilliform A = a0 + a1·x/L (a0 not small)
               subcarangiform A = a·(x/L)^1.5
               carangiform A = a·(x/L)^2
               thunniform A ≈ 0 for x < 0.7L, then grows
               ostraciiform A = 0 except tail fin rotation
wave speed c = λ f; body speed U < c (wave must outrun the body for thrust) [background]
```
In side-view 2D games fish are often top-view or side-view; in side view the "lateral" wave becomes a rotation of
tail segments, so the same chain component is driven with angles instead of offsets.

**Validation**: A(x) monotonic for the chosen mode; tail amplitude/length ratio within taste range (~0.1–0.2 L
**[background]**); St in band; head yaw small for thunniform, larger for anguilliform.

**Sources**: Wikipedia *Fish locomotion*, *Undulatory locomotion*; Taylor et al. 2003.

### 1.5 Undulatory / serpentine locomotion (snakes, worms, eels on land, dragons' bodies)

**Key concepts**
- Classical four modes: **lateral undulation** (S-waves pushing on contact points), **concertina** (alternating
  anchored bunched region and sliding extension; head-to-tail length changes), **sidewinding** (body lifted in
  sections, static ground contacts, moves diagonally), **rectilinear** (straight body, skin moves relative to
  skeleton — no bending). Jayne (2020) argues the four-mode scheme is too coarse; rectilinear and sidewinding are
  distinct modes, lateral undulation and concertina are families.
- Sidewinding has a standard model (Burdick, Radford, Chirikjian) with static contact segments.

**Simplified 2D model**
- **Lateral undulation (top view)**: "follow the leader" — the head follows a sinusoidal or steered path; each
  segment is placed at fixed arc-length behind along the head's recorded path. No foot-slip-like sliding sideways.
- **Concertina**: state machine per section: ANCHOR (bunched, fixed) / EXTEND (front moves forward) / PULL (rear
  bunches up to front anchor).
- **Sidewinding (top view)**: two waves, horizontal and vertical, π/2 out of phase; segments with vertical lift > 0
  are drawn raised (shadow offset) and do not touch the ground.
- **Rectilinear**: body straight, belly-texture scroll or small segment-length pulses (shader or scale ripple).

**Validation**: segment spacing constant (inextensible except concertina); body follows head path within tolerance
(lateral undulation); ground-contact segments have ~zero world velocity (sidewinding/concertina anchors).

**Sources**: Wikipedia *Undulatory locomotion*, *Rectilinear locomotion*; Jayne 2020 (PMC7391877) via search summary;
Tingle, Garner & Astley 2024 review (search summary only).

### 1.6 Soft bodies / slimes

**Key concepts**: squash and stretch is the most important of Disney's 12 principles (Thomas & Johnston); a non-rigid
body changes shape but **keeps its volume**; the bouncing ball is the canonical exercise. Related principles:
anticipation, follow-through / overlapping action **[the rest of the 12 from background]**.

**Simplified 2D models**
1. **Scale-only (cheapest)**: `sy = 1 + s`, `sx = 1 / sy` (area preserved). Drive `s` with a spring on vertical
   velocity / impact: stretch along velocity, squash on contact. Rotate the squash axis to the velocity direction.
2. **Pressure ring soft body**: N points on a ring, edge springs + **area constraint** (target area A₀; push
   points along normals by `k·(A₀ − A)`), gravity, ground collision. Render as Polygon2D with UV, or shader.
3. **Shader wobble**: vertex displacement `offset = n · amp · sin(ωt + angle·k)` on a subdivided mesh.

**Validation**: area ratio A/A₀ ∈ [0.95, 1.05] for model 2; `sx·sy ≈ 1` for model 1; no self-intersecting polygon;
ground penetration < 1 px; settles (kinetic energy → 0) within N seconds when idle.

**Sources**: Wikipedia *Squash and stretch*; Ten Minute Physics tutorials 10/12 (soft bodies); PBD/XPBD (see 1.7).

### 1.7 Cloth, rope and chain dynamics for games

**Key concepts**
- **Verlet integration + constraint relaxation** (Jakobsen, *Advanced Character Physics*, GDC 2001, used in
  Hitman: Codename 47): particles store current and previous position (velocity implicit), then distance constraints
  are enforced by repeatedly moving endpoints. Good for non-rigid and articulated bodies; cloth, ropes, ragdolls.
- **Position Based Dynamics (PBD)** (Müller et al. 2007) and **XPBD** (extended PBD with compliance, making
  stiffness independent of iteration count) — the modern standard for game cloth/rope/soft body
  **[background — the PBD PDF could not be parsed; Ten Minute Physics pages confirm PBD for ropes/hair, XPBD for joints]**.

**Simplified 2D model (rope / chain / cloth)**
```
for each particle: x_new = x + (x - x_prev)·damping + g·dt²; x_prev = x; x = x_new
repeat K iterations (4–20):
   for each link (i,j,L): d = x_j - x_i; diff = (|d| - L)/|d|; move i,j by ±0.5·diff·d (weighted by inverse mass)
   pin constraints (anchors), collision projection (push out of shapes)
rope  = 1D chain of particles, render Line2D through points (width_curve for taper)
chain = same, render one sprite per link oriented along d (alternate 90° for side view look)
cloth = 2D grid; structural (neighbours), shear (diagonals), bend (skip-one) constraints; render Polygon2D/mesh UV
```

**Validation**: max link stretch error < 1–2 % after solve; no NaN; anchors exact; total energy does not grow
over 10 s at rest (stability); frame-rate independence (fixed physics step).

**Sources**: Jakobsen 2001 (via search; original PDF at edelkas.github.io not read); Ten Minute Physics index;
myPhysicsLab (chain, springs); GDNative-Ropesim README.

### 1.8 Springs and pendulums (secondary motion)

**Key concepts / models**
- Damped spring (1D or 2D): `a = −k (x − x_target) − c v`. Better artist parametrisation: natural frequency `f`
  (Hz) and damping ratio `ζ` → `k = (2πf)²`, `c = 2ζ·2πf` (unit mass). ζ < 1 overshoot (jiggle), ζ = 1 critical,
  ζ > 1 sluggish **[background]**. Integrate with semi-implicit Euler at fixed step.
- Pendulum: `θ'' = −(g/L) sin θ − c θ'`; small-angle period `T = 2π √(L/g)` **[background]**. Driven pendulum
  (pivot accelerates) adds `−(a_pivot_x cos θ + a_pivot_y sin θ)/L`.
- Godot built-ins: DampedSpringJoint2D (`length` max, `rest_length`, `stiffness` default 20, `damping` 0–1);
  PinJoint2D (`softness`, angular limits, motor with target velocity rad/s); SkeletonModification2DJiggle
  (stiffness 3.0, mass 0.75, damping 0.75, optional gravity; **experimental**); Spine physics constraints
  (inertia, strength, damping, mass, wind, gravity, mix on translate/rotate/scale/shear channels).

**Validation**: oscillation frequency measured by zero-crossings within ±10 % of target f; overshoot matches ζ;
energy decays (never grows); pendulum period matches `2π√(L/g)` within 5 % for small swings.

**Sources**: Godot class refs (DampedSpringJoint2D, PinJoint2D, SkeletonModification2DJiggle); Spine physics
constraints page; myPhysicsLab (pendulum and spring sims, Apache-2.0).

### 1.9 Projectile (ballistic) motion

**Model**: `p(t) = p₀ + v₀ t + ½ g t²`; apex time `v₀y/g`; flat-ground range `v₀² sin 2α / g`; to hit a target in
time T: `v₀ = (p_target − p₀ − ½ g T²)/T`. Optional linear drag `a = g − k v`. Sprite rotation = atan2(v). Squash on
landing (1.6). Telegraph: draw the predicted arc **[background — standard kinematics]**.

**Validation**: analytic vs simulated position error < 1 px at landing; rotation tangent to path; lands at target.

### 1.10 Mechanical linkages (gears, pistons, four-bar)

**Key concepts**
- **Four-bar**: ground, input (crank), coupler, output (rocker). **Grashof**: with S shortest, L longest, P, Q others,
  the shortest link can fully rotate iff `S + L ≤ P + Q`. Types: crank-rocker, double-crank, double-rocker,
  parallelogram, antiparallelogram.
- **Slider-crank** (piston): three revolute joints + one sliding joint; offset version gives quick-return.
- Gears **[background]**: meshing gears `ω₂ = −ω₁ · N₁/N₂` (teeth counts); rack and pinion `v = ω r`.

**Simplified 2D model**
```
four-bar: A = ground pivot 1, D = ground pivot 2; B = A + r_crank·(cos θ, sin θ)
          C = intersection of circle(B, r_coupler) and circle(D, r_rocker); choose branch consistently
slider-crank: x = r cos θ + sqrt(l² − (r sin θ − e)²)        # e = offset
gears: rotation_i = rotation_driver · (−N_driver/N_i)^(depth parity)
```
**Validation**: Grashof check before animating (if crank must rotate); circle intersection exists for all θ in the
loop (no "lock-up"); link lengths constant; branch never flips mid-cycle; gear teeth phase aligned (no visual
interpenetration at mesh point).

**Sources**: Wikipedia *Four-bar linkage*; myPhysicsLab (pendulum clock, car suspension).

### 1.11 Particles: fire, smoke, energy

**Godot capabilities (read today)**: GPUParticles2D + ParticleProcessMaterial: turbulence (noise), collision
(rigid / hide on contact; 2D collides only with **LightOccluder2D**), sub-emitters (at interval, start, end, on
collision), emission shapes (point, sphere, box, ring, points from texture), directional/radial/orbital velocity
curves, velocity limit, scale/colour/alpha curves; trails (mesh-skinned; GPU only); `emit_particle()` from code
(not in the Compatibility renderer); `amount_ratio` for live intensity; flipbook frames via CanvasItemMaterial.

**Recipes (simplified)** **[background, to tune]**
- **Fire**: emitter at base, upward initial velocity, negative gravity (buoyancy), turbulence, short life (0.4–1 s),
  scale curve grow-then-shrink, colour ramp white-yellow → orange → red → transparent, additive blend; spawn a
  smoke sub-emitter at end.
- **Smoke**: slower, longer life (2–4 s), scale grows ×2–4, alpha fades, normal blend, slight drift (wind).
- **Energy / magic**: orbit velocity around the caster, radial velocity inward (charge) or outward (release),
  bright saturated core + soft halo, trails for streaks.
- **Sparks / impacts**: explosiveness ≈ 1, one-shot, high initial velocity, gravity on, trails, collide with
  LightOccluder2D.

**Validation**: particle budget (count × lifetime) under a cap per effect; effect finishes (one-shot `finished`
signal); colour ramp ends at alpha 0 (no popping); readable at gameplay zoom (render a thumbnail, check silhouette).

**Sources**: Godot docs: 2D particle systems, GPUParticles2D, ParticleProcessMaterial.

### 1.12 Magical / non-physical motion design

**Principles**
- **Hierarchy**: attention an effect grabs should match its gameplay importance (Riot, *Clarity in League*).
- **Telegraphs**: dangerous / crowd-control attacks need a wind-up (visual + audio) before the hit; do not imply
  more dodge time than exists.
- **Consistency**: fixed shape language per meaning (e.g. circle = area, line = beam, chevron = direction) kept
  across skins/variants; hitboxes match visuals; projectiles show travel direction (stretched tail).
- **Internal physics consistency** **[background]**: invented motion still obeys *its own* rules — choose a
  "material" per element (fire rises, ice shatters and falls, void pulls inward, holy radiates) and keep it.
- **Timing grammar**: anticipation → action → recovery (the same wind-up / freeze / recover structure PixelFX uses).

**Simplified model**: telegraph component = `{windup_s, active_s, recovery_s, shape, color_role, audio_cue}`; magic
motion = particles (1.11) + shader (dissolve, glow, distortion) + oscillators (hover, orbit).

**Validation**: windup ≥ studio minimum (reaction-time based; typical human visual reaction ~0.2–0.25 s
**[background]**); hitbox outline overlaps telegraph shape ≥ 90 %; colour role from a fixed palette table; thumbnail
readability test at 1× and 0.5×.

**Sources**: League of Legends *Clarity in League*; LoL VFX style guide (found, not read); Game Developer articles on
telegraphing (found, not read).

### 1.13 Environmental objects (foliage, water surfaces, doors, platforms)

**Models** **[background]**: foliage sway = vertex shader `offset.x = A · h(uv.y) · sin(ωt + phase(world_x))` with
`h` = height weight; water surface = 1D column springs (each column a damped spring + neighbour spreading) drawn as
Polygon2D; doors/drawbridges = hinge (PinJoint2D or tween with ease + overshoot); moving platforms = Path2D +
PathFollow2D with eased speed.

---

## 2. Motion components

Format per component: **Entities** · **Inputs** · **Parameters** · **Outputs** · **Hard constraints** (must never
break) · **Soft constraints** (style targets) · **Validation** · **Limitations** · **Godot 4.6 runtime** ·
**Existing feature sufficient?**

Common contract for all components (proposal): each component is a pure function
`evaluate(state, inputs, dt) → {bone/node transforms, contact events, debug metrics}` driven by a **shared clock**
(time, cycle phase, speed) owned by the Entity Motion Profile, with **attach points** (named sockets) so components
mount on each other (wing on shoulder bone, tail chain on pelvis, emitter on mouth).

### 2.1 Articulated limb
- **Entities**: humanoid arms/legs, quadruped legs, bird legs, insect/spider legs, robot arms, cranes.
- **Inputs**: root (hip/shoulder) transform; target point (foot/hand); pole/bend direction.
- **Parameters**: segment lengths; per-joint min/max angle; bend_sign; foot posture (plantigrade/digitigrade/unguligrade);
  IK method (2-bone analytic, FABRIK, CCD).
- **Outputs**: joint angles / Bone2D rotations; end-effector position; "reach failed" flag.
- **Hard**: segment lengths constant; joint limits; bend direction fixed; foot never below ground.
- **Soft**: knee/elbow slightly bent at full reach; ankle angle follows ground normal.
- **Validation**: length error; limit violation count; bend-sign flips = 0; end-effector error < 1 px when reachable.
- **Limitations**: IK alone ignores dynamics (no weight); 3+ segment IK is under-determined → needs preferred-pose bias.
- **Godot**: Skeleton2D + Bone2D + `SkeletonModification2DTwoBoneIK` / `FABRIK` / `CCDIK` via SkeletonModificationStack2D
  (**experimental**, still present in 4.7 docs). Godot 4.6's new IK framework (IKModifier3D, TwoBoneIK3D, FABRIK3D…)
  is **3D only**. Simple custom 2-bone solver in GDScript is ~30 lines and avoids experimental API.
- **Sufficient?** Mostly yes; write a tiny custom 2-bone solver as a stable fallback.

### 2.2 Skeletal chain (generic N-segment chain)
- **Entities**: necks, spines, tails, tentacles, snakes, worms, eels, dragon bodies, hair strands, antennae, whips.
- **Inputs**: root transform (and its history), optional tip target, optional driver wave.
- **Parameters**: segment count & lengths; mode (`follow_leader` path / `fabrik_to_target` / `wave_driven` /
  `spring_lag`); per-segment stiffness, damping, angle limit; taper.
- **Outputs**: segment transforms; Line2D points or Bone2D rotations.
- **Hard**: inextensible (except concertina mode); angle between consecutive segments ≤ limit.
- **Soft**: smooth curvature; lag increases toward tip.
- **Validation**: spacing error; curvature max; no self-overlap (optional); tip lag phase measured.
- **Limitations**: no collision unless added; very long chains need iterations.
- **Godot**: Bone2D chain + custom script, or SkeletonModification2DJiggle (experimental) for spring lag; render
  with Line2D (update via `set_point_position`, `width_curve` for taper) or Polygon2D skinned to Bone2D.
- **Sufficient?** Partial; this is **the** core custom component — build it once, reuse everywhere.

### 2.3 Multi-legged gait (2 to N legs)
- **Entities**: humans, quadrupeds, birds walking, insects, spiders, centipedes (N legs), mechs, walking robots.
- **Inputs**: body velocity, terrain query (raycast / ground function), turn rate.
- **Parameters**: leg list with hip offsets and limb refs (2.1); gait table {φᵢ, β} per gait; stride frequency
  curve vs speed (or Froude); step height; body bob amplitude/phase (walk vs run); gait-switch thresholds with hysteresis.
- **Outputs**: foot targets per leg; stance/swing flags; body offset and pitch; footstep events (for SFX/dust).
- **Hard**: stance feet do not slide; feet above ground; stride_len × f = velocity.
- **Soft**: target β, φ; body pitch follows terrain; anticipation before gait change.
- **Validation**: foot slip metric; measured β/φ vs profile; support polygon (walks); loop seam.
- **Limitations**: kinematic only (no balance physics); stairs/ledges need footprint planner; uneven turning.
- **Godot**: custom GDScript scheduler + 2.1 IK + RayCast2D/ShapeCast2D for ground. No built-in gait system.
- **Sufficient?** No — custom (idea from Abdul Karim et al.); small (few hundred lines).

### 2.4 Wing articulation
- **Entities**: birds, bats, dragons, insects, fairies, flying machines (ornithopters).
- **Inputs**: flight state (flap/glide/hover/takeoff/land), speed, climb rate.
- **Parameters**: wing type (feathered / membrane / insect blur); bones (shoulder, elbow, wrist, finger tips);
  frequency f; amplitude A; downstroke fraction d; fold ratio on upstroke; membrane points (for bats/dragons).
- **Outputs**: bone rotations; membrane polygon; body lift offset; wingbeat events (SFX, dust).
- **Hard**: membrane edges stay attached to finger bones; wing does not pass through body silhouette.
- **Soft**: St in 0.2–0.4 at cruise; fold on upstroke; body counter-bob.
- **Validation**: St; span ratio up/down; tip path closed; membrane area doesn't invert (polygon winding).
- **Limitations**: perspective of wings in pure side view is faked (foreshortening by scale-x).
- **Godot**: Bone2D + Polygon2D weights (membrane), or AnimationPlayer driven procedurally; insect wings via shader blur.
- **Sufficient?** Rendering yes; motion logic custom (oscillator + fold curve).

### 2.5 Body undulation
- **Entities**: fish, eels, snakes, worms, tadpoles, sea serpents, dragon torso, larvae, rays (fin undulation).
- **Inputs**: speed, turning.
- **Parameters**: mode (anguilliform…ostraciiform, lateral undulation, sidewinding, concertina, rectilinear);
  amplitude envelope A(x); wavelength λ; frequency f (tied to speed via St or slip ratio).
- **Outputs**: per-segment offsets/angles for 2.2 chain.
- **Hard**: segment spacing constant; head yaw within limit.
- **Soft**: envelope matches mode; wave travels head→tail.
- **Validation**: envelope monotonic; wave direction sign; St.
- **Limitations**: water resistance not simulated (kinematic).
- **Godot**: driver on top of 2.2 (script) or vertex shader on a subdivided mesh for simple fish.
- **Sufficient?** Custom driver; tiny.

### 2.6 Tentacle
- **Entities**: octopus/squid, plant vines, eldritch horrors, mechanical cables, tongues.
- **Inputs**: goal (grab target / idle), root motion.
- **Parameters**: segment count; taper; curl amount; idle noise freq/amp; reach mode (FABRIK) blend with wave;
  suction "stick" points.
- **Outputs**: chain transforms; contact events.
- **Hard**: length conservation (or explicit stretch budget); root attached.
- **Soft**: curl toward tip; secondary lag.
- **Validation**: as 2.2 + reach error.
- **Godot**: 2.2 + Line2D/Polygon2D; or Ropesim for physical dangling tentacles.
- **Sufficient?** Reuse 2.2 with a tentacle preset — no separate engine.

### 2.7 Flexible tail
- **Entities**: cats, dogs, lizards, dragons, monkeys (prehensile), fish tails, ponytails.
- **Inputs**: pelvis transform and acceleration.
- **Parameters**: segments; stiffness/damping gradient root→tip; rest curve; gravity; expressive overlay (wag f/A).
- **Outputs**: chain transforms.
- **Hard**: root fixed to pelvis; length constant.
- **Soft**: follow-through after stops; counter-balance on turns.
- **Validation**: settle time; overshoot count; tip lag.
- **Godot**: SkeletonModification2DJiggle (experimental) or 2.2 spring_lag mode; Spine physics constraint if Spine is used.
- **Sufficient?** Jiggle mod mostly suffices; preset of 2.2 otherwise.

### 2.8 Rigid attachment
- **Entities**: weapons in hands, armour plates, riders on mounts, turrets, saddles, emitters on mouths.
- **Inputs**: parent socket transform.
- **Parameters**: socket name, local offset/rotation, inherit flags (position/rotation/scale), z-order.
- **Outputs**: child transform.
- **Hard**: no drift from socket.
- **Validation**: socket-to-child distance = offset.
- **Godot**: node parenting; `RemoteTransform2D` to push a transform to a node elsewhere in the tree **[background]**.
- **Sufficient?** Yes, fully built-in.

### 2.9 Hinge
- **Entities**: doors, lids, jaws, drawbridges, levers, flippers, pendulum arms, swinging signs.
- **Inputs**: drive (angle target, torque, or physics).
- **Parameters**: pivot, angle limits, motor speed, softness; tween curve if kinematic.
- **Outputs**: rotation; "hit limit" event.
- **Hard**: angle within limits.
- **Soft**: overshoot & settle on stop.
- **Godot**: PinJoint2D (softness, angular limits, motor) between physics bodies; or Tween/AnimationPlayer for kinematic.
- **Sufficient?** Yes.

### 2.10 Mechanical linkage
- **Entities**: pistons, steam engines, walking machines (Jansen/Klann linkages), cranes, scissor lifts, gear trains, clockwork.
- **Inputs**: driver angle / speed.
- **Parameters**: link lengths, ground pivots, branch choice, gear tooth counts, slider offset.
- **Outputs**: all link transforms; coupler point path.
- **Hard**: loop closes for every θ; lengths constant; Grashof if full rotation required.
- **Validation**: closure residual < 0.01 px; branch consistency; gear mesh phase.
- **Limitations**: kinematic only (no forces).
- **Godot**: custom script (circle intersection) is simplest and deterministic; physics joints (PinJoint2D,
  GrooveJoint2D for sliders **[GrooveJoint2D page not read today]**) work but jitter and drift.
- **Sufficient?** Custom solver (small); avoid physics for closed loops.

### 2.11 Pendulum
- **Entities**: lamps, chandeliers, swinging blades, hanging signs, censers, wrecking balls, ear/earring dangles.
- **Inputs**: pivot motion, impulses.
- **Parameters**: length, gravity, damping, angle limit.
- **Outputs**: angle.
- **Validation**: period vs `2π√(L/g)`; energy non-increasing.
- **Godot**: RigidBody2D + PinJoint2D, or analytic/semi-implicit script (preferred for determinism).
- **Sufficient?** Yes either way.

### 2.12 Spring
- **Entities**: everything secondary — antennae, ears, bellies, bouncy platforms, UI juice, slime squash, cameras.
- **Inputs**: target value (position, angle, scale), dt.
- **Parameters**: f (Hz), ζ, optional response/anticipation term; per-axis.
- **Outputs**: value + velocity.
- **Hard**: stable for all dt in range (fixed step or semi-implicit).
- **Validation**: measured f, overshoot vs ζ; no energy gain.
- **Godot**: DampedSpringJoint2D for physics bodies; script spring for kinematic use (most cases).
- **Sufficient?** Build a 20-line reusable spring utility; it underpins 2.2, 2.7, 2.18, 2.19.

### 2.13 Rope
- **Entities**: ropes, vines, grappling hooks, leashes, bridges, hair, cables, whips.
- **Inputs**: anchor(s), attached bodies, collisions.
- **Parameters**: segment count/length, iterations, damping, gravity, stiffness, collision radius, tear threshold.
- **Outputs**: point list; tension events.
- **Hard**: stretch error within budget; anchors exact.
- **Validation**: stretch %, energy stability, no tunnelling through thin colliders.
- **Godot**: **GDNative-Ropesim** (MIT, GDExtension C++ core + GDScript; Godot 4.3+; Line2D renderer, anchors,
  handles, interaction, collision shape generator) — or a GDScript Verlet loop for short ropes; RigidBody2D +
  PinJoint2D chains are possible but jittery.
- **Sufficient?** Yes with Ropesim (needs security review + Godot 4.6 compatibility check before install).

### 2.14 Chain
- Same as rope, but rendered as rigid link sprites aligned to each segment and with lower stretch tolerance and
  stronger angle limits. **Godot**: Ropesim + per-link Sprite2D, or RigidBody2D links with PinJoint2D for
  heavy physical chains that must collide individually. **Sufficient?** Yes.

### 2.15 Cloth
- **Entities**: capes, flags, banners, curtains, sails, skirts, tents.
- **Inputs**: attachment points (bones), wind, character velocity.
- **Parameters**: grid resolution; structural/shear/bend stiffness; iterations; wind vector + noise; pinned vertices.
- **Outputs**: mesh vertex positions (UV fixed).
- **Hard**: pinned vertices exact; no NaN; triangle area not inverted.
- **Soft**: limited stretch (< 5 %); folds read at gameplay scale.
- **Validation**: stretch error, inverted-triangle count = 0, energy.
- **Limitations**: no self-collision (fine for 2D); body collision approximated with circles.
- **Godot**: no 2D cloth node. Options: (a) vertex shader wave on a subdivided mesh for flags (cheap, stateless);
  (b) Bone2D chain(s) with jiggle for capes; (c) custom Verlet/PBD grid writing to a Polygon2D/ArrayMesh;
  (d) bake in Blender (offline) to a sprite sheet.
- **Sufficient?** Partially; (a)/(b) cover most 2D needs. (c) is custom but small.

### 2.16 Deformable body
- **Entities**: slimes, jelly, balloons, blobs, organs, bouncy mushrooms, cartoon squash on any character.
- **Inputs**: velocity, impacts, ground contact.
- **Parameters**: model (scale squash / pressure ring / shader wobble); stiffness; area target; damping.
- **Outputs**: scale/skew or ring polygon.
- **Hard**: area preserved within ±5 %; no self-intersection.
- **Validation**: area ratio; `sx·sy`; settle time.
- **Godot**: **no 2D soft body** (SoftBody3D is 3D only). Use script squash on Node2D scale, Polygon2D ring,
  or a canvas_item vertex shader. Rapier 2D (addon) advertises liquids but not 2D soft bodies **[not verified]**.
- **Sufficient?** Custom (small).

### 2.17 Ballistic
- **Entities**: arrows, grenades, thrown items, jumping creatures (airborne phase), debris, gibs, coins.
- **Inputs**: launch position/velocity or target + flight time.
- **Parameters**: gravity, drag, spin, bounce restitution.
- **Outputs**: position, rotation, landing event, predicted arc (for telegraph).
- **Validation**: analytic vs sim landing error.
- **Godot**: RigidBody2D (physical) or analytic script / CharacterBody2D (deterministic, preferred for gameplay).
- **Sufficient?** Yes.

### 2.18 Hovering
- **Entities**: drones, ghosts, fairies, floating eyes, hummingbirds, UFOs, magic orbs, jetpacks.
- **Inputs**: target position.
- **Parameters**: bob f/A, tilt toward velocity, spring follow (2.12), thruster emitter refs.
- **Outputs**: offset, tilt, emitter intensity.
- **Validation**: bob loops; tilt ∝ acceleration; never touches ground unless landing.
- **Godot**: script + GPUParticles2D for thrusters (`amount_ratio` from thrust). **Sufficient?** Yes (trivial custom).

### 2.19 Floating / bobbing
- **Entities**: boats, buoys, logs, ducks, pickups, lily pads, debris on water.
- **Inputs**: water height function (or water surface columns), object width.
- **Parameters**: buoyancy spring f/ζ, sample points (2+ for roll), random phase.
- **Outputs**: y offset, roll angle.
- **Validation**: rests at waterline; roll follows surface slope; no drift.
- **Godot**: script; or RigidBody2D inside Area2D with gravity/damping overrides. **Sufficient?** Yes.

### 2.20 Rotational
- **Entities**: wheels, fans, gears, turrets, propellers, coins, saw blades, planets, spinning magic sigils.
- **Inputs**: angular speed or linear speed (wheels: `ω = v / r`).
- **Parameters**: ω, acceleration curve, gear ratio chain, wobble.
- **Outputs**: rotation; motion-blur switch over a threshold (propellers: swap to blurred sprite) **[background]**.
- **Validation**: rolling without slip (`ω r = v`); avoid wagon-wheel aliasing (rotation per frame < half the symmetry angle).
- **Godot**: Node2D rotation in `_process`; AnimationPlayer for loops. **Sufficient?** Yes.

### 2.21 Fluid
- **Entities**: water surfaces, waterfalls, lava, blood, potions, rivers, slime trails.
- **Options**: (a) shader (UV scroll + noise distortion) — most 2D games; (b) 1D spring-column water surface
  (interactive splashes); (c) particles + metaball shader for blobs; (d) Rapier physics addon "liquids" (MIT; 2D/3D;
  still in development); (e) bake in Blender Mantaflow to flipbook (offline).
- **Validation**: seamless tiling; surface returns to rest; particle budget.
- **Sufficient?** Shaders + particles cover it; do not build a Navier–Stokes/SPH solver.

### 2.22 Particle emission
- **Entities**: fire, smoke, sparks, dust (footsteps), magic, rain, snow, blood, leaves, bubbles, engine exhaust, dragon breath.
- **Inputs**: emitter socket (2.8), intensity, direction, events (footstep, impact).
- **Parameters**: ParticleProcessMaterial fields (see 1.11), texture/flipbook, blend mode, sub-emitters.
- **Outputs**: rendered particles; finished signal.
- **Hard**: budget cap; ends cleanly.
- **Validation**: budget, alpha-to-zero, thumbnail readability.
- **Limitations**: 2D collision only with LightOccluder2D; trails and `emit_particle()` not in Compatibility renderer;
  CPUParticles2D lacks trails. Particle attractor nodes are 3D-only **[background — verify]**.
- **Godot**: GPUParticles2D; PixelFX (already installed) for pixel-art effect sheets.
- **Sufficient?** Yes, fully built-in.

### 2.23 Shader deformation
- **Entities**: foliage sway, flags, heat haze, water reflections, jelly wobble, dissolve/teleport, hit flash,
  breathing idle, ghosts, energy shields.
- **Inputs**: TIME, per-instance data (INSTANCE_CUSTOM), uniforms (wind, hit time).
- **Parameters**: amplitude, frequency, spatial phase, mask texture, height weighting.
- **Outputs**: per-vertex VERTEX offsets (vertex()) or UV distortion (fragment()).
- **Hard**: displacement stays inside the sprite's bounds or the visibility rect is enlarged (else culled/clipped) **[background]**.
- **Validation**: seamless loop at period; no tearing between tiles (phase from world position).
- **Limitations**: `vertex()` can move only existing vertices — a Sprite2D is a 4-vertex quad **[background]**, so
  smooth bends need a subdivided Polygon2D / MeshInstance2D, otherwise distort UVs in `fragment()`. TIME wraps after
  3600 s by default.
- **Godot**: canvas_item shaders (`VERTEX` inout in vertex(), `world_vertex_coords` render mode).
- **Sufficient?** Yes.

---

## 3. Entity Motion Profile — composition sketch

```yaml
entity: dragon_small
clock: { speed_source: velocity, gait_by: froude, leg_length_px: 48 }
skeleton: res://entities/dragon/skeleton.tscn
components:
  - id: legs        type: multi_legged_gait
    legs: [LH, LF, RH, RF]  limb: articulated_limb{posture: digitigrade}
    gaits: [walk, trot, bound]
  - id: wings       type: wing_articulation   mount: spine_2   wing_type: membrane
    states: {flap: {f: 2.5, A: 50deg, downstroke: 0.58, fold: 0.7}, glide: {...}}
  - id: tail        type: skeletal_chain      mount: pelvis    mode: spring_lag  segments: 8
    overlay: body_undulation{mode: anguilliform, A_tip: 0.15}
  - id: neck        type: skeletal_chain      mount: spine_4   mode: fabrik_to_target(look_at)
  - id: breath      type: particle_emission   mount: jaw_socket preset: fire_cone
    telegraph: {windup_s: 0.6, shape: cone, audio: inhale}
validation: [foot_slip, bone_length, strouhal_wings, particle_budget, loop_seam]
```
The profile owns the clock and mounting; components never reference each other directly, only sockets and
shared state (velocity, phase, flight state). Hybrids are just different component lists.

---

## 4. Technology evaluation

| Tool | What for | Licence | Commercial OK? | Hardware fit (3060 12 GB / 16 GB) | Automation by agents | 2D applicability | Verdict |
|---|---|---|---|---|---|---|---|
| Godot 4.6 core (Node2D, Bone2D, Skeleton2D, Polygon2D, Line2D, AnimationPlayer, Tween) | Runtime for all components | MIT [background] | Yes | Trivial | High (text scenes/scripts/resources) | Native | **Adopt** (base) |
| SkeletonModification2D stack (TwoBoneIK, FABRIK, CCDIK, LookAt, Jiggle) | 2D IK, jiggle | MIT | Yes | Trivial | High | Native | **Use with fallback** — experimental, may change |
| Godot 4.6 IK framework (IKModifier3D etc.) | IK | MIT | Yes | — | — | **3D only** | Not applicable to 2D |
| Joint2D family (PinJoint2D, DampedSpringJoint2D, GrooveJoint2D) | Hinges, springs, sliders between bodies | MIT | Yes | Trivial | High | Native | **Adopt** for physical props |
| GPUParticles2D / ParticleProcessMaterial | Fire, smoke, magic | MIT | Yes | Good | High (`.tres`) | Native | **Adopt** |
| canvas_item shaders | Sway, wobble, distortion | MIT | Yes | Good | High | Native | **Adopt** |
| SoftBody3D | Soft bodies | MIT | Yes | — | — | **3D only** | Not applicable |
| GDNative-Ropesim | Verlet rope/chain | MIT | Yes | Light (C++ GDExtension) | High (nodes + GDScript) | Native 2D | **Candidate** — security review + 4.6 compat test before install |
| Godot Rapier Physics (appsinacup) | Alternative 2D physics, determinism, liquids | MIT (per asset listings) | Yes | Light | Medium | 2D + 3D | **Defer** — only if Godot Physics 2D jitter blocks us; still in development |
| Spine (+ spine-godot runtime) | Skeletal 2D + physics constraints | Proprietary; runtimes require each user to hold a Spine Editor licence; physics constraints not in Essential | Yes, with paid licences | Light | Low–medium (editor is GUI; JSON format scriptable) | 2D | **Do not adopt now** — cost + GUI-bound; our needs are covered in-engine |
| Blender (bpy, headless) | Offline bake of cloth/fluid/smoke to sprites | GPL (outputs yours) [background] | Yes | Fine | High (Python, `-b`) | Via render-to-sprite | **Optional** offline tool for hard sims |
| DeepLabCut | Measure animal keypoints from video | Code LGPL-3.0; SuperAnimal weights non-commercial | Code yes; **weights no** | OK (≥8 GB VRAM ideal) | High | Indirect (analysis only) | **Reject for pipeline**; maybe later for internal measurement with own-trained model |
| Kirin | Text/image → 3D quadruped motion | Code MIT; dataset licence unknown; needs gated HF models + Rodin API key | Unclear | Unknown VRAM | Medium, needs accounts | Indirect (3D → 2D projection) | **Reject** (accounts, data rights) |
| Muybridge plates (LoC, Smithsonian, Wellcome copies) | Gait/pose reference | US public domain (pre-1929) | Yes in US; check per-holder record | n/a | Agents can read **our** traced phase tables | High as reference | **Adopt** as reference (store our own derived data) |
| Smithsonian Open Access | Animal images | CC0 for marked items | Yes | n/a | Offline cache by humans | Reference | **Adopt** (CC0-marked only) |
| Biodiversity Heritage Library | Historic anatomy illustrations | Mostly PD, some "no known restrictions", some not | Per item | n/a | — | Reference | **Use per item** with licence check |
| Truebones Zoo | Animal mocap (FBX/BVH) | Royalty-free incl. commercial, no redistribution, credit requested; current free offer unclear | Probably yes | Fine | Low (3D, needs Blender retarget) | Indirect | **Defer**; 3D-to-2D cost too high; licence text not read in full |
| Goldfinger, *Animal Anatomy for Artists* | Human-readable anatomy | Copyrighted, paid | Reading yes; copying no | n/a | None | Reference | **Buy for artists**, write own notes |
| Raibert & Hodgins 1991; Abdul Karim et al. | Algorithms | Papers | Ideas free to implement | n/a | n/a | Conceptual | **Use ideas** (gait scheduler, hop dynamics) |
| myPhysicsLab | Reference sims (pendulum, springs, chains, linkages) | Apache-2.0 | Yes | Browser | Code readable offline if vendored | Conceptual | **Reference** |
| Ten Minute Physics (Müller) | PBD/XPBD rope/cloth/soft body tutorials | Code licence **not stated on page** | Unknown | Browser | — | Conceptual | **Reference** (re-implement, don't copy until licence checked) |
| PixelFX (installed) | Pixel-art VFX library | (per earlier rollout) | — | Fine | High | 2D | **Adopt** for 2.22 presets |

---

## 5. What NOT to build ourselves

1. A physics engine or rigid-body solver (use Godot Physics 2D; Rapier only if needed).
2. A particle system or particle editor (GPUParticles2D + PixelFX).
3. 2D skinning / mesh deformation (Skeleton2D + Polygon2D weights).
4. A generic multi-solver IK library (use SkeletonModification2D; only a tiny 2-bone + FABRIK fallback).
5. A rope/Verlet GDExtension (GDNative-Ropesim exists, MIT).
6. A fluid simulator (SPH / Navier–Stokes / FLIP) — shaders, particles, spring-column water, or offline Blender bakes.
7. Cloth with self-collision or 3D cloth (2D needs bones+jiggle, shader waves, or a small Verlet grid at most).
8. Pose-estimation or motion-generation ML (DeepLabCut, Kirin, etc.) — licences, accounts and 3D→2D cost outweigh value.
9. A mocap retargeting pipeline from 3D animal mocap.
10. A Spine-like skeletal editor or exporter.
11. Physics-based locomotion controllers (Raibert-style balance) — kinematic gait + springs is enough for 2D games.
12. A deterministic-lockstep physics layer (only if multiplayer ever demands it, and then Rapier's).

What we **should** build (small, custom, the actual knowledge system): spring utility, skeletal chain, gait scheduler,
wing oscillator, undulation driver, linkage solver, squash/area-preserving deformer, telegraph timing component,
profile loader, and the validation metrics.

---

## 6. Sources

**Read successfully (WebFetch)**
- OUP — Goldfinger, *Animal Anatomy for Artists* (academic.oup.com/book/41965) — read in two parts
- UPenn Archives — Muybridge collection finding aid (archives.upenn.edu/collections/finding-aid/upt50m993/)
- DeepLabCut GitHub README (github.com/DeepLabCut/DeepLabCut)
- DeepLabCut Model Zoo docs and Installation docs (deeplabcut.github.io/.../ModelZoo.html, installation.html)
- Hugging Face — SuperAnimal-Quadruped model card (licence)
- Kirin project page (kirin-ani.github.io) and repo (github.com/briannlongzhao/kirin)
- Abdul Karim — Procedural locomotion page
- CMU RI — Raibert & Hodgins 1991 record
- Blender manual — Physics index (first half only)
- Godot 4.7 docs: Physics introduction; 2D particle systems; GPUParticles2D; ParticleProcessMaterial (first part);
  SkeletonModification2DJiggle; DampedSpringJoint2D; PinJoint2D; SoftBody3D; Line2D; 2D skeletons;
  canvas_item shader reference
- Godot 4.6 release page (godotengine.org/releases/4.6/)
- Esoteric Software — Spine physics constraints; Spine Runtimes licence
- Wikipedia — Gait; Horse gait; Undulatory locomotion; Fish locomotion; Bird flight; Bat flight; Digitigrade;
  Arthropod leg; Four-bar linkage; Squash and stretch
- myPhysicsLab home; Ten Minute Physics index
- GDNative-Ropesim README (github.com/mphe/GDNative-Ropesim)
- Riot — *Clarity in League*

**Search-result summaries only (not opened)**: Jakobsen 2001 Verlet; Muybridge PD status (LoC/Commons, Smithsonian,
Wellcome, Brooklyn); Alexander 1984 / Froude; SkeletonModificationStack2D experimental status; Smithsonian Open Access
CC0 / BHL; Godot Rapier licence; snake locomotion reviews (Jayne 2020, Tingle 2024); spider tetrapod gait papers;
Strouhal (Taylor, Nudds & Thomas 2003); Truebones licence; VFX telegraph/readability talks.

**Failed**
- deeplabcut.github.io/DeepLabCut/ (home page returned empty content) — covered via GitHub + docs subpages instead
- en.wikipedia.org/wiki/Insect_locomotion — HTTP 404 (insect gait covered via *Gait* and *Arthropod leg*)
- Müller et al. PBD PDF (matthias-research.github.io/.../posBasedDyn.pdf) — binary not parseable; not opened
- wellcomecollection.org/works/e998rea7 — empty content
- Not attempted: GrooveJoint2D class page, Hildebrand original papers, Jakobsen full text
