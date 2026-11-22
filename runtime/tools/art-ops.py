"""Image operations for game-artist on ComfyUI drafts (Board decision 2026-11-22: AI makes the final art).

Run with: python -I runtime/tools/art-ops.py <command> [args]
It re-runs itself with ComfyUI's embedded Python, which has Pillow and NumPy, so the studio Python
needs no packages. Tests: runtime/tools/test_art_ops.py (run with that embedded Python).

Commands (all sizes in pixels):
  info     <img>                                  print size, mode, alpha bounding box
  crop     <in> <out> --box X Y W H               the box must lie inside the image
  resize   <in> <out> --size W H [--fit contain|cover|stretch] [--filter lanczos|nearest]
                                                  contain pads with transparency; nearest keeps pixel art crisp
  key      <in> <out> [--color R G B] [--tolerance N] [--soft N]  colour key to alpha (default: the
                                                  median colour of the four corners, e.g. a flat green backdrop)
  trim     <in> <out> [--pad N]                   crop to the alpha bounding box plus padding
  canvas   <in> <out> --size W H [--anchor bottom_center|center]  place on a transparent canvas
  sheet    <out> --cols C --cell W H <frame1> <frame2> ...       grid sprite sheet, row-major
  grade    <in> <out> [--brightness F] [--contrast F] [--saturation F]
  contact  <out> --cell W H [--bg R G B] [--filter lanczos|nearest] <img1> <img2> ...
                                                  review sheet with labels; --bg previews on a flat target colour
  mask     <out> (--size W H | --like IMG) [--rect X Y W H]... [--ellipse X Y W H]... [--polygon X1 Y1 X2 Y2 X3 Y3 ...]...
                 [--from-alpha IMG [--threshold N]] [--from-color IMG R G B [--tolerance N]]
                 [--grow N] [--shrink N] [--invert] [--feather N]
                                                  greyscale mask (255 = selected): union of the shapes and
                                                  sources, then grow, shrink, invert, feather, in that order
  compose  <out> --base IMG --over IMG [--at X Y] [--opacity F] [--mask MASK]
                                                  alpha "over" of --over onto --base at X Y (output = base size);
                                                  with --mask (base size), output = base wherever the mask is 0,
                                                  exactly, and blends by the mask value elsewhere
  diff     <out> <a> <b> [--mask MASK] [--fail-outside]
                                                  heat map of |a - b| plus changed-pixel count, max and mean delta
                                                  per channel; with --mask, the count of changed pixels where the
                                                  mask is 0 (--fail-outside exits 1 if any)

RGBA: canvas, sheet and contain-resize copy pixels exactly (no re-blending of alpha); contact composites
each image over its background with the alpha "over" operator; resize premultiplies alpha (Pillow).

Path boundary (enforced by this script; everything else is policy, see security-architecture.md §4):
- It must run from the Task Workspace root: the current folder must contain `.git`.
- Inputs: a file under ~/game-studio-workspace/staging/art/<asset_id>/ or under the Task Workspace.
- Outputs: PNG under ~/game-studio-workspace/staging/art/<asset_id>/, or under assets/slice/ or art_src/
  of the Task Workspace.
- Refused: paths whose real location leaves those roots (`..`, other drives, UNC and device paths,
  alternate data streams), any symbolic link or junction below a root, anything inside `.git` or
  `.paperclip` (other Tasks' worktrees), staging files outside an <asset_id> folder.
- Also refused: hard-linked inputs and outputs. Files are opened and written only through their validated
  canonical path; an output is written to a new temporary file that is then renamed over the target.
- Limits: inputs up to MAX_INPUT_PIXELS (colour key: MAX_KEY_PIXELS), outputs up to MAX_SIDE per side,
  at most MAX_FILES images per command. `resize --fit cover` crops before it resamples, so no
  intermediate image is larger than the target. Masks: at most MAX_SHAPES shapes, MAX_POLY_POINTS points
  per polygon, grow/shrink/feather up to MAX_MASK_RADIUS.
"""
import argparse
import bisect
import os
import re
import sys
import tempfile
import warnings

