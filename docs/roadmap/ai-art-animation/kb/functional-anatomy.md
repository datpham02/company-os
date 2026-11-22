# Functional Anatomy for Code-Driven 2D/3D Rigs

> **Status:** `PROPOSED` (functional anatomy, 12 body parts; clinical vs functional vs stylised ranges). Compiled 2026-11-22 by a Claude Code research agent in the studio's own words; every number carries a source id or a status (verified / derived / unverified / heuristic); machine-readable table: [human_joint_table.json](human_joint_table.json). **Licence note:** OpenStax A&P 2e is CC BY-NC-SA 4.0 and forbids AI ingestion without permission - no OpenStax text or figures in studio assets; facts are cross-checked against the other sources (decision U-G). Content review by `director` pending (K4).


Knowledge base for agents that rig and animate humanoid and creature characters from code (skeletons, joints, local rotations, joint limits). Companion data file: `human_joint_table.json` (same folder). Compiled 2026-11-22.

## 0. How to read this document

**Evidence labels.** Every number carries a source id in brackets, for example `[CDC_ROM]`. Source ids are listed in section 15.
- A number with a source id was read by the compiler in that source (sometimes in an abstract only, which is noted).
- **(unverified)** means the number is common textbook or practitioner knowledge that the compiler could not confirm in a source actually read during this research. Treat it as a placeholder to be checked before it becomes a hard limit.
- **(derived)** means arithmetic on sourced numbers (for example 2:1 ratio applied to 180 degrees).
- **(heuristic)** means a studio rule of thumb for animation, not a measurement. All "artistic stylisation allowance" content is heuristic: no source measures what looks believable.

**Three ROM columns.**
- *Clinical ROM*: normative maximum range in healthy adults, usually measured with a goniometer from anatomical position. This is the hard physical ceiling for a realistic human.
- *Functional ROM*: the range actually used to complete everyday (or athletic, where noted) tasks. This is where most animation lives; keyframes should spend most of their time inside it.
- *Artistic stylisation allowance*: how far past (or short of) clinical range a stylised animation can go before it reads as broken.

**Big caveats on the numbers.**
1. Clinical ROM sources disagree, often by 10 to 30 degrees, because of measurement method, active vs passive motion, age, sex and position. The CDC study [CDC_ROM][SOUCIE2011] found that its healthy-adult means differed significantly from the commonly used normative charts in most joints, that ROM declines with age, and that females are more mobile in nearly all joints.
2. Most "shoulder" clinical values are *humerothoracic* (arm relative to trunk), which already includes scapular motion. A rig that has a separate scapula/clavicle bone must split that range (section 3 and 4).
3. Functional ROM studies use different tasks and different angle definitions (for example Gates et al. use plane-of-elevation / elevation / axial-rotation angles rather than flexion and abduction [GATES2016]). Numbers are not perfectly comparable.

**Licence warning (important for the Board).** The brief said OpenStax A&P 2e is CC BY 4.0. The pages actually read state **CC BY-NC-SA 4.0** (non-commercial, share-alike), and also state the book must not be used to train large language models or be ingested into generative AI offerings without OpenStax's prior written permission [OS95][OS115]. This document only paraphrases anatomical facts (facts are not copyrightable) and does not copy OpenStax text or figures. Do not paste OpenStax text or images into studio assets, prompts or training data. Required attribution if OpenStax is cited: "Access for free at https://openstax.org/books/anatomy-and-physiology-2e/pages/1-introduction".

---

## 1. Global conventions for rigs

### 1.1 Anatomical reference frame
- **Anatomical position** (the zero for clinical ROM): standing upright, facing forward, arms at the sides, palms facing forward (forearm supinated), feet flat and pointing forward [OS95].
- **Planes and axes** [OS95]:
  - Sagittal plane (splits left/right). Motion about a mediolateral axis: flexion/extension, dorsiflexion/plantarflexion.
  - Coronal (frontal) plane (splits front/back). Motion about an anteroposterior axis: abduction/adduction, lateral flexion of the spine, radial/ulnar deviation, scapular up/down rotation (approximately).
  - Transverse (horizontal) plane. Motion about the long (vertical) axis: medial/lateral rotation, spinal axial rotation, pronation/supination.
- **Movement vocabulary** (paraphrased from [OS95]): flexion reduces the angle between bones, extension increases it, hyperextension is extension past the normal range; abduction moves away from the midline, adduction toward/across it; circumduction is a cone combining flexion, abduction, extension and adduction; medial/lateral rotation turns the front of a limb toward/away from the midline and occurs only at shoulder and hip; supination turns the palm forward with radius and ulna parallel, pronation turns it back with the radius crossing the ulna; dorsiflexion lifts the top of the foot, plantarflexion points the toes; inversion turns the sole medially and is the larger of the two, eversion laterally; these are intertarsal (mainly subtalar), not ankle, motions; protraction/retraction and elevation/depression apply to scapula and mandible; superior (upward) rotation of the scapula turns the glenoid upward and is required for full arm abduction.

### 1.2 Joint type to DOF map [OS94]
| Synovial type | Axes | Examples | Rig treatment |
|---|---|---|---|
| Pivot | 1 (uniaxial) | atlantoaxial (C1-C2), proximal radioulnar | 1 rotational DOF about the bone's long axis |
| Hinge | 1 | elbow (humeroulnar), knee, ankle (talocrural), finger IP | 1 DOF; in practice the knee adds small axial rotation when flexed [OS96] |
| Condyloid (ellipsoid) | 2 | radiocarpal (wrist), MCP knuckles | 2 DOF, no axial twist |
| Saddle | 2 | thumb CMC, sternoclavicular | 2 DOF (SC joint also has some axial rotation of the clavicle in practice (unverified)) |
| Plane (gliding) | multiaxial by shape but ligament-limited | intercarpal, intertarsal, acromioclavicular, spinal facet (zygapophysial) | usually not individual bones; aggregate into one composite joint |
| Ball-and-socket | 3 | glenohumeral, hip | 3 DOF (swing 2 + twist 1) |

### 1.3 Recommended local coordinate system (all joints)
This is a recommendation for the studio, not an anatomical fact.
- **3D**: bone axis = **+Y** pointing from the joint to the child joint (Blender and Godot `Bone`/`Skeleton3D` convention). **X** = mediolateral axis (flexion/extension axis for sagittal hinges). **Z** = anteroposterior axis (abduction/adduction, lateral flexion). Rotation about **Y** = axial twist (medial/lateral rotation, pronation/supination).
- **Anatomical sign convention stored in data**: every joint limit is stored as *anatomical* angles where the "named" motion is positive: flexion +, abduction +, lateral (external) rotation + for shoulder/hip, supination + for forearm, dorsiflexion + for ankle, inversion + for subtalar, elevation/protraction/upward rotation + for scapula, lateral flexion toward the bone's own side + for spine and neck, axial rotation toward the character's left + for spine and neck. Negative values mean the opposite motion (extension, adduction, medial rotation, pronation, plantarflexion, eversion).
- A per-bone **sign map** converts anatomical angles to engine rotation: `engine_angle = sign(side, facing, axis) * anatomical_angle + rest_offset`. Left and right limbs have opposite signs for abduction and axial rotation. Elbow flexion and knee flexion bend in opposite sagittal directions, so the "flexion is positive" rule needs a per-joint sign.
- **2D** (Godot `Bone2D`, Spine, DragonBones): the bone axis is local **+X** from joint to child; the only rotation is about the screen normal. Store one anatomical angle per bone plus metadata: which anatomical motion the screen rotation represents for the current view (see section 14), the facing direction (`+1` right, `-1` left), and the side (`L`/`R`). Flipping a character by negative X scale reverses the screen-angle sign, so limits must be re-signed on flip.
- **Rest pose vs zero pose**: bind the rig in a relaxed-neutral rest pose (1.4), but measure limits from anatomical position. Store `rest_offset` per bone so a validator can convert.

