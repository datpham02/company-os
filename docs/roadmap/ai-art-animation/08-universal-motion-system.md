# Universal Motion & Animation Knowledge System

- **Status:** `PROPOSED`, R&D. Responds to the Board amendments "Functional Anatomy & Biomechanics" (P0) and
  "Universal Motion & Animation Knowledge System" (2026-11-22), which supersede the humanoid-first scope of
  [04](04-animation-methodology.md)–[07](07-agent-skills-proposal.md). Prepared by Claude Code (decision D1);
  `director` reviews and presents.
- **Scope:** characters, creatures, objects, environments and effects for every current and future project.
  Human anatomy is one knowledge domain, not the root of the system. Benchmarks are validation cases.
- **Evidence base:** research files in [kb/](kb/) (animation fundamentals, Spine/Godot workflow, functional anatomy,
  biomechanics and existing systems, universal motion) and [05](05-motion-reference-and-licensing.md) (motion data
  licences); working R&D code in `rnd/motion/` (mirrored in [spikes/motion/](spikes/motion/)).

## 1. Capability architecture

```
                     knowledge (kb/*.md, profiles/*.json, component registry, reference library)
                                   |
 request ──> ENTITY MOTION PROFILE (composition of components, fictional rules, gameplay, references)
                                   |
             method selection (entity.py plan): per component -> method + constraints + validators
                                   |
   ┌───────────── motion production per component ─────────────────────────────────────────┐
   | skeletal: motion spec -> FK/IK-baked keys | mocap retarget (C) | procedural generators  |
   | gaits (phase tables) | chains (spring/wave/FABRIK presets) | pendulum/rope/cloth (Verlet) |
   | rigid attachments (transforms) | particles / shaders (engine runtime)                    |
   └───────────────────────────────────────────────────────────────────────────────────────┘
                                   |
             QA: component validators (hard/soft) + fictional overrides + artistic review on previews
                                   |
             engine adapter (Godot first: Skeleton2D/Bone2D/Polygon2D, Line2D, Joint2D,
             GPUParticles2D, canvas shaders) -> runtime
```
Principles: composition over inheritance (a new creature = a new profile, never a core change); deterministic
tools own geometry, timing, contacts and continuity; generative models own artwork only; every component reports
validation metrics; intentional non-physical behaviour is declared as a fictional rule, not flagged as an error.

## 2. Knowledge research plan (status)

| Domain | Status | File |
|---|---|---|
| Animation principles, timing, combat, stylisation, blocking, FK/IK | done (draft) | kb/animation-fundamentals.md |
| Professional 2D workflow (Spine, Godot) | done (draft) | kb/animation-workflow-spine-godot.md |
| Functional anatomy, 12 body parts, clinical vs functional vs stylised ROM, 2D projection | done (draft); numbers applied to `profiles/humanoid_base.json` | kb/functional-anatomy.md + kb/human_joint_table.json |
| Biomechanics, kinesiology, existing systems (OpenSim, Unity, Unreal, Godot, VRM, Rigify, SMPL) | done (draft) | kb/biomechanics-and-existing-systems.md |
| Comparative anatomy, gaits, flight, swimming, undulation, soft bodies, cloth/rope, springs, ballistics, linkages, particles, magical motion | done (draft) | kb/universal-motion.md |
| Motion data and licences | done; CMU verified in browser | 05 |
Gaps (all marked in the files): no published sledgehammer biomechanics; books (Neumann, Mattesi, Williams, Goldfinger)
only through secondary descriptions; several licence pages unreadable (OpenSim model-specific licences, VRM spec,
Truebones). `director` reviews the KB content before it becomes agent knowledge (decision K4).

## 3. Entity Motion Profile (schema proposal)

Definition: `rnd/motion/entity/entity-motion-profile.schema.json`. Required: `id`, `components`, `validation`;
everything else optional: identity and movement identity, topology, anatomy profile reference, proportions, mass,
materials (elasticity, damping, friction), components (type, name, params, `attach_to` socket), locomotion modes,
contacts (always / phase / never), attachments, collision approximations, environment interactions, cross-entity
interactions, references (with licence), artistic characteristics, gameplay events and timing budgets, allowed
methods, **fictional rules** (each names the validators it replaces), validation (physical / fictional / artistic).