COMFY_PY = os.path.expanduser(os.path.join("~", "game-studio-workspace", "tools", "ComfyUI_windows_portable",
                                           "python_embeded", "python.exe"))
STAGING = os.path.expanduser(os.path.join("~", "game-studio-workspace", "staging", "art"))

MAX_SIDE = 8192                    # output width or height
MAX_INPUT_PIXELS = 4096 * 4096     # per input image
MAX_KEY_PIXELS = 4096 * 4096       # colour key (scanline flood fill, O(runs log runs))
MAX_FILES = 256                    # images per sheet or contact command
MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_SHAPES = 64                    # rectangles + ellipses + polygons per mask command
MAX_POLY_POINTS = 256
MAX_MASK_RADIUS = 64               # grow, shrink and feather, in pixels
ASSET_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
OUTPUT_DIRS = (("assets", "slice"), ("art_src",))
FORBIDDEN_PARTS = {".git", ".paperclip"}

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError
    import numpy as np
except ImportError:
    if os.environ.get("ART_OPS_REEXEC") or not os.path.isfile(COMFY_PY):
        sys.exit("art-ops needs ComfyUI's embedded Python (Pillow, NumPy) at " + COMFY_PY)
    import subprocess
    env = dict(os.environ, ART_OPS_REEXEC="1")
    sys.exit(subprocess.call([COMFY_PY, "-I", "-s", os.path.abspath(__file__)] + sys.argv[1:], env=env))

warnings.simplefilter("error", Image.DecompressionBombWarning)
FILTERS = {"lanczos": Image.LANCZOS, "nearest": Image.NEAREST}


def fail(msg):
    raise SystemExit(f"art-ops: {msg}")


# ---------- path boundary ----------

def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def _real(p):
    return os.path.normcase(os.path.realpath(p))


def _inside(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:              # different drives, or mixed absolute/relative
        return False


def _is_link(p):
    if os.path.islink(p):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction and isjunction(p))


def workspace_root():
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, ".git")):
        fail("run art-ops from the Task Workspace root (the folder that contains .git)")
    return cwd


def _locate(path):
    """Return (kind, root, parts, canonical) for a path inside staging or the workspace, or fail.

    `canonical` is the resolved real path; callers open and write only that path."""
    if not path or "\0" in path:
        fail("empty or invalid path")
    if path.startswith(("\\\\", "//")):
        fail(f"UNC and device paths are not allowed: {path}")
    if ":" in os.path.splitdrive(path)[1]:
        fail(f"alternate data streams are not allowed: {path}")
    lexical = _norm(path)
    for kind, root in (("staging", STAGING), ("workspace", workspace_root())):
        lroot = _norm(root)
        if not _inside(lexical, lroot):
            continue
        parts = os.path.relpath(lexical, lroot).split(os.sep)
        if parts == ["."]:
            parts = []
        # No link or junction anywhere below the root, then the real path must stay inside too.
        cur = lroot
        for part in parts:
            cur = os.path.join(cur, part)
            if os.path.lexists(cur) and _is_link(cur):
                fail(f"symbolic links and junctions are not allowed: {cur}")
        if os.path.exists(lroot) and not _inside(_real(lexical), _real(lroot)):
            fail(f"path leaves {kind} through a link: {path}")
        if any(p in FORBIDDEN_PARTS for p in parts):
            fail(f"paths inside .git or .paperclip are not allowed: {path}")
        if kind == "staging" and (len(parts) < 2 or not ASSET_ID.match(parts[0])):
            fail(f"staging paths must be staging/art/<asset_id>/<file> (asset_id: a-z, 0-9, _ or -): {path}")
        return kind, lroot, parts, os.path.realpath(os.path.abspath(path))
    fail(f"path outside the staging folder and the Task Workspace: {path}")


def _links(p):
    try:
        return os.stat(p, follow_symlinks=False).st_nlink
    except OSError:
        return 0