### 1.4 Anatomical position vs relaxed standing neutral
| Region | Anatomical position (ROM zero) | Relaxed standing neutral (good rest pose) |
|---|---|---|
| Head/neck | eyes level, neck neutral | same; small forward head carriage common (unverified) |
| Spine | upright | normal curves: cervical and lumbar lordosis, thoracic kyphosis (not covered by sources read; unverified) |
| Scapula | resting on ribcage | same; slightly protracted in many people (unverified) |
| Shoulder | arm at side, palm forward | arm at side, humerus slightly medially rotated so palm faces thigh (unverified) |
| Elbow | fully extended (0) | slight flexion, roughly 10-20 degrees (unverified) |
| Forearm | fully supinated (palm forward) | mid-position / semi-pronated, thumb forward (unverified) |
| Wrist/hand | neutral, fingers extended | slight wrist extension, fingers loosely flexed in a cascade increasing toward the little finger (unverified) |
| Pelvis | neutral | same; slight anterior tilt common (unverified) |
| Hip | 0 | 0; hip extension is ligament-limited near vertical, so standing needs little muscle effort [OS96] |
| Knee | 0 (full extension) | 0 to slight flexion; extended knee is the close-packed position [OUHSC_KNEE] |
| Ankle | 0 (foot at 90 degrees to leg) | 0; feet slightly toed-out (unverified) |

Clinical ROM is measured from anatomical position. A rig bound at relaxed neutral must add the rest offsets before checking limits (for example a forearm bound semi-pronated is already at roughly -80 to -90 degrees of the 0-to-supinated scale: (unverified)).

---

## 2. Head and neck

- **Anatomical structure**: skull on 7 cervical vertebrae. Atlanto-occipital joint (occipital condyles on C1) rocks for nodding; atlantoaxial joint (C1 on C2) has a pivot around the dens for head turning; C2-C7 are linked by plane facet joints and intervertebral discs [OS96].
- **Joint type**: C0-C1 condylar rocking joint (OS does not formally classify it); C1-C2 pivot [OS94][OS96]; subaxial facets plane joints.
- **Degrees of freedom**: 3 for the whole neck (flexion/extension, lateral flexion, axial rotation). The cervical region has the greatest spinal range in all directions [OS96].
- **Rotation axes**: flexion/extension about mediolateral axis (sagittal plane); lateral flexion about AP axis (coronal); rotation about the vertical neck axis (transverse).
- **Rig local coordinate system**: 2 to 3 bones recommended: `neck_lower` (C3-C7), `neck_upper` (C1-C2), `head` (C0-C1). Y along neck toward skull; X flexion axis; positive X = flexion (chin toward chest). Put most axial rotation on `neck_upper` (see coupling) and most nodding on `head`.
- **Neutral pose**: anatomical: eyes level. Relaxed: same, often slight forward head (unverified).
- **Movement definitions**: flexion = chin toward chest; extension = head back; lateral flexion = ear toward shoulder; rotation = turn to look over the shoulder [OS95].
- **Valid movement directions**: all three; combinations (look up and over shoulder) are valid.
- **Range of motion**
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion | 0-60 [LUTT] (other charts list about 45: unverified) | 0-40 looking down at hands/feet (unverified) | up to ~70 for cartoon "slump"; past that the chin sinks into the chest and reads as a broken neck |
| Extension | 0-75 [LUTT] | 0-40 looking up (unverified) | ~80; beyond that the skull appears to slide off the spine |
| Lateral flexion (each side) | 0-45 [LUTT] | 0-20 (unverified) | ~50 for tilts of curiosity; more reads as injury |
| Rotation (each side) | 0-80 [LUTT] | 0-60 shoulder check (unverified) | ~90 in toon; beyond 90 without shoulder/torso help reads as "owl" (acceptable only for creatures/gags) |
- **Parent-child**: parent = upper thoracic spine (`chest`); child = head; head is parent of jaw, eyes, ears.
- **Coupled movements**:
  - Roughly half (some studies more) of cervical axial rotation happens at C1-C2, with C0-C1 contributing mainly flexion/extension (search-snippet only; unverified). Rig rule: put about 50% of head yaw on the upper neck bone.
  - In the subaxial cervical spine lateral bending and axial rotation are coupled toward the same side [LIEBSCH2025] (in vitro meta-analysis). Rig rule: when the head tilts sideways, add a small same-side yaw, and vice versa.
  - Head turns usually lead and are followed by eyes first, then head, then torso for big turns (heuristic).
- **Functional movements**: look-at (aim), balance correction in landing, nodding speech beats, head lead in a throw or swing (head stays stable while body rotates under it).
- **Common animation errors**: all rotation in a single neck joint (rubber hinge at the skull base); head yaw > 90 with no chest rotation; neck that stays rigid while the chest bends (head ends up looking at the floor in a run); head not counter-rotating to keep eyes level during walks; lateral tilt without the small coupled yaw.
- **Context-dependent constraints**: during landing or impact, the head lags then recovers (overlap), but the neck should not exceed functional flexion on a normal landing; when aiming or reading, the head is stabilised relative to the world, not the torso.
- **Validation methods**: per-axis limits on the summed neck chain; ratio check that no single neck bone holds more than about 60-70% of total neck rotation in a pose (heuristic); eye-line check (world pitch of the head within plus/minus 15 degrees during locomotion unless intentionally looking: heuristic).
- **Character exceptions**: heavy/muscular builds (large trapezius, thick neck) lose visible extension and lateral flexion by soft-tissue contact; children have proportionally larger heads, so the same angle moves the centre of mass more; owls and some birds rotate far beyond human limits (creature profile); long-necked creatures need many segments with distributed bend.

---

## 3. Spine and torso (thoracic + lumbar)

- **Anatomical structure**: 12 thoracic and 5 lumbar vertebrae joined by intervertebral discs and plane facet joints. Thoracic motion is greatly restricted by the ribcage and overlapping spinous processes; the lumbar region allows considerable flexion, extension and lateral flexion but largely blocks axial rotation [OS96].
- **Joint type**: chain of plane facet joints plus cartilaginous disc joints [OS94][OS96].
- **DOF**: 3 per region, small per segment.
- **Rotation axes**: sagittal flex/ext, coronal lateral flexion, transverse axial rotation.
- **Rig local coordinate system**: minimum 3 bones (`spine_lumbar`, `spine_lower_thoracic`, `chest`), better 4-5. Y up the spine. Positive X = flexion (forward bend). Distribute: flexion/extension mostly lumbar; axial rotation mostly thoracic (because lumbar rotation is largely prevented [OS96]); lateral flexion spread across all.
- **Neutral pose**: anatomical: upright with normal curves. Relaxed: same; slouch adds thoracic flexion.
- **Movement definitions**: flexion = forward bend; extension = backward bend; lateral flexion = side bend; rotation = twist [OS95].
- **Range of motion** (thoracolumbar combined, relative to pelvis)
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion | 0-50 [LUTT lists 45-50]; Esola measured mean lumbar contribution 41.6 during a 111-degree total forward bend [ESOLA1996] | ADLs needed up to 59 total trunk flexion-extension excursion [GATES2016] | large; squash-and-stretch on the torso is the most forgiving region if volume is preserved |
| Extension | 0-25 [LUTT] | 0-15 (unverified) | ~35; more makes the character look broken backward unless it is a dramatic arch with the hips forward |
| Lateral flexion (each side) | 0-25 [LUTT] | 0-23 trunk lean across ADLs [GATES2016] | ~40 for toon |
| Rotation (each side) | 0-30 [LUTT] | 0-32 trunk axial rotation across ADLs [GATES2016] (likely includes some pelvis motion) | ~45 total chest vs pelvis for wind-ups; beyond that reads as a twisted rag |
- **Parent-child**: parent = pelvis (`hips`, usually the root or child of root); children: neck chain, both clavicles.
- **Coupled movements**:
  - **Lumbopelvic rhythm** [ESOLA1996]: in forward bending the lumbar spine leads early and the hips dominate late. Mean lumbar-to-hip ratios were 1.9 (0-30 degrees of bend), 0.9 (30-60), 0.4 (60-90). Total 111 = 41.6 lumbar + 69.4 hip. Rig rule: for a trunk-bend target T, distribute using these phase ratios; never achieve a deep bend with spine alone.
  - Spinal lateral bending and axial rotation are coupled [LIEBSCH2025]; the abstract read confirms strong coupling but gives a clear same-side direction only for the cervical spine. Lumbar coupling direction varies between studies (unverified); do not hard-code a lumbar coupling direction.
  - Counter-rotation of chest vs pelvis in walking and running (chest turns opposite the pelvis): standard animation knowledge (unverified magnitude).
