"""Rig/solver tests and regression tests (Board amendment, 2026-11-22). Run from rnd/motion:

    python -I -s -m unittest tests.test_motion_system -v      (with the folder on sys.path, see main)

Solver tests (isolated joint movement): rest reproduction, degrees, local vs global inheritance, elbow sweep without
shoulder motion / flips / length change, weapon attachment transform, IK reachability flag, knee bend direction
under a crouch sweep, left/right mirroring.
Regression tests: every failure the Board found becomes a case the validators must catch.
"""
import copy
import json
import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import motion as mo  # noqa: E402
import posecheck as pc  # noqa: E402

S_PATH = os.path.join(HERE, "data", "structure_brute_hammer.json")
B_PATH = os.path.join(HERE, "data", "attack_hammer_B.motion.json")


def load():
    with open(S_PATH) as a, open(B_PATH) as b:
        return json.load(a), json.load(b)


def neutral_motion(s, n=10, **pose_over):
    pose = {"root": [0, 0], "chains": {c: [0.0] * len(v["channels"]) for c, v in s["chains"].items()},
            "shift": {"arm_f": [0, 0]}, "feet": {"foot_k": [0, 0], "foot_f": [0, 0]}}
    for k, v in pose_over.items():
        pose[k] = v
    return {"schema": "motion.v2", "id": "t", "fps": 60, "keys": [{"frame": 0, "ease": "lin", "pose": pose},
                                                                  {"frame": n, "ease": "lin", "pose": copy.deepcopy(pose)}],
            "phases": [], "events": [], "constraints": [], "acceptance": {}}


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.s, self.m = load()

    def test_rest_pose_reproduced(self):
        sol = mo.Solver(self.s, neutral_motion(self.s))
        fr = sol.solve(0)
        for j, r in sol.R.items():
            self.assertLess(float(np.linalg.norm(fr["J"][j] - r)), 1e-6, j)

    def test_degrees_and_local_rotation(self):
        m = neutral_motion(self.s)
        for k in m["keys"]:
            k["pose"]["chains"]["arm_f"] = [90.0, 0.0, 0.0]
        sol = mo.Solver(self.s, m)
        fr = sol.solve(0)
        R = sol.R
        before = R["elbow_f"] - R["shoulder_f"]
        after = fr["J"]["elbow_f"] - fr["J"]["shoulder_f"]
        self.assertAlmostEqual(math.degrees(math.atan2(after[1], after[0]) - math.atan2(before[1], before[0])) % 360, 90.0, 4)
        # the whole chain turns rigidly with the shoulder (local inheritance): the elbow relative angle is unchanged
        self.assertAlmostEqual(fr["rel"]["arm_f.elbow"], sol.chain_rest["arm_f"]["rel"][1], 6)

    def test_parent_inheritance_spine_moves_arm_rigidly(self):
        m = neutral_motion(self.s)
        for k in m["keys"]:
            k["pose"]["chains"]["trunk"] = [20.0, 0.0, 0.0]
        sol = mo.Solver(self.s, m)
        fr = sol.solve(0)
        R = sol.R
        a0 = R["hand_f"] - R["shoulder_f"]
        a1 = fr["J"]["hand_f"] - fr["J"]["shoulder_f"]
        self.assertAlmostEqual(float(np.linalg.norm(a0)), float(np.linalg.norm(a1)), 6)
        rot = (math.degrees(math.atan2(a1[1], a1[0]) - math.atan2(a0[1], a0[0])) + 360) % 360
        self.assertAlmostEqual(rot, 20.0, 4)

    def test_elbow_sweep_isolated(self):
        """The elbow moves through its range: shoulder and elbow joints stay put, lengths constant, no flip."""
        for e in np.linspace(-150, 150, 31):
            m = neutral_motion(self.s)
            for k in m["keys"]:
                k["pose"]["chains"]["arm_f"] = [0.0, float(e) - mo.Solver(self.s, m).chain_rest["arm_f"]["rel"][1], 0.0]
            sol = mo.Solver(self.s, m)
            fr = sol.solve(0)
            for j in ("shoulder_f", "elbow_f"):
                self.assertLess(float(np.linalg.norm(fr["J"][j] - sol.R[j])), 1e-6)
            self.assertAlmostEqual(fr["rel"]["arm_f.elbow"], e, 6)
            for b in ("upperarm_f", "forearm_f", "hand_f"):
                v = self.s["bones"][b]
                self.assertAlmostEqual(float(np.linalg.norm(fr["J"][v["to"]] - fr["J"][v["from"]])), sol.L[b], 6)

    def test_weapon_attachment_rest(self):
        sol = mo.Solver(self.s, neutral_motion(self.s))
        fr = sol.solve(0)
        self.assertAlmostEqual(fr["ham_angle"], self.s["attachments"]["hammer"]["rest_axis_deg"], 6)
        self.assertLess(float(np.linalg.norm(fr["H"]["grip"] - fr["J"]["hand_f"])), 1e-9)

    def test_ik_reachability_flag(self):
        m = neutral_motion(self.s, root=[0, -80])           # pelvis lifted beyond leg length
        sol = mo.Solver(self.s, m)
        sol.solve(0)
        self.assertTrue(any("overextended" in f[1] for f in sol.flags))

    def test_knee_bend_direction_under_crouch(self):
        for dy in range(0, 61, 10):
            m = neutral_motion(self.s, root=[0, dy])
            sol = mo.Solver(self.s, m)
            fr = sol.solve(0)
            for leg in ("k", "f"):
                h, k, a = fr["J"]["hip_" + leg], fr["J"]["knee_" + leg], fr["J"]["ankle_" + leg]
                line_x = h[0] + (a[0] - h[0]) * (k[1] - h[1]) / (a[1] - h[1])
                if dy >= 10:
                    self.assertGreater(k[0], line_x - 0.5, f"knee {leg} bends backward at crouch {dy}")

    def test_mirroring(self):
        """Mirror the structure (x -> W - x) and negate all rotations: every joint mirrors."""
        W = 832.0
        s2 = copy.deepcopy(self.s)
        for j in s2["joints"].values():
            j["rest"] = [W - j["rest"][0], j["rest"][1]]
        s2["attachments"]["hammer"]["rest_axis_deg"] = 180 - self.s["attachments"]["hammer"]["rest_axis_deg"]
        for l in s2["legs"].values():
            l["bend"] = "-x"
        for c in s2["contacts"].values():
            c["toe"], c["heel"] = [-c["toe"][0], c["toe"][1]], [-c["heel"][0], c["heel"][1]]
        _, mB = load()
        mB2 = copy.deepcopy(mB)
        for k in mB2["keys"]:
            p = k["pose"]
            p["root"] = [-p["root"][0], p["root"][1]]
            for c in p["chains"]:
                p["chains"][c] = [-v for v in p["chains"][c]]
            p["shift"]["arm_f"] = [-p["shift"]["arm_f"][0], p["shift"]["arm_f"][1]]
            p["feet"] = {c: [-v[0], v[1]] for c, v in p["feet"].items()}
        a, b = mo.Solver(self.s, mB), mo.Solver(s2, mB2)
        for f in (0, 30, 46, 56, 90):
            fa, fb = a.solve(f), b.solve(f)
            for j in fa["J"]:
                pa, pb = fa["J"][j], fb["J"][j]
                self.assertLess(abs((W - pa[0]) - pb[0]) + abs(pa[1] - pb[1]), 1e-6, f"{j} at {f}")


