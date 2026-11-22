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
- **Review:** `director` (SOU-87, 2026-11-22): *accept for Board presentation*, with amendments now applied in this
  revision; the two high-severity items are presented as **conditions** (§5 reference-selection gate, §8 order).

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
methods, **environment** (gravity vector, medium: air / water / none - physical context, not fiction),
**characteristic_length** (the unit for every threshold: leg length for legged bodies, body length or diameter
otherwise), **fictional rules** (only for behaviour that contradicts the declared environment; each names the
validators it replaces), validation (physical / fictional / artistic).

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

Registry: `rnd/motion/entity/components.json` (18 entries incl. the `interaction_contact` stub; every validator is
tagged with its structural assumption - bilateral, legged, grounded, trunk, articulated, periodic - so a snake, slime
or jellyfish never inherits a check that assumes legs or a trunk; the research lists 23 incl. hinge, spring, chain,
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
| a reference passes the **reference-selection gate** (below) | reference retarget + KB adjustment (C+B) | real coordination and timing; adjust what the source cannot give (S4 finding) |
| big articulated action with no reference | knowledge-guided FK keys + validators (B) | deterministic, checkable |
| repeating locomotion | procedural gait scheduler | parameters scale to N legs, speeds |
| secondary motion (tails, cloth, chains, lanterns) | procedural springs/Verlet, baked | cheap, stable |
| impacts, magic, elements | particles + shaders + short frame sequences | runtime features exist |
| pixel art, effects with changing shapes | frame-by-frame (generated + validated) | rotation blurs pixels |
| AI motion generation (video → motion) | not now | licences (SMPL, SuperAnimal NC), accounts, RAM |
| idle / breathing loops | layered oscillators (breath, sway, secondary springs) | loop seam by construction; cheap |
| transitions and hit reactions | blend from any pose to a reaction key set, return to idle within tolerance | every card unit needs them |
| facing (opponent side) | mirror policy per entity (mirror allowed / mirror forbidden for handed props) | asymmetric weapons and props |

**Reference-selection gate (condition, `director` high):** before a reference is used, the motion spec records a
written acceptance for this request and the result of checking the reference against it: target height of the
contact (e.g. ground vs chest), limb extension at contact, grip type (one/two hands, handed side), start pose
compatible with the entity's idle (or a planned transition), facing, phase durations within the category ratios,
and licence (production-OK, with the CMU acknowledgement line stored). A reference that fails any item is rejected
or explicitly adjusted; the S4 chop-instead-of-smash result is the failure this gate prevents.

**Hybrid adjustment covers timing, not only poses:** after retargeting, phase durations are redistributed to the
action category's ratios (longer anticipation hold, short contact, exaggerated recovery), then a stylisation pass
bounded by the entity's ROM tier; the source's realism never overrides the project's timing or style.

## 6. Reference library strategy

Production-OK only: CMU mocap original data (verified: free for all uses, no resale), CC0 packs (Quaternius,
Kenney), Muybridge plates (US public domain; we store our own traced phase tables, not the images), Smithsonian
Open Access items marked CC0. R&D only: NC datasets (Bandai Namco, LaFAN1, AMASS, SMPL family, SuperAnimal).
Store derived data (motion.v2 keys, phase/duty tables, contact schedules) with the source pointer and licence check
date; never commit raw third-party data. Agents have no web access, so formulas and tables live in kb/ and profiles.
CMU asks for an acknowledgement line in products that use the data; it is stored with each licence check.
**Production-OK sources are human-heavy:** animal mocap is non-commercial or absent, so for creatures the reference
branch will rarely fire and most creature motion falls to knowledge-guided keys and procedural generators
(Muybridge-derived phase tables are the main creature reference). This raises U2-U3 effort (see §9).

## 7. Entity-specific QA architecture

Validators attach to components, so an entity gets exactly the checks of its components minus those its fictional
rules replace. Three tiers (implemented for skeletal entities in `posecheck.py`): **A anatomical/structural**
(hierarchy, lengths, ranges for the chosen tier, bend, flips, reachability), **B physical/biomechanical**
(balance per phase, contacts, weight transfer, sequencing, grip, self-collision, coupling, contact speed),
**C action/artistic** (intent checks for the action category + an explicit review list for `director` on real-time
and slow previews). Planned per family: gait sequence and duty factor (quadruped, multi-legged), support polygon
with ≥3 contacts (insects), wing timing/fold coupling/body response (flying), wave direction and amplitude envelope
(serpentine), area preservation and elastic recovery (soft body), pivot/linkage closure/intersection (mechanical),
loop seam and event sync (magical, hovering). Thresholds are in the profile's characteristic length (reports give
both that and pixels). Physical, fictional and artistic correctness are reported separately; the limit tier in force
is printed in every report.

Universal checks added for a 2D card game (`director` review):