- **Functional movements**: lift (hinge at hips with spine fairly neutral; spine flexion increases with fatigue/poor technique), throw and swing (pelvis rotates first, then chest: kinetic chain, heuristic/unverified), crouch (spine flexes while hips flex), reach (spine contributes once arm reach is exhausted), push/pull (spine braced, near neutral).
- **Common animation errors**: whole bend at one vertebra (V-shaped kink); spine bending while pelvis stays locked (no lumbopelvic rhythm); twist done only at the waist; chest translating instead of rotating; lumbar rotation exceeding thoracic.
- **Context-dependent constraints**: under heavy load (lift, landing), keep lumbar flexion small and take motion at hips and knees; in a throw, chest rotation peaks after pelvis rotation.
- **Validation methods**: (1) summed chain limits; (2) curvature distribution: max share of total bend in any one spine bone below about 50% (heuristic); (3) lumbopelvic check during bends: pelvis (hip) contribution at least 0.4 x lumbar early and dominant past 60 degrees of trunk flexion [ESOLA1996]; (4) axial rotation share: thoracic bones should carry more than lumbar [OS96].
- **Character exceptions**: muscular/heavy builds lose flexion and lateral flexion to soft-tissue contact (belly, chest); elderly characters: reduced ROM [CDC_ROM: ROM declines with age]; children more flexible; quadrupeds use the spine for locomotion (galloping flexion/extension) and serpentine creatures are spine-only rigs with per-segment limits.

---

## 4. Scapula and shoulder girdle

- **Anatomical structure**: clavicle (strut from sternum to acromion) and scapula (on the back of the ribcage). Joints: sternoclavicular (saddle) [OS94], acromioclavicular (plane) [OS94], and the scapulothoracic "joint" (scapula gliding on ribcage, muscular rather than true synovial).
- **Joint type**: compound: saddle + plane + scapulothoracic glide.
- **DOF**: functionally elevation/depression, protraction/retraction, upward/downward rotation, plus tilts. Muscles [OS115]: trapezius elevates (shrug), retracts and depresses; rhomboids retract and rotate downward (inferiorly); serratus anterior protracts; pectoralis minor depresses and tilts anteriorly. (OS 11.5 does not name upward rotators; trapezius plus serratus anterior is standard knowledge: unverified.)
- **Rotation axes**: elevation/depression approx. about an AP axis at the SC joint (clavicle tip rises); protraction/retraction about a vertical axis at the SC joint; upward rotation about an axis perpendicular to the scapular blade, located below the scapular spine [OS95].
- **Rig local coordinate system**: one `clavicle` bone per side, from sternal end to acromion, Y along the clavicle. Positive Z (in the clavicle frame) = elevation; positive rotation about the vertical = protraction. Upward rotation of the scapula is approximated by clavicle elevation plus a twist; a separate `scapula` bone or corrective shape is needed for visible shoulder-blade motion. In 2D side views the clavicle bone is mostly elevation (moves the shoulder point up) and protraction (moves it forward).
- **Neutral pose**: scapula resting flat; slight protraction common in relaxed posture (unverified).
- **Movements**: elevation, depression, protraction, retraction, upward (superior) rotation, downward (inferior) rotation [OS95].
- **Range of motion**
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Upward rotation (scapula) | ~60 over full arm elevation (derived from the 2:1 rule [INMAN_via_OUHSC]); with a 2.3:1 ratio [BRAMAN2009] about 50 (derived) | ~33 for 108 degrees of humeral elevation used in ADLs [GATES2016 + BRAMAN2009, derived] | must not be 0 when arms go overhead |
| Elevation (clavicle angle) | ~0-45 (unverified) | 0-20 (unverified) | shrugs can be exaggerated heavily in toon |
| Depression | ~0-10 (unverified) | 0-5 (unverified) | small |
| Protraction / retraction (clavicle yaw) | ~0-30 each (unverified) | 0-20 (unverified) | protraction on punches/reaches can be pushed |
| Posterior tilt | increases progressively to max elevation [BRAMAN2009]; magnitude not read | | |
- **Parent-child**: parent = `chest`; child = upper arm (`upperarm`/humerus).
- **Coupled movements**:
  - **Scapulohumeral rhythm**: overall about 2 degrees of glenohumeral motion per 1 degree of scapular upward rotation [INMAN_via_OUHSC]; the first ~30 degrees of elevation is a "setting phase" that is mostly glenohumeral [OUHSC_SCAP]. In vivo bone-pin data: ratio 2.3 raising and 2.7 lowering; the scapula rotates upward about 0.43 degrees per degree of glenohumeral elevation when raising; scapular posterior tilt increases to max elevation; the scapula rotates internally up to about 125 degrees glenohumeral elevation and externally beyond [BRAMAN2009]. Ratios vary between people and are non-linear (search-level synthesis; McClure 1.7:1 and child 1.3:1 figures not read: unverified).
  - Protraction accompanies forward reach and punches (serratus anterior moves the arm from the side to the front [OS115]).
- **Functional movements**: reach (protraction), overhead reach/throw (upward rotation + elevation), push (protraction), pull/row (retraction), carry (depression/stabilisation), shrug (elevation).
- **Common animation errors**: shoulder that does not rise when the arm goes overhead (no scapular upward rotation/elevation); shoulder point that stays fixed during punches (no protraction); clavicle elevating instead of the scapula rotating so the shoulder hits the ear; asymmetric shoulder line from carrying with no matching trunk lean.
- **Context-dependent constraints**: carrying heavy loads depresses the girdle; aiming a weapon locks the scapula as a stable base (small motion).
- **Validation methods**: when humerothoracic elevation E > 30 degrees, require scapular upward rotation >= (E - 30) / 3.5 and <= (E - 30) / 1.5 (heuristic band built around the 2:1 to 2.7:1 data [INMAN_via_OUHSC][BRAMAN2009]); check that clavicle elevation is non-zero when the hand is above the head.
- **Character exceptions**: heavy trapezius/deltoid builds hide scapular motion but still need the shoulder point to lift; quadrupeds: the scapula is the main limb segment for stride (no clavicle in many mammals: unverified); birds/flying creatures need a separate wing girdle profile.

---

## 5. Shoulder (glenohumeral joint) and humerothoracic arm motion