def run_variant(edit):
    s, m = load()
    edit(s, m)
    tmp_s = os.path.join(HERE, "tests", "_tmp_s.json")
    tmp_m = os.path.join(HERE, "tests", "_tmp_m.json")
    json.dump(s, open(tmp_s, "w"))
    json.dump(m, open(tmp_m, "w"))
    try:
        rep = pc.validate(tmp_s, tmp_m)
    finally:
        for p in (tmp_s, tmp_m):
            try:
                os.remove(p)
            except OSError:
                pass
    return {f["id"]: f for f in rep["findings"]}


def key(m, frame):
    return [k for k in m["keys"] if k["frame"] == frame][0]


U0, E0, W0 = 142.1, 155.2, -46.4


def set_arm(m, frame, U, E, W):
    key(m, frame)["pose"]["chains"]["arm_f"] = [U - U0, E - E0, W - W0]


class RegressionTests(unittest.TestCase):
    """Each Board-reported failure must be caught (the baseline B must pass the same check)."""

    def test_baseline_B_hard_constraints_pass(self):
        rep = run_variant(lambda s, m: None)
        hard_fail = [k for k, f in rep.items() if f["class"] == "hard" and f["pass"] is False]
        self.assertEqual(hard_fail, [])

    def test_excessively_folded_elbow_at_impact(self):
        f = run_variant(lambda s, m: set_arm(m, 56, 398, -95, -38))
        self.assertFalse(f["heavy_strike:extension_at_impact"]["pass"])

    def test_forearm_crossing_face_in_held_pose(self):
        def e(s, m):
            for fr in (56, 60):
                set_arm(m, fr, 330, 70, -30)
        f = run_variant(e)
        self.assertFalse(f["self_collision_face_zone_held_poses"]["pass"])

    def test_elbow_flip_through_fold(self):
        def e(s, m):
            set_arm(m, 72, 414, 168, -36)       # nearly folded ...
            set_arm(m, 84, 300, 192, -54)       # ... and continuing past 180: the forearm snaps to the other side
        f = run_variant(e)
        self.assertFalse(f["no_flip_through_fold:arm_f.elbow"]["pass"])

    def test_impossible_joint_rotation(self):
        f = run_variant(lambda s, m: set_arm(m, 84, 300, -12, 120))
        self.assertFalse([v for k, v in f.items() if k.startswith("range:arm_f.wrist")][0]["pass"])

    def test_elbow_hyperextension(self):
        def e(s, m):
            s["anatomy"]["map"]["arm_f.elbow"]["sign"] = 1     # signed check for this case
        def e2(s, m):
            e(s, m)
            set_arm(m, 84, 300, -40, -54)
        f = run_variant(e2)
        self.assertFalse([v for k, v in f.items() if k.startswith("range:arm_f.elbow")][0]["pass"])

    def test_incorrect_weapon_grip(self):
        def e(s, m):
            s["objects"]["hammer_master"]["grip_point"] = [30, 0]
        f = run_variant(e)
        self.assertFalse(f["grip (weapon on the hand)"]["pass"])

    def test_disconnected_shoulder(self):
        def e(s, m):
            for k in m["keys"]:
                k["pose"]["shift"]["arm_f"] = [0, 0]
        f = run_variant(e)
        self.assertFalse(f["scapulohumeral_coupling"]["pass"])

    def test_foot_sliding(self):
        def e(s, m):
            key(m, 30)["pose"]["feet"]["foot_k"] = [25, 0]
        f = run_variant(e)
        self.assertFalse(f["ground_contact (foot slide)"]["pass"])

    def test_invalid_weight_transfer(self):
        def e(s, m):
            for fr in (30, 40, 46):
                key(m, fr)["pose"]["root"][0] = 70
        f = run_variant(e)
        self.assertFalse(f["weight_transfer_back_in_windup"]["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
