"""Edit the project's own art with the studio's local ComfyUI: img2img, masked inpainting and matting.

Board decision 2026-11-22 (early 2A after SOU-64's tool capability failure): input images are allowed through
this wrapper only; `comfy-draft.py` stays text-to-image (D1). Run from the Task Workspace root:

  python -I ~/game-studio-workspace/tools/comfy-edit.py img2img --asset <id> --model sdxl|flux --input <png>
         --prompt "..." --denoise 0.15-0.75 [--seed N] [--count 1-4] [--steps N] [--backdrop R G B]
  python -I ~/game-studio-workspace/tools/comfy-edit.py inpaint --asset <id> --model sdxl --input <png>
         --mask <png> --prompt "..." [--denoise 0.3-1.0] [--seed N] [--count 1-4] [--steps N] [--backdrop R G B]
  python -I ~/game-studio-workspace/tools/comfy-edit.py matte --asset <id> --input <png>
         [--snap 128-255] [--floor 0-127] [--max-leftover 0-2] [--backdrop R G B]

img2img and inpaint are Phase 2A stage 1. `matte` (Board decision 2026-11-22, after spike S7) cuts a figure out
of an opaque generation on a flat backdrop with BiRefNet (core RemoveBackground node, MIT, registry entry
`birefnet`). It replaces `art-ops key` for figures; `key` stays for flat non-figure assets. The model's alpha is
snapped (>= --snap becomes 255, <= --floor becomes 0; BiRefNet leaves figure interiors about 1% translucent),
then the leftover-backdrop check runs: opaque pixels (alpha >= 128) within LEFTOVER_DIST of the backdrop colour,
as a percentage of opaque pixels. Above --max-leftover the run fails and keeps only a `_rejected` image for
review (a kept shadow, an enclosed backdrop pocket such as a lantern halo). The backdrop colour is the median of
the two top corners unless --backdrop is given; a backdrop that is not flat there is refused. The model file's
SHA256 is checked against the pinned value on every run.

It re-runs itself with ComfyUI's embedded Python (Pillow, NumPy) and uses art-ops.py (installed next to it)
for the path boundary, so inputs follow the same rules as art-ops.

Prerequisites enforced here (roadmap 2A):
1. Server verification: the running ComfyUI must report `--listen 127.0.0.1`, `--offline` and version
   EXPECTED_VERSION in /system_stats, else the run is refused. A stopped server is started with those flags.
2. Input isolation: each run re-encodes its input (and mask) into a fresh ComfyUI/input/edit/<asset>/<run-id>/
   folder that only this run's workflow names; no ComfyUI path is ever taken from the caller.
3. Cleanup: that folder and this run's ComfyUI output files are deleted after success or failure. Outputs and
   provenance are kept only in staging/art/<asset>/ (retention: the Board clears an asset's folder after its
   Task is done).
4. Model compatibility: only the (template, model) pairs in SUPPORTED run; anything else is refused.
5. Deterministic outside-mask preservation (inpaint): the model's output is composited back onto the original
   input through the mask, so every pixel where the mask is 0 is copied from the input; the run fails if any
   such pixel differs.

Inputs: PNG under staging/art/<asset_id>/ or under the Task Workspace's assets/slice/ or art_src/ (project art
with recorded provenance, never another game's, studio's or artist's work: the latter is policy). Sides
256-2048 px, multiples of 16 (matte: 64-4096 px, any size, fully opaque). Transparent inputs are flattened onto
--backdrop (default 128 128 128) for the model; the restored inpaint result keeps the original alpha outside the
mask.
"""
import argparse
import datetime
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

TOOLS = os.path.dirname(os.path.abspath(__file__))
COMFY_DIR = os.path.expanduser(os.path.join("~", "game-studio-workspace", "tools", "ComfyUI_windows_portable"))
COMFY_PY = os.path.join(COMFY_DIR, "python_embeded", "python.exe")
STAGING_ROOT = os.path.expanduser(os.path.join("~", "game-studio-workspace", "staging", "art"))
HOST, PORT = "127.0.0.1", 8188
BASE = f"http://{HOST}:{PORT}"
EXPECTED_VERSION = "0.46.0"

try:
    import numpy as np
    from PIL import Image