- **Anatomical structure**: humeral head in the shallow glenoid cavity of the scapula, deepened by the glenoid labrum; loose capsule; stability comes mainly from the rotator cuff (supraspinatus, infraspinatus, teres minor, subscapularis). It has the largest ROM in the body, at the cost of stability; most dislocations are inferior [OS96].
- **Joint type**: ball-and-socket [OS94].
- **DOF**: 3: flexion/extension, abduction/adduction, medial/lateral rotation; circumduction combines them [OS95].
- **Rotation axes**: flexion about mediolateral axis; abduction about AP axis; rotation about humeral long axis [OS95].
- **Muscles (for intent)**: deltoid main abductor, also flexes, extends, rotates; supraspinatus abducts; infraspinatus and teres minor laterally rotate; subscapularis medially rotates; pectoralis major brings arms together and up; latissimus dorsi pulls arm back and down; teres major extends, adducts, medially rotates [OS115].
- **Rig local coordinate system**: Y along humerus to the elbow; X = flexion axis; Z = abduction axis; Y twist = rotation. Use swing-twist decomposition and limit the swing as a cone (or spherical polygon), not as independent Euler limits, because Euler X/Z limits create gimbal artefacts near 90 degrees abduction.
- **Neutral pose**: anatomical: arm at side, palm forward (externally rotated relative to relaxed). Relaxed: palm faces thigh.
- **Range of motion** (humerothoracic, i.e. includes scapular contribution unless noted)
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion (forward raise) | 0-170: CDC means 168.8 M / 172.0 F age 20-44 [CDC_ROM]; LUTT 180 | 0-121 average needed for 10 ADL tasks [NAMDARI2012]; humeral elevation 0-108 across 8 ADLs [GATES2016] | to ~180 with scapula/torso help; beyond reads as dislocated |
| Extension (backward) | 0-50 [LUTT] | 0-46 [NAMDARI2012] | ~60 |
| Abduction | 0-180 [LUTT] | 0-128 [NAMDARI2012] | ~180 with clear clavicle lift |
| Adduction / cross-body | 0-50 [LUTT]; cross-body (horizontal) adduction is a different measure | cross-body adduction 116 [NAMDARI2012] | |
| Lateral (external) rotation | 0-90 at 90 abduction [LUTT] | 0-59 at 90 abduction [NAMDARI2012]; 55 [GATES2016] | throwers' cocking can be pushed to ~110 (unverified for real athletes) |
| Medial (internal) rotation | 0-90 at 90 abduction [LUTT] | 79 for hand-to-back-pocket [GATES2016]; 102 arm-at-side measure [NAMDARI2012] (different position, exceeds the abducted clinical value) | |
| Glenohumeral-only elevation | ~120 of the 180 total (derived from 2:1) | | |
- **Parent-child**: parent = clavicle/scapula; child = upper arm segment / elbow.
- **Coupled movements**: scapulohumeral rhythm (section 4); arm elevation above roughly 90-120 degrees in abduction needs lateral rotation of the humerus to clear the greater tubercle (standard kinesiology, unverified in sources read); trunk lateral flexion to the opposite side extends overhead reach (heuristic).
- **Functional movements**: reach (flexion + protraction), lift (flexion with elbow flexion), push (flexion + protraction, elbow extending), pull (extension + retraction, elbow flexing), throw (abduction ~90 + extreme lateral rotation then fast medial rotation: unverified magnitudes), swing (horizontal adduction across the body), climb/hang (full elevation).
- **Common animation errors**: arm raised overhead with no shoulder rise; arm passing through the torso on cross-body moves; Euler flips (candy-wrapper twist at the shoulder) at ~90 degrees abduction; internal rotation done as forearm twist; "T-pose arms" collapsing deltoid volume.
- **Context-dependent constraints**: under load overhead the arm stays near the scapular plane (between flexion and abduction) (unverified); during falls/landings arms abduct and extend for balance but keep elbows soft.
- **Validation methods**: cone limit on swing (max ~180 forward/up, ~50 back, ~50 across); twist limit as a function of swing direction; rhythm coupling check with the scapula; mesh/collision check between humerus capsule and torso capsule.
- **Character exceptions**: very muscular builds (big deltoids, lats, pecs) cannot fully adduct or reach full abduction without contact; reduce limits by soft-tissue collision instead of a fixed number; stylised characters with noodle arms may ignore cone limits but should keep the rise of the shoulder point; children are more mobile; quadrupeds: shoulder is mostly sagittal swing.

---

## 6. Upper arm (humerus segment)

- **Anatomical structure**: single long bone from glenohumeral joint to elbow. It carries the biceps (elbow flexor and supinator), brachialis, triceps (elbow extensor) and coracobrachialis (flexes and adducts the arm) [OS115].
- **Joint type**: not a joint; this is the segment between shoulder and elbow. Its axial twist belongs to the shoulder's rotation DOF.
- **DOF**: 0 own; inherits 3 from the shoulder. Optional *twist bones* (upper-arm roll) distribute shoulder rotation along the segment for deformation.
- **Rotation axes**: long axis (twist) is the important one for skinning.
- **Rig local coordinate system**: Y along the humerus. Elbow flexion axis must be perpendicular to Y and aligned with the anatomical elbow hinge; when the shoulder twists, the elbow hinge axis twists with it (this is how the arm "points" the forearm).
- **Neutral pose**: hangs vertical; relaxed slight medial rotation (unverified).
- **Movements**: none independent; rotation via shoulder.
- **Range of motion**: as shoulder rotation. Twist-bone distribution: commonly 50% at the mid-humerus (heuristic).
- **Artistic allowance**: bone length must not stretch except in explicit squash-and-stretch styles; even then preserve visual volume (heuristic).
- **Parent-child**: parent = shoulder joint; child = elbow/forearm.
- **Coupled movements**: carrying angle: in anatomical position the forearm angles outward from the humerus by roughly 5-15 degrees (unverified; not in sources read). Model it as a fixed rest offset of the elbow hinge axis, not as an extra DOF.
- **Functional movements**: transmits push/pull/lift; orients the elbow hinge.
- **Common errors**: candy-wrapper collapse from twisting the shoulder without twist bones; elbow hinge axis not following humeral rotation (elbow bends sideways); length change between frames.
- **Context constraints**: none beyond shoulder and elbow.
- **Validation**: bone-length invariance per frame (tolerance 0 for rigid rigs, configurable for stretchy rigs); twist-bone share check.
- **Character exceptions**: muscular arms collide with the torso earlier (lats/pecs); toon arms may be rubber hoses (no hinge) by design: use a curve-based limb profile instead.

---

## 7. Elbow (humeroulnar + humeroradial)

- **Anatomical structure**: humerus, ulna and radius in one capsule: humeroulnar (trochlea in trochlear notch), humeroradial, and proximal radioulnar joints. Ulnar (medial) collateral ligament, strongest anteriorly, resists hyperextension; radial collateral ligament blends with the annular ligament; side-to-side motion and hyperextension are resisted [OS96].
- **Joint type**: hinge (humeroulnar) [OS94][OS96].
- **DOF**: 1 (flexion/extension). Pronation/supination is a separate joint (section 8).
- **Rotation axes**: mediolateral hinge axis through the distal humerus.
- **Rig local coordinate system**: Y along forearm; X hinge axis; positive = flexion. Hard-lock Z and Y at the elbow joint (forearm twist goes to section 8 bones).
- **Neutral pose**: anatomical 0 (straight); relaxed ~10-20 flexion (unverified).
- **Movement definitions**: flexion brings forearm toward upper arm (biceps, brachialis, brachioradialis); extension straightens (triceps, anconeus) [OS115].
- **Range of motion** (signed: negative = hyperextension)
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion | 0-145: CDC means 144.6 M / 150.0 F age 20-44 [CDC_ROM]; LUTT 140 | 30-130 (100-degree arc) [MORREY1981, via JBJS commentary]; drinking needed 121, box-to-head-height 120 [GATES2016] | to ~155 in toon if the forearm mesh compresses visibly into the biceps |
| Extension / hyperextension | 0 to about 1 (M) and 5 (F) degrees beyond straight: CDC "extension" means 0.8 M / 4.7 F [CDC_ROM] (interpreted as hyperextension; the page does not define the sign) | rarely past 0 in tasks; some tasks (reaching a desk phone) needed more extension than the 30-degree Morrey limit [MORREY1981 commentary] | never visibly bend backward; allow at most ~5 hyperextension on female/flexible characters |
- **Parent-child**: parent = upper arm; child = forearm (radius/ulna) and through it the wrist.
- **Coupled movements**: none mechanical; biceps flexion also supinates [OS115], so strong lifts with palm up read correctly with slight supination.
- **Functional movements**: reach (extension to 0-30), lift (flexion under load), push (extension), pull (flexion), throw/punch (fast extension then decelerate before lock), hammer swing.
- **Common animation errors**: hyperextended elbow (bends backward); elbow pops straight then bends again in one frame on IK targets near max reach ("IK snap"); elbow bending sideways (hinge axis not orthogonal); arm too straight on punches (reads robotic).
- **Context-dependent constraints**: at impact (punch, push, catch), the elbow should be nearly straight but not locked: keep ~5-15 degrees flexion (heuristic); IK should soft-limit reach at ~97-99% of chain length to avoid snapping (heuristic).
- **Validation methods**: hinge axis check (no Y/Z rotation at elbow); angle within [-hyperext_allow, max_flex]; IK reach ratio <= 0.99 unless intended lock; detect sign flip between consecutive frames (bend direction inverted).
- **Character exceptions**: muscular arms stop flexion earlier by biceps-forearm contact (soft-tissue limit, use collision); hypermobile/young characters may show slight hyperextension; toon "noodle arm" rigs may bend anywhere along the arm by design; insects/creatures can have reversed or multi-hinge limbs (creature profile).

---

## 8. Forearm (radioulnar joints)

