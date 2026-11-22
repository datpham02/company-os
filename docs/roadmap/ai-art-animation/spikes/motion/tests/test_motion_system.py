"""Rig/solver tests, regression tests and validator-semantics tests (Board amendment 2026-11-22; KA-BD-5 and
KA-BD-6, 2026-11-23). Run from spikes/motion with a Python that has numpy, scipy and Pillow:

    python -I -s tests/test_motion_system.py

Solver tests (isolated joint movement): rest reproduction, degrees, local vs global inheritance, elbow sweep without
shoulder motion / flips / length change, weapon attachment transform, IK reachability flag, knee bend direction
under a crouch sweep, left/right mirroring.
Regression tests: every failure the Board found becomes a case the validators must catch (fail for structural
invariants, warn for rules that are not enforcement-eligible).
Semantics tests: unknown is never pass, mandatory unknown blocks, advisory unknown does not, verified-but-ineligible
warns, eligible structural invariants fail, mirrored clips give identical outcomes, the 140 px ground penetration
fails, a non-strike clip gets not_applicable for strike rules, a missing joint mapping is unknown, and profile
overrides never inherit verified provenance. Nothing is written into the repository (temp dirs only).
"""
import copy
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import motion as mo  # noqa: E402
import posecheck as pc  # noqa: E402
import rules as ru  # noqa: E402

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


DATA = os.path.join(HERE, "data")
A_PATH = os.path.join(DATA, "attack_hammer_v1_A.motion.json")


def run_variant(edit, review=None, full=False):
    """Validate an edited copy of structure + motion B in memory (nothing is written into the repository)."""
    s, m = load()
    edit(s, m)
    rep = pc.validate_data(s, m, DATA, review)
    return rep if full else {f["id"]: f for f in rep["findings"]}


def state(findings, prefix):
    hits = [f for k, f in findings.items() if k == prefix or k.startswith(prefix + ":")]
    assert len(hits) == 1, (prefix, [h["id"] for h in hits])
    return hits[0]["state"]


def key(m, frame):
    return [k for k in m["keys"] if k["frame"] == frame][0]


U0, E0, W0 = 142.1, 155.2, -46.4


def set_arm(m, frame, U, E, W):
    key(m, frame)["pose"]["chains"]["arm_f"] = [U - U0, E - E0, W - W0]


BASE = None


def baseline():
    global BASE
    if BASE is None:
        BASE = run_variant(lambda s, m: None)
    return BASE


