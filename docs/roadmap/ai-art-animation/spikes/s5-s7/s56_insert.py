"""Spikes S5 and S6 (Board R&D, 2026-11-22) on the R&D ComfyUI (127.0.0.1:8189).

Inputs: 3 house-style subjects (SOU-81 approved images): Scrivener 6102, attacker 6115, frayer 6127.
Masks are built from each figure's BiRefNet alpha (spike S7):
  open : a 200x280 box on the backdrop, clear of the figure (the side with more room), bottom at 85% height
  next : a 180x260 box centred on the figure's left edge at mid height (overlaps the figure by ~60 px)
Tasks:
  insert   (S5 Fooocus+SDXL, S6 klein): add "a small iron lantern with a warm flame" in the mask
  complete (S6 klein): remove the held book/hand region and paint what lies behind (Scrivener only, 4 seeds)
  identity (S6 klein): the same character in a new pose from the image as reference (3 subjects x 4 seeds)
Every masked result is composited back onto the input through the feathered mask (exact outside the mask),
as comfy-edit does. Outputs: rnd/spikes/s56/<task>_<method>_<subject>_<placement>_s<seed>.png
Usage: python -I -s s56_insert.py [s5|s6|all]"""
import io, json, os, shutil, sys, time, urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

R = os.path.expanduser("~/game-studio-workspace/rnd")
IN, S7, OUT = (os.path.join(R, "spikes", d) for d in ("inputs", "s7", "s56"))
RC = os.path.join(R, "ComfyUI_rnd", "ComfyUI")
BASE = "http://127.0.0.1:8189"
os.makedirs(OUT, exist_ok=True)
SUBJ = {"scrivener": "20261122-135759_s6102", "attacker": "20261122-140233_s6115", "frayer": "20261122-140315_s6127"}
SEEDS = [31, 32, 33, 34]
STYLE = "2D hand-drawn illustration, bold uneven black ink outline, flat cel shading with two or three flat tones, clean flat colour"
LANTERN = f"a small iron lantern with a warm orange flame, {STYLE}"
WHICH = sys.argv[1] if len(sys.argv) > 1 else "all"
log = []