- **Anatomical structure**: radius rotates around the ulna at the proximal radioulnar joint (pivot, radial head held by the annular ligament) and the distal radioulnar joint [OS94][OS96]. In supination the bones are parallel; in pronation the radius crosses the ulna [OS95]. Pronator teres and pronator quadratus pronate; supinator and biceps supinate [OS115].
- **Joint type**: pivot [OS94].
- **DOF**: 1 (pronation/supination).
- **Rotation axes**: an oblique long axis from radial head to ulnar head (approximately the forearm long axis).
- **Rig local coordinate system**: Y along forearm; twist about Y; positive = supination. Use 1-2 forearm twist bones; drive most of the twist near the wrist (radius rotates distally) (heuristic).
- **Neutral pose**: anatomical = full supination (palm forward). Relaxed = mid/semi-pronated (thumb forward) (unverified). Choose "mid-position = 0" for the rig and store a rest offset to anatomical.
- **Range of motion** (from mid-position, thumb up)
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Pronation | 0-80: CDC means 76.9 M / 82.0 F [CDC_ROM]; LUTT 80 | 0-50 [MORREY1981]; ADLs peaked at only 13 pronation in Gates' set [GATES2016]; computer work needs more [MORREY1981 commentary] | to ~90; beyond, the forearm reads as twisted like a towel |
| Supination | 0-85: CDC means 85.0 M / 90.6 F [CDC_ROM]; LUTT 80 | 0-50 [MORREY1981]; 53 for perineal care [GATES2016] | ~90 |
- **Parent-child**: parent = elbow/upper arm; child = wrist/hand.
- **Coupled movements**: **forearm rotation with shoulder rotation**: when the elbow is straight, extra apparent hand rotation comes from humeral rotation, so total hand roll can exceed 180 degrees (shoulder + forearm) (standard kinesiology, unverified number). Validators must separate the two. Supination is strongest with the elbow flexed (biceps) (unverified).
- **Functional movements**: turning a key/doorknob, using a screwdriver, pouring, palm-up carry, palm-down typing, punch (pronates toward impact; heuristic).
- **Common animation errors**: twist applied at the wrist joint (wrist "breaks" as a corkscrew); twist applied at the elbow (whole forearm rotates rigidly, skin tears near elbow); exceeding 180 total from forearm alone.
- **Context constraints**: under heavy grip load, rotation range narrows (unverified).
- **Validation**: twist limit per forearm chain; wrist joint must carry no twist; total hand roll = shoulder rotation + forearm rotation, each checked against its own limit.
- **Character exceptions**: chunky/stylised forearms can hide twist; claws/paws on quadrupeds: forearm often locked in pronation (unverified for specific species).

---

## 9. Wrist and hand

- **Anatomical structure**: radiocarpal joint (condyloid) plus midcarpal and intercarpal plane joints; MCP knuckles condyloid; finger interphalangeal joints hinge; thumb CMC saddle allowing opposition [OS94][OS95]. Wrist and finger flexors sit on the anterior forearm, extensors on the posterior forearm; intrinsic hand muscles in thenar, hypothenar and intermediate groups [OS115].
- **Joint type**: wrist = condyloid (biaxial) [OS94].
- **DOF**: wrist 2 (flexion/extension, radial/ulnar deviation); no own axial rotation (that comes from the forearm). Fingers: MCP 2, PIP and DIP 1 each. Thumb CMC 2 (+ opposition as a combined motion); thumb abduction can reach 90 degrees from the palm [OS95].
- **Rotation axes**: flexion/extension about the radioulnar (mediolateral in anatomical position) axis; deviation about the dorsopalmar axis.
- **Rig local coordinate system**: `hand` Y along the third metacarpal; X = flexion axis (positive = palmar flexion); Z = deviation (positive = radial deviation for each side after sign map).
- **Neutral pose**: anatomical: straight. Relaxed: slight extension, fingers in a cascade of flexion (unverified).
- **Range of motion**
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion (palmar) | 0-60 [LUTT] (other charts list up to ~80-90: unverified) | max used in daily tasks 54; 70% of max (about 40) suffices for most tasks [RYU1991]; 38 in Gates' ADLs [GATES2016] | ~80 |
| Extension (dorsal) | 0-60 [LUTT] | max used 60; ~40 sufficient for most tasks [RYU1991]; 40 [GATES2016] | ~80 for push-off poses; beyond reads broken |
| Radial deviation | 0-20 [LUTT] | 17 [RYU1991]; 28 [GATES2016] | ~25 |
| Ulnar deviation | 0-30 [LUTT] | 40 [RYU1991]; 38 [GATES2016] (functional exceeds the LUTT clinical value, so LUTT is conservative here) | ~45 |
| Thumb abduction | to 90 from palm [OS95] | | |
- **Parent-child**: parent = forearm; child = metacarpals and finger chains.
- **Coupled movements**: **dart-thrower's motion** (extension with radial deviation to flexion with ulnar deviation) is the natural functional path (unverified in sources read). Gripping is strongest with the wrist slightly extended; flexing the wrist slackens finger grip (tenodesis effect: unverified in sources read). Forearm rotation, not the wrist, turns the palm.
- **Functional movements**: grip (wrist slightly extended, fingers flex), pinch (thumb opposition [OS95]), push (wrist extended under load), throw release (wrist flexion snap), swing (ulnar deviation at club/bat release: unverified), catching (wrist extended, fingers spread), landing on hands (extended wrist, high-risk).
- **Common animation errors**: "broken wrist" (sharp flexion or deviation kink where the hand is an extension of an aim line); wrist used for palm rotation (twist); wrist staying rigid during overlap (hand does not drag in swings); fingers fully straight at rest; all fingers curling identically.
- **Context constraints**: weight-bearing on hands requires extension near the clinical limit (unverified ~70-90); holding a sword or tool: ulnar deviation set to align the tool.
- **Validation**: 2D-ellipse limit on (flex, deviation) rather than independent box limits (corners of the box are not reachable: heuristic); no wrist twist; finger cascade monotonic from index to little finger in relaxed hands (heuristic).
- **Character exceptions**: mitten/toon hands (3-4 fingers) keep the same wrist limits; heavy builds unaffected; children have greater wrist ROM (unverified); creature claws and paws need their own digit profiles.

---

## 10. Pelvis

- **Anatomical structure**: two hip bones and the sacrum forming a ring; the sacroiliac joints allow very little motion. OS describes the pelvis as built to stabilise and support the body [OS116].
- **Joint type**: effectively rigid for rigs (SI joints negligible); the pelvis moves as a unit on the hips and lumbar spine.
- **DOF**: 6 as the rig root's child (translation + 3 rotations): anterior/posterior tilt (sagittal), obliquity/hip hike (coronal), rotation (transverse).
- **Rotation axes**: tilt about the bi-hip mediolateral axis; obliquity about AP axis; rotation about vertical axis.
- **Rig local coordinate system**: `hips` bone at the pelvis centre (between hip joints, around S1); Y up toward the lumbar spine; positive X = anterior tilt; positive Z = left side up (hike); positive Y = rotation to the left.
- **Neutral pose**: anatomical: neutral; relaxed: slight anterior tilt (unverified).
- **Range of motion** (relative to world or to the femurs)
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Anterior/posterior tilt | coupled to hip flexion/extension and lumbar extension/flexion; no normative value read (unverified) | in forward bends the hips (pelvis on femurs) contribute 69.4 of a 111 total [ESOLA1996] | |
| Obliquity in walking | not read (unverified ~5 each side) | | exaggerate in stylised walks (hip sway), keep opposite to shoulder tilt |
| Rotation in walking | not read (unverified ~5-10 each side) | | exaggerate in runs and swagger |
- **Parent-child**: parent = root (ground projection) or COG control; children: lumbar spine and both femurs.
- **Coupled movements**: lumbopelvic rhythm [ESOLA1996]; pelvis vs chest counter-rotation in gait (unverified); pelvic drop on the swing side in gait resisted by gluteus medius of the stance leg (standard; OS 11.6 does not state the pelvic stabilisation role [OS116]).
- **Functional movements**: walk/run (rotation, obliquity, vertical bob), crouch (posterior tilt late in deep squats: unverified), lift (anterior tilt, hip hinge), throw/swing (pelvis leads rotation).
- **Common animation errors**: pelvis locked during walks (stiff "robot" hips); pelvis floating with feet sliding; hip hike on the wrong side; centre of mass outside base of support in a static pose.
- **Context constraints**: during landing the pelvis drops vertically while hips and knees flex; pelvis height must be consistent with leg length (feet cannot leave the ground unintentionally).
- **Validation**: balance check: projected COM within the support polygon for static/held frames (heuristic); leg length check (pelvis-to-ankle distance <= leg length); foot-skate check.
- **Character exceptions**: wide-hip or heavy builds show more lateral sway; quadrupeds: pelvis is the hind-limb girdle, its tilt drives hind-leg reach.