class RegressionTests(unittest.TestCase):
    """Each Board-reported failure must be caught (the baseline B must pass the same check).
    KA-BD-5 (2026-11-23): a catch is `fail` only for enforcement-eligible rules (structural invariants); every other
    rule catches with `warn`. Tests that asserted `pass is False` for a non-eligible rule now assert `warn`."""

    def test_baseline_B_hard_constraints_pass(self):
        # CHANGED (KA-BD-5): the old test asserted "B passes every hard check", which was true only because the repo had
        # no ground check while B sinks the hammer 140 px below the ground for 34 frames (U1, audit D-19). B's only
        # mandatory fail is now that known defect; every other structural invariant passes and B is rejected.
        rep = run_variant(lambda s, m: None, full=True)
        fails = [f["id"] for f in rep["findings"] if f["state"] == "fail"]
        self.assertEqual(fails, ["environment.weapon_ground_penetration"])
        structural = [f for f in rep["findings"] if f["class"] == "structural_invariant" and f["rule_id"] != "environment.weapon_ground_penetration"]
        self.assertTrue(structural and all(f["state"] in ("pass", "not_applicable") for f in structural), [(f["id"], f["state"]) for f in structural])
        self.assertEqual(rep["verdict"], "rejected")

    def test_excessively_folded_elbow_at_impact(self):
        # CHANGED: heavy-strike intent rule (action_specific, heuristic, no enforcement record) -> warn, not fail.
        self.assertEqual(state(baseline(), "strike.extension_at_impact"), "pass")
        f = run_variant(lambda s, m: set_arm(m, 56, 398, -95, -38))
        self.assertEqual(state(f, "strike.extension_at_impact"), "warn")

    def test_forearm_crossing_face_in_held_pose(self):
        # CHANGED: 2D screen-overlap proxy (representation_constraint) -> warn.
        def e(s, m):
            for fr in (56, 60):
                set_arm(m, fr, 330, 70, -30)
        self.assertEqual(state(baseline(), "rep.face_zone_overlap"), "pass")
        self.assertEqual(state(run_variant(e), "rep.face_zone_overlap"), "warn")

    def test_elbow_flip_through_fold(self):
        # CHANGED: a 2D bend-side flip can be a projection artefact (C's far arm) -> representation_constraint, warn.
        def e(s, m):
            set_arm(m, 72, 414, 168, -36)       # nearly folded ...
            set_arm(m, 84, 300, 192, -54)       # ... and continuing past 180: the forearm snaps to the other side
        self.assertEqual(state(baseline(), "rep.no_flip_through_fold:arm_f.elbow"), "pass")
        self.assertEqual(state(run_variant(e), "rep.no_flip_through_fold:arm_f.elbow"), "warn")

    def test_impossible_joint_rotation(self):
        # CHANGED: a profile range measured on a screen-projected 2D proxy -> warn (never fail).
        self.assertEqual(state(baseline(), "anat.range:arm_f.wrist->wrist.flex[stylized]"), "pass")
        f = run_variant(lambda s, m: set_arm(m, 84, 300, -12, 120))
        self.assertEqual(state(f, "anat.range:arm_f.wrist->wrist.flex[stylized]"), "warn")

    def test_elbow_hyperextension(self):
        # CHANGED: the old test rewrote the production mapping to sign = 1 before checking, so it tested a mapping that
        # production does not use (audit D-03). With the production sign 'abs' mapping the bend side is now reported as
        # unknown (never pass); with a signed mapping the hyperextension is caught as warn (projected proxy).
        prod = run_variant(lambda s, m: set_arm(m, 84, 300, -40, -54))
        self.assertEqual(state(prod, "anat.bend_side:arm_f.elbow"), "unknown")
        self.assertIn("abs", [f for k, f in prod.items() if k == "anat.bend_side:arm_f.elbow"][0]["reason"])

        def signed(s, m):
            s["anatomy"]["map"]["arm_f.elbow"]["sign"] = 1
            set_arm(m, 84, 300, -40, -54)
        self.assertEqual(state(run_variant(signed), "anat.range:arm_f.elbow->elbow.flex[stylized]"), "warn")

    def test_incorrect_weapon_grip(self):
        # structural invariant (attachment connectivity): still a fail, now through the rule id structure.grip
        self.assertEqual(state(baseline(), "structure.grip"), "pass")
        def e(s, m):
            s["objects"]["hammer_master"]["grip_point"] = [30, 0]
        self.assertEqual(state(run_variant(e), "structure.grip"), "fail")

    def test_disconnected_shoulder(self):
        # CHANGED: scapulohumeral rule uses unsourced numbers (120 deg, -2 px) -> artistic_heuristic, warn.
        def e(s, m):
            for k in m["keys"]:
                k["pose"]["shift"]["arm_f"] = [0, 0]
        self.assertEqual(state(baseline(), "coupling.scapulohumeral"), "pass")
        self.assertEqual(state(run_variant(e), "coupling.scapulohumeral"), "warn")

    def test_foot_sliding(self):
        # structural invariant (the motion's own declared contact): still a fail
        self.assertEqual(state(baseline(), "contact.foot_slide"), "pass")
        def e(s, m):
            key(m, 30)["pose"]["feet"]["foot_k"] = [25, 0]
        self.assertEqual(state(run_variant(e), "contact.foot_slide"), "fail")

    def test_invalid_weight_transfer(self):
        # CHANGED: heavy-strike weight rule (action_specific, heuristic) -> warn.
        def e(s, m):
            for fr in (30, 40, 46):
                key(m, fr)["pose"]["root"][0] = 70
        self.assertEqual(state(baseline(), "strike.weight_back_in_windup"), "pass")
        self.assertEqual(state(run_variant(e), "strike.weight_back_in_windup"), "warn")