| Check | Class | What |
|---|---|---|
| readability at display size | **hard for key poses (high)** | downscale to the card-slot resolution; key poses must differ in silhouette (difference above a threshold) |
| loop seam | hard | every idle/loop: last frame = first frame within tolerance, no velocity pop at the seam |
| gameplay event sync | hard | the contact frame equals the damage event frame; clip duration inside the profile's timing budget |
| footprint and anchor | hard | motion stays inside the allotted box; the base sits on the card ground line; no drift across a loop |
| transition continuity | hard | idle → action → idle returns within tolerance; no pops at blends |
| draw-order stability | hard | far-limb / prop layer swaps only at declared frames (projection cleanup becomes a validator) |
| mirror safety | soft | handedness of weapons and asymmetric props after mirroring |
| key and bone budget | soft | keys/bones per clip within the runtime budget |
`director` receives a **review card** per preview package: frame numbers to look at, what to compare, the metrics
per frame - because the reviewer cannot open media itself.

**Done and verified today:** 18 automated tests (`tests/test_motion_system.py`): solver tests (rest reproduction,
degrees, local vs global inheritance, isolated elbow sweep without shoulder motion/flips/length change, weapon
transform, IK reachability flag, knee bend under a crouch sweep, left/right mirroring) and 10 regression tests, one
per Board-reported failure. The new validators found a real solver bug (leg IK bend side inverted, rest pose not
reproduced) - fixed; knees now follow the anatomical preferred bend.

## 8. Benchmark suite (12) and spike priorities

| # | Benchmark | Intent | Components | Acceptance (summary) |
|---|---|---|---|---|
| 1 | Humanoid combat + idle | idle loop, light attack, hit reaction (receiver), mirrored facing | skeleton, attachment, interaction_contact | loop seam ≤ 0.002 L; contact frame = damage event; reaction starts ≤ 2 frames after contact; card-scale readability; mirror safety |
| 2 | Heavy humanoid (**current**) | heavy overhead smash | skeleton, attachment, flexible appendage | done: B 17/17 hard, C as reference; hybrid next |
| 3 | Quadruped locomotion | walk → trot → gallop | skeleton, gait, chain (tail) | footfall order exact; duty factor within ±0.05 of the gait table; foot slip ≤ 0.01 L in contact; spine flex/extension phase-locked in gallop |
| 4 | Flying creature | take-off, flap, glide | wing, skeleton, chain | elbow-wrist fold coupling; downstroke/upstroke duration ratio ≤ 0.8; body bob opposite to the wing stroke, amplitude 0.02-0.08 L |
| 5 | Multi-legged | spider skitter | skeleton, gait (8) | ≥ 3 non-collinear supports every frame; tetrapod order exact; no leg crossing |
| 6 | Serpentine / tentacle | slither, strike | chain (wave) | wave travels head → tail; amplitude envelope rising toward the tail; segment length error ≤ 0.001 L |
| 7 | Soft body | slime hop | deformable, ballistic | area within ±10 %; elastic recovery ≤ 12 frames; airborne path fits a parabola (R² ≥ 0.98) |
| 8 | Mechanical | robot arm / door linkage | hinge, linkage | pivot drift 0; linkage closure error ≤ 0.001 L; no part intersection |
| 9 | Rigid object + attachment | lantern carried, sword thrown | attachment, pendulum, ballistic | grip error 0 until detach; detach at the declared frame; pendulum settles ≤ 1.5 s |
| 10 | Magical/abstract | ghost drift, artifact spin | hover, shader, particles | loop seam ≤ 0.002 L; card-scale readability; fictional rules declared |
| 11 | Environmental | foliage, banner, chain | spring, cloth, rope | wind response lag 2-10 frames; no frame-to-frame jitter above 0.002 L |
| 12 | Hybrid | dragon | gait + wing + chain + particles | composition without core changes; gait and wing phase-locked; tail driven by the body (lag 2-8 frames); fire particles start at the declared frame |
Thresholds are starting values in characteristic length L (§3), to be tuned in each spike; every benchmark also
carries the `director` preview list (review card).
Each benchmark records intent, structure, references (with licence), expected behaviour, technical constraints,
artistic criteria, previews (real-time, slow, sheet, trajectories), QA method, automation cost and reusability.

**Spike order (condition, `director` high; do not run all at once):** finish #2 as the hybrid C+B - **a hypothesis
until a hybrid clip exists**, with its own acceptance: B's impact numbers (elbow ≥ 150° interior, contact ≥ 0.8 of
peak speed), C's wind-up coil (COM back ≥ 0.15 L), an idle-to-clip transition, no projection artefacts, and the arm
raised through the front/side (fixing B's soft finding) → **#1 light attack + hit reaction + idle loop** (every card
unit needs idle, attack, hit, death; proves transitions, loops, event sync, card-scale readability and mirroring) →
**#5/#3 gait scheduler** → **#6 chain presets** → **#4 wing** → #12 dragon composes the three. Then #7, #9, #10.