---

## 11. Hip

- **Anatomical structure**: femoral head in the acetabulum, deepened by the acetabular labrum; iliofemoral, pubofemoral and ischiofemoral ligaments tighten in extension, so there is little extension beyond vertical and upright standing needs little muscle work; ligamentum teres is normally slack [OS96]. More restricted than the shoulder for weight-bearing stability [OS96]. Iliopsoas flexes; gluteus maximus extends; gluteus medius abducts; adductors adduct; deep lateral rotators turn the thigh outward [OS116] (OS 11.6 lists gluteus minimus confusingly; it is normally an abductor (unverified in OS)).
- **Joint type**: ball-and-socket [OS94].
- **DOF**: 3.
- **Rotation axes**: flexion mediolateral, abduction AP, rotation along the femoral mechanical axis.
- **Rig local coordinate system**: Y along femur to knee; X flexion axis (positive = flexion, thigh forward); Z abduction; Y twist rotation (positive = lateral rotation, sign-mapped per side). Use swing-twist cone limits as for the shoulder.
- **Neutral pose**: 0 in standing.
- **Range of motion**
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion | 0-130: CDC means 130.4 M / 133.8 F [CDC_ROM] (passive; LUTT lists 100, probably measured knee-straight) | up to 101 mean max (crouching with trunk rotation) in 22 ADLs [HYODO2017]; ~30 at heel contact in walking [WIKI_GAIT]; heels-flat squat ~95 [HEMMERICH2006, abstract not read: unverified] | ~140 for high kicks only with pelvis posterior tilt and lumbar flexion |
| Extension | 0-18: CDC means 17.4 M / 18.1 F [CDC_ROM]; LUTT 30 | 10-15 just before toe-off in walking [WIKI_GAIT] | ~25; beyond, the lumbar spine must arch (show it) |
| Abduction | 0-40 [LUTT] | 0-20 (unverified) | splits/high side kicks need trained flexibility profile |
| Adduction | 0-20 [LUTT] | 17 putting on shoes [HYODO2017] | |
| Lateral rotation | 0-50 [LUTT] | 0-20 (unverified) | |
| Medial rotation | 0-40 [LUTT] | 0-20 (unverified) | |
- **Parent-child**: parent = pelvis; child = thigh/knee.
- **Coupled movements**: lumbopelvic rhythm (hip dominates the late phase of forward bending [ESOLA1996]); two-joint muscles couple hip and knee: hamstrings extend the hip and flex the knee, rectus femoris flexes the hip and extends the knee [OS116, inferred from listed actions], so maximum hip flexion with a straight knee is limited by hamstrings (the LUTT 100 vs CDC 130 gap is consistent with this, interpretation unverified).
- **Functional movements**: step/walk (~30 flexion to ~10 extension [WIKI_GAIT]), stairs, crouch (deep flexion), lift (hip hinge), kick (flexion + knee extension), land (flexion absorbs), lunge.
- **Common animation errors**: high kick with no pelvis tilt; thigh passing through the belly/other thigh; knee pointing inward (excessive medial rotation/valgus) during landings and squats; hips over-extended in a run (leg trails too far behind with no lumbar arch).
- **Context constraints**: on landing, hips must flex together with knees and ankles (triple flexion) to absorb load; knee alignment over the toes in squats (heuristic).
- **Validation**: cone limit; knee-direction check: in sagittal-dominant actions, the knee's direction vector stays within ~15-20 degrees of the foot direction (heuristic); thigh-belly collision.
- **Character exceptions**: heavy builds: thigh-abdomen contact limits flexion well before 130; dancers/martial artists: a "trained" profile with greater abduction/flexion; quadrupeds: hip is mostly sagittal with limited abduction.

---

## 12. Knee

- **Anatomical structure**: femur, tibia, patella; three articulations in one capsule (femoropatellar, medial and lateral tibiofemoral); menisci; collateral ligaments taut in full extension; ACL tightens in extension and resists hyperextension; PCL supports the flexed weight-bearing knee; posterior capsule ligaments resist hyperextension; quadriceps via patella acts as a dynamic stabiliser [OS96]. Quadriceps extend; hamstrings flex; gastrocnemius also helps flex [OS116].
- **Joint type**: modified hinge; some axial rotation is possible only when flexed [OS96].
- **DOF**: 1 primary + small axial rotation in flexion.
- **Rotation axes**: flexion about a mediolateral axis through the femoral condyles (the axis moves: rolling and gliding [OS96]); axial rotation about the tibial long axis.
- **Rig local coordinate system**: Y along tibia; X hinge; positive = flexion (heel toward buttock). Allow a small Y twist only when flexion > ~20 degrees (heuristic; see screw-home).
- **Neutral pose**: 0 (full extension, close-packed [OUHSC_KNEE]); relaxed standing 0-5 (unverified).
- **Range of motion** (signed: negative = hyperextension)
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Flexion | 0-140: CDC means 137.7 M / 141.9 F [CDC_ROM]; LUTT 150 | walking and slopes < 90 (walking swing peak ~60 [WIKI_GAIT]); stairs and chairs 90-120; getting into a bath ~135 [ROWE2000]; crouching up to 149 mean max [HYODO2017]; heels-up squat ~157 [HEMMERICH2006, not read: unverified] | ~155 when calf meets thigh visibly |
| Extension / hyperextension | CDC "extension" means 1.0 M / 1.6 F [CDC_ROM] (sign not defined on the page) | 0 at heel contact and near heel-off in walking [WIKI_GAIT] | 0 to -5 only for hypermobile characters; any visible backward bend reads as injury |
| Tibial axial rotation | available in flexion only [OS96]; magnitude not read (unverified ~30-40 total) | small | |
- **Parent-child**: parent = thigh; child = shin/ankle.
- **Coupled movements**: **screw-home**: during the last ~20 degrees of extension the tibia rotates externally on the femur (equivalently the femur rotates internally on a fixed tibia), locking the knee; flexion from 0 starts with the reverse (popliteus unlocks) [OS96][OUHSC_KNEE]. Magnitude reported around 10-15 degrees (search snippets only: unverified). Gastrocnemius and hamstrings couple knee to ankle and hip [OS116 inferred].
- **Functional movements**: step (loading response ~10-15 flexion, swing ~60 [WIKI_GAIT]), crouch, land (absorbing flexion), jump (rapid extension), kneel, climb stairs (90-120 [ROWE2000]), kick.
- **Common animation errors**: knee bending backward (sign flip or IK pole flip); knee popping (IK snap at full extension); knee locked straight on landing; knee caving in (valgus) on landing; knee too straight in walk contact poses for stylised walks (ok) vs realistic (should be near 0 at contact then flex ~10-15 in loading).
- **Context-dependent constraints**: under load during landing the knee never locks: flexion must increase after contact for several frames (heuristic: at least 20-30 degrees for a moderate landing); at walk heel-strike it can be near 0 [WIKI_GAIT].
- **Validation**: hinge plane check (knee bends in the plane defined by hip-knee-ankle and the pole vector); no negative flexion beyond the character's hyperextension allowance; IK reach ratio <= 0.995 except designated locked frames; landing rule: after a ground-contact event with downward velocity, flexion is monotonically increasing for N frames; screw-home cosmetic twist <= ~15 near extension (unverified threshold).
- **Character exceptions**: heavy builds: calf-thigh contact stops flexion early (around 120-130: unverified), use collision; digitigrade creatures (dogs, birds) have the "backward knee" which is actually the ankle: build a creature profile with an extra segment rather than reversing the human knee limit; children: more hyperextension common (unverified).

---

