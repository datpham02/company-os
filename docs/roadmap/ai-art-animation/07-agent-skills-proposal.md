# Agent Skills Proposal: Animation

- **Status:** `PROPOSED`. No skill is installed and no agent, permission or runtime changes until the Board approves
  (Board directive 2026-11-22). Skills are studio-level: no project, character or weapon is named inside them.
- **Who runs them:** during R&D the Board operator (Claude Code, decision D1); later the role chosen by decision D7.
  Read-only reviewers (`director`) use only the review checklists.

Common inputs for all skills: a `structure.v2` file, a `motion.v2` file or a motion request, the KB
([kb/animation-fundamentals.md](kb/animation-fundamentals.md)), and the QA tool (`motion.py`). Common output rule:
evidence is real-time + slow-motion playback, a sequential sheet, trajectories and checks.json; stills alone never
pass.

| Skill | Trigger | Required inputs | Knowledge | Tools | Steps | Outputs | Failure conditions | Review checklist |
|---|---|---|---|---|---|---|---|---|
| **motion-design** | a new motion is requested | intent, gameplay events, structure, category | KB §1, 10-12, 17, 20 | none (writes a spec) | write intent → phases with frame budgets from the category's timing ratios → key pose list with purpose per pose → contacts, events, acceptance | motion spec draft (no curves yet) | missing gameplay event; phase ratios outside the category range without a stated reason | every phase has a purpose; timing ratio; contacts named |
| **animation-reference-research** | before authoring any motion | category, character type | 05 (licences) | library search; Board-approved datasets only | search library → list candidate trials with licence status → pick ≤3 | reference list with licence lines | only non-production licences found (then fall back to authored, say so) | licence checked on the source page; no NC data |
| **pose-analysis** | a reference trial is selected | trial data | KB §5-9 | reader, analysis script | extract joints → phases from speed/height extrema → key poses → contacts | key pose table + plots | noisy joints (CMU hands/toes) unfiltered; phases not found | phase boundaries plotted; contacts match foot speed |
| **body-mechanics** | blocking pass of any motion | spec + blocking render | KB §4-9, 20 | `motion.py` checks | check COM path, weight transfer, kinetic-chain order (peak speed order), contacts, arcs | findings list (location, expected, actual) | COM outside support in held poses; chain order wrong | ground-up order; weight shift before arms |
| **character-rigging** | a new character or creature | master art, character type | KB §2-3, 16; workflow §1-5 | skeleton overlay, measurement grid | measure joints on the art → chains → limits for this type → contacts → masses → attachments | `structure.v2` + overlay image | joints off the art; limits copied from humans onto a non-human | overlay matches art; limits justified per type |
| **motion-retargeting** | a reference motion to a structure | source joints, structure, mapping | 06 §2 | retarget + projection script | map joints → project → keep directions, apply target lengths → pin contacts → bake FK offsets | `motion.v2` + checks | unmapped required chain; joint limits broken after retarget | foot slide; grip; limits; silhouette vs source |
| **animation-generation** | spec approved | spec, structure | KB §14-16 | `motion.py` | blocking (stepped keys) → breakdowns → PCHIP splines with broken tangents where physical → QA | `motion.v2` + evidence | any hard check fails | all hard checks pass; soft findings listed |
| **animation-polishing** | blocking approved | motion + review findings | KB §12-13, 19 | springs (secondary), events | overlap and follow-through on loose parts → hold timing → stylisation within limits → events (hit-stop as runtime) | polished `motion.v2` | polish breaks a hard check; baked hit-stop decelerates contact | contact speed; overlap present; no new pops |
| **motion-qa** | any motion handed off | motion + structure | 06 §4 | `motion.py` | run checks → classify hard/soft/artistic → render evidence → verdict | QA report + evidence | evidence missing; judging from stills | hard checks; soft findings; real-time and slow previews watched |

**Order (`director`, SOU-87):** motion-qa (the evidence contract) → animation-reference-research (licence gate) → motion-design (with the reference-selection gate of 08 §5) → motion-retargeting → body-mechanics; creature, gait, chain and wing skills wait until those tools exist.

**Review cards:** every skill that hands work to `director` attaches a review card per preview package (frame numbers to look at, what to compare, per-frame metrics). `director` can open still images committed in the Task Workspace (smoke test SOU-91, 2026-11-22: it opened and judged a PNG); whether it can play GIF or MP4 previews is untested. **Stable anchors:** skills cite KB sections by stable anchors (not section numbers), because the K4 review will renumber the KB.

**Packaging:** each skill becomes a `SKILL.md` with these sections plus links to the KB sections, stored with the
studio knowledge (not in a project repository), after Board approval and a `director` review of the KB content.
