"""Rig/solver tests, regression tests and validator-semantics tests (Board amendment 2026-11-22; KA-BD-5 and
KA-BD-6, 2026-11-23; independent review and Board code review of PR #110, 2026-11-23). Run from spikes/motion with a
Python that has numpy, scipy and Pillow:

    python -I -s tests/test_motion_system.py

What kind of evidence each test is (Board code review 110-07):
  - unit tests: SolverTests (isolated joint movement on the benchmark rig) and the rules/registry checks
    (test_registry_rejects_unjustified_representation_exclusion, test_roles_come_from_the_profile_and_promotions).
  - synthetic regression fixtures: every other test. They edit the committed benchmark data in memory (a broken grip,
    an injected stretch, a renamed attachment, NaN, a stale review ...) or build a synthetic clip (the breathing idle)
    on the SAME heavy-hammer humanoid. lift_ground is a verdict-semantics fixture only: moving the ground line proves
    nothing about a valid motion. The review fixture's GIF is a synthetic stand-in for evidence hashing, not a
    preview: it says nothing about visual quality.
  - actual motion benchmarks: the committed motions B and C and the pose library, as stored (test_baseline_*,
    test_ground_penetration_case_fails, test_mirrored_clip_identical_outcomes, test_benchmark_C_outcome).
  - visual review: none. Production validation: none. No CI workflow runs this suite; it is run locally.
The solver is validated on one structure (the heavy-hammer benchmark humanoid); tests of other entities assert that
they are reported unsupported, not that they are animated correctly. Nothing is written into the repository.
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


def run_variant(edit, review=None, full=False, reg=None):
    """Validate an edited copy of structure + motion B in memory (nothing is written into the repository).
    review: None (no record), True (a record bound to the edited revision plus a governed approval) or a dict of
    ReviewFixture options."""
    s, m = load()
    edit(s, m)
    if review is None:
        rep = pc.validate_data(s, m, DATA, None, reg=reg)
    else:
        fx = ReviewFixture(s, m, reg=reg, **(review if isinstance(review, dict) else {}))
        try:
            rep = pc.validate_data(s, m, DATA, fx.record, reg=reg, approval=fx.approval)
        finally:
            fx.close()
    return rep if full else {f["id"]: f for f in rep["findings"]}


def registry_without_value(rule_id):
    """An in-memory registry whose registry-owned threshold for rule_id has no value (missing mandatory data)."""
    with open(ru.REGISTRY_PATH) as fh:
        raw = json.load(fh)
    for r in raw["rules"]:
        if r["id"] == rule_id:
            r["threshold"].pop("value")
    return ru.prepare_registry(raw)


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
    """Verdict-semantics fixture only: move the ground line down so B has no ground penetration and the verdict logic
    can be tested in isolation. It does NOT make B a valid motion (the real B is rejected for its penetration)."""
    for c in s["contacts"].values():
        c["ground_y"] += dy


class ReviewFixture:
    """Evidence-hashing fixture: a review record bound to the revision of (s, m) and, unless approve=False, a separate
    governed approval record. The 'GIF' is a synthetic stand-in for hashing, not a preview (no visual quality)."""

    def __init__(self, s, m, items="pass", tamper=False, approve=True, approver="board (test)", role="board", reg=None):
        self.dir = tempfile.mkdtemp(prefix="motion_review_")
        ev = os.path.join(self.dir, "preview.gif")
        with open(ev, "wb") as fh:
            fh.write(b"GIF89a evidence stand-in for the test")
        with open(ev, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        if tamper:
            digest = "0" * 64
        self.record = {"schema": "motion-review.v1", "motion": m.get("id"), "reviewer": "director (test)", "date": "2026-11-23",
                       "binding": pc.review_binding(s, m, DATA, reg),
                       "evidence": [{"path": "preview.gif", "sha256": digest}], "items": {rid: items for rid in pc.ART_ITEMS},
                       "_base": self.dir}
        self.approval = None
        if approve:
            self.approval = {"ref": "TEST-APPROVAL-1", "approved_by": approver, "role": role, "date": "2026-11-23",
                             "review_sha256": pc.content_sha256({k: v for k, v in self.record.items() if k != "_base"})}

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class SemanticsTests(unittest.TestCase):
    """KA-BD-5 / KA-BD-6 regression tests (Board, 2026-11-23). Synthetic regression fixtures on the benchmark."""

    def test_unknown_is_never_pass(self):
        f = run_variant(lambda s, m: s["anatomy"]["map"]["arm_f.wrist"].update(joint="wristt"))
        rng = [v for k, v in f.items() if k.startswith("anat.range:arm_f.wrist")]
        self.assertEqual([v["state"] for v in rng], ["unknown"])
        self.assertIn("wristt", rng[0]["reason"])
        self.assertEqual(ru.classify("anat.range", {"representation": "planar_2d", "category": "x", "entity_tags": set(),
                                                     "phases": set(), "events": set()}, measured=False)["state"], "unknown")
        # CHANGED (review of PR #110, H2): structural thresholds are registry-owned, so the missing-data case is a
        # registry without the value (the motion dropping its copy no longer matters). Still unknown, no default.
        missing = run_variant(lambda s, m: None, reg=registry_without_value("structure.bone_length_constant"))
        self.assertEqual(state(missing, "structure.bone_length_constant"), "unknown")   # no hammer default fills it
        no_motion_value = run_variant(lambda s, m: m["acceptance"].pop("com_back_in_windup_px"))
        self.assertEqual(state(no_motion_value, "strike.weight_back_in_windup"), "unknown")  # motion-owned, missing

    def test_missing_joint_mapping_is_unknown(self):
        f = run_variant(lambda s, m: s["anatomy"]["map"].update({"arm_f.bogus": {"joint": "elbow", "movement": "flex", "sign": 1}}))
        self.assertEqual(state(f, "anat.range:arm_f.bogus"), "unknown")
        self.assertEqual(state(baseline(), "anat.profile_coverage:hip.flex"), "unknown")       # profile joint nobody maps
        self.assertEqual(state(baseline(), "rep.joint_limits_2d:arm_f.shoulder"), "unknown")   # channel with no 2D limit

    def test_mandatory_unknown_blocks(self):
        ok = run_variant(lift_ground, review=True, full=True)
        self.assertEqual(ok["verdict"], "accepted", ok["summary"]["blocked_by"] + ok["summary"]["rejected_by"])

        # CHANGED (H2): the missing mandatory value is removed from the registry, which owns it now
        rep = run_variant(lift_ground, review=True, full=True, reg=registry_without_value("contact.foot_slide"))
        self.assertEqual(rep["verdict"], "blocked")
        self.assertTrue(any(b.startswith("contact.foot_slide") for b in rep["summary"]["blocked_by"]))
        no_review = run_variant(lift_ground, full=True)                                   # artistic items await review
        self.assertEqual(no_review["verdict"], "blocked")
        tampered = run_variant(lift_ground, review={"tamper": True}, full=True)
        self.assertEqual(tampered["verdict"], "blocked")
        self.assertIn("sha256", [f for f in tampered["findings"] if f["rule_id"] == "art.intent_read"][0]["reason"])

    def test_advisory_unknown_does_not_block(self):
        def e(s, m):
            lift_ground(s, m)
            s["anatomy"]["map"]["arm_f.wrist"]["joint"] = "wristt"
        rep = run_variant(e, review=True, full=True)
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
        # CHANGED (review of PR #110, H3): measured against the floor the feet stand on (contact points, y 990), not
        # the ankle height ground_y 972: B is 122.1 px through the floor (was reported as 140.1), same 34 frames.
        f = [v for k, v in baseline().items() if k == "environment.weapon_ground_penetration"][0]
        self.assertEqual(f["state"], "fail")
        self.assertTrue(f["enforcement_eligible"])
        self.assertAlmostEqual(f["value"]["max_below_ground"], 122.1, 1)
        self.assertEqual(f["value"]["ground_reference"]["line_y"], 990.0)
        self.assertIn("contact points", f["value"]["ground_reference"]["source"])
        # the 140 px regression is kept: against the ankle line (y 972) the same clip is 140.1 px deep, same frames
        ankle = run_variant(lambda s, m: s.__setitem__("ground", {"line_y": 972}))["environment.weapon_ground_penetration"]
        self.assertEqual(ankle["state"], "fail")
        self.assertAlmostEqual(ankle["value"]["max_below_ground"], 140.1, 1)
        self.assertEqual((ankle["value"]["frame_count"], ankle["value"]["frame_span"]), (34, [56, 89]))
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


ACC_STRUCT = {"bone_length_dev_px": 0.01, "grip_error_px": 0.5, "foot_slide_px": 2.0, "ground_penetration_tol_px": 3.0}


def idle_motion(s, mid="idle_breath", contacts=True):
    """Synthetic fixture: a non-strike breathing idle written independently of B (not derived by moving the ground).
    Used on the same heavy-hammer humanoid (the only validated structure) or on unsupported structures."""
    keys = []
    for f, dy, sp in ((0, 0, 0), (30, 6, -3), (60, 0, 0)):
        pose = {"root": [0, dy], "chains": {c: [0.0] * len(v["channels"]) for c, v in s["chains"].items()},
                "shift": {c: [0, 0] for c, v in s["chains"].items() if v.get("shift")},
                "feet": {l["contact"]: [0, 0] for l in (s.get("legs") or {}).values()}}
        first = next(iter(s["chains"]))
        pose["chains"][first][0] = sp
        keys.append({"frame": f, "ease": "inout", "pose": pose})
    cons = [{"type": "contact", "contact": c, "frames": [0, 61]} for c in (s.get("contacts") or {})] if contacts else []
    return {"schema": "motion.v2", "id": mid, "category": "locomotion.idle", "fps": 30, "keys": keys,
            "phases": [{"name": "idle", "start": 0, "end": 60}], "events": [], "constraints": cons,
            "acceptance": dict(ACC_STRUCT)}


def validate_with_review(s, m, reg=None, **kw):
    fx = ReviewFixture(s, m, reg=reg, **kw)
    try:
        return pc.validate_data(s, m, DATA, fx.record, reg=reg, approval=fx.approval)
    finally:
        fx.close()


def hovering(s):
    """Remove legs, contacts and the leg joints/bones of the benchmark structure (a hovering humanoid)."""
    s["legs"], s["contacts"] = {}, {}
    for j in ("hip_k", "knee_k", "ankle_k", "hip_f", "knee_f", "ankle_f"):
        s["joints"].pop(j)
    for b in ("thigh_k", "shin_k", "thigh_f", "shin_f"):
        s["bones"].pop(b)
        s["masses"].pop(b)
    s["anatomy"]["derived"] = {k: v for k, v in s["anatomy"]["derived"].items() if not k.startswith("knee")}


def unarmed(s):
    s.pop("attachments")
    s.pop("objects")
    s["masses"].pop("hammer")


def quadruped():
    return {"schema": "structure.v2", "id": "quad", "entity_tags": ["quadruped"], "representation": "planar_2d",
            "joints": {"pelvis": {"parent": None, "rest": [300, 500]}, "chest": {"parent": "pelvis", "rest": [500, 500]},
                       "head": {"parent": "chest", "rest": [620, 420]},
                       "hip_r": {"parent": "pelvis", "rest": [300, 510]}, "knee_r": {"parent": "hip_r", "rest": [310, 600]},
                       "ankle_r": {"parent": "knee_r", "rest": [300, 690]}},
            "bones": {"back": {"from": "pelvis", "to": "chest", "width": 80}, "head": {"from": "chest", "to": "head", "width": 40},
                      "thigh_r": {"from": "hip_r", "to": "knee_r", "width": 30}, "shin_r": {"from": "knee_r", "to": "ankle_r", "width": 20}},
            "chains": {"body": {"joints": ["pelvis", "chest", "head"], "channels": ["spine", "head"], "base": "root"}},
            "legs": {"leg_r": {"joints": ["hip_r", "knee_r", "ankle_r"], "contact": "paw_r", "bend": "-x"}},
            "masses": {"back": 0.6}, "contacts": {"paw_r": {"joint": "ankle_r", "ground_y": 690, "toe": [10, 5], "heel": [-10, 5]}},
            "proxy": {"back": [], "body": ["back"], "front": [], "torso": ["pelvis", "chest", "hip_r"], "head_circle": {"joint": "head", "r": 30}},
            "anatomy": {"profile": "../profiles/quadruped.json", "facing": "+x", "map": {}}}


def by_rule(rep, rule_id):
    return sorted({f["state"] for f in rep["findings"] if f["rule_id"] == rule_id})


def kinds(rep, rule_id):
    return sorted({f["unknown_kind"] for f in rep["findings"] if f["rule_id"] == rule_id and f["state"] == "unknown"})


def registry_with(edit):
    with open(ru.REGISTRY_PATH) as fh:
        raw = json.load(fh)
    edit(raw)
    return ru.prepare_registry(raw)


STRUCTURAL = ("structure.hierarchy", "structure.bone_length_constant", "structure.attachment", "structure.grip",
              "structure.weapon_rigid", "structure.reachability", "contact.foot_slide", "environment.weapon_ground_penetration")
DIRECTIONAL = ("strike.weight_back_in_windup", "strike.weight_forward_at_impact", "strike.anticipation_opposite",
               "strike.follow_through", "strike.continuous_swing_arc")


class BoardCodeReviewTests(unittest.TestCase):
    """Regression tests for the independent review and the Board code review of PR #110 (2026-11-23): 110-01..110-07
    and the earlier H/M items. Synthetic regression fixtures unless stated."""

    # ---- 110-01 mandatory acceptance authority (H2)
    def test_attempted_mandatory_rule_downgrade(self):
        demote = run_variant(lambda s, m: m["acceptance"].update(roles={"environment.weapon_ground_penetration": "advisory"}),
                             full=True)
        g = [f for f in demote["findings"] if f["rule_id"] == "environment.weapon_ground_penetration"][0]
        self.assertEqual((g["state"], g["role"]), ("fail", "mandatory"))
        self.assertEqual(demote["verdict"], "rejected")
        self.assertEqual(by_rule(demote, "meta.acceptance_overrides"), ["warn"])
        # an exception the registry does not hold (or holds without approval) is refused and reported
        req = [{"id": "EXC-1", "rule": "environment.weapon_ground_penetration", "why": "the motion says so"}]
        rep = run_variant(lambda s, m: m["acceptance"].update(exceptions=req), full=True)
        self.assertEqual(rep["verdict"], "rejected")
        self.assertIn("no approved exception", rep["summary"]["acceptance_overrides"]["refused"][0]["why"])
        unapproved = {"id": "EXC-1", "rule": "environment.weapon_ground_penetration", "scope": {"motion_ids": ["attack_hammer_B"]},
                      "provenance": "test", "approval": {"approved_by": "", "date": "2026-11-23", "ref": ""}}
        reg = registry_with(lambda r: r["approved_exceptions"].append(unapproved))
        rep = run_variant(lambda s, m: m["acceptance"].update(exceptions=req), full=True, reg=reg)
        self.assertEqual(rep["verdict"], "rejected")
        self.assertIn("approval record", rep["summary"]["acceptance_overrides"]["refused"][0]["why"])
        approved = dict(unapproved, approval={"approved_by": "Board (test)", "date": "2026-11-23", "ref": "TEST-DECISION"})
        reg = registry_with(lambda r: r["approved_exceptions"].append(approved))
        rep = run_variant(lambda s, m: m["acceptance"].update(exceptions=req), full=True, reg=reg)
        g = [f for f in rep["findings"] if f["rule_id"] == "environment.weapon_ground_penetration"][0]
        self.assertEqual((g["state"], g["role"]), ("fail", "advisory"))          # still measured and reported as fail
        self.assertNotIn("environment.weapon_ground_penetration", rep["summary"]["rejected_by"])
        other = run_variant(lambda s, m: (m.__setitem__("id", "other"), m["acceptance"].update(exceptions=req)), full=True, reg=reg)
        self.assertEqual(other["verdict"], "rejected")                            # out of the exception's scope

    def test_unauthorized_threshold_change(self):
        loose = run_variant(lambda s, m: m["acceptance"].update(ground_penetration_tol_px=200), full=True)
        g = [f for f in loose["findings"] if f["rule_id"] == "environment.weapon_ground_penetration"][0]
        self.assertEqual((g["state"], g["threshold"], g["threshold_owner"]), ("fail", 3.0, "registry"))
        self.assertEqual(loose["verdict"], "rejected")
        orig = mo.Solver.solve

        def stretched(self_, f):                       # an injected 10 % forearm stretch, frames 20-22
            fr = orig(self_, f)
            if 20 <= f <= 22:
                d = (fr["J"]["wrist_f"] - fr["J"]["elbow_f"]) * 0.10
                for j in ("wrist_f", "hand_f"):
                    fr["J"][j] = fr["J"][j] + d
            return fr
        mo.Solver.solve = stretched
        try:
            rep = run_variant(lambda s, m: (lift_ground(s, m), m["acceptance"].update(bone_length_dev_px=1e9)), full=True)
        finally:
            mo.Solver.solve = orig
        self.assertEqual(by_rule(rep, "structure.bone_length_constant"), ["fail"])
        self.assertEqual(rep["verdict"], "rejected")

    def test_motion_may_tighten_and_promote(self):
        def e(s, m):
            lift_ground(s, m)
            m["acceptance"].update(grip_error_px=0.1, roles={"phys.com_inside_support": "mandatory"})
        rep = run_variant(e, review=True, full=True)
        self.assertEqual([f["threshold"] for f in rep["findings"] if f["rule_id"] == "structure.grip"], [0.1])
        self.assertEqual([f["role"] for f in rep["findings"] if f["rule_id"] == "phys.com_inside_support"], ["mandatory"])
        self.assertEqual(by_rule(rep, "meta.acceptance_overrides"), ["pass"])

    def test_acceptance_profile_unknown_or_out_of_scope(self):
        rep = run_variant(lambda s, m: (lift_ground(s, m), m["acceptance"].update(profile="strict")), review=True, full=True)
        self.assertEqual(by_rule(rep, "meta.acceptance_profile"), ["unknown"])           # M3: no KeyError
        self.assertEqual(rep["verdict"], "blocked")
        rep = run_variant(lambda s, m: (lift_ground(s, m), m["acceptance"].update(profile="pose_library")), full=True)
        self.assertEqual(by_rule(rep, "meta.acceptance_profile"), ["unknown"])
        self.assertEqual({f["role"] for f in rep["findings"] if f["rule_id"].startswith("art.")}, {"mandatory"})

    def test_roles_come_from_the_profile_and_promotions(self):
        rep = run_variant(lambda s, m: None, full=True)
        roles = {f["rule_id"]: f["role"] for f in rep["findings"]}
        self.assertEqual(roles["structure.grip"], "mandatory")
        self.assertEqual(roles["strike.extension_at_impact"], "advisory")                # 110-06
        prom = run_variant(lambda s, m: m["acceptance"].update(roles={"phys.com_inside_support": "mandatory"}), full=True)
        self.assertEqual([f["role"] for f in prom["findings"] if f["rule_id"] == "phys.com_inside_support"], ["mandatory"])
        self.assertEqual(ru.role_of("art.intent_read", {"acceptance_profile": "pose_library"}), "advisory")
        self.assertEqual(ru.role_of("art.intent_read", {"acceptance_profile": "default"}), "mandatory")

    # ---- 110-02 representation capability (H1), category vocabulary (M2)
    def test_representation_mismatch(self):
        for decl, kind in (("depth_3d", "unsupported"), ("planar2d", "invalid_input"), (None, "invalid_input")):
            def e(s, m, decl=decl):
                lift_ground(s, m)
                s["objects"]["hammer_master"]["grip_point"] = [30, 0]       # a broken grip the planar solver would see
                if decl is None:
                    s.pop("representation")
                else:
                    s["representation"] = decl
            rep = run_variant(e, review=True, full=True)
            self.assertEqual(by_rule(rep, "meta.representation"), ["unknown"], decl)
            self.assertEqual(kinds(rep, "meta.representation"), [kind], decl)
            for rid in STRUCTURAL:                    # not solved: never pass, never not_applicable
                self.assertEqual(by_rule(rep, rid), ["unknown"], (decl, rid))
            self.assertFalse([f for f in rep["findings"] if f["rule_id"].startswith("anat.")], decl)   # nothing relabelled
            self.assertEqual(rep["verdict"], "blocked", decl)
            self.assertEqual(rep["representation"], "planar_2d")

    def test_registry_rejects_unjustified_representation_exclusion(self):
        with open(ru.REGISTRY_PATH) as fh:
            raw = json.load(fh)
        for edit in (lambda r: [x for x in r["rules"] if x["id"] == "structure.grip"][0]["scope"].update(representations=["planar_2d"]),
                     lambda r: r["acceptance_profiles"]["default"]["mandatory"].remove("environment.weapon_ground_penetration"),
                     lambda r: [x for x in r["rules"] if x["id"] == "structure.grip"][0]["threshold"].update(owner="motion")):
            bad = copy.deepcopy(raw)
            edit(bad)
            with self.assertRaises(ValueError):
                ru.prepare_registry(bad)

    def test_misspelt_category_is_unknown(self):
        rep = run_variant(lambda s, m: (lift_ground(s, m), m.__setitem__("category", "strike.heavy_overhed")), review=True, full=True)
        self.assertEqual(by_rule(rep, "meta.category_declared"), ["unknown"])
        self.assertEqual(kinds(rep, "meta.category_declared"), ["invalid_input"])
        for rid in DIRECTIONAL + ("strike.contact_speed", "strike.proximal_to_distal"):
            self.assertEqual(by_rule(rep, rid), ["unknown"], rid)              # never not_applicable
        self.assertEqual(rep["verdict"], "blocked")

    # ---- 110-03 review evidence binding and governed approval
    def test_bound_review_with_governed_approval_accepts(self):
        rep = run_variant(lift_ground, review=True, full=True)
        self.assertEqual(rep["verdict"], "accepted", rep["summary"]["blocked_by"])
        self.assertEqual(by_rule(rep, "art.intent_read"), ["pass"])

    def test_stale_review_record(self):
        s, m = load()
        lift_ground(s, m)
        old_reg = registry_with(lambda r: r["coverage_gaps"].append("an older validation profile"))
        fx = ReviewFixture(s, m, reg=old_reg)        # reviewed under another validation-profile revision
        try:
            rep = pc.validate_data(s, m, DATA, fx.record, approval=fx.approval)
        finally:
            fx.close()
        self.assertEqual(by_rule(rep, "art.intent_read"), ["unknown"])
        self.assertIn("stale review", [f for f in rep["findings"] if f["rule_id"] == "art.intent_read"][0]["reason"])
        self.assertEqual(rep["verdict"], "blocked")

    def test_review_invalid_after_modified_motion(self):
        s, m = load()
        lift_ground(s, m)
        fx = ReviewFixture(s, m)
        try:
            key(m, 30)["pose"]["root"][0] += 1.0       # a material change after the review
            rep = pc.validate_data(s, m, DATA, fx.record, approval=fx.approval)
        finally:
            fx.close()
        self.assertIn("motion", [f for f in rep["findings"] if f["rule_id"] == "art.intent_read"][0]["reason"])
        self.assertEqual(rep["verdict"], "blocked")

    def test_review_invalid_after_modified_structure(self):
        s, m = load()
        lift_ground(s, m)
        fx = ReviewFixture(s, m)
        try:
            s["joints"]["hand_f"]["rest"][0] += 1.0
            rep = pc.validate_data(s, m, DATA, fx.record, approval=fx.approval)
        finally:
            fx.close()
        self.assertIn("structure", [f for f in rep["findings"] if f["rule_id"] == "art.intent_read"][0]["reason"])
        self.assertEqual(rep["verdict"], "blocked")

    def test_recorded_review_is_not_governed_approval(self):
        for opts, why in (({"approve": False}, "no governed approval"),
                          ({"approver": "director (test)"}, "not independent"),
                          ({"role": "director"}, "role")):
            rep = run_variant(lift_ground, review=opts, full=True)
            f = [x for x in rep["findings"] if x["rule_id"] == "art.intent_read"][0]
            self.assertEqual(f["state"], "unknown", opts)
            self.assertIn("awaiting governed approval", f["reason"])
            self.assertIn(why, f["reason"])
            self.assertEqual(rep["verdict"], "blocked")

    # ---- 110-04 declared supported scope (H4): explicit unsupported, no crash, no false verdict
    def test_unsupported_entities_are_explicit(self):
        s, _ = load()
        cases = {}
        su = copy.deepcopy(s)
        unarmed(su)
        cases["unarmed"] = su
        ss = copy.deepcopy(s)
        ss["attachments"] = {"sword": ss["attachments"].pop("hammer")}
        cases["sword"] = ss
        cases["quadruped"] = quadruped()
        sh = copy.deepcopy(su)
        hovering(sh)
        cases["hovering unarmed"] = sh
        sa = copy.deepcopy(s)
        hovering(sa)
        cases["hovering armed"] = sa
        sf = copy.deepcopy(s)
        sf["anatomy"]["profile"] = "../profiles/flying_creature.json"
        cases["flying profile"] = sf
        for name, st in cases.items():
            rep = validate_with_review(st, idle_motion(st))
            self.assertEqual(by_rule(rep, "meta.solver_scope"), ["unknown"], name)
            self.assertEqual(kinds(rep, "meta.solver_scope"), ["unsupported"], name)
            self.assertTrue(rep["summary"]["unsupported"], name)
            for rid in STRUCTURAL:
                self.assertEqual(by_rule(rep, rid), ["unknown"], (name, rid))
            self.assertEqual(rep["verdict"], "blocked", name)
        fly = pc.load_profile(os.path.join(HERE, "profiles", "flying_creature.json"))     # no crash on the 'legs' note
        self.assertIn("legs", fly["joint_notes"])

    def test_non_strike_idle_on_the_hammer_humanoid(self):
        """110-07: the only valid-motion fixture not derived from B by moving the ground: a synthetic idle written
        independently, on the same hammer humanoid (the solver's only validated structure), with the real floor."""
        s, _ = load()
        rep = validate_with_review(s, idle_motion(s))
        self.assertEqual(rep["verdict"], "accepted", rep["summary"]["blocked_by"] + rep["summary"]["rejected_by"])
        strike = {f["state"] for f in rep["findings"] if f["rule_id"].startswith("strike.")}
        self.assertEqual(strike, {"not_applicable"})

    # ---- 110-05 invalid input vs unsupported vs unmeasurable; no blanket exception handler
    def test_invalid_input_cases(self):
        cases = {
            "out-of-range event frame": (lambda s, m: m["events"][1].update(frame=500), "motion.events[1].frame"),
            "invalid phase range": (lambda s, m: m["phases"][2].update(start=50, end=40), "motion.phases[2]"),
            "missing attachment asset": (lambda s, m: s["attachments"]["hammer"].update(asset="nope"), "structure.attachments.hammer.asset"),
            "missing contact point": (lambda s, m: s["contacts"]["foot_k"].pop("toe"), "structure.contacts.foot_k.toe"),
            "unknown anatomy profile": (lambda s, m: s["anatomy"].update(profile="../profiles/nope.json"), "structure.anatomy.profile"),
            "non-finite number": (lambda s, m: key(m, 30)["pose"]["chains"]["arm_f"].__setitem__(0, float("nan")), "motion.keys"),
            "undeclared contact in a constraint": (lambda s, m: m["constraints"][0].update(contact="foot_x"), "motion.constraints[0].contact"),
            "malformed key": (lambda s, m: m["keys"][3]["pose"]["chains"].pop("arm_f"), "motion.keys[3].pose.chains.arm_f"),
        }
        for name, (edit, field) in cases.items():
            rep = run_variant(edit, full=True)
            self.assertEqual(by_rule(rep, "meta.input_valid"), ["unknown"], name)
            self.assertEqual(kinds(rep, "meta.input_valid"), ["invalid_input"], name)
            self.assertTrue(any(field in e for e in rep["summary"]["input_errors"]), (name, rep["summary"]["input_errors"]))
            self.assertEqual(rep["verdict"], "blocked", name)

    def test_unmeasurable_is_not_invalid(self):
        f = run_variant(lambda s, m: s["anatomy"]["map"].update({"arm_f.bogus": {"joint": "elbow", "movement": "flex", "sign": 1}}),
                        full=True)                       # missing mapping target: advisory unknown naming the field
        a = [x for x in f["findings"] if x["id"] == "anat.range:arm_f.bogus"][0]
        self.assertEqual((a["state"], a["unknown_kind"], a["role"]), ("unknown", "unmeasurable", "advisory"))
        self.assertIn("structure.anatomy.map.arm_f.bogus", a["reason"])
        t = run_variant(lambda s, m: s["anatomy"].update(limit_tier="cartoon"), full=True)
        self.assertTrue(all("limit_tier" in x["reason"] for x in t["findings"] if x["rule_id"] == "anat.range" and x["state"] == "unknown"))
        g = run_variant(lambda s, m: [c.pop("ground_y") for c in s["contacts"].values()], full=True)
        gf = [x for x in g["findings"] if x["rule_id"] == "environment.weapon_ground_penetration"][0]
        self.assertEqual((gf["state"], gf["unknown_kind"]), ("unknown", "unmeasurable"))
        self.assertEqual(by_rule(g, "meta.input_valid"), ["pass"])

    def test_programming_errors_are_not_hidden(self):
        orig = mo.run_checks

        def boom(*a, **k):
            raise ZeroDivisionError("a bug in a check")
        mo.run_checks = boom
        try:
            with self.assertRaises(ZeroDivisionError):
                run_variant(lambda s, m: None)
        finally:
            mo.run_checks = orig

    # ---- 110-06 advisory by default; ground tolerance labelled experimental (M6)
    def test_strike_heuristics_are_advisory_by_default(self):
        rep = run_variant(lambda s, m: (lift_ground(s, m), m.__setitem__("phases", [p for p in m["phases"] if p["name"] != "windup"])),
                          review=True, full=True)
        self.assertEqual(by_rule(rep, "strike.weight_back_in_windup"), ["unknown"])
        self.assertEqual(rep["verdict"], "accepted")      # a missing advisory measurement does not block
        g = [f for f in run_variant(lambda s, m: None, full=True)["findings"] if f["rule_id"] == "environment.weapon_ground_penetration"][0]
        for word in ("experimental", "benchmark", "not a universal Studio threshold", "awaiting Board confirmation"):
            self.assertIn(word, g["threshold_status"])

    def test_benchmark_C_outcome(self):
        """Actual motion benchmark: C as committed. Projection artefacts warn (advisory), nothing blocks except the
        artistic review; with a bound review and approval it is accepted (warns never block)."""
        with open(os.path.join(DATA, "attack_hammer_C.motion.json")) as fh:
            mC = json.load(fh)
        s, _ = load()
        rep = validate_with_review(s, mC)
        self.assertEqual(rep["verdict"], "accepted", rep["summary"]["blocked_by"] + rep["summary"]["rejected_by"])
        self.assertTrue(rep["summary"]["warnings"])
        self.assertFalse([f for f in rep["findings"] if f["state"] == "warn" and f["role"] == "mandatory"])

    # ---- H3 ground reference = the floor the feet stand on
    def test_weapon_near_the_drawn_floor(self):
        s, m = load()
        sol = mo.Solver(s, m)
        low = max(max(float(q[1]) for poly in sol.solve(f)["shape"].values() for q in poly) for f in range(sol.n))
        sole = s["contacts"]["foot_k"]["toe"][1]

        def at(offset):                                  # floor line = low + offset (ankle line = floor - sole)
            def e(s_, m_):
                for c in s_["contacts"].values():
                    c["ground_y"] = low + offset - sole
            return run_variant(e)["environment.weapon_ground_penetration"]
        touch = at(5)                                    # 5 px above the floor, 13 px below the ankle line
        self.assertEqual(touch["state"], "pass", touch["value"])
        self.assertAlmostEqual(touch["value"]["max_below_ground"], -5.0, 3)
        self.assertEqual(at(-10)["state"], "fail")       # 10 px through the floor
        self.assertEqual(touch["threshold"], 3.0)        # M6: value unchanged
        line = run_variant(lambda s_, m_: s_.__setitem__("ground", {"line_y": low + 1}))["environment.weapon_ground_penetration"]
        self.assertEqual((line["state"], line["value"]["ground_reference"]["source"]), ("pass", "structure.ground.line_y"))

    # ---- M1 facing
    def test_missing_facing_is_unknown_for_directional_rules(self):
        rep = run_variant(lambda s, m: (lift_ground(s, m), s["anatomy"].pop("facing")), review=True, full=True)
        for rid in DIRECTIONAL + ("rep.knee_bend_side_2d", "rep.joint_limits_2d", "anat.shoulder_extension_behind"):
            self.assertEqual(by_rule(rep, rid), ["unknown"], rid)
        self.assertIn("facing", [f for f in rep["findings"] if f["rule_id"] == "strike.follow_through"][0]["reason"])
        base = run_variant(lift_ground, full=True)
        for rid in DIRECTIONAL:
            self.assertEqual(by_rule(base, rid), ["pass"], rid)

    # ---- M4 and the undetected mutation "joint_limits_2d disabled"
    def test_joint_limits_2d_detects_and_wraps(self):
        self.assertEqual(state(baseline(), "rep.joint_limits_2d:trunk.spine"), "pass")
        f = run_variant(lambda s, m: key(m, 30)["pose"]["chains"]["trunk"].__setitem__(0, 60.0))
        self.assertEqual(state(f, "rep.joint_limits_2d:trunk.spine"), "warn")
        s, _ = load()
        out = {}
        for label, extra in (("-60", 0.0), ("+300", 360.0)):
            m = idle_motion(s)
            rest = mo.Solver(s, m).chain_rest["arm_b"]["rel"][1]
            for k in m["keys"]:
                k["pose"]["chains"]["arm_b"][1] = (-60 - rest) + extra
            rep = pc.validate_data(copy.deepcopy(s), m, DATA)
            g = [x for x in rep["findings"] if x["id"] == "rep.joint_limits_2d:arm_b.elbow"][0]
            out[label] = (g["state"], g["value"])
        self.assertEqual(out["-60"], out["+300"])
        self.assertEqual(out["-60"][0], "pass")

    # ---- M5 missing contact declaration
    def test_missing_contact_declaration_is_unknown(self):
        s, _ = load()
        m = idle_motion(s, contacts=False)
        rep = validate_with_review(copy.deepcopy(s), m)
        self.assertEqual(by_rule(rep, "contact.foot_slide"), ["unknown"])
        self.assertEqual(rep["verdict"], "blocked")
        m["contacts"] = "none"                           # explicit, recorded opt-out
        rep = validate_with_review(copy.deepcopy(s), m)
        f = [x for x in rep["findings"] if x["rule_id"] == "contact.foot_slide"][0]
        self.assertEqual(f["state"], "not_applicable")
        self.assertIn("contacts", f["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