## 13. Ankle and foot (talocrural + subtalar + forefoot)

- **Anatomical structure**: talocrural joint = talus in the mortise of tibia and fibula (malleoli), uniaxial hinge permitting only dorsiflexion and plantarflexion; malleoli block side motion; medial deltoid ligament resists excess eversion; lateral ligaments (anterior and posterior talofibular, calcaneofibular) resist excess inversion; tibiofibular syndesmosis keeps the mortise tight [OS96]. Inversion/eversion happen at the subtalar (talus-calcaneus) and transverse tarsal (talonavicular, calcaneocuboid) joints together [OS96]; inversion has greater range than eversion [OS95]. Gastrocnemius and soleus plantarflex; tibialis anterior dorsiflexes; lateral leg muscles evert, medial invert [OS116].
- **Joint type**: talocrural hinge [OS94][OS96]; subtalar and intertarsal plane/gliding joints acting together [OS94].
- **DOF**: rig as 1 (ankle) + 1 (subtalar inversion/eversion) + 1 (toe/MTP hinge). Real subtalar axis is oblique so its motion combines components in all planes (unverified detail; QUT source failed).
- **Rotation axes**: talocrural ~mediolateral (slightly oblique: unverified); subtalar oblique (unverified orientation); toes mediolateral.
- **Rig local coordinate system**: `foot` Y from ankle to ball of foot; X = dorsi/plantar axis (positive = dorsiflexion); separate `subtalar` or Y/Z roll on the foot for inversion (positive); `toe` bone at the MTP line, X axis, positive = toe extension (toes up). Reverse-foot controls (heel pivot, ball pivot, toe pivot) should drive these.
- **Neutral pose**: 0 = foot at 90 degrees to shin; relaxed standing similar, slight toe-out (unverified).
- **Range of motion**
| Movement | Clinical | Functional | Artistic allowance (heuristic) |
|---|---|---|---|
| Dorsiflexion | 0-13: CDC means 12.7 M / 13.8 F [CDC_ROM] (lower than commonly quoted ~20 (unverified); LUTT lists 30, likely swapped with plantarflexion on the page read) | max ~10 in stance during walking; at least 10 is commonly cited as needed for normal gait [WIKI_GAIT] (QUT podiatry figure via snippet only) | ~30 in deep crouches/lunges (heels-down squat needs more than walking: magnitude unverified) |
| Plantarflexion | 0-55: CDC means 54.6 M / 62.1 F [CDC_ROM] (LUTT lists 20, likely swapped) | 15-20 just before push-off; at least 10-20 needed at ~1.25 m/s [WIKI_GAIT] | ~70 on tiptoe/ballet pointe |
| Inversion (subtalar + midfoot) | ~0-30 (unverified; Milgrom 1985 reported means 22-32 depending on technique: snippet only, not read) | 0-10 (unverified) | sprain zone if large inversion under load: avoid unless intentional |
| Eversion | ~0-15 (unverified) | 0-5 (unverified) | |
| Toe (MTP) extension | not read (unverified ~60-90) | needed at push-off and tiptoe | |
- **Parent-child**: parent = shin (tibia); child = foot (talus/calcaneus) then toes.
- **Coupled movements**: **ankle-subtalar coupling**: subtalar pronation (eversion component) couples with internal tibial rotation and supination with external rotation in weight-bearing (standard kinesiology; not confirmed in sources read: unverified). Knee and ankle couple through the gastrocnemius (two-joint) [OS116 inferred]: with the knee straight, dorsiflexion is reduced (unverified magnitude). The ankle is most stable in dorsiflexion (common claim; OS 9.6 does not state it [OS96]: unverified).
- **Functional movements**: step (heel strike near neutral, dorsiflex through mid-stance, plantarflex at push-off [WIKI_GAIT]), crouch (dorsiflexion), land (plantarflexed at contact then rapid dorsiflexion to absorb: heuristic), jump (plantarflexion push), run on uneven ground (inversion/eversion adapt), tiptoe.
- **Common animation errors**: foot passing through the ground; foot staying flat while the heel should lift at push-off; ankle rotating sideways at the talocrural joint (should be subtalar); sliding feet during planted frames; landing flat-footed with locked ankles; toes not bending at push-off (whole foot rotates as a plank).
- **Context constraints**: planted foot = zero world velocity at contact pivot; landing must show ankle dorsiflexion increasing after contact (absorption); on slopes the foot conforms by ankle + subtalar not by bending the shin.
- **Validation**: ground-penetration check; foot-skate check (contact point velocity below threshold during contact frames); ankle limit; inversion/eversion only on the subtalar bone; heel-lift check during push-off in walk cycles.
- **Character exceptions**: high-heeled characters live at ~20-30 plantarflexion (unverified); heavy builds: reduced dorsiflexion (unverified); digitigrade creatures stand on toes: their "ankle" is the visible reverse knee; hooved creatures: fused distal segments.

---

## 14. 2D side and three-quarter projection: what can and cannot be measured

A 2D rig shows only the projection of motion onto the picture plane. Anatomical limits are defined in 3D, so the validator must know what the 2D angle represents.

### 14.1 What projection does
- **Side view (camera looks along the mediolateral axis)**: sagittal motions (shoulder flexion/extension, elbow, hip, knee, ankle dorsi/plantarflexion, spinal flexion/extension) are seen at true angle. Coronal motions (abduction, lateral flexion, radial/ulnar deviation, inversion) point at the camera and appear only as foreshortening. Transverse rotations (shoulder/hip rotation, pronation/supination, spinal twist) appear only as shape changes (silhouette swap), not as angles.
- **Front view**: coronal motions are true angle; sagittal motions are foreshortening.
- **Three-quarter view (camera yawed ~30-60 degrees)**: every motion projects partly; no single 2D angle is a pure anatomical angle.

### 14.2 Specific ambiguities
1. **Shoulder abduction vs flexion**: in a side view, an arm raised 90 degrees in flexion looks horizontal and full-length; the same arm raised 90 degrees in abduction points at/away from the camera and appears short (foreshortened). In three-quarter views a raised, full-length arm could be flexion, scaption (scapular-plane elevation) or abduction. The 2D angle cannot tell them apart.
2. **Elbow angle appearing over 180 degrees**: a flexed elbow whose forearm points partly toward the camera, combined with humeral rotation, can project with the forearm on the "wrong" side of the upper-arm line, so the measured 2D angle exceeds 180 (looks hyperextended) while the 3D elbow is legally flexed. Conversely a hyperextended elbow viewed from the front can look straight.
3. **Knee valgus vs flexion**: from the front a flexed knee can look bent inward (valgus) if the hip is internally rotated; from the side valgus is invisible.
4. **Forearm rotation and humeral rotation** are not visible as angles in any 2D view; only sprite or mesh swaps reveal them.
5. **Foreshortened bones** keep their 2D angle range but change length; a bone that never shortens while its parent rotates out of plane is inconsistent.
6. **Mirroring/flip**: flipping X reverses the sign of all 2D rotations; limits must be re-signed, and left/right labelling may swap visually.

### 14.3 How to validate in 2D anyway
1. **Tag every 2D bone with a view-plane intent** per animation (or per keyframe): `sagittal` (side view, angle = flexion), `coronal` (front view, angle = abduction/lateral flexion), or `mixed`. Apply clinical/functional limits directly only for the matching plane.
2. **Use projected-limit envelopes**: for a given camera yaw (0 side, 90 front, 45 three-quarter), sample the 3D legal space of the joint (cone + twist limits from `human_joint_table.json`), project each sample with the same camera, and record the min/max 2D angle. That envelope is the legal 2D range for that view. Precompute it per joint per view (for example 0, 15, 30, 45, 60, 75, 90 degrees yaw).
3. **Infer out-of-plane angle from foreshortening**: if a bone has rest length L and projected length l, its out-of-plane angle is `phi = arccos(l / L)` (orthographic). The sign (toward or away from the camera) is ambiguous; require a `depth_sign` annotation or draw order (which sprite is in front) to resolve it. With phi known for both bones of a joint, reconstruct an approximate 3D joint angle and check it against 3D limits.
4. **Draw order as depth evidence**: in 2D cut-out rigs, z-order of the hand vs torso tells whether the arm is in front of or behind the body; check consistency (for example an arm in extension behind the body should be drawn behind the torso).
5. **Hinge-side check instead of angle check**: for elbow and knee, check the *side* of the bend relative to a reference vector (the elbow point must lie on the dorsal side of the shoulder-wrist line in sagittal views; the knee must lie on the anterior side of the hip-ankle line). This survives most projection cases and catches backward-bending errors.
6. **Coupling checks survive projection**: "hand above head height implies shoulder point raised" can be checked in 2D as vertical displacement of the shoulder joint relative to its rest position.
7. **Length invariants**: bone lengths should be constant unless the view tag says the bone is turning out of plane; sudden length change across one frame indicates a snap.
8. **Velocity/acceleration sanity**: limit 2D angular velocity per joint per frame (heuristic per style) to catch flips and pops that projection can hide.

