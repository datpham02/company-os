"""Image operations for game-artist on ComfyUI drafts (Board decision 2026-11-22: AI makes the final art).

Run with: python -I runtime/tools/art-ops.py <command> [args]
It re-runs itself with ComfyUI's embedded Python, which has Pillow and NumPy, so the studio Python
needs no packages.

Commands (all sizes in pixels):
  info     <img>                                  print size, mode, alpha bounding box
  crop     <in> <out> --box X Y W H
  resize   <in> <out> --size W H [--fit contain|cover|stretch]  (Lanczos; contain pads with transparency)
  key      <in> <out> [--color R G B] [--tolerance N] [--soft N]  colour key to alpha (default: the
                                                  median colour of the four corners, e.g. a flat green backdrop)
  trim     <in> <out> [--pad N]                   crop to the alpha bounding box plus padding
  canvas   <in> <out> --size W H [--anchor bottom_center|center]  place on a transparent canvas
  sheet    <out> --cols C --cell W H <frame1> <frame2> ...       grid sprite sheet, row-major
  grade    <in> <out> [--brightness F] [--contrast F] [--saturation F]
  contact  <out> --cell W H <img1> <img2> ...    review sheet with labels, dark background

Paths:
- Inputs: under ~/game-studio-workspace/staging/art/ or the current repository.
- Outputs: under ~/game-studio-workspace/staging/art/, or under assets/slice/ or art_src/ of the
  current repository (the Task Workspace). Anything else is refused. Outputs are PNG.
"""
import argparse
import os
import sys

COMFY_PY = os.path.expanduser(os.path.join("~", "game-studio-workspace", "tools", "ComfyUI_windows_portable",
                                           "python_embeded", "python.exe"))
STAGING = os.path.realpath(os.path.expanduser(os.path.join("~", "game-studio-workspace", "staging", "art")))

try:
    from PIL import Image, ImageDraw, ImageEnhance
    import numpy as np
except ImportError:
    if os.environ.get("ART_OPS_REEXEC") or not os.path.isfile(COMFY_PY):
        sys.exit("art-ops needs ComfyUI's embedded Python (Pillow, NumPy) at " + COMFY_PY)
    import subprocess
    env = dict(os.environ, ART_OPS_REEXEC="1")
    sys.exit(subprocess.call([COMFY_PY, "-I", "-s", os.path.abspath(__file__)] + sys.argv[1:], env=env))