Examples (validated by `entity.py plan`, 0 structural errors): brute with hammer, dragon (skeleton + gait + wings +
undulating tail + flexible tip + armour plates + fire particles), slime, ghost (no gravity, phasing), golem, giant
spider, lantern carried by a character.

**Anatomy profiles** (`profiles/*.json`, `anatomy-profile.v1`) are one *parameter* of the skeletal component: joint
types, DOF, movements with three ranges (clinical / functional / stylised), preferred bends, 2D flip policy, coupled
rules, mass model, character overrides that must state why. Provided: humanoid base, stylised humanoid, heavy
humanoid, quadruped, flying creature, multi-limbed, custom template. Recommended conventions adopted from existing
systems (kb/biomechanics): Godot SkeletonProfileHumanoid bone names and axes (MIT), VRM's required humanoid bones as
the minimum humanoid, alias tables for Mixamo/Unity/BVH-CMU, de Leva segment mass tables (CC BY 4.0), Unreal-style
per-joint settings (free/limited/locked, stiffness, preferred bend), contact schedules per clip.

## 4. Composable motion components

Registry: `rnd/motion/entity/components.json` (17 entries today; the research lists 23 incl. hinge, spring, chain,
floating as separate presets). Each entry: applicable entities, inputs, parameters, outputs, methods, hard and soft
constraints, validators, implementation status, runtime option. Build-vs-reuse verdicts (kb/universal-motion §2, §5):

| Component | Runtime | Build | Status |
|---|---|---|---|
| articulated skeleton | Godot Skeleton2D/Bone2D/Polygon2D, keys baked from our solver | solver + validators (have) | implemented |
| skeletal chain (tail, tentacle, neck, snake, fish) | baked keys or Skeleton2D jiggle (experimental) | **one chain component with presets**: follow-the-leader, FABRIK, travelling wave, spring lag | to spike |
| multi-legged gait (2..N legs) | baked foot targets + IK | **gait scheduler** from phase/duty tables, Froude-based gait choice | to spike |
| wing articulation | baked keys | oscillator on a socket, fold coupling, Strouhal check | to spike |
| rigid attachment / hinge / linkage | transforms; Joint2D for physical props | linkage solver later | attachment implemented |
| pendulum / spring | baked springs | have (S4) | partial |
| rope / chain / cloth strips | Verlet (own small solver) or GDNative-Ropesim (MIT, needs review) | decide after a spike | — |
| deformable body | Polygon2D mesh + spring lattice, or shader | small lattice | — |
| ballistic / hovering / floating / rotational | procedural | trivial generators | — |
| particles, fire, smoke, energy | GPUParticles2D / PixelFX presets | **do not build** a simulator | — |
| shader deformation | canvas_item shaders | **do not build** an engine | — |

Not built ourselves: a muscle simulator, a physics engine, a particle simulator, 2D soft body physics, Spine
authoring (licence: every user needs an Editor licence; physics constraints need Professional).

## 5. Motion method selection criteria

Procedure (agent, every request): analyse structure → capabilities → references (real or analogue) → intent and
gameplay → rigid vs deformable parts → choose methods per component → constraints → produce → render → validate
and refine. `entity.py plan` makes steps 1, 2, 5, 6 and 7 checkable.

| Situation | Preferred method | Why |
|---|---|---|
| a matching, commercially usable reference exists (mocap, Muybridge-derived tables) | reference retarget + KB adjustment (C+B) | real coordination and timing; adjust what the source cannot give (S4 finding) |
| big articulated action with no reference | knowledge-guided FK keys + validators (B) | deterministic, checkable |
| repeating locomotion | procedural gait scheduler | parameters scale to N legs, speeds |
| secondary motion (tails, cloth, chains, lanterns) | procedural springs/Verlet, baked | cheap, stable |
| impacts, magic, elements | particles + shaders + short frame sequences | runtime features exist |
| pixel art, effects with changing shapes | frame-by-frame (generated + validated) | rotation blurs pixels |
| AI motion generation (video → motion) | not now | licences (SMPL, SuperAnimal NC), accounts, RAM |

## 6. Reference library strategy

Production-OK only: CMU mocap original data (verified: free for all uses, no resale), CC0 packs (Quaternius,
Kenney), Muybridge plates (US public domain; we store our own traced phase tables, not the images), Smithsonian
Open Access items marked CC0. R&D only: NC datasets (Bandai Namco, LaFAN1, AMASS, SMPL family, SuperAnimal).
Store derived data (motion.v2 keys, phase/duty tables, contact schedules) with the source pointer and licence check
date; never commit raw third-party data. Agents have no web access, so formulas and tables live in kb/ and profiles.