except ImportError:
    if os.environ.get("COMFY_EDIT_REEXEC") or not os.path.isfile(COMFY_PY):
        sys.exit("comfy-edit needs ComfyUI's embedded Python (Pillow, NumPy) at " + COMFY_PY)
    env = dict(os.environ, COMFY_EDIT_REEXEC="1")
    sys.exit(subprocess.call([COMFY_PY, "-I", "-s", os.path.abspath(__file__)] + sys.argv[1:], env=env))

_spec = importlib.util.spec_from_file_location("art_ops", os.path.join(TOOLS, "art-ops.py"))
art_ops = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(art_ops)

MODELS = {
    "sdxl": {"ckpt": "sd_xl_base_1.0.safetensors", "licence": "CreativeML Open RAIL++-M",
             "steps": 30, "cfg": 7.0, "sampler": "euler", "scheduler": "normal"},
    "flux": {"ckpt": "flux1-schnell-fp8.safetensors", "licence": "Apache-2.0",
             "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple"},
}
# (template, model) pairs tested at the 2026-11-22 runtime validation; others are refused, not tried.
# inpaint + flux was tried and refused: FLUX.1 schnell with a latent noise mask fills the region with an
# unrelated bright pane instead of the prompted object (4 steps, no inpainting training).
SUPPORTED = {("img2img", "sdxl"), ("img2img", "flux"), ("inpaint", "sdxl")}
DENOISE = {"img2img": (0.15, 0.75), "inpaint": (0.3, 1.0)}
MIN_SIDE, MAX_EDIT_SIDE, SIDE_STEP = 256, 2048, 16

# matte: one pinned model (registry entry `birefnet`), installed by the Board into the production models folder.
MATTE_MODEL = {"file": "birefnet.safetensors", "licence": "MIT", "registry": "birefnet",
               "sha256": "9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154"}
MATTE_MIN_SIDE, MATTE_MAX_SIDE = 64, 4096
LEFTOVER_DIST = 40          # colour distance to the backdrop that counts as leftover backdrop (spike S7 metric)
CORNER = 8                  # corner patch size for the backdrop estimate


def fail(msg):
    raise SystemExit(f"comfy-edit: {msg}")


# ---------- server ----------

def get(path, timeout=5):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def system_stats():
    try:
        return json.loads(get("/system_stats", timeout=2))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def listen_address(argv):
    """The value of the last --listen (argparse keeps the last one), or None."""
    found = None
    for i, v in enumerate(argv):
        if v == "--listen":
            found = argv[i + 1] if i + 1 < len(argv) else None
        elif v.startswith("--listen="):
            found = v.split("=", 1)[1]
    return found


def verify_server(stats):
    """Prerequisite 1: refuse a server that is not loopback-only, offline, and the expected version."""
    sysinfo = (stats or {}).get("system") or {}
    argv = sysinfo.get("argv") or []
    problems = []
    if "--offline" not in argv:
        problems.append("started without --offline")
    listen = listen_address(argv)
    if listen != HOST:
        problems.append(f"listen address is {listen!r}, not {HOST}")
    if sysinfo.get("comfyui_version") != EXPECTED_VERSION:
        problems.append(f"version {sysinfo.get('comfyui_version')!r}, expected {EXPECTED_VERSION}")
    if problems:
        fail("refusing the running ComfyUI (" + "; ".join(problems) + "). The Board restarts it with "
             "comfy-draft.py's flags; agents do not.")
    return sysinfo.get("comfyui_version")


def ensure_server(wait_s=180):
    stats = system_stats()
    if stats is None:
        main = os.path.join(COMFY_DIR, "ComfyUI", "main.py")
        if not (os.path.isfile(COMFY_PY) and os.path.isfile(main)):
            fail(f"ComfyUI is not installed at {COMFY_DIR}")
        os.makedirs(STAGING_ROOT, exist_ok=True)
        log = open(os.path.join(STAGING_ROOT, "comfyui-server.log"), "ab")
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen([COMFY_PY, "-s", main, "--windows-standalone-build", "--listen", HOST, "--port", str(PORT),
                          "--disable-auto-launch", "--offline"], cwd=COMFY_DIR, stdout=log, stderr=log,
                         creationflags=flags)
        deadline = time.time() + wait_s
        while stats is None and time.time() < deadline:
            time.sleep(2)
            stats = system_stats()
        if stats is None:
            fail("ComfyUI did not start within the time limit; see staging/art/comfyui-server.log")
    return verify_server(stats)


