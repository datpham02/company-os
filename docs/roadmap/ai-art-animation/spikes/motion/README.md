# Motion spike tools (Board R&D, 2026-11-22)

Engine-neutral, standard library + NumPy/Pillow/SciPy (ComfyUI's embedded Python; no new dependency).

| File | Purpose |
|---|---|
| `motion.py` | solver v2 (structure.v2 + motion.v2: FK chains, joint limits, shoulder shift, PCHIP splines with broken-tangent keys, leg IK to contacts, rigid weapon on the hand bone), 20 QA checks, evidence renders |
| `motion_v1.py` | solver v1 (method A, arm IK) - kept for the record; its structure.v1 file was superseded by `structure_brute_hammer.json` v2, so A is reproduced from `attack_hammer_v1_A.motion.json` only with the v1 structure from this branch's history of the R&D folder (not kept). |
| `cmu_amc.py` | ASF/AMC reader + 3D forward kinematics |
| `retarget_cmu.py` | method C: projection, retargeting, contact cleanup, hip clamp, KB wrist rule, phase detection → motion.v2 |
| `data/structure_brute_hammer.json` | benchmark structure (measured on the master art) |
| `data/attack_hammer_B.motion.json` | method B |
| `data/map_cmu79_brute.json`, `data/attack_hammer_C.motion.json` | method C map and its derived motion |

**CMU data is not in this repository** (licence: free for all uses, the data may not be resold even converted; we keep
only derived keys). The Board downloads `79.asf`, `79_01.amc`, `80.asf`, `80_71.amc` from mocap.cs.cmu.edu/subjects/
into `refs/cmu/` next to `data/` (decision K1, 2026-11-22) before running method C.

Run (from the folder holding `data/` and `refs/`):
```
python -I -s motion.py data/structure_brute_hammer.json data/attack_hammer_B.motion.json review_B
python -I -s retarget_cmu.py data/map_cmu79_brute.json data/structure_brute_hammer.json data/attack_hammer_C.motion.json
python -I -s motion.py data/structure_brute_hammer.json data/attack_hammer_C.motion.json review_C
```

## Added after the anatomy and universal-motion amendments (2026-11-22)

| File | Purpose |
|---|---|
| `profiles/*.json` | anatomy profiles (`anatomy-profile.v1`): humanoid base (verified clinical/functional ranges, kb/human_joint_table.json), stylized and heavy humanoid, quadruped, flying, multi-limbed, custom template |
| `posecheck.py` | three-tier validation (A anatomical, B biomechanical, C action/artistic), hard/soft/artistic classes, character overrides with a reason |
| `poselib.py`, `data/poses_brute.json`, `poses_brute/` | validated pose library (10 poses + 1 negative example) |
| `tests/test_motion_system.py` | 18 tests: solver (rest, degrees, inheritance, isolated elbow sweep, weapon, IK reach, knee bend, mirroring) + 10 regression cases from Board-reported failures |
| `entity/` | Entity Motion Profile schema, component registry (`components.json`), 7 example entities, `entity.py plan` (method selection) |

```
python -I -s tests/test_motion_system.py
python -I -s posecheck.py data/structure_brute_hammer.json data/attack_hammer_B.motion.json out.json
python -I -s poselib.py data/structure_brute_hammer.json data/poses_brute.json poses_out
python -I -s entity/entity.py plan entity/examples/dragon.json
```