## 9. Implementation roadmap

| Phase | Content | Estimate (Board-operator days, excl. agent time) |
|---|---|---|
| U0 | review of this package + KB by `director`; Board decisions | 1 |
| U1 | heavy humanoid hybrid C+B (gated reference, timing redistribution); Godot adapter for motion.v2 (bake to AnimationPlayer); art pass prerequisites incl. skeleton-overlay-on-art previews; measure baked-key size | 4–6 |
| U1b | benchmark #1: idle loop, light attack, hit reaction, interaction handshake, card-scale readability, mirroring; new universal checks (§7) | 3–5 |
| U2 | gait scheduler + quadruped/spider benchmarks; component validators (creature motion mostly B/procedural: references scarce) | 6–10 |
| U3 | chain presets + wing + dragon composition | 5–8 |
| U4 | soft body, rope/cloth, attachments/throws, magical (particles/shaders) | 6–10 |
| U5 | Agent Skills packaging, pose and motion libraries, regression suite in CI | 3–5 |
Total about 28–45 days, highly uncertain after U2; each phase re-estimates from its spike.

## 10. Agent responsibility proposal

No new agent now (constraint: do not add agents). During R&D the Board operator (Claude Code) builds the tools
(decision D1); `director` reviews motion and KB content (read-only, on previews); `qa-engineer` later runs the
validators in CI; `game-artist` supplies artwork for layered parts/master assets; `gameplay-programmer` owns the Godot
adapter and runtime integration. Decision D7 (a technical artist or animator role) is revisited after U2 with evidence
of how much motion work recurs per project. Skills ([07](07-agent-skills-proposal.md)) extend to: comparative anatomy,
creature motion analysis, animal locomotion, creature rigging, procedural locomotion, physical motion design, object
and mechanical animation, soft body, secondary motion, environmental animation, magical motion design, cross-entity
interaction, entity-specific QA - each with trigger, inputs, knowledge, tools, steps, outputs, failure conditions and
review checklist, packaged only after K4. **Skills first** (`director`): motion-qa (the evidence contract),
animation-reference-research (licence gate), motion-design (with the §5 selection gate), then motion-retargeting and
body-mechanics; creature skills wait until the gait and chain tools exist. Known weakness: the Board operator builds
and first-scores the motion (evaluation bias); mitigated by the validators and by review cards that give `director`
per-frame metrics.

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
| Reference scarcity for non-humans (animal mocap NC or absent) | creature motion falls to B/procedural; more effort | Muybridge-derived tables; procedural gaits; effort raised in U2-U3 |
| Motion-to-art coupling (joint gaps, texture stretch, far-arm reveal) | correct motion looks broken on the real art | skeleton-overlay-on-art previews from U1; art pass rules for overlaps |
| Style drift between reference realism and project art | realistic motion on stylised art | stylisation tier per project; timing redistribution (§5) |
| Reviewer evidence gap (`director` cannot open media) | judgements from numbers only | review cards with per-frame metrics; or a reviewer with preview access (Board decision) |
| Runtime size of baked keys for many units | memory/build size | measure in U1; key reduction per clip |
| Single builder until K4/U5 (know-how in sessions) | bus factor | KB + skills packaged after K4; regression suite in CI |

## 13. Required Board decisions

| # | Decision | Recommendation |
|---|---|---|
| U-A | Adopt this architecture (composition, component registry, entity profiles; human anatomy as one domain), with validator assumption tags | approve (`director`: approve with the tags - applied) |
| U-B | Adopt existing conventions: Godot SkeletonProfileHumanoid names/axes, VRM minimum humanoid, de Leva mass tables, Unreal-style joint settings; no Spine export without a legal check | approve (`director`: naming and mass tables only) |
| U-C | Reference policy: production-OK sources only (CMU original, CC0 packs, Muybridge-derived tables, Smithsonian CC0); NC datasets and SuperAnimal/SMPL R&D-only; Kirin rejected | approve |
| U-D | Spike order: hybrid #2 → **#1 + idle** → gait #5/#3 → chain #6 → wing #4 → dragon #12 (condition) | approve (`director` amendment) |
| U-I | Reference-selection gate (§5) mandatory before any reference is used (condition) | approve (`director` high) |
| U-E | KB content review by `director` (K4) before any skill packaging | approve |
| U-F | Optional dependency review of GDNative-Ropesim (MIT) when the rope spike starts | later |
| U-G | OpenStax: stop using it as a source (CC BY-NC-SA, AI-ingestion clause); keep only facts already cross-checked elsewhere; ask OpenStax/legal if the Board wants it | approve |
| U-H | Functional ROM is informative, not a limit; clinical (realistic) or stylized (stylised) tier gates per character; character overrides must state why; the tier is recorded in the profile and printed in every QA report | approve |
| U-J | Reviewer evidence: review cards with per-frame metrics for `director`, or give a reviewer preview access | review cards now; access is a separate Board decision |