def run_prompt(wf, timeout_s=900):
    req = urllib.request.Request(BASE + "/prompt", data=json.dumps({"prompt": wf}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            pid = json.load(r)["prompt_id"]
    except urllib.error.HTTPError as e:
        fail(f"ComfyUI refused the workflow: {e.read()[:400]!r}")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        h = json.loads(get(f"/history/{pid}"))
        if pid in h:
            status = h[pid].get("status", {})
            if status.get("status_str") != "success":
                fail(f"ComfyUI reported {status.get('status_str')}: {json.dumps(status.get('messages', []))[:400]}")
            return [i for o in h[pid]["outputs"].values() for i in o.get("images", [])]
        time.sleep(2)
    fail("generation timed out")


def fetch_image(img):
    q = urllib.request.quote
    return get(f"/view?filename={q(img['filename'])}&subfolder={q(img.get('subfolder', ''))}&type={q(img['type'])}",
               timeout=60)


# ---------- inputs ----------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_input(path, what):
    """Path boundary from art-ops, plus: PNG, and inside staging/<asset> or the workspace art folders."""
    kind, _root, parts, _canonical = art_ops._locate(path)
    canonical = art_ops.check_in(path)
    if not path.lower().endswith(".png"):
        fail(f"{what} must be a PNG file: {path}")
    if kind == "workspace" and not any(tuple(parts[:len(d)]) == d for d in art_ops.OUTPUT_DIRS):
        fail(f"{what} in the Task Workspace must be under assets/slice/ or art_src/: {path}")
    return canonical


def check_size(img, what):
    w, h = img.size
    for v, side in ((w, "width"), (h, "height")):
        if not (MIN_SIDE <= v <= MAX_EDIT_SIDE and v % SIDE_STEP == 0):
            fail(f"{what} {side} is {v}; it must be a multiple of {SIDE_STEP} between {MIN_SIDE} and "
                 f"{MAX_EDIT_SIDE} (use art-ops canvas or resize first)")


def flatten(rgba, backdrop):
    bg = Image.new("RGBA", rgba.size, tuple(backdrop) + (255,))
    bg.alpha_composite(rgba)
    return bg.convert("RGB")


def restore_outside(original_rgba, edited_rgb, mask_l):
    """Prerequisite 5: output = original wherever mask == 0, edited where 255, linear blend between."""
    o = np.asarray(original_rgba).astype(np.uint32)
    e = np.asarray(edited_rgb.convert("RGBA")).astype(np.uint32)
    m = np.asarray(mask_l).astype(np.uint32)[..., None]
    mixed = (o * (255 - m) + e * m + 127) // 255
    out = np.where(m == 0, o, np.where(m == 255, e, mixed)).astype(np.uint8)
    changed_outside = int(((out != np.asarray(original_rgba)).any(-1) & (np.asarray(mask_l) == 0)).sum())
    return Image.fromarray(out, "RGBA"), changed_outside


# ---------- matte ----------

def matte_model_path():
    return os.path.join(COMFY_DIR, "ComfyUI", "models", "background_removal", MATTE_MODEL["file"])


def check_matte_model():
    path = matte_model_path()
    if not os.path.isfile(path) or os.path.islink(path):
        fail(f"the matte model is not installed at {path}; the Board installs it (registry entry "
             f"{MATTE_MODEL['registry']})")
    if sha256(path) != MATTE_MODEL["sha256"]:
        fail(f"{MATTE_MODEL['file']} does not match the pinned SHA256; refusing to run")


def estimate_backdrop(rgb):
    """Median colour of the two top corner patches; refused when those pixels are not one flat colour."""
    h, w = rgb.shape[:2]
    k = max(1, min(CORNER, h // 2, w // 2))
    px = np.concatenate([rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3)]).astype(float)
    bg = np.median(px, axis=0)
    if np.sqrt(((px - bg) ** 2).sum(-1)).max() > LEFTOVER_DIST:
        fail("the top corners are not one flat backdrop colour; generate on a flat plain backdrop or give "
             "--backdrop R G B")
    return [int(round(v)) for v in bg]


def snap_alpha(mask_l, snap, floor):
    a = np.asarray(mask_l).astype(np.uint8).copy()
    a[a >= snap] = 255
    a[a <= floor] = 0
    return a


def matte_metrics(rgb, alpha, backdrop):
    opaque = alpha >= 128
    n = int(opaque.sum())
    near = np.sqrt(((rgb.astype(float) - np.asarray(backdrop, float)) ** 2).sum(-1)) < LEFTOVER_DIST
    soft = (alpha > 0) & (alpha < 255)
    return {"opaque_pixels": n,
            "leftover_backdrop_pct": round(100.0 * int((opaque & near).sum()) / max(1, n), 3),
            "soft_edge_pct": round(100.0 * int(soft.sum()) / max(1, n), 3)}


def matte_workflow(image_name, prefix):
    return {
        "10": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "20": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": MATTE_MODEL["file"]}},
        "21": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["20", 0], "image": ["10", 0]}},
        "22": {"class_type": "MaskToImage", "inputs": {"mask": ["21", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["22", 0], "filename_prefix": prefix}},
    }


def run_matte(a):
    validate_matte(a)
    in_path = check_input(a.input, "--input")
    original = art_ops.load(a.input)
    w, h = original.size
    if not (MATTE_MIN_SIDE <= w <= MATTE_MAX_SIDE and MATTE_MIN_SIDE <= h <= MATTE_MAX_SIDE):
        fail(f"--input is {w}x{h}; matte needs {MATTE_MIN_SIDE}-{MATTE_MAX_SIDE} px per side")
    rgba = np.asarray(original.convert("RGBA"))
    if (rgba[..., 3] < 255).any():
        fail("--input already has transparency; matte works on the opaque generation (its flat backdrop)")
    rgb = np.ascontiguousarray(rgba[..., :3])
    backdrop = list(a.backdrop) if a.backdrop is not None else estimate_backdrop(rgb)
    check_matte_model()

    version = ensure_server()
    out_dir = os.path.join(STAGING_ROOT, a.asset)
    os.makedirs(out_dir, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    rel_dir = f"edit/{a.asset}/{run_id}"
    run_in = os.path.join(comfy_input_dir(), "edit", a.asset, run_id)
    os.makedirs(run_in)                                      # fresh; fails if it already exists
    prefix = f"matte_{a.asset}_{run_id}"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{a.asset}_matte_{stamp}_{run_id}"
    try:
        Image.fromarray(rgb, "RGB").save(os.path.join(run_in, "input.png"))
        wf = matte_workflow(f"{rel_dir}/input.png", prefix)
        images = run_prompt(wf)
        if len(images) != 1:
            fail(f"expected one mask, got {len(images)}")
        mask = Image.open(io.BytesIO(fetch_image(images[0]))).convert("L")
        if mask.size != original.size:
            fail(f"model mask {mask.size} differs from the input {original.size}")
        alpha = snap_alpha(mask, a.snap, a.floor)
        m = matte_metrics(rgb, alpha, backdrop)
        if m["opaque_pixels"] == 0:
            fail("the model found no figure (no pixel with alpha >= 128); nothing written")
        cut = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
        if m["leftover_backdrop_pct"] > a.max_leftover:
            rejected = os.path.join(out_dir, f"{name}_rejected.png")
            cut.save(rejected)
            fail(f"leftover backdrop {m['leftover_backdrop_pct']}% of opaque pixels is above --max-leftover "
                 f"{a.max_leftover}% (backdrop {backdrop}): a kept shadow or an enclosed backdrop pocket. "
                 f"No cut-out written; review image {rejected}")
        mask_png = os.path.join(out_dir, f"{name}_mask.png")
        mask.save(mask_png)
        png = os.path.join(out_dir, f"{name}.png")
        cut.save(png)
        print(png)
        record = {"asset": a.asset, "tool": f"ComfyUI {version} via comfy-edit.py", "template": "matte",
                  "model": MATTE_MODEL["file"], "model_sha256": MATTE_MODEL["sha256"],
                  "licence": MATTE_MODEL["licence"], "registry": MATTE_MODEL["registry"],
                  "size": list(original.size), "input": a.input, "input_sha256": sha256(in_path),
                  "backdrop": backdrop, "backdrop_source": "given" if a.backdrop is not None else "top corners",
                  "snap": a.snap, "floor": a.floor, "max_leftover_pct": a.max_leftover, "check": "passed",
                  **m, "raw_mask": os.path.basename(mask_png), "workflow": f"{name}.workflow.json",
                  "created": stamp, "run_id": run_id}
        with open(os.path.join(out_dir, f"{name}.workflow.json"), "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=1)
        with open(os.path.join(out_dir, f"{name}.provenance.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=1)
        print(f"provenance {name}: " + json.dumps(record, ensure_ascii=False))
    finally:
        cleanup(run_in, prefix)


# ---------- workflows (fixed templates, built in code) ----------

def workflow(template, model, image_name, mask_name, prompt, negative, seed, steps, denoise, prefix):
    m = MODELS[model]
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": m["ckpt"]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": prompt}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": negative if model == "sdxl" else ""}},
        "3": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                                                     "latent_image": ["11", 0], "seed": seed, "steps": steps,
                                                     "cfg": m["cfg"], "sampler_name": m["sampler"],
                                                     "scheduler": m["scheduler"], "denoise": denoise}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }
    if template == "inpaint":
        wf["12"] = {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}}
        wf["13"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["11", 0], "mask": ["12", 0]}}
        wf["3"]["inputs"]["latent_image"] = ["13", 0]
    return wf


def comfy_input_dir():
    return os.path.join(COMFY_DIR, "ComfyUI", "input")


def comfy_output_dir():
    return os.path.join(COMFY_DIR, "ComfyUI", "output")


# ---------- main ----------

def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="template", required=True)
    m = sub.add_parser("matte")
    m.add_argument("--asset", required=True)
    m.add_argument("--input", required=True)
    m.add_argument("--snap", type=int, default=250, help="alpha at or above this becomes 255")
    m.add_argument("--floor", type=int, default=8, help="alpha at or below this becomes 0")
    m.add_argument("--max-leftover", type=float, default=0.5,
                   help="percent of opaque pixels allowed near the backdrop colour")
    m.add_argument("--backdrop", type=int, nargs=3, default=None)
    for t in ("img2img", "inpaint"):
        s = sub.add_parser(t)
        s.add_argument("--asset", required=True)
        s.add_argument("--model", required=True, choices=sorted(MODELS))
        s.add_argument("--input", required=True)
        if t == "inpaint":
            s.add_argument("--mask", required=True)
        s.add_argument("--prompt", required=True, help="original design description only; no game or artist names")
        s.add_argument("--negative", default="text, watermark, logo, signature")
        s.add_argument("--denoise", type=float, default=0.45 if t == "img2img" else 0.9)
        s.add_argument("--seed", type=int, default=None)
        s.add_argument("--count", type=int, default=1)
        s.add_argument("--steps", type=int, default=None)
        s.add_argument("--backdrop", type=int, nargs=3, default=[128, 128, 128])
    return ap.parse_args(argv)