def check_in(path):
    """Validate an input and return its canonical path."""
    canonical = _locate(path)[3]
    if not os.path.isfile(canonical):
        fail(f"no such file: {path}")
    if _links(canonical) > 1:
        fail(f"hard-linked files are not allowed: {path}")
    if os.path.getsize(canonical) > MAX_INPUT_BYTES:
        fail(f"input larger than {MAX_INPUT_BYTES} bytes: {path}")
    return canonical


def check_out(path):
    """Validate an output and return its canonical path."""
    kind, root, parts, canonical = _locate(path)
    if kind == "workspace" and not any(tuple(parts[:len(d)]) == d and len(parts) > len(d) for d in OUTPUT_DIRS):
        fail(f"workspace outputs must be under assets/slice/ or art_src/: {path}")
    if not path.lower().endswith(".png"):
        fail("outputs are PNG files")
    if os.path.lexists(canonical) and (_is_link(canonical) or not os.path.isfile(canonical) or _links(canonical) > 1):
        fail(f"output exists and is not a plain, single-link file: {path}")
    os.makedirs(os.path.dirname(canonical), exist_ok=True)
    if _locate(path)[3] != canonical:   # re-check after creating folders
        fail(f"output path changed while it was checked: {path}")
    return canonical


# ---------- image helpers ----------

def _open(path, max_pixels=None):
    canonical = check_in(path)
    limit = max_pixels or MAX_INPUT_PIXELS
    try:
        img = Image.open(canonical)
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError) as e:
        fail(f"cannot open {path}: {e}")
    if img.width * img.height > limit:
        fail(f"{path} is {img.width}x{img.height}; the limit is {limit} pixels")
    return img


def load(path, max_pixels=None):
    with _open(path, max_pixels) as img:
        return img.convert("RGBA")


def save(img, path):
    if img.width > MAX_SIDE or img.height > MAX_SIDE:
        fail(f"output {img.width}x{img.height} exceeds {MAX_SIDE} per side")
    canonical = check_out(path)
    # Write a new file next to the target, then rename it over the target: never write through an
    # existing directory entry (a hard link created after the check is replaced, not modified).
    fd, tmp = tempfile.mkstemp(prefix=".art-ops-", suffix=".png", dir=os.path.dirname(canonical))
    try:
        with os.fdopen(fd, "wb") as f:
            img.save(f, "PNG", optimize=True)
        os.replace(tmp, canonical)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    print(f"{path} {img.width}x{img.height}")


def _size(w, h, what="size"):
    if not (1 <= w <= MAX_SIDE and 1 <= h <= MAX_SIDE):
        fail(f"{what} must be between 1 and {MAX_SIDE} per side, got {w}x{h}")
    return w, h


def _count(items, what):
    if len(items) > MAX_FILES:
        fail(f"at most {MAX_FILES} {what} per command, got {len(items)}")


def _range(value, lo, hi, name):
    if not (lo <= value <= hi):
        fail(f"--{name} must be between {lo} and {hi}, got {value}")


def _colour(c, name):
    if c is not None and not all(0 <= v <= 255 for v in c):
        fail(f"--{name} components must be 0-255, got {c}")


# ---------- commands ----------

def cmd_info(a):
    with _open(a.img) as img:
        bbox = img.convert("RGBA").getchannel("A").getbbox()
        print(f"{a.img}: {img.width}x{img.height} mode={img.mode} alpha_bbox={bbox}")


def cmd_crop(a):
    x, y, w, h = a.box
    img = load(a.inp)
    if w < 1 or h < 1 or x < 0 or y < 0 or x + w > img.width or y + h > img.height:
        fail(f"box {a.box} is not inside the {img.width}x{img.height} image")
    save(img.crop((x, y, x + w, y + h)), a.out)