---

## 15. Sources

| id | Source | Read status | Licence / notes |
|---|---|---|---|
| OS95 | OpenStax, Anatomy and Physiology 2e, 9.5 Types of Body Movements. https://openstax.org/books/anatomy-and-physiology-2e/pages/9-5-types-of-body-movements | read OK | page states CC BY-NC-SA 4.0 plus no-LLM-training clause (not CC BY 4.0) |
| OS94 | OpenStax A&P 2e, 9.4 Synovial Joints. https://openstax.org/books/anatomy-and-physiology-2e/pages/9-4-synovial-joints | read OK | same |
| OS96 | OpenStax A&P 2e, 9.6 Anatomy of Selected Synovial Joints. https://openstax.org/books/anatomy-and-physiology-2e/pages/9-6-anatomy-of-selected-synovial-joints | read OK | same; no numeric ranges |
| OS115 | OpenStax A&P 2e, 11.5 Muscles of the Pectoral Girdle and Upper Limbs. https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs | read OK | same; page contains two internal inconsistencies (supinator "palm-down"; rotator cuff "elbow") |
| OS116 | OpenStax A&P 2e, 11.6 Appendicular Muscles of the Pelvic Girdle and Lower Limbs. https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs | read OK | same; gluteus minimus action listed inconsistently |
| CDC_ROM | CDC Joint Range of Motion Study (reference values 20-44 y). https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html | read OK | US government work (public domain, assumed) |
| SOUCIE2011 | Soucie JM et al. Range of motion measurements: reference values and a database for comparison studies. Haemophilia 2011;17(3):500-507 (abstract via Europe PMC REST) | abstract read | subscription |
| LUTT | Joint ROM table on WikEM (attributes Luttgens & Hamilton 1997). https://wikem.org/wiki/Joint_ROM_(Table) | read OK (secondary) | ankle values look swapped; licence not stated on page |
| GATES2016 | Gates DH et al. Range of motion requirements for upper-limb activities of daily living. Am J Occup Ther 2016. https://pmc.ncbi.nlm.nih.gov/articles/PMC4690598 | full text read | copyright AOTA |
| NAMDARI2012 | Namdari S et al. Defining functional shoulder range of motion for activities of daily living. J Shoulder Elbow Surg 2012;21(9):1177-83 (Europe PMC abstract) | abstract read | |
| MORREY1981 | Morrey BF, Askew LJ, Chao EY. A biomechanical study of normal functional elbow motion. JBJS Am 1981;63:872-7, via JBJS OrthoBuzz "JBJS Classics" commentary. https://orthobuzz.jbjs.org/2016/10/26/jbjs-classics-biomechanics-of-the-normal-elbow/ | secondary commentary read | original not read |
| RYU1991 | Ryu J et al. Functional ranges of motion of the wrist joint. J Hand Surg Am 1991;16(3):409-19 (abstract). https://mayoclinic.elsevierpure.com/en/publications/functional-ranges-of-motion-of-the-wrist-joint/ | abstract read | |
| HYODO2017 | Hyodo K et al. Hip, knee, and ankle kinematics during activities of daily living: a cross-sectional study. Braz J Phys Ther 2017;21(3):159-166 (Europe PMC abstract) | abstract read | open access |
| ROWE2000 | Rowe PJ et al. Knee joint kinematics in gait and other functional activities measured using flexible electrogoniometry. Gait Posture 2000;12(2):143-155 (Europe PMC abstract) | abstract read | |
| HEMMERICH2006 | Hemmerich A et al. Hip, knee, and ankle kinematics of high range of motion activities of daily living. J Orthop Res 2006 | NOT read (search snippets only) | numbers marked unverified |
| ESOLA1996 | Esola MA et al. Analysis of lumbar spine and hip motion during forward bending in subjects with and without a history of low back pain. Spine 1996;21(1):71-78 (Europe PMC abstract) | abstract read | |
| BRAMAN2009 | Braman JP et al. In vivo assessment of scapulohumeral rhythm during unconstrained overhead reaching in asymptomatic subjects. J Shoulder Elbow Surg 2009;18(6):960-7 (Europe PMC abstract) | abstract read | |
| OUHSC_SCAP | Univ. of Oklahoma HSC kinesiology notes, shoulder elevation (scapulohumeral rhythm, citing Inman 1944). https://ouhsc.edu/bserdac/dthompso/web/namics/scapryme.htm | read OK | educational page; licence not stated |
| INMAN_via_OUHSC | Inman, Saunders & Abbott 1944 (2:1 ratio) as reported by OUHSC_SCAP | secondary | original not read |
| OUHSC_KNEE | Univ. of Oklahoma HSC, Biomechanics of the knee (arthrokinematics, screw-home window). https://ouhsc.edu/bserdac/dthompso/web/namics/kneeak.htm | read OK | |
| WIKI_GAIT | Wikipedia, Lower-limb walking pattern. https://en.wikipedia.org/wiki/Lower-limb_walking_pattern | read OK (tertiary) | CC BY-SA 4.0 |
| YOUDAS1992 | Youdas JW et al. Normal range of motion of the cervical spine: an initial goniometric study. Phys Ther 1992;72(11):770-80 (abstract) | abstract read, no numbers in abstract | supports: all six cervical motions decline with age |
| LIEBSCH2025 | Liebsch C, Wilke HJ. Coupled motions of the spine under standardized in vitro conditions: systematic review and meta-analysis (2025, Europe PMC search record) | abstract read | |
| NEUMANN | Neumann DA. Kinesiology of the Musculoskeletal System (Elsevier; 4th ed. listing). Publisher description only | not read (book) | cited as secondary context only; no page numbers |
| MATTESI | Mattesi M. FORCE: Drawing Human Anatomy (CRC Press/Focal). Publisher and retailer descriptions | not read (book) | secondary; describes rhythm-of-forces approach to anatomy-in-motion |
| WILLIAMS | Williams R. The Animator's Survival Kit (Faber/Farrar). Public reviews and contents (arcs, breakdowns, overlapping action, weight, walks) | not read (book) | secondary |

### Failed or blocked fetches
- physio-pedia.com Range of Motion Normative Values and Scapulohumeral Rhythm pages: HTTP 403.
- pmc.ncbi.nlm.nih.gov PMC4935167 (Willmore & Smith scapulohumeral review) and PMC9218764 table: reCAPTCHA page.
- pubmed.ncbi.nlm.nih.gov abstracts: "enable cookies" page (worked around via Europe PMC REST API).
- McClure et al. 2001 JSES PDF (uoregon.edu): downloaded but no PDF text extractor available; not read.
- QUT podiatry anatomy app (ankle and subtalar ROM): HTTP 403.
- sncc.ca ROM normal values PDF: HTTP 500.
- Europe PMC full-text XML for PMC4935167: HTTP 500.
- Springer (cervical C1-C2 in vivo study): auth redirect.
- hal.bim.msu.edu upper cervical biomechanics page: empty content.
- Neumann wrist kinesiology slides (uwm.edu): redirect not followed (binary PDF, no extractor).
- No AAOS publication was read directly. Values commonly attributed to AAOS are therefore not used; where they would differ, the text says so and marks them unverified.

### How books are used
Neumann (kinesiology), Mattesi (anatomy for figure drawing in motion) and Williams (animation craft: arcs, weight, overlap, breakdowns) were not read. They are listed only as recommended human reading for the art team. Nothing in this document depends on them, and no page numbers are given.
