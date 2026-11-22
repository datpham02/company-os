"""Method C (Board R&D, 2026-11-22): reference-driven motion. CMU mocap -> 2D projection -> retarget to a studio
structure.v2 -> motion.v2 (dense FK offsets, PCHIP, broken tangent at the detected impact).

    python -I -s retarget_cmu.py <map.json> <structure.json> <out motion.json>

All character/clip specifics are in the map file (source files, frame window, camera yaw, joint mapping, weapon
rule, adjustments); this script has no knowledge of the hammer character.
Steps: FK of the source -> orthographic projection (screen x = forward rotated by yaw, y = up) -> per-frame bone
directions -> trunk/head as offsets from the source's neutral frame added to the target rest posture; arms as bone
directions in the chest frame (target bone lengths kept); shoulder shift from the source clavicle motion; weapon axis
from the line through both hands (sign kept continuous); feet from the source ankles; phases detected from hand
height and speed; impact = largest hand deceleration after the swing peak (a broken-tangent key).
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cmu_amc as cmu  # noqa: E402


def ang(v):
    return math.degrees(math.atan2(v[1], v[0]))


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def unwrap(seq):
    out = [seq[0]]
    for v in seq[1:]:
        out.append(out[-1] + wrap(v - out[-1]))
    return np.array(out)


def main(map_path, structure_path, out_path):
    M = json.load(open(map_path))
    S = json.load(open(structure_path))
    base = os.path.dirname(os.path.abspath(map_path))
    B, H = cmu.read_asf(os.path.join(base, M["source"]["asf"]))
    F = cmu.read_amc(os.path.join(base, M["source"]["amc"]))
    f0, f1 = M["source"]["frames"]
    P3 = [cmu.fk(B, H, F[i]) for i in range(f0, f1 + 1)]
    end = lambda p, b: p[b][1]
    start = lambda p, b: p[b][0]
    # camera: forward from the pelvis at the first frame, rotated by yaw about the vertical
    p = P3[0]
    lat = start(p, M["source"]["lateral_pair"][1]) - start(p, M["source"]["lateral_pair"][0])
    lat[1] = 0
    lat /= np.linalg.norm(lat)
    fwd = np.cross(np.array([0, 1.0, 0]), lat) * M["camera"].get("forward_sign", 1)
    a = math.radians(M["camera"]["yaw_deg"])
    sx = math.cos(a) * fwd + math.sin(a) * lat
    pr = lambda q: np.array([float(q @ sx), -float(q[1])])         # y down like the studio canvas
    J = [{k: pr(v) for k, v in [(n, end(pp, n)) for n in pp] + [("root", pp["root"][0])]} for pp in P3]
    jm = M["joints"]                                                 # target joint -> source bone end
    src = lambda fr, tj: fr[jm[tj]] if jm[tj] != "root" else fr["root"]
    R = {j: np.array(v["rest"], float) for j, v in S["joints"].items()}
    rest_dir = lambda a_, b_: ang(R[b_] - R[a_])
    n = len(J)
    # scale: target leg length / source leg length (projected, frame 0)
    def leg(fr, hip, ank):
        return np.linalg.norm(src(fr, hip) - src(fr, ank))
    s_leg = np.mean([leg(J[0], "hip_k", "ankle_k"), leg(J[0], "hip_f", "ankle_f")])
    t_leg = np.mean([np.linalg.norm(R["hip_k"] - R["ankle_k"]), np.linalg.norm(R["hip_f"] - R["ankle_f"])])
    scale = t_leg / s_leg
    # ---- trunk: offsets from the source neutral (frame 0) added to the target rest
    def dirs(a_, b_):
        return unwrap([ang(src(fr, b_) - src(fr, a_)) for fr in J])
    spine = dirs("pelvis", "chest"); neck = dirs("chest", "neck"); head = dirs("neck", "head")
    sp_off = spine - spine[0]
    nk_off = (neck - spine) - (neck[0] - spine[0])
    hd_off = (head - neck) - (head[0] - neck[0])
    # ---- arms: bone directions in the chest frame
    def chain_offsets(js, spine_world_target):
        rd = [rest_dir(js[i], js[i + 1]) for i in range(len(js) - 1)]
        rest_sp = rest_dir("pelvis", "chest")
        offs = []
        for k in range(len(js) - 1):
            src_dir = dirs(js[k], js[k + 1])
            rel_to_chest = src_dir - spine                          # source bone vs source chest
            want = (rest_sp + sp_off) + rel_to_chest                # same relation on the target chest
            offs.append(want)
        out = []
        for t in range(n):
            base_rot = sp_off[t]
            acc = 0.0
            row = []
            for k in range(len(js) - 1):
                o = offs[k][t] - rd[k] - base_rot - acc
                row.append(o)
                acc += o
            out.append(row)
        return np.array(out)
    arm_f = chain_offsets(S["chains"]["arm_f"]["joints"][:3], None)  # shoulder->elbow->wrist from the source
    js0 = S["chains"]["arm_f"]["joints"]
    rel_e_rest = wrap(rest_dir(js0[1], js0[2]) - rest_dir(js0[0], js0[1]))
    tot0 = rel_e_rest + arm_f[0][1]
    arm_f[:, 1] -= 360.0 * round((tot0 - wrap(tot0)) / 360.0)
    # weapon axis from the two hands, sign continuous, anchored at impact later
    hf, hb = M["weapon"]["front_hand"], M["weapon"]["back_hand"]
    axis = []
    for fr in J:
        v = fr[hf] - fr[hb]
        axis.append(v / (np.linalg.norm(v) + 1e-9))
    axis = np.array(axis)
    # ---- phases from hand height/speed (source)
    hy = np.array([-(fr[hf][1] + fr[hb][1]) / 2 for fr in J])          # up = larger
    hp = np.array([(fr[hf] + fr[hb]) / 2 for fr in J])
    spd = np.r_[0, np.linalg.norm(np.diff(hp, axis=0), axis=1)]
    top = int(np.argmax(hy))
    peak = top + int(np.argmax(spd[top:top + 30]))
    dec = np.r_[0, -np.diff(spd)]
    impact = peak + 1 if M['adjust'].get('impact_at_speed_peak', True) else peak + int(np.argmax(dec[peak:peak + 12]))
    lift = int(np.argmax(spd[:top] > 0.15 * spd[:top].max())) if top > 0 else 0
    settle_idx = impact + 10 + int(np.argmax(spd[impact + 10:] < 0.08 * spd.max())) if impact + 10 < n else n - 1
    # make the weapon point AWAY from the body at impact (forward = +x), then keep continuity
    if axis[impact][0] < 0:
        axis = -axis
    for t in range(impact + 1, n):
        if axis[t] @ axis[t - 1] < 0:
            axis[t] = -axis[t]
    for t in range(impact - 1, -1, -1):
        if axis[t] @ axis[t + 1] < 0:
            axis[t] = -axis[t]
    w_world = unwrap([ang(v) for v in axis])
    # wrist: CMU does not capture hand rotation (the hand bone follows the forearm) and the line between two hands is
    # unreliable when they slide together, so the wrist follows the KB rule (map "weapon.wrist_rule"): cocked back to
    # the structure's limit at the top of the wind-up, held, released late in the swing, in line at contact,
    # past it in the follow-through, back to rest in the recovery.
    wr = M["weapon"]["wrist_rule"]
    js = S["chains"]["arm_f"]["joints"]
    rd = [rest_dir(js[i], js[i + 1]) for i in range(len(js) - 1)]
    rest_w = wrap(rd[2] - rd[1])
    def sstep(x):
        x = min(max(x, 0.0), 1.0)
        return x * x * (3 - 2 * x)
    rel_w = []
    for t in range(n):
        if t <= top:
            v = rest_w + (wr["cocked"] - rest_w) * sstep((t - lift) / max(1, top - lift))
        elif t <= impact:
            u = (t - top) / max(1, impact - top)
            v = wr["cocked"] + (wr["contact"] - wr["cocked"]) * sstep((u - wr["release_at"]) / (1 - wr["release_at"]))
        elif t <= impact + 8:
            v = wr["contact"] + (wr["follow"] - wr["contact"]) * sstep((t - impact) / 8)
        else:
            v = wr["follow"] + (rest_w - wr["follow"]) * sstep((t - impact - 8) / max(1, settle_idx - impact - 8))
        rel_w.append(v)
    clamped = 0
    wrist = []
    for t in range(n):
        wrist.append(rel_w[t] - rest_w)          # offset from rest (relative angle in the chain)
    # elbow limits: wrap relative elbow into the structure range (same physical pose)
    arm_b = chain_offsets(S["chains"]["arm_b"]["joints"], None)
    jb = S["chains"]["arm_b"]["joints"]
    tb = wrap(rest_dir(jb[1], jb[2]) - rest_dir(jb[0], jb[1])) + arm_b[0][1]
    arm_b[:, 1] -= 360.0 * round((tb - wrap(tb)) / 360.0)
    # shoulder shift from the source clavicle motion (shoulder relative to chest, chest frame)
    def rel_in_chest(t, joint):
        v = src(J[t], joint) - src(J[t], "chest")
        return np.array([[math.cos(-math.radians(spine[t] - spine[0])), -math.sin(-math.radians(spine[t] - spine[0]))],
                         [math.sin(-math.radians(spine[t] - spine[0])), math.cos(-math.radians(spine[t] - spine[0]))]]) @ v
    sh0 = rel_in_chest(0, "shoulder_f")
    shift = [((rel_in_chest(t, "shoulder_f") - sh0) * scale * M["adjust"].get("shoulder_shift_gain", 1.0)).tolist() for t in range(n)]
    # root and feet
    root0 = src(J[0], "pelvis")
    root = [((src(J[t], "pelvis") - root0) * scale).tolist() for t in range(n)]
    feet = {}
    for c, tj in (("foot_k", "ankle_k"), ("foot_f", "ankle_f")):
        a0 = src(J[0], tj)
        xs = [float((src(J[t], tj) - a0)[0] * scale) for t in range(n)]
        # contact cleanup: a foot that moves less than the threshold is planted (mocap noise)
        feet[c] = [0.0] * n if max(xs) - min(xs) < M["adjust"].get("plant_threshold_px", 25) else xs
    # hip clamp: the pelvis may not rise above what the target's legs can reach (proportions differ)
    for t in range(n):
        for leg, (hj, aj, c) in {"k": ("hip_k", "ankle_k", "foot_k"), "f": ("hip_f", "ankle_f", "foot_f")}.items():
            L = np.linalg.norm(R[S["legs"]["leg_" + leg]["joints"][1]] - R[hj]) + np.linalg.norm(R[aj] - R[S["legs"]["leg_" + leg]["joints"][1]])
            hip = R[hj] + np.array(root[t])
            ank = R[aj] + np.array([feet[c][t], 0])
            dx = ank[0] - hip[0]
            need_y = ank[1] - math.sqrt(max(0.0, (L - 0.5) ** 2 - dx * dx))
            if hip[1] < need_y:
                root[t][1] += need_y - hip[1]
    # ---- motion.v2, dense keys (every `key_step` frames), broken tangent at impact
    step = M["adjust"].get("key_step", 2)
    frames_out = sorted(set(list(range(0, n, step)) + [n - 1, impact]))
    keys = []
    for t in frames_out:
        k = {"frame": int(t), "ease": "spline",
             "pose": {"root": [round(v, 2) for v in root[t]],
                      "chains": {"trunk": [round(float(sp_off[t]), 2), round(float(nk_off[t]), 2), round(float(hd_off[t]), 2)],
                                 "arm_f": [round(float(arm_f[t][0]), 2), round(float(arm_f[t][1]), 2), round(float(wrist[t]), 2)],
                                 "arm_b": [round(float(arm_b[t][0]), 2), round(float(arm_b[t][1]), 2)]},
                      "shift": {"arm_f": [round(v, 2) for v in shift[t]]},
                      "feet": {"foot_k": [round(feet["foot_k"][t], 1), 0], "foot_f": [round(feet["foot_f"][t], 1), 0]}}}
        if t == impact:
            k["break"] = True
        keys.append(k)
    ph = [("idle", 0, lift), ("anticipation", lift, lift + max(2, (top - lift) // 4)), ("windup", lift + max(2, (top - lift) // 4), top),
          ("swing", top, impact), ("impact", impact, impact + 2), ("follow_through", impact + 2, impact + 10),
          ("recovery", impact + 10, settle_idx), ("return_to_idle", settle_idx, n)]
    motion = {"schema": "motion.v2", "id": M["id"], "structure": S["id"], "fps": M["source"]["fps"], "loop": False,
              "interpolation": "pchip", "method": "C: reference-driven (" + M["source"]["label"] + ")",
              "source": M["source"], "camera": M["camera"], "retarget": {"scale": round(scale, 3), "wrist_clamped_frames": clamped},
              "intent": M["intent"],
              "phases": [{"name": a_, "start": int(b_), "end": int(c_)} for a_, b_, c_ in ph],
              "keys": keys, "step": {"lift_px": 0},
              "constraints": [{"type": "contact", "contact": "foot_k", "frames": [0, n - 1]},
                              {"type": "contact", "contact": "foot_f", "frames": [0, n - 1]},
                              {"type": "attachment", "object": "hammer", "frames": "all"}],
              "events": [{"frame": int(top), "name": "swing_start"},
                         {"frame": int(impact), "name": "impact", "point": "hammer.head", "hitstop_frames": 4,
                          "hitstop": "runtime time-freeze"}],
              "acceptance": M["acceptance"]}
    json.dump(motion, open(out_path, "w"), indent=1)
    print(f"frames {n} scale {scale:.2f} lift {lift} top {top} peak {peak} impact {impact} settle {settle_idx} wrist clamped {clamped}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