def cmd_resize(a):
    w, h = _size(*a.size)
    img, flt = load(a.inp), FILTERS[a.filter]
    if a.fit == "stretch":
        out = img.resize((w, h), flt)
    elif a.fit == "cover":
        # Crop the source to the target aspect ratio, then resample straight to W x H: no intermediate
        # image larger than the target, whatever the input's aspect ratio.
        out = ImageOps.fit(img, (w, h), method=flt, centering=(0.5, 0.5))
    else:
        scale = min(w / img.width, h / img.height)
        r = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), flt)
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.paste(r, ((w - r.width) // 2, (h - r.height) // 2))   # exact copy onto a transparent canvas
    save(out, a.out)


def border_connected(bg):
    """Pixels of the boolean mask `bg` 4-connected to the image border.

    Scanline connected components: NumPy finds each row's runs of background pixels, then a depth-first
    search visits each run once and finds its overlapping runs in the rows above and below by binary
    search. Time O(R log R) for R runs (R <= pixels / 2), memory O(R); no per-pixel Python loop and no
    repeated whole-image passes."""
    h, w = bg.shape
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = bg
    d = np.diff(padded, axis=1)
    run_y, run_s = np.nonzero(d == 1)          # row-major, so runs are sorted within each row
    _, run_e = np.nonzero(d == -1)             # exclusive end of each run
    n = len(run_y)
    if n == 0:
        return np.zeros_like(bg)
    offs = np.searchsorted(run_y, np.arange(h + 1)).tolist()
    ys, ss, es = run_y.tolist(), run_s.tolist(), run_e.tolist()
    row_s = [ss[offs[y]:offs[y + 1]] for y in range(h)]
    row_e = [es[offs[y]:offs[y + 1]] for y in range(h)]
    seen = bytearray(n)
    stack = [r for r in range(n) if ys[r] == 0 or ys[r] == h - 1 or ss[r] == 0 or es[r] == w]
    for r in stack:
        seen[r] = 1
    while stack:
        r = stack.pop()
        y, s, e = ys[r], ss[r], es[r]
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                base = offs[ny]
                lo = bisect.bisect_right(row_e[ny], s)   # first run that ends after s
                hi = bisect.bisect_left(row_s[ny], e)    # runs that start before e
                for j in range(base + lo, base + hi):
                    if not seen[j]:
                        seen[j] = 1
                        stack.append(j)
    keep = np.frombuffer(bytes(seen), dtype=np.uint8).astype(bool)
    marks = np.zeros((h, w + 1), dtype=np.int32)
    np.add.at(marks, (run_y[keep], run_s[keep]), 1)
    np.add.at(marks, (run_y[keep], run_e[keep]), -1)
    return np.cumsum(marks, axis=1)[:, :w] > 0


def cmd_key(a):
    _colour(a.color, "color")
    _range(a.tolerance, 0, 442, "tolerance")
    _range(a.soft, 1, 442, "soft")
    img = load(a.inp, MAX_KEY_PIXELS)
    arr = np.asarray(img).astype(np.float32)
    color = a.color
    if color is None:
        k = max(1, min(8, arr.shape[0] // 2, arr.shape[1] // 2))
        corners = np.concatenate([arr[:k, :k, :3].reshape(-1, 3), arr[:k, -k:, :3].reshape(-1, 3),
                                  arr[-k:, :k, :3].reshape(-1, 3), arr[-k:, -k:, :3].reshape(-1, 3)])
        color = [int(v) for v in np.median(corners, axis=0)]
        print(f"key colour (from corners): {color}")
    key = np.array(color, dtype=np.float32)
    dist = np.sqrt(((arr[..., :3] - key) ** 2).sum(-1))
    alpha = np.clip((dist - a.tolerance) / a.soft, 0, 1)
    # Keep only background that is connected to the image border, so subject colours close to the
    # backdrop (dark green cloth, shadows) stay opaque.
    reach = border_connected(alpha < 1)
    alpha = np.where(reach, alpha, 1.0)
    arr[..., 3] = arr[..., 3] * alpha
    # remove the key colour's spill from semi-transparent edges
    g = color.index(max(color))
    others = [c for c in range(3) if c != g]
    edge = alpha < 1
    arr[..., g] = np.where(edge, np.minimum(arr[..., g], arr[..., others].max(-1)), arr[..., g])
    save(Image.fromarray(np.rint(arr).astype(np.uint8), "RGBA"), a.out)


def cmd_trim(a):
    _range(a.pad, 0, 1024, "pad")
    img = load(a.inp)
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        fail("image is fully transparent")
    p = a.pad
    bbox = (max(0, bbox[0] - p), max(0, bbox[1] - p), min(img.width, bbox[2] + p), min(img.height, bbox[3] + p))
    save(img.crop(bbox), a.out)


def cmd_canvas(a):
    w, h = _size(*a.size, what="canvas")
    img = load(a.inp)
    if img.width > w or img.height > h:
        fail(f"image {img.width}x{img.height} is larger than the canvas {w}x{h}; resize first")
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = h - img.height if a.anchor == "bottom_center" else (h - img.height) // 2
    out.paste(img, ((w - img.width) // 2, y))                      # exact copy
    save(out, a.out)


def cmd_sheet(a):
    cw, ch = _size(*a.cell, what="cell")
    _range(a.cols, 1, MAX_SIDE, "cols")
    _count(a.frames, "frames")
    cols = a.cols                   # the sheet is always `cols` cells wide, as engines expect
    rows = -(-len(a.frames) // cols)
    _size(cw * cols, ch * rows, what="sheet")
    out = Image.new("RGBA", (cw * cols, ch * rows), (0, 0, 0, 0))
    for i, f in enumerate(a.frames):
        fr = load(f)
        if fr.size != (cw, ch):
            fail(f"{f} is {fr.width}x{fr.height}, not the cell size {cw}x{ch}")
        out.paste(fr, ((i % cols) * cw, (i // cols) * ch))         # exact copy into its own cell
    save(out, a.out)


def cmd_grade(a):
    for k in ("brightness", "contrast", "saturation"):
        _range(getattr(a, k), 0, 4, k)
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
    cw, ch = _size(*a.cell, what="cell")
    _colour(a.bg, "bg")
    _count(a.images, "images")
    cols = min(4, len(a.images))
    rows = -(-len(a.images) // cols)
    label = 0 if a.no_labels else 18
    _size(cw * cols, (ch + label) * rows, what="contact sheet")
    bg = tuple(a.bg) + (255,) if a.bg else (24, 26, 32, 255)
    out = Image.new("RGBA", (cw * cols, (ch + label) * rows), bg)
    d = ImageDraw.Draw(out)
    lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    ink = (20, 20, 20, 255) if lum > 140 else (220, 220, 220, 255)
    for i, f in enumerate(a.images):
        im = load(f)
        im.thumbnail((cw, ch), FILTERS[a.filter])                   # shrinks only, never enlarges
        x, y = (i % cols) * cw, (i // cols) * (ch + label)
        out.alpha_composite(im, dest=(x + (cw - im.width) // 2, y + (ch - im.height) // 2))
        if label:
            d.text((x + 4, y + ch + 2), os.path.basename(f)[:40], fill=ink)
    save(out, a.out)


def load_mask(path, size=None):
    """A greyscale mask (0-255). RGB(A) masks are read by luminance; the mask's own alpha is ignored."""
    with _open(path) as im:
        m = im.convert("L")
    if size is not None and m.size != tuple(size):
        fail(f"mask {path} is {m.width}x{m.height}, not {size[0]}x{size[1]}")
    return m


def _dilate(arr, n):
    """Grey dilation by a (2n+1) square, as n separable 3-pixel max passes (n <= MAX_MASK_RADIUS)."""
    for _ in range(n):
        p = np.pad(arr, 1, mode="edge")
        arr = np.maximum(np.maximum(p[1:-1, :-2], p[1:-1, 1:-1]), p[1:-1, 2:])
        p = np.pad(arr, 1, mode="edge")
        arr = np.maximum(np.maximum(p[:-2, 1:-1], p[1:-1, 1:-1]), p[2:, 1:-1])
    return arr


def cmd_mask(a):
    for k in ("grow", "shrink", "feather"):
        _range(getattr(a, k), 0, MAX_MASK_RADIUS, k)
    _range(a.threshold, 0, 254, "threshold")
    _range(a.tolerance, 0, 442, "tolerance")
    shapes = len(a.rect) + len(a.ellipse) + len(a.polygon)
    if shapes > MAX_SHAPES:
        fail(f"at most {MAX_SHAPES} shapes per mask, got {shapes}")
    if not shapes and not a.from_alpha and not a.from_color:
        fail("give at least one shape (--rect, --ellipse, --polygon) or source (--from-alpha, --from-color)")
    if (a.size is None) == (a.like is None):
        fail("give exactly one of --size W H or --like IMG")
    if a.like:
        with _open(a.like) as im:
            w, h = im.size
    else:
        w, h = _size(*a.size, what="mask")
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for x, y, rw, rh in a.rect:
        if rw < 1 or rh < 1:
            fail(f"--rect {x} {y} {rw} {rh}: width and height must be at least 1")
        d.rectangle((x, y, x + rw - 1, y + rh - 1), fill=255)
    for x, y, ew, eh in a.ellipse:
        if ew < 1 or eh < 1:
            fail(f"--ellipse {x} {y} {ew} {eh}: width and height must be at least 1")
        d.ellipse((x, y, x + ew - 1, y + eh - 1), fill=255)
    for pts in a.polygon:
        if len(pts) % 2 or not 3 <= len(pts) // 2 <= MAX_POLY_POINTS:
            fail(f"--polygon needs 3 to {MAX_POLY_POINTS} X Y pairs, got {len(pts)} numbers")
        d.polygon([(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)], fill=255)
    arr = np.asarray(m).copy()
    if a.from_alpha:
        src = load(a.from_alpha)
        if src.size != (w, h):
            fail(f"--from-alpha image is {src.width}x{src.height}, not the mask size {w}x{h}")
        arr = np.maximum(arr, np.where(np.asarray(src.getchannel("A")) > a.threshold, 255, 0).astype(np.uint8))
    if a.from_color:
        path, rgb = a.from_color[0], a.from_color[1:]
        try:
            rgb = [int(v) for v in rgb]
        except ValueError:
            fail(f"--from-color needs IMG R G B, got {a.from_color}")
        _colour(rgb, "from-color")
        src = load(path)
        if src.size != (w, h):
            fail(f"--from-color image is {src.width}x{src.height}, not the mask size {w}x{h}")
        px = np.asarray(src).astype(np.float32)
        dist = np.sqrt(((px[..., :3] - np.array(rgb, dtype=np.float32)) ** 2).sum(-1))
        arr = np.maximum(arr, np.where((dist <= a.tolerance) & (px[..., 3] > 0), 255, 0).astype(np.uint8))
    if a.grow:
        arr = _dilate(arr, a.grow)
    if a.shrink:
        arr = 255 - _dilate(255 - arr, a.shrink)
    if a.invert:
        arr = 255 - arr
    out = Image.fromarray(arr.astype(np.uint8), "L")
    if a.feather:
        out = out.filter(ImageFilter.GaussianBlur(a.feather))
    save(out, a.out)
    sel = int((np.asarray(out) > 0).sum())
    print(f"mask: {w}x{h}, selected (value > 0) {sel} px, full (255) {int((np.asarray(out) == 255).sum())} px")


def cmd_compose(a):
    _range(a.opacity, 0, 1, "opacity")
    base = load(a.base)
    over = load(a.over)
    x, y = a.at
    if abs(x) > MAX_SIDE or abs(y) > MAX_SIDE:
        fail(f"--at must be within +-{MAX_SIDE}, got {x} {y}")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(over, (x, y))                                   # exact copy, clipped to the base
    if a.opacity < 1:
        la = np.asarray(layer).copy()
        la[..., 3] = np.rint(la[..., 3].astype(np.float32) * a.opacity).astype(np.uint8)
        layer = Image.fromarray(la, "RGBA")
    comp = base.copy()
    comp.alpha_composite(layer)
    if a.mask:
        m = np.asarray(load_mask(a.mask, base.size)).astype(np.uint32)[..., None]
        b, c = np.asarray(base).astype(np.uint32), np.asarray(comp).astype(np.uint32)
        mixed = (b * (255 - m) + c * m + 127) // 255
        # exact at both ends: mask 0 -> base, mask 255 -> composite
        mixed = np.where(m == 0, b, np.where(m == 255, c, mixed))
        comp = Image.fromarray(mixed.astype(np.uint8), "RGBA")
    save(comp, a.out)


def cmd_diff(a):
    ia, ib = load(a.a), load(a.b)
    if ia.size != ib.size:
        fail(f"sizes differ: {ia.width}x{ia.height} and {ib.width}x{ib.height}")
    da = np.abs(np.asarray(ia).astype(np.int16) - np.asarray(ib).astype(np.int16))
    changed = da.max(-1) > 0
    heat = np.zeros(da.shape[:2] + (4,), dtype=np.uint8)
    heat[..., 0] = np.where(changed, np.maximum(64, da.max(-1)), 0).astype(np.uint8)
    heat[..., 3] = 255
    save(Image.fromarray(heat, "RGBA"), a.out)
    n = changed.size
    print(f"diff: {int(changed.sum())} of {n} px changed")
    for i, ch in enumerate("RGBA"):
        print(f"  {ch}: max {int(da[..., i].max())}, mean {float(da[..., i].mean()):.4f}")
    if a.mask:
        m = np.asarray(load_mask(a.mask, ia.size))
        outside = int((changed & (m == 0)).sum())
        print(f"  outside mask (mask = 0): {int((m == 0).sum())} px, changed {outside}")
        if a.fail_outside and outside:
            fail(f"{outside} pixels changed outside the mask")
    elif a.fail_outside:
        fail("--fail-outside needs --mask")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info"); s.add_argument("img"); s.set_defaults(fn=cmd_info)
    s = sub.add_parser("crop"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--box", type=int, nargs=4, required=True); s.set_defaults(fn=cmd_crop)
    s = sub.add_parser("resize"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--size", type=int, nargs=2, required=True)
    s.add_argument("--fit", choices=["contain", "cover", "stretch"], default="contain")
    s.add_argument("--filter", choices=sorted(FILTERS), default="lanczos"); s.set_defaults(fn=cmd_resize)
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
    s.add_argument("--bg", type=int, nargs=3, default=None, help="flat background colour R G B (target-background preview)")
    s.add_argument("--filter", choices=sorted(FILTERS), default="lanczos")
    s.add_argument("--no-labels", action="store_true")
    s.add_argument("images", nargs="+"); s.set_defaults(fn=cmd_contact)
    s = sub.add_parser("mask"); s.add_argument("out")
    s.add_argument("--size", type=int, nargs=2, default=None); s.add_argument("--like", default=None)
    s.add_argument("--rect", type=int, nargs=4, action="append", default=[])
    s.add_argument("--ellipse", type=int, nargs=4, action="append", default=[])
    s.add_argument("--polygon", type=int, nargs="+", action="append", default=[])
    s.add_argument("--from-alpha", default=None); s.add_argument("--threshold", type=int, default=0)
    s.add_argument("--from-color", nargs=4, default=None, metavar=("IMG", "R", "G", "B"))
    s.add_argument("--tolerance", type=float, default=30)
    s.add_argument("--grow", type=int, default=0); s.add_argument("--shrink", type=int, default=0)
    s.add_argument("--invert", action="store_true"); s.add_argument("--feather", type=float, default=0)
    s.set_defaults(fn=cmd_mask)
    s = sub.add_parser("compose"); s.add_argument("out"); s.add_argument("--base", required=True)
    s.add_argument("--over", required=True); s.add_argument("--at", type=int, nargs=2, default=[0, 0])
    s.add_argument("--opacity", type=float, default=1.0); s.add_argument("--mask", default=None)
    s.set_defaults(fn=cmd_compose)
    s = sub.add_parser("diff"); s.add_argument("out"); s.add_argument("a"); s.add_argument("b")
    s.add_argument("--mask", default=None); s.add_argument("--fail-outside", action="store_true")
    s.set_defaults(fn=cmd_diff)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
