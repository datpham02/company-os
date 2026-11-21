"""Generate concept drafts with the studio's local ComfyUI (Board decision D1, 2026-11-21).

Stdlib only. Run with: python -I runtime/tools/comfy-draft.py --asset <id> --model sdxl|flux --prompt "..." [options]

What it does:
- Starts the local ComfyUI portable build on 127.0.0.1:8188 if it is not already running (detached, loopback only).
- Builds a text-to-image workflow for one of the two Board-approved checkpoints:
    sdxl -> sd_xl_base_1.0.safetensors   (CreativeML Open RAIL++-M)
    flux -> flux1-schnell-fp8.safetensors (Apache-2.0)
- Saves each image, the exact workflow JSON and a provenance record into
  ~/game-studio-workspace/staging/art/<asset>/ (outside every repository).

What it refuses (pipeline §2.1, COMFYUI-WORKFLOW.md):
- Any input image (no img2img, no reference images, no LoRA, no other model).
- Writing anywhere except the staging folder.
- Listening on anything but loopback.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

COMFY_DIR = os.path.expanduser(os.path.join("~", "game-studio-workspace", "tools", "ComfyUI_windows_portable"))
STAGING_ROOT = os.path.expanduser(os.path.join("~", "game-studio-workspace", "staging", "art"))
HOST, PORT = "127.0.0.1", 8188
BASE = f"http://{HOST}:{PORT}"

MODELS = {
    "sdxl": {"ckpt": "sd_xl_base_1.0.safetensors", "licence": "CreativeML Open RAIL++-M",
             "steps": 25, "cfg": 7.0, "sampler": "euler", "scheduler": "normal", "latent": "EmptyLatentImage"},
    "flux": {"ckpt": "flux1-schnell-fp8.safetensors", "licence": "Apache-2.0",
             "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "latent": "EmptySD3LatentImage"},
}
ASSET_ID = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


def get(path, timeout=5):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def server_up():
    try:
        get("/system_stats", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def ensure_server(wait_s=180):
    if server_up():
        return
    py = os.path.join(COMFY_DIR, "python_embeded", "python.exe")
    main = os.path.join(COMFY_DIR, "ComfyUI", "main.py")
    if not (os.path.isfile(py) and os.path.isfile(main)):
        sys.exit(f"ComfyUI is not installed at {COMFY_DIR}")
    log = open(os.path.join(STAGING_ROOT, "comfyui-server.log"), "ab")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([py, "-s", main, "--windows-standalone-build", "--listen", HOST, "--port", str(PORT),
                      "--disable-auto-launch"], cwd=COMFY_DIR, stdout=log, stderr=log, creationflags=flags)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if server_up():
            return
        time.sleep(2)
    sys.exit("ComfyUI did not start within the time limit; see staging/art/comfyui-server.log")


def workflow(model, prompt, negative, width, height, seed, steps, prefix):
    m = MODELS[model]
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": m["ckpt"]}},
        "5": {"class_type": m["latent"], "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": prompt}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": negative if model == "sdxl" else ""}},
        "3": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                                                     "latent_image": ["5", 0], "seed": seed, "steps": steps,
                                                     "cfg": m["cfg"], "sampler_name": m["sampler"],
                                                     "scheduler": m["scheduler"], "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }


def run_one(wf, timeout_s=900):
    req = urllib.request.Request(BASE + "/prompt", data=json.dumps({"prompt": wf}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pid = json.load(r)["prompt_id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        h = json.loads(get(f"/history/{pid}"))
        if pid in h:
            status = h[pid].get("status", {})
            if status.get("status_str") != "success":
                sys.exit(f"ComfyUI reported {status.get('status_str')}: {json.dumps(status.get('messages', []))[:400]}")
            return [i for o in h[pid]["outputs"].values() for i in o.get("images", [])]
        time.sleep(2)
    sys.exit("generation timed out")


def fetch_image(img):
    q = urllib.request.quote
    return get(f"/view?filename={q(img['filename'])}&subfolder={q(img.get('subfolder', ''))}&type={q(img['type'])}",
               timeout=60)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--asset", required=True, help="asset id from design/assets/asset-registry.yaml (snake_case)")
    ap.add_argument("--model", required=True, choices=sorted(MODELS))
    ap.add_argument("--prompt", required=True, help="original design description only; no game or artist names")
    ap.add_argument("--negative", default="text, watermark, logo, signature")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=None, help="first seed; each further candidate adds 1")
    ap.add_argument("--count", type=int, default=1, help="number of candidates (1-8)")
    ap.add_argument("--steps", type=int, default=None)
    a = ap.parse_args(argv)

    if not ASSET_ID.match(a.asset):
        sys.exit("--asset must be a snake_case asset id")
    if not 1 <= a.count <= 8:
        sys.exit("--count must be between 1 and 8")
    for v, name in ((a.width, "width"), (a.height, "height")):
        if not (256 <= v <= 2048 and v % 64 == 0):
            sys.exit(f"--{name} must be a multiple of 64 between 256 and 2048")
    os.makedirs(STAGING_ROOT, exist_ok=True)
    out_dir = os.path.join(STAGING_ROOT, a.asset)
    os.makedirs(out_dir, exist_ok=True)

    ensure_server()
    stats = json.loads(get("/system_stats"))
    comfy_version = (stats.get("system") or {}).get("comfyui_version", "unknown")
    seed = a.seed if a.seed is not None else int(time.time()) % 2_000_000_000
    steps = a.steps or MODELS[a.model]["steps"]
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for n in range(a.count):
        s = seed + n
        name = f"{a.asset}_{a.model}_{stamp}_s{s}"
        wf = workflow(a.model, a.prompt, a.negative, a.width, a.height, s, steps, f"staging_{a.asset}")
        images = run_one(wf)
        for k, img in enumerate(images):
            png = os.path.join(out_dir, f"{name}_{k}.png")
            with open(png, "wb") as f:
                f.write(fetch_image(img))
            print(png)
        with open(os.path.join(out_dir, f"{name}.workflow.json"), "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=1)
        with open(os.path.join(out_dir, f"{name}.provenance.json"), "w", encoding="utf-8") as f:
            json.dump({"asset": a.asset, "tool": f"ComfyUI {comfy_version}", "model": MODELS[a.model]["ckpt"],
                       "licence": MODELS[a.model]["licence"], "seed": s, "steps": steps,
                       "sampler": MODELS[a.model]["sampler"], "scheduler": MODELS[a.model]["scheduler"],
                       "cfg": MODELS[a.model]["cfg"], "size": [a.width, a.height], "prompt": a.prompt,
                       "negative": a.negative if a.model == "sdxl" else "", "reference_images_as_input": "none",
                       "workflow": f"{name}.workflow.json", "created": stamp}, f, indent=1)


if __name__ == "__main__":
    main()