## 7. Entity-specific QA architecture

Validators attach to components, so an entity gets exactly the checks of its components minus those its fictional
rules replace. Three tiers (implemented for skeletal entities in `posecheck.py`): **A anatomical/structural**
(hierarchy, lengths, ranges for the chosen tier, bend, flips, reachability), **B physical/biomechanical**
(balance per phase, contacts, weight transfer, sequencing, grip, self-collision, coupling, contact speed),
**C action/artistic** (intent checks for the action category + an explicit review list for `director` on real-time
and slow previews). Planned per family: gait sequence and duty factor (quadruped, multi-legged), support polygon
with ≥3 contacts (insects), wing timing/fold coupling/body response (flying), wave direction and amplitude envelope
(serpentine), area preservation and elastic recovery (soft body), pivot/linkage closure/intersection (mechanical),
loop seam and event sync (magical, hovering). Thresholds are fractions of leg/body length, not pixels (2D units are
arbitrary). Physical, fictional and artistic correctness are reported separately.

**Done and verified today:** 18 automated tests (`tests/test_motion_system.py`): solver tests (rest reproduction,
degrees, local vs global inheritance, isolated elbow sweep without shoulder motion/flips/length change, weapon
transform, IK reachability flag, knee bend under a crouch sweep, left/right mirroring) and 10 regression tests, one
per Board-reported failure. The new validators found a real solver bug (leg IK bend side inverted, rest pose not
reproduced) - fixed; knees now follow the anatomical preferred bend.

## 8. Benchmark suite (12) and spike priorities

| # | Benchmark | Intent | Components | Acceptance (summary) |
|---|---|---|---|---|
| 1 | Humanoid combat | light attack + hit reaction | skeleton, attachment | tier A/B hard pass; director on previews |
| 2 | Heavy humanoid (**current**) | heavy overhead smash | skeleton, attachment, flexible appendage | done: B 17/17 hard, C as reference; hybrid next |
| 3 | Quadruped locomotion | walk → trot → gallop | skeleton, gait, chain (tail) | footfall order, duty factor, no slip, spine flex in gallop |
| 4 | Flying creature | take-off, flap, glide | wing, skeleton, chain | fold coupling, downstroke > upstroke, body bob |
| 5 | Multi-legged | spider skitter | skeleton, gait (8) | ≥3 supports, tetrapod order, no leg crossing |
| 6 | Serpentine / tentacle | slither, strike | chain (wave) | wave head→tail, amplitude envelope, lengths |
| 7 | Soft body | slime hop | deformable, ballistic | area ±10 %, recovery, parabola |
| 8 | Mechanical | robot arm / door linkage | hinge, linkage | pivots, closure, no intersection |
| 9 | Rigid object + attachment | lantern carried, sword thrown | attachment, pendulum, ballistic | grip, detach event, settle |
| 10 | Magical/abstract | ghost drift, artifact spin | hover, shader, particles | loop seam, readability, fictional rules |
| 11 | Environmental | foliage, banner, chain | spring, cloth, rope | wind response, no jitter |
| 12 | Hybrid | dragon | gait + wing + chain + particles | composition works without core changes |
Each benchmark records intent, structure, references (with licence), expected behaviour, technical constraints,
artistic criteria, previews (real-time, slow, sheet, trajectories), QA method, automation cost and reusability.

**Spike order (do not run all at once):** finish #2 (hybrid C+B, idle transition) → **#5/#3 gait scheduler**
(proves shared clock, phase tables, contacts across leg counts) → **#6 chain presets** (one component for tail,
tentacle, snake, fish) → **#4 wing** (oscillator on a socket) → #12 dragon composes the three. Then #7, #9, #10.

## 9. Implementation roadmap

| Phase | Content | Estimate (Board-operator days, excl. agent time) |
|---|---|---|
| U0 | review of this package + KB by `director`; Board decisions | 1 |
| U1 | heavy humanoid hybrid C+B; Godot adapter for motion.v2 (bake to AnimationPlayer); art pass prerequisites | 4–6 |
| U2 | gait scheduler + quadruped/spider benchmarks; component validators | 5–8 |
| U3 | chain presets + wing + dragon composition | 5–8 |
| U4 | soft body, rope/cloth, attachments/throws, magical (particles/shaders) | 6–10 |
| U5 | Agent Skills packaging, pose and motion libraries, regression suite in CI | 3–5 |
Total about 24–38 days, highly uncertain after U2; each phase re-estimates from its spike.

