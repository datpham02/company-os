"""Spike S7 (Board R&D, 2026-11-22): cut-out quality, art-ops colour key vs BiRefNet vs ToonOut.
Inputs: the 11 house-style images approved in SOU-81 (raw generations on a light flat backdrop).
For each method and image: an RGBA cut-out, then metrics on it:
  leftover_bg  = opaque pixels (alpha >= 128) whose colour is within 40 of the backdrop colour
                 (backdrop fragments and baked pale shadows that survived the cut-out), as % of opaque pixels
  soft_edge    = pixels with 0 < alpha < 255, as % of opaque pixels (fringe width proxy)
  shadow_band  = opaque pixels in the bottom 6% of the figure's bbox that are low-saturation and lighter than
                 the figure's median (a baked foot shadow), as % of that band
Writes cut-outs and preview sheets to rnd/spikes/s7/. Run with the R&D ComfyUI up on 8189."""
import glob, json, os, shutil, subprocess, sys, time, urllib.parse, urllib.request
import numpy as np
from PIL import Image

R = os.path.expanduser("~/game-studio-workspace/rnd")
IN, OUT = os.path.join(R, "spikes", "inputs"), os.path.join(R, "spikes", "s7")
RC = os.path.join(R, "ComfyUI_rnd", "ComfyUI")
BASE = "http://127.0.0.1:8189"
ARTOPS = os.path.expanduser("~/game-studio-workspace/tools/art-ops.py")
os.makedirs(OUT, exist_ok=True)


def comfy_mask(path, model):
    d = os.path.join(RC, "input", "s7"); os.makedirs(d, exist_ok=True)
    Image.open(path).convert("RGB").save(os.path.join(d, "in.png"))
    wf = {"1": {"class_type": "LoadImage", "inputs": {"image": "s7/in.png"}},
          "2": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": model}},
          "3": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
          "4": {"class_type": "MaskToImage", "inputs": {"mask": ["3", 0]}},
          "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "s7_mask"}}}
    req = urllib.request.Request(BASE + "/prompt", data=json.dumps({"prompt": wf}).encode(), headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    while True:
        h = json.load(urllib.request.urlopen(f"{BASE}/history/{pid}"))
        if pid in h:
            im = [i for o in h[pid]["outputs"].values() for i in o.get("images", [])][0]
            q = urllib.parse.quote
            data = urllib.request.urlopen(f"{BASE}/view?filename={q(im['filename'])}&subfolder={q(im['subfolder'])}&type={im['type']}").read()
            import io
            return np.asarray(Image.open(io.BytesIO(data)).convert("L"))
        time.sleep(0.5)


def metrics(rgba, bgc):
    a = rgba[..., 3].astype(int); rgb = rgba[..., :3].astype(int)
    op = a >= 128
    n = max(1, int(op.sum()))
    near_bg = np.sqrt(((rgb - bgc) ** 2).sum(-1)) < 40
    ys, xs = np.nonzero(op)
    y0, y1 = ys.min(), ys.max()
    band = np.zeros_like(op); band[int(y1 - 0.06 * (y1 - y0)):y1 + 1] = True
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    lum = rgb.mean(-1)
    med = np.median(lum[op])
    shadow = band & op & (sat < 0.15) & (lum > med)
    return {"leftover_bg": round(100 * float((op & near_bg).sum()) / n, 2),
            "soft_edge": round(100 * float(((a > 0) & (a < 255)).sum()) / n, 2),
            "shadow_band": round(100 * float(shadow.sum()) / max(1, int((band & op).sum())), 1)}


rows = []
for path in sorted(glob.glob(os.path.join(IN, "*.png"))):
    name = os.path.basename(path).split("_s")[-1].replace("_0.png", "")
    src = np.asarray(Image.open(path).convert("RGBA"))
    k = max(1, min(8, src.shape[0] // 2))
    bgc = np.median(np.concatenate([src[:k, :k, :3].reshape(-1, 3), src[:k, -k:, :3].reshape(-1, 3)]), axis=0)
    res = {"seed": name}
    # art-ops key, as the agents use it (run from the R&D folder, which has .git? no: use the spikes workspace)
    key_out = os.path.join(OUT, f"{name}_key.png")
    tmp = os.path.join("art_src", "s7_tmp", f"{name}_key.png")  # art-ops writes only under art_src/ or assets/slice/
    subprocess.run([sys.executable, "-I", "-s", ARTOPS, "key", os.path.relpath(path, R), tmp,
                    "--tolerance", "35", "--soft", "8"], cwd=R, check=True, capture_output=True)
    shutil.move(os.path.join(R, tmp), key_out)
    res["key"] = metrics(np.asarray(Image.open(key_out).convert("RGBA")), bgc)
    for label, model in (("birefnet", "birefnet.safetensors"), ("toonout", "toonout_birefnet.safetensors")):
        m = comfy_mask(path, model)
        cut = src.copy(); cut[..., 3] = m
        Image.fromarray(cut, "RGBA").save(os.path.join(OUT, f"{name}_{label}.png"))
        res[label] = metrics(cut, bgc)
    rows.append(res)
    print(json.dumps(res))
shutil.rmtree(os.path.join(RC, "input", "s7"), ignore_errors=True)
for f in glob.glob(os.path.join(RC, "output", "s7_mask_*")):
    for _ in range(10):
        try:
            os.remove(f); break
        except PermissionError:
            time.sleep(1)
json.dump(rows, open(os.path.join(OUT, "s7_metrics.json"), "w"), indent=1)
for meth in ("key", "birefnet", "toonout"):
    for m in ("leftover_bg", "soft_edge", "shadow_band"):
        v = [r[meth][m] for r in rows]
        print(f"{meth:9s} {m:12s} median {np.median(v):6.2f} worst {max(v):6.2f}")
