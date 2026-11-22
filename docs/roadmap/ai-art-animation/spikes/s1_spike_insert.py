"""Board spike S1 (2026-11-22): can SDXL base insert a new object with core inpaint conditioning?
Variants on the same input, mask, prompt and seeds:
  A latent noise mask (comfy-edit today)       B InpaintModelConditioning + DifferentialDiffusion
Input/mask are copied into ComfyUI/input/spike/<run>/ and removed afterwards. Outputs to scratch only."""
import io, json, os, shutil, sys, time, urllib.request, uuid
from PIL import Image

BASE = "http://127.0.0.1:8188"
COMFY = os.path.expanduser("~/game-studio-workspace/tools/ComfyUI_windows_portable/ComfyUI")
inp, mask, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
prompt = sys.argv[4]
run = uuid.uuid4().hex[:8]
d = os.path.join(COMFY, "input", "spike", run); os.makedirs(d)
Image.open(inp).convert("RGB").save(os.path.join(d, "in.png"))
Image.open(mask).convert("RGB").save(os.path.join(d, "m.png"))
rel = f"spike/{run}"


def wf(variant, seed):
    w = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": f"{rel}/in.png"}},
        "12": {"class_type": "LoadImageMask", "inputs": {"image": f"{rel}/m.png", "channel": "red"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": prompt}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": "text, watermark, blurry, extra cloak"}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": f"spike_{run}"}},
    }
    ks = {"seed": seed, "steps": 30, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}
    if variant == "A":
        w["11"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}}
        w["13"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["11", 0], "mask": ["12", 0]}}
        w["3"] = {"class_type": "KSampler", "inputs": dict(ks, model=["4", 0], positive=["6", 0], negative=["7", 0], latent_image=["13", 0])}
    else:
        w["14"] = {"class_type": "InpaintModelConditioning", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "vae": ["4", 2], "pixels": ["10", 0], "mask": ["12", 0], "noise_mask": True}}
        w["15"] = {"class_type": "DifferentialDiffusion", "inputs": {"model": ["4", 0]}}
        w["3"] = {"class_type": "KSampler", "inputs": dict(ks, model=["15", 0], positive=["14", 0], negative=["14", 1], latent_image=["14", 2])}
    return w


def run_wf(w):
    req = urllib.request.Request(BASE + "/prompt", data=json.dumps({"prompt": w}).encode(), headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    while True:
        h = json.load(urllib.request.urlopen(f"{BASE}/history/{pid}"))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") != "success":
                raise SystemExit(str(st)[:400])
            img = [i for o in h[pid]["outputs"].values() for i in o.get("images", [])][0]
            q = urllib.parse.quote
            return urllib.request.urlopen(f"{BASE}/view?filename={q(img['filename'])}&subfolder={q(img['subfolder'])}&type={img['type']}").read()
        time.sleep(1)


import urllib.parse
try:
    os.makedirs(out_dir, exist_ok=True)
    for v in "AB":
        for seed in (21, 22):
            t = time.time()
            data = run_wf(wf(v, seed))
            p = os.path.join(out_dir, f"{v}_{seed}.png")
            open(p, "wb").write(data)
            print(v, seed, f"{time.time()-t:.1f}s", p)
finally:
    shutil.rmtree(d, ignore_errors=True)
    for f in os.listdir(os.path.join(COMFY, "output")):
        if f.startswith(f"spike_{run}"):
            os.remove(os.path.join(COMFY, "output", f))