def validate_matte(a):
    if not art_ops.ASSET_ID.match(a.asset):
        fail("--asset must be an asset id (a-z, 0-9, _ or -)")
    if not 128 <= a.snap <= 255:
        fail("--snap must be between 128 and 255")
    if not 0 <= a.floor <= 127:
        fail("--floor must be between 0 and 127")
    if not 0 <= a.max_leftover <= 2:
        fail("--max-leftover must be between 0 and 2 (percent)")
    if a.backdrop is not None and not all(0 <= v <= 255 for v in a.backdrop):
        fail("--backdrop components must be 0-255")


def validate(a):
    if not art_ops.ASSET_ID.match(a.asset):
        fail("--asset must be an asset id (a-z, 0-9, _ or -)")
    if (a.template, a.model) not in SUPPORTED:
        fail(f"{a.template} is not supported with {a.model}")
    lo, hi = DENOISE[a.template]
    if not lo <= a.denoise <= hi:
        fail(f"--denoise for {a.template} must be between {lo} and {hi}, got {a.denoise}")
    if not 1 <= a.count <= 4:
        fail("--count must be between 1 and 4")
    if a.steps is not None and not 1 <= a.steps <= 60:
        fail("--steps must be between 1 and 60")
    if not all(0 <= v <= 255 for v in a.backdrop):
        fail("--backdrop components must be 0-255")
    if len(a.prompt) > 2000:
        fail("--prompt is limited to 2000 characters")