def masks(subject):
    a = np.asarray(Image.open(os.path.join(S7, f"{SUBJ[subject].split('_s')[1]}_birefnet.png")).convert("RGBA"))[..., 3]
    ys, xs = np.nonzero(a >= 128)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    W, H = a.shape[1], a.shape[0]
    out = {}
    w, h = 200, 280
    bottom = int(0.85 * H)
    if x0 > W - x1:   # more room on the left
        bx = max(8, (x0 - w) // 2)
    else:
        bx = min(W - w - 8, x1 + (W - x1 - w) // 2)
    out["open"] = (bx, bottom - h, w, h)
    w2, h2 = 180, 260
    out["next"] = (max(0, x0 - w2 + 60), int(y0 + 0.5 * (y1 - y0)) - h2 // 2, w2, h2)
    res = {}
    for k, (x, y, w_, h_) in out.items():
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle((x, y, x + w_ - 1, y + h_ - 1), fill=255)
        res[k] = (m.filter(ImageFilter.GaussianBlur(4)), tuple(int(v) for v in (x, y, w_, h_)))  # int: the JSON log failed on numpy int64 in the 2026-11-22 run
    return res


def book_mask(subject):
    # the Scrivener's held book and front hand: the brightest pale block inside the figure's upper half
    src = np.asarray(Image.open(os.path.join(IN, f"style_validation_flux_{SUBJ[subject]}_0.png")).convert("RGB")).astype(int)
    a = np.asarray(Image.open(os.path.join(S7, f"{SUBJ[subject].split('_s')[1]}_birefnet.png")).convert("RGBA"))[..., 3]
    pale = (src.mean(-1) > 170) & (a >= 128)
    pale[int(0.6 * pale.shape[0]):] = False
    ys, xs = np.nonzero(pale)
    m = Image.new("L", (src.shape[1], src.shape[0]), 0)
    ImageDraw.Draw(m).rectangle((xs.min() - 20, ys.min() - 20, xs.max() + 20, ys.max() + 20), fill=255)
    return m.filter(ImageFilter.GaussianBlur(4))


def put(img, mask):
    d = os.path.join(RC, "input", "s56"); os.makedirs(d, exist_ok=True)
    img.convert("RGB").save(os.path.join(d, "in.png"))
    if mask is not None:
        mask.convert("RGB").save(os.path.join(d, "m.png"))


def run(wf):
    req = urllib.request.Request(BASE + "/prompt", data=json.dumps({"prompt": wf}).encode(), headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    t = time.time()
    while True:
        h = json.load(urllib.request.urlopen(f"{BASE}/history/{pid}"))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") != "success":
                raise RuntimeError(json.dumps(st.get("messages"))[-300:])
            im = [i for o in h[pid]["outputs"].values() for i in o.get("images", [])][0]
            q = urllib.parse.quote
            data = urllib.request.urlopen(f"{BASE}/view?filename={q(im['filename'])}&subfolder={q(im['subfolder'])}&type={im['type']}").read()
            return Image.open(io.BytesIO(data)).convert("RGB"), time.time() - t
        time.sleep(0.5)


def restore(orig, edited, mask):
    o = np.asarray(orig.convert("RGB")).astype(np.uint32)
    e = np.asarray(edited).astype(np.uint32)
    m = np.asarray(mask).astype(np.uint32)[..., None]
    out = np.where(m == 0, o, (o * (255 - m) + e * m + 127) // 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def wf_fooocus(prompt, seed):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": "s56/in.png"}},
        "3": {"class_type": "LoadImageMask", "inputs": {"image": "s56/m.png", "channel": "red"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "text, watermark, signature, blurry, 3D render, photo"}},
        "6": {"class_type": "INPAINT_MaskedFill", "inputs": {"image": ["2", 0], "mask": ["3", 0], "fill": "neutral", "falloff": 0}},
        "7": {"class_type": "INPAINT_VAEEncodeInpaintConditioning", "inputs": {"positive": ["4", 0], "negative": ["5", 0], "vae": ["1", 2], "pixels": ["6", 0], "mask": ["3", 0]}},
        "8": {"class_type": "INPAINT_LoadFooocusInpaint", "inputs": {"head": "fooocus_inpaint_head.pth", "patch": "inpaint_v26.fooocus.patch"}},
        "9": {"class_type": "INPAINT_ApplyFooocusInpaint", "inputs": {"model": ["1", 0], "patch": ["8", 0], "latent": ["7", 2]}},
        "10": {"class_type": "KSampler", "inputs": {"model": ["9", 0], "positive": ["7", 0], "negative": ["7", 1], "latent_image": ["7", 3], "seed": seed, "steps": 24, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": "s56"}},
    }


def wf_klein(prompt, seed, masked):
    w = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-4b.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": "s56/in.png"}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["3", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "7": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["6", 0], "latent": ["5", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": "s56"}},
    }
    if masked:
        w["13"] = {"class_type": "LoadImageMask", "inputs": {"image": "s56/m.png", "channel": "red"}}
        w["9"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["5", 0], "mask": ["13", 0]}}
    else:
        w["9"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}}
    w["10"] = {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["9", 0], "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    return w


try:
    for subject, stem in SUBJ.items():
        src = Image.open(os.path.join(IN, f"style_validation_flux_{stem}_0.png")).convert("RGB")
        for place, (m, box) in masks(subject).items():
            put(src, m)
            for seed in SEEDS:
                if WHICH in ("s5", "all"):
                    img, dt = run(wf_fooocus(LANTERN, seed))
                    restore(src, img, m).save(os.path.join(OUT, f"insert_fooocus_{subject}_{place}_s{seed}.png"))
                    log.append(("insert", "fooocus", subject, place, seed, round(dt, 1), box))
                if WHICH in ("s6", "all"):
                    instr = f"Add {LANTERN} hanging in the marked area; keep everything else unchanged."
                    img, dt = run(wf_klein(instr, seed, True))
                    restore(src, img, m).save(os.path.join(OUT, f"insert_klein_{subject}_{place}_s{seed}.png"))
                    log.append(("insert", "klein", subject, place, seed, round(dt, 1), box))
        if WHICH in ("s6", "all"):
            if subject == "scrivener":
                bm = book_mask(subject)
                put(src, bm)
                for seed in SEEDS:
                    img, dt = run(wf_klein("Remove the book and the hand holding it; paint the dark hooded cloak fabric that is behind them, same ink line and flat cel shading; keep everything else unchanged.", seed, True))
                    restore(src, img, bm).save(os.path.join(OUT, f"complete_klein_{subject}_book_s{seed}.png"))
                    log.append(("complete", "klein", subject, "book", seed, round(dt, 1), None))
            put(src, None)
            pose = {"scrivener": "The same hooded scrivener character, now holding the contract book high above the head with both hands, full body, same colours, same ink line and flat cel shading, plain light grey background.",
                    "attacker": "The same brute character, now swinging the mallet down in front of the body, full body, same colours, same ink line and flat cel shading, plain light grey background.",
                    "frayer": "The same thin robed creature, now crouching low with both long hands reaching forward, full body, same colours, same ink line and flat cel shading, plain light grey background."}[subject]
            for seed in SEEDS:
                img, dt = run(wf_klein(pose, seed, False))
                img.save(os.path.join(OUT, f"identity_klein_{subject}_pose_s{seed}.png"))
                log.append(("identity", "klein", subject, "pose", seed, round(dt, 1), None))
        print(subject, "done", len(log))
finally:
    shutil.rmtree(os.path.join(RC, "input", "s56"), ignore_errors=True)
    json.dump(log, open(os.path.join(OUT, f"log_{WHICH}.json"), "w"), indent=0)
    for f in os.listdir(os.path.join(RC, "output")):
        if f.startswith("s56"):
            try:
                os.remove(os.path.join(RC, "output", f))
            except OSError:
                pass
