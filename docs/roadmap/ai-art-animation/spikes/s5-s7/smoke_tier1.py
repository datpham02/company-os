"""Tier-1 smoke tests on the R&D ComfyUI (127.0.0.1:8189). Board R&D, 2026-11-22.
Each test only checks that the model loads and produces an output; quality is for spikes S5-S7.
Usage (ComfyUI embedded Python): python -I -s smoke_tier1.py <input.png> <mask.png> <outdir>"""
import json, os, shutil, sys, time, urllib.parse, urllib.request
from PIL import Image

BASE = "http://127.0.0.1:8189"
RC = os.path.expanduser("~/game-studio-workspace/rnd/ComfyUI_rnd/ComfyUI")
inp, mask, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
d = os.path.join(RC, "input", "smoke"); os.makedirs(d, exist_ok=True)
Image.open(inp).convert("RGB").save(os.path.join(d, "in.png"))
Image.open(mask).convert("RGB").save(os.path.join(d, "m.png"))


def run(name, wf):
    t = time.time()
    req = urllib.request.Request(BASE + "/prompt", data=json.dumps({"prompt": wf}).encode(), headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        print(name, "REFUSED", e.read()[:300]); return
    while True:
        h = json.load(urllib.request.urlopen(f"{BASE}/history/{pid}"))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") != "success":
                print(name, "FAILED", json.dumps(st.get("messages"))[-400:]); return
            for o in h[pid]["outputs"].values():
                for im in o.get("images", []):
                    q = urllib.parse.quote
                    data = urllib.request.urlopen(f"{BASE}/view?filename={q(im['filename'])}&subfolder={q(im['subfolder'])}&type={im['type']}").read()
                    open(os.path.join(out, f"{name}.png"), "wb").write(data)
            print(name, "OK", f"{time.time()-t:.1f}s"); return
        time.sleep(1)


save = lambda src, p: {"class_type": "SaveImage", "inputs": {"images": src, "filename_prefix": f"smoke_{p}"}}

klein = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-4b.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "2D hand-drawn illustration, bold ink outlines, flat cel shading, a small iron lantern with a warm flame, plain light grey background"}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
    "6": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 768, "height": 768, "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": 1, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": save(["8", 0], "klein"),
}


def bg(model):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": "smoke/in.png"}},
        "2": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": model}},
        "3": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "MaskToImage", "inputs": {"mask": ["3", 0]}},
        "5": save(["4", 0], model.split(".")[0]),
    }


fooocus = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
    "2": {"class_type": "LoadImage", "inputs": {"image": "smoke/in.png"}},
    "3": {"class_type": "LoadImageMask", "inputs": {"image": "smoke/m.png", "channel": "red"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "a glowing brass lantern hanging from an iron hook, painterly fantasy game art"}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "text, watermark, blurry"}},
    "6": {"class_type": "INPAINT_MaskedFill", "inputs": {"image": ["2", 0], "mask": ["3", 0], "fill": "neutral", "falloff": 0}},
    "7": {"class_type": "INPAINT_VAEEncodeInpaintConditioning", "inputs": {"positive": ["4", 0], "negative": ["5", 0], "vae": ["1", 2], "pixels": ["6", 0], "mask": ["3", 0]}},
    "8": {"class_type": "INPAINT_LoadFooocusInpaint", "inputs": {"head": "fooocus_inpaint_head.pth", "patch": "inpaint_v26.fooocus.patch"}},
    "9": {"class_type": "INPAINT_ApplyFooocusInpaint", "inputs": {"model": ["1", 0], "patch": ["8", 0], "latent": ["7", 2]}},
    "10": {"class_type": "KSampler", "inputs": {"model": ["9", 0], "positive": ["7", 0], "negative": ["7", 1], "latent_image": ["7", 3], "seed": 21, "steps": 24, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
    "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
    "12": save(["11", 0], "fooocus"),
}

try:
    run("birefnet", bg("birefnet.safetensors"))
    run("toonout", bg("toonout_birefnet.safetensors"))
    run("fooocus", fooocus)
    run("klein", klein)
finally:
    shutil.rmtree(d, ignore_errors=True)
    for f in os.listdir(os.path.join(RC, "output")):
        if f.startswith("smoke_"):
            os.remove(os.path.join(RC, "output", f))