## 10. Agent responsibility proposal

No new agent now (constraint: do not add agents). During R&D the Board operator (Claude Code) builds the tools
(decision D1); `director` reviews motion and KB content (read-only, on previews); `qa-engineer` later runs the
validators in CI; `game-artist` supplies artwork for layered parts/master assets; `gameplay-programmer` owns the Godot
adapter and runtime integration. Decision D7 (a technical artist or animator role) is revisited after U2 with evidence
of how much motion work recurs per project. Skills ([07](07-agent-skills-proposal.md)) extend to: comparative anatomy,
creature motion analysis, animal locomotion, creature rigging, procedural locomotion, physical motion design, object
and mechanical animation, soft body, secondary motion, environmental animation, magical motion design, cross-entity
interaction, entity-specific QA - each with trigger, inputs, knowledge, tools, steps, outputs, failure conditions and
review checklist, packaged only after K4.

## 11. Budget and resources

No new paid tool, account or service is proposed. Compute: CPU-only Python (NumPy/SciPy/Pillow from ComfyUI's
embedded Python) and Godot; no GPU needed for motion. Disk: small (derived JSON, previews). Optional later: a book
budget for human-readable references (Goldfinger, Neumann, Williams) if the Board wants a reviewer to read them;
GDNative-Ropesim would need a dependency review.

## 12. Risks and unresolved blockers

| Risk / blocker | Impact | Mitigation |
|---|---|---|
| 2D projection ambiguities (shoulder front/back, far-limb flips) | false positives/negatives in QA | projection-aware checks (elevation, flip-through-neutral) documented; director review |
| Unverified anatomy numbers (scapula angles, subtalar, neck functional, ankle dorsiflexion spread) | wrong limits | each value carries a status; only verified/derived values gate realistic characters |
| 2D trunk channel = hip + spine inclination (CMU actor arched to -40 deg, beyond the spine-only limit) | false hard failures on real motion | split the trunk channel by lumbopelvic rhythm before using clinical spine limits |
| OpenStax licence (CC BY-NC-SA, no AI ingestion without permission) | KB provenance | no OpenStax text/figures; facts cross-checked (U-G) |
| Art supply for layered parts (Phase 3 tools not built) | motion cannot be shown on the real art | U1 prerequisites; partial skeletal + master assets first |
| Godot 2D IK experimental; no 2D soft body | runtime gaps | bake from our solver; small lattice/Verlet tools |
| Licences: SMPL/SuperAnimal NC, Spine Editor licence, unknown OpenSim model licences, VRM spec licence | blocked reuse | use only production-OK sources; legal check before any Spine export |
| Scope growth (each amendment widened scope) | delay | spike order in §8; one benchmark proven before the next |
| Artistic judgement still human-like (director) | Board load | director reviews on previews; validators remove mechanical errors first |

## 13. Required Board decisions

| # | Decision | Recommendation |
|---|---|---|
| U-A | Adopt this architecture (composition, component registry, entity profiles; human anatomy as one domain) | approve |
| U-B | Adopt existing conventions: Godot SkeletonProfileHumanoid names/axes, VRM minimum humanoid, de Leva mass tables, Unreal-style joint settings; no Spine export without a legal check | approve |
| U-C | Reference policy: production-OK sources only (CMU original, CC0 packs, Muybridge-derived tables, Smithsonian CC0); NC datasets and SuperAnimal/SMPL R&D-only; Kirin rejected | approve |
| U-D | Spike order: hybrid #2 → gait #5/#3 → chain #6 → wing #4 → dragon #12 | approve |
| U-E | KB content review by `director` (K4) before any skill packaging | approve |
| U-F | Optional dependency review of GDNative-Ropesim (MIT) when the rope spike starts | later |
| U-G | OpenStax: stop using it as a source (CC BY-NC-SA, AI-ingestion clause); keep only facts already cross-checked elsewhere; ask OpenStax/legal if the Board wants it | approve |
| U-H | Functional ROM is informative, not a limit; clinical (realistic) or stylized (stylised) tier gates per character; character overrides must state why | approve |