def _inside(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return os.path.commonpath([path, root]) == root


def check_in(path):
    cwd = os.getcwd()
    if not (_inside(path, STAGING) or _inside(path, cwd)):
        sys.exit(f"input outside the staging folder and the repository: {path}")
    if not os.path.isfile(path):
        sys.exit(f"no such file: {path}")
    return path


def check_out(path):
    cwd = os.getcwd()
    ok = _inside(path, STAGING) or any(_inside(path, os.path.join(cwd, d)) for d in ("assets/slice", "art_src"))
    if not ok:
        sys.exit(f"output must be under {STAGING}, assets/slice/ or art_src/: {path}")
    if not path.lower().endswith(".png"):
        sys.exit("outputs are PNG files")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path


def load(path):
    return Image.open(check_in(path)).convert("RGBA")


def save(img, path):
    img.save(check_out(path), "PNG", optimize=True)
    print(f"{path} {img.width}x{img.height}")


def cmd_info(a):
    img = Image.open(check_in(a.img))
    bbox = img.convert("RGBA").getchannel("A").getbbox()
    print(f"{a.img}: {img.width}x{img.height} mode={img.mode} alpha_bbox={bbox}")


def cmd_crop(a):
    x, y, w, h = a.box
    save(load(a.inp).crop((x, y, x + w, y + h)), a.out)


def cmd_resize(a):
    img, (w, h) = load(a.inp), a.size
    if a.fit == "stretch":
        out = img.resize((w, h), Image.LANCZOS)
    else:
        scale = (min if a.fit == "contain" else max)(w / img.width, h / img.height)
        r = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.paste(r, ((w - r.width) // 2, (h - r.height) // 2), r)
    save(out, a.out)


def cmd_key(a):
    img = load(a.inp)
    arr = np.asarray(img).astype(np.float32)
    if a.color is None:
        k = 8
        corners = np.concatenate([arr[:k, :k, :3].reshape(-1, 3), arr[:k, -k:, :3].reshape(-1, 3),
                                  arr[-k:, :k, :3].reshape(-1, 3), arr[-k:, -k:, :3].reshape(-1, 3)])
        a.color = [int(v) for v in np.median(corners, axis=0)]
        print(f"key colour (from corners): {a.color}")
    key = np.array(a.color, dtype=np.float32)
    dist = np.sqrt(((arr[..., :3] - key) ** 2).sum(-1))
    alpha = np.clip((dist - a.tolerance) / max(a.soft, 1), 0, 1)
    # Keep only background that is connected to the image border, so subject colours close to the
    # backdrop (dark green cloth, shadows) stay opaque.
    bg = alpha < 1
    reach = np.zeros_like(bg)
    reach[0, :], reach[-1, :], reach[:, 0], reach[:, -1] = bg[0, :], bg[-1, :], bg[:, 0], bg[:, -1]
    for _ in range(max(arr.shape[:2])):
        grown = reach.copy()
        grown[1:, :] |= reach[:-1, :]; grown[:-1, :] |= reach[1:, :]
        grown[:, 1:] |= reach[:, :-1]; grown[:, :-1] |= reach[:, 1:]
        grown &= bg
        if (grown == reach).all():
            break
        reach = grown
    alpha = np.where(reach, alpha, 1.0)
    arr[..., 3] = arr[..., 3] * alpha
    # remove the key colour's spill from semi-transparent edges
    g = a.color.index(max(a.color))
    others = [c for c in range(3) if c != g]
    edge = alpha < 1
    arr[..., g] = np.where(edge, np.minimum(arr[..., g], arr[..., others].max(-1)), arr[..., g])
    save(Image.fromarray(arr.astype(np.uint8), "RGBA"), a.out)


def cmd_trim(a):
    img = load(a.inp)
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        sys.exit("image is fully transparent")
    p = a.pad
    bbox = (max(0, bbox[0] - p), max(0, bbox[1] - p), min(img.width, bbox[2] + p), min(img.height, bbox[3] + p))
    save(img.crop(bbox), a.out)


def cmd_canvas(a):
    img, (w, h) = load(a.inp), a.size
    if img.width > w or img.height > h:
        sys.exit(f"image {img.width}x{img.height} is larger than the canvas {w}x{h}; resize first")
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = h - img.height if a.anchor == "bottom_center" else (h - img.height) // 2
    out.paste(img, ((w - img.width) // 2, y), img)
    save(out, a.out)


def cmd_sheet(a):
    cw, ch = a.cell
    rows = -(-len(a.frames) // a.cols)
    out = Image.new("RGBA", (cw * a.cols, ch * rows), (0, 0, 0, 0))
    for i, f in enumerate(a.frames):
        fr = load(f)
        if fr.size != (cw, ch):
            sys.exit(f"{f} is {fr.width}x{fr.height}, not the cell size {cw}x{ch}")
        out.paste(fr, ((i % a.cols) * cw, (i // a.cols) * ch), fr)
    save(out, a.out)


def cmd_grade(a):
    img = load(a.inp)
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(a.brightness)
    rgb = ImageEnhance.Contrast(rgb).enhance(a.contrast)
    rgb = ImageEnhance.Color(rgb).enhance(a.saturation)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    save(out, a.out)


def cmd_contact(a):
    cw, ch = a.cell
    cols = min(4, len(a.images))
    rows = -(-len(a.images) // cols)
    out = Image.new("RGBA", (cw * cols, (ch + 18) * rows), (24, 26, 32, 255))
    d = ImageDraw.Draw(out)
    for i, f in enumerate(a.images):
        im = load(f)
        im.thumbnail((cw, ch), Image.LANCZOS)
        x, y = (i % cols) * cw, (i // cols) * (ch + 18)
        out.paste(im, (x + (cw - im.width) // 2, y + (ch - im.height) // 2), im)
        d.text((x + 4, y + ch + 2), os.path.basename(f)[:40], fill=(220, 220, 220, 255))
    save(out, a.out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info"); s.add_argument("img"); s.set_defaults(fn=cmd_info)
    s = sub.add_parser("crop"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--box", type=int, nargs=4, required=True); s.set_defaults(fn=cmd_crop)
    s = sub.add_parser("resize"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--size", type=int, nargs=2, required=True)
    s.add_argument("--fit", choices=["contain", "cover", "stretch"], default="contain"); s.set_defaults(fn=cmd_resize)
    s = sub.add_parser("key"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--color", type=int, nargs=3, default=None)
    s.add_argument("--tolerance", type=float, default=45); s.add_argument("--soft", type=float, default=30); s.set_defaults(fn=cmd_key)
    s = sub.add_parser("trim"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--pad", type=int, default=4); s.set_defaults(fn=cmd_trim)
    s = sub.add_parser("canvas"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--size", type=int, nargs=2, required=True)
    s.add_argument("--anchor", choices=["bottom_center", "center"], default="bottom_center"); s.set_defaults(fn=cmd_canvas)
    s = sub.add_parser("sheet"); s.add_argument("out"); s.add_argument("--cols", type=int, required=True); s.add_argument("--cell", type=int, nargs=2, required=True)
    s.add_argument("frames", nargs="+"); s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("grade"); s.add_argument("inp"); s.add_argument("out")
    for k in ("brightness", "contrast", "saturation"):
        s.add_argument(f"--{k}", type=float, default=1.0)
    s.set_defaults(fn=cmd_grade)
    s = sub.add_parser("contact"); s.add_argument("out"); s.add_argument("--cell", type=int, nargs=2, default=[256, 256])
    s.add_argument("images", nargs="+"); s.set_defaults(fn=cmd_contact)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