def lift_ground(s, m, dy=200):
    """Test fixture only: move the ground line down so B has no ground penetration and the verdict logic can be
    tested in isolation (the real B is rejected for its penetration)."""
    for c in s["contacts"].values():
        c["ground_y"] += dy


class ReviewFixture:
    def __init__(self, motion_id, items="pass", tamper=False):
        self.dir = tempfile.mkdtemp(prefix="motion_review_")
        ev = os.path.join(self.dir, "preview.gif")
        with open(ev, "wb") as fh:
            fh.write(b"GIF89a evidence stand-in for the test")
        with open(ev, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        if tamper:
            digest = "0" * 64
        self.record = {"schema": "motion-review.v1", "motion": motion_id, "reviewer": "director (test)", "date": "2026-11-23",
                       "evidence": [{"path": "preview.gif", "sha256": digest}], "items": {rid: items for rid in pc.ART_ITEMS},
                       "_base": self.dir}

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class SemanticsTests(unittest.TestCase):
    """KA-BD-5 / KA-BD-6 regression tests (Board, 2026-11-23)."""

    @classmethod
    def setUpClass(cls):
        cls.review = ReviewFixture("attack_hammer_B")

    @classmethod
    def tearDownClass(cls):
        cls.review.close()

    def test_unknown_is_never_pass(self):
        f = run_variant(lambda s, m: s["anatomy"]["map"]["arm_f.wrist"].update(joint="wristt"))
        rng = [v for k, v in f.items() if k.startswith("anat.range:arm_f.wrist")]
        self.assertEqual([v["state"] for v in rng], ["unknown"])
        self.assertIn("wristt", rng[0]["reason"])
        self.assertEqual(ru.classify("anat.range", {"representation": "planar_2d", "category": "x", "entity_tags": set(),
                                                     "phases": set(), "events": set()}, measured=False)["state"], "unknown")
        missing = run_variant(lambda s, m: m["acceptance"].pop("bone_length_dev_px"))
        self.assertEqual(state(missing, "structure.bone_length_constant"), "unknown")   # no hammer default fills it

    def test_missing_joint_mapping_is_unknown(self):
        f = run_variant(lambda s, m: s["anatomy"]["map"].update({"arm_f.bogus": {"joint": "elbow", "movement": "flex", "sign": 1}}))
        self.assertEqual(state(f, "anat.range:arm_f.bogus"), "unknown")
        self.assertEqual(state(baseline(), "anat.profile_coverage:hip.flex"), "unknown")       # profile joint nobody maps
        self.assertEqual(state(baseline(), "rep.joint_limits_2d:arm_f.shoulder"), "unknown")   # channel with no 2D limit

    def test_mandatory_unknown_blocks(self):
        ok = run_variant(lift_ground, review=self.review.record, full=True)
        self.assertEqual(ok["verdict"], "accepted", ok["summary"]["blocked_by"] + ok["summary"]["rejected_by"])

        def e(s, m):
            lift_ground(s, m)
            m["acceptance"].pop("foot_slide_px")
        rep = run_variant(e, review=self.review.record, full=True)
        self.assertEqual(rep["verdict"], "blocked")
        self.assertTrue(any(b.startswith("contact.foot_slide") for b in rep["summary"]["blocked_by"]))
        no_review = run_variant(lift_ground, full=True)                                   # artistic items await review
        self.assertEqual(no_review["verdict"], "blocked")
        bad = ReviewFixture("attack_hammer_B", tamper=True)
        try:
            tampered = run_variant(lift_ground, review=bad.record, full=True)
        finally:
            bad.close()
        self.assertEqual(tampered["verdict"], "blocked")
        self.assertIn("sha256", [f for f in tampered["findings"] if f["rule_id"] == "art.intent_read"][0]["reason"])

    def test_advisory_unknown_does_not_block(self):
        def e(s, m):
            lift_ground(s, m)
            s["anatomy"]["map"]["arm_f.wrist"]["joint"] = "wristt"
        rep = run_variant(e, review=self.review.record, full=True)
        self.assertEqual([f["state"] for f in rep["findings"] if f["id"].startswith("anat.range:arm_f.wrist")], ["unknown"])
        self.assertEqual(rep["verdict"], "accepted")
        self.assertTrue(any(g.startswith("anat.range:arm_f.wrist") for g in rep["summary"]["undetectable_defect_classes"]))

    def test_verified_but_ineligible_warns(self):
        def e(s, m):
            s["anatomy"]["limit_tier"] = "clinical"
            set_arm(m, 84, 300, -12, 120)
        f = [v for k, v in run_variant(e).items() if k.startswith("anat.range:arm_f.wrist")][0]
        self.assertEqual(f["state"], "warn")
        self.assertEqual(f["provenance"]["confidence"], "verified")          # LUTT number read in the source ...
        self.assertEqual(f["provenance"]["kind"], "clinical_reference")
        self.assertFalse(f["enforcement_eligible"])                         # ... is still not enforcement-eligible
        self.assertTrue(any("screen-projected" in r for r in f["eligibility_reasons"]))
        ok, why = ru.eligibility(ru.rule("anat.range"), "depth_3d", {"confidence": "verified", "gate_eligible": False})
        self.assertFalse(ok)                                                # not even on a depth rig without a record
        self.assertTrue(any("enforcement record" in r for r in why))

    def test_eligible_structural_invariant_fails(self):
        f = run_variant(lambda s, m: s["attachments"]["hammer"].update(count=2), full=True)
        att = [x for x in f["findings"] if x["rule_id"] == "structure.attachment"][0]
        self.assertEqual(att["state"], "fail")
        self.assertTrue(att["enforcement_eligible"])
        self.assertIn("structure.attachment", f["summary"]["rejected_by"])
        h = run_variant(lambda s, m: s["joints"]["hand_f"].update(parent="no_such_joint"))
        self.assertEqual(state(h, "structure.hierarchy"), "fail")

    def test_mirrored_clip_identical_outcomes(self):
        W = 832.0
        s, m = load()
        s2, m2 = copy.deepcopy(s), copy.deepcopy(m)
        for j in s2["joints"].values():
            j["rest"] = [W - j["rest"][0], j["rest"][1]]
        s2["attachments"]["hammer"]["rest_axis_deg"] = 180 - s["attachments"]["hammer"]["rest_axis_deg"]
        s2["anatomy"]["facing"] = "-x"
        for l in s2["legs"].values():
            l["bend"] = "-x"
        for c in s2["contacts"].values():
            c["toe"], c["heel"] = [-c["toe"][0], c["toe"][1]], [-c["heel"][0], c["heel"][1]]
        obj = s2["objects"]["hammer_master"]
        obj["grip_point"] = [obj["grip_point"][0], -obj["grip_point"][1]]
        obj["points"] = {k: [v[0], -v[1]] for k, v in obj["points"].items()}
        obj["shape"] = {k: [[q[0], -q[1]] for q in v] for k, v in obj["shape"].items()}
        for k in m2["keys"]:
            p = k["pose"]
            p["root"] = [-p["root"][0], p["root"][1]]
            for c in p["chains"]:
                p["chains"][c] = [-v for v in p["chains"][c]]
            p["shift"]["arm_f"] = [-p["shift"]["arm_f"][0], p["shift"]["arm_f"][1]]
            p["feet"] = {c: [-v[0], v[1]] for c, v in p["feet"].items()}
        a = pc.validate_data(s, m, DATA)
        b = pc.validate_data(s2, m2, DATA)
        sa = {f["id"]: f["state"] for f in a["findings"]}
        sb = {f["id"]: f["state"] for f in b["findings"]}
        self.assertEqual(sa, sb)
        self.assertEqual(a["summary"]["counts"], b["summary"]["counts"])
        va = {f["id"]: f["value"] for f in a["findings"] if isinstance(f["value"], (int, float)) and not isinstance(f["value"], bool)}
        vb = {f["id"]: f["value"] for f in b["findings"] if f["id"] in va}
        for k in va:
            self.assertAlmostEqual(va[k], vb[k], 1, k)

    def test_ground_penetration_case_fails(self):
        f = [v for k, v in baseline().items() if k == "environment.weapon_ground_penetration"][0]
        self.assertEqual(f["state"], "fail")
        self.assertTrue(f["enforcement_eligible"])
        self.assertAlmostEqual(f["value"]["max_below_ground"], 140.1, 1)
        self.assertEqual(f["value"]["frame_count"], 34)
        self.assertEqual(f["value"]["frame_span"], [56, 89])

    def test_non_strike_clip_not_applicable(self):
        s, m = load()
        idle = neutral_motion(s)
        idle["category"] = "locomotion.idle"
        idle["acceptance"] = copy.deepcopy(m["acceptance"])
        rep = pc.validate_data(s, idle, DATA)                               # must not crash
        strike = [f for f in rep["findings"] if f["rule_id"].startswith("strike.") or f["rule_id"] == "rep.face_zone_overlap"]
        self.assertTrue(strike)
        self.assertEqual({f["state"] for f in strike}, {"not_applicable"}, [(f["id"], f["state"]) for f in strike])
        no_cat = neutral_motion(s)                                          # no category: unknown, never a hammer default
        no_cat["acceptance"] = copy.deepcopy(m["acceptance"])
        rep2 = pc.validate_data(s, no_cat, DATA)
        self.assertEqual({f["state"] for f in rep2["findings"] if f["rule_id"].startswith("strike.")}, {"unknown"})
        self.assertEqual(rep2["verdict"], "blocked")

    def test_v1_motion_is_unknown_not_a_crash(self):
        with open(A_PATH) as fh:
            mA = json.load(fh)
        s, _ = load()
        rep = pc.validate_data(s, mA, DATA)
        self.assertEqual([f["state"] for f in rep["findings"] if f["rule_id"] == "meta.motion_schema"], ["unknown"])
        self.assertEqual(rep["verdict"], "blocked")

    def test_profile_override_provenance_not_verified(self):
        heavy = pc.load_profile(os.path.join(HERE, "profiles", "heavy_humanoid.json"))
        base = pc.load_profile(os.path.join(HERE, "profiles", "humanoid_base.json"))
        self.assertEqual(base["joints"]["elbow"]["movements"]["flex"]["provenance"]["clinical"]["confidence"], "verified")
        for jn in ("elbow", "hip", "spine", "neck"):
            mv = heavy["joints"][jn]["movements"]["flex"]
            self.assertNotIn("sources", mv)
            for tier in ("clinical", "functional", "stylized"):
                pv = mv["provenance"][tier]
                self.assertNotEqual(pv["confidence"], "verified", (jn, tier))
                self.assertFalse(pv["gate_eligible"])
                self.assertEqual(pv["origin"], "heavy_humanoid")
        # a child that overrides a range WITHOUT declaring provenance still does not inherit the base record
        tmp = tempfile.mkdtemp(prefix="profile_")
        try:
            shutil.copy(os.path.join(HERE, "profiles", "humanoid_base.json"), tmp)
            with open(os.path.join(tmp, "child.json"), "w") as fh:
                json.dump({"schema": "anatomy-profile.v1", "id": "child", "extends": "humanoid_base",
                           "overrides": {"joints": {"wrist": {"movements": {"flex": {"clinical": [-50, 50]}}, "why": "test"}}}}, fh)
            child = pc.load_profile(os.path.join(tmp, "child.json"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        pv = child["joints"]["wrist"]["movements"]["flex"]["provenance"]
        self.assertEqual((pv["clinical"]["kind"], pv["clinical"]["confidence"], pv["clinical"]["origin"]), ("heuristic", None, "child"))
        self.assertEqual(pv["functional"]["origin"], "humanoid_base")                   # untouched tiers keep theirs
        # the structure-level override (elbow stylized [-5, 160], measured on the overlay) is labelled as such
        f = [v for k, v in baseline().items() if k.startswith("anat.range:arm_f.elbow")][0]
        self.assertEqual(f["provenance"]["origin"], "structure:brute_hammer")
        self.assertNotEqual(f["provenance"]["confidence"], "verified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