def main(argv=None):
    a = parse(argv)
    if a.template == "matte":
        return run_matte(a)
    validate(a)
    in_path = check_input(a.input, "--input")
    original = art_ops.load(a.input)
    check_size(original, "--input")
    mask = None
    if a.template == "inpaint":
        mask_path = check_input(a.mask, "--mask")
        mask = art_ops.load_mask(a.mask, original.size)
        if not np.asarray(mask).any():
            fail("--mask selects nothing (all 0)")

    version = ensure_server()
    out_dir = os.path.join(STAGING_ROOT, a.asset)
    os.makedirs(out_dir, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    rel_dir = f"edit/{a.asset}/{run_id}"
    run_in = os.path.join(comfy_input_dir(), "edit", a.asset, run_id)
    os.makedirs(run_in)                                      # fresh; fails if it already exists
    prefix = f"edit_{a.asset}_{run_id}"
    seed = a.seed if a.seed is not None else int(time.time()) % 2_000_000_000
    steps = a.steps or MODELS[a.model]["steps"]
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Re-encode (never copy bytes): the model sees exactly the flattened pixels, no metadata.
        flatten(original, a.backdrop).save(os.path.join(run_in, "input.png"))
        if mask is not None:
            mask.convert("RGB").save(os.path.join(run_in, "mask.png"))
        for n in range(a.count):
            s = seed + n
            name = f"{a.asset}_{a.template}_{a.model}_{stamp}_s{s}"
            wf = workflow(a.template, a.model, f"{rel_dir}/input.png", f"{rel_dir}/mask.png", a.prompt,
                          a.negative, s, steps, a.denoise, prefix)
            images = run_prompt(wf)
            if len(images) != 1:
                fail(f"expected one image, got {len(images)}")
            edited = Image.open(io.BytesIO(fetch_image(images[0]))).convert("RGB")
            if edited.size != original.size:
                fail(f"model output {edited.size} differs from the input {original.size}")
            record = {"asset": a.asset, "tool": f"ComfyUI {version} via comfy-edit.py", "template": a.template,
                      "model": MODELS[a.model]["ckpt"], "licence": MODELS[a.model]["licence"], "seed": s,
                      "steps": steps, "denoise": a.denoise, "sampler": MODELS[a.model]["sampler"],
                      "scheduler": MODELS[a.model]["scheduler"], "cfg": MODELS[a.model]["cfg"],
                      "size": list(original.size), "prompt": a.prompt,
                      "negative": a.negative if a.model == "sdxl" else "", "backdrop": a.backdrop,
                      "input": a.input, "input_sha256": sha256(in_path),
                      "workflow": f"{name}.workflow.json", "created": stamp, "run_id": run_id}
            if a.template == "inpaint":
                final, changed = restore_outside(original, edited, mask)
                if changed:
                    fail(f"{changed} pixels outside the mask differ after the restore; output discarded")
                raw = os.path.join(out_dir, f"{name}_raw.png")
                edited.save(raw)
                record.update({"mask": a.mask, "mask_sha256": sha256(mask_path), "raw_output": os.path.basename(raw),
                               "outside_mask_changed": 0,
                               "outside_mask_pixels": int((np.asarray(mask) == 0).sum())})
            else:
                final = edited.convert("RGBA")
            png = os.path.join(out_dir, f"{name}.png")
            final.save(png)
            print(png)
            with open(os.path.join(out_dir, f"{name}.workflow.json"), "w", encoding="utf-8") as f:
                json.dump(wf, f, indent=1)
            with open(os.path.join(out_dir, f"{name}.provenance.json"), "w", encoding="utf-8") as f:
                json.dump(record, f, indent=1)
            print(f"provenance {name}: " + json.dumps(record, ensure_ascii=False))
    finally:
        cleanup(run_in, prefix)


def cleanup(run_in, prefix):
    """Prerequisite 3: delete the run's input folder and its ComfyUI output files."""
    shutil.rmtree(run_in, ignore_errors=True)
    parent = os.path.dirname(run_in)
    try:
        os.rmdir(parent)          # the asset folder under input/edit, only if empty
    except OSError:
        pass
    out = comfy_output_dir()
    if os.path.isdir(out):
        for f in os.listdir(out):
            if f.startswith(prefix) and os.path.isfile(os.path.join(out, f)):
                os.remove(os.path.join(out, f))


if __name__ == "__main__":
    main()
