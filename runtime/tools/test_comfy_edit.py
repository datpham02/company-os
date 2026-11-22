"""Tests for comfy-edit.py (no ComfyUI needed: the server calls are replaced). Run with ComfyUI's embedded Python:

    & "$HOME/game-studio-workspace/tools/ComfyUI_windows_portable/python_embeded/python.exe" -I -s runtime/tools/test_comfy_edit.py
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("comfy_edit", os.path.join(HERE, "comfy-edit.py"))
ce = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ce)
art_ops, np, Image = ce.art_ops, ce.np, ce.Image

GOOD_STATS = {"system": {"comfyui_version": ce.EXPECTED_VERSION,
                         "argv": ["main.py", "--listen", "127.0.0.1", "--port", "8188", "--offline"]}}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="comfy-edit-test-")
        self.ws = os.path.join(self.tmp, "ws")
        self.staging = os.path.join(self.tmp, "staging", "art")
        self.comfy = os.path.join(self.tmp, "comfy")
        for d in (os.path.join(self.ws, ".git"), os.path.join(self.ws, "art_src"), os.path.join(self.ws, "docs"),
                  self.staging, os.path.join(self.comfy, "ComfyUI", "input"), os.path.join(self.comfy, "ComfyUI", "output"),
                  os.path.join(self.tmp, "outside")):
            os.makedirs(d)
        self._cwd = os.getcwd()
        os.chdir(self.ws)
        self.saved = {"ao_STAGING": art_ops.STAGING, "STAGING_ROOT": ce.STAGING_ROOT, "COMFY_DIR": ce.COMFY_DIR,
                      "ensure_server": ce.ensure_server, "run_prompt": ce.run_prompt, "fetch_image": ce.fetch_image}
        art_ops.STAGING = self.staging
        ce.STAGING_ROOT = self.staging
        ce.COMFY_DIR = self.comfy
        ce.ensure_server = lambda: ce.EXPECTED_VERSION
        self.workflows = []

        def fake_run(wf):
            self.workflows.append(wf)
            # the run's input folder exists while the workflow runs
            rel = wf["10"]["inputs"]["image"]
            self.assertTrue(os.path.isfile(os.path.join(ce.comfy_input_dir(), *rel.split("/"))))
            prefix = wf["9"]["inputs"]["filename_prefix"]
            open(os.path.join(ce.comfy_output_dir(), prefix + "_00001_.png"), "wb").close()
            return [{"filename": "x.png", "subfolder": "", "type": "output"}]

        def fake_fetch(_img):
            size = self.size
            a = np.random.default_rng(5).integers(0, 256, (size[1], size[0], 3)).astype("uint8")
            buf = io.BytesIO()
            Image.fromarray(a, "RGB").save(buf, "PNG")
            return buf.getvalue()

        ce.run_prompt, ce.fetch_image = fake_run, fake_fetch
        self.size = (256, 272)

    def tearDown(self):
        os.chdir(self._cwd)
        art_ops.STAGING = self.saved["ao_STAGING"]
        for k in ("STAGING_ROOT", "COMFY_DIR", "ensure_server", "run_prompt", "fetch_image"):
            setattr(ce, k, self.saved[k])
        shutil.rmtree(self.tmp, ignore_errors=True)

    def noise(self, rel, size, seed=1, alpha=True):
        a = np.random.default_rng(seed).integers(0, 256, (size[1], size[0], 4)).astype("uint8")
        if not alpha:
            a[..., 3] = 255
        path = os.path.join(self.ws, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.fromarray(a, "RGBA").save(path)
        return a

    def mask(self, rel, size, box):
        m = Image.new("L", size, 0)
        x, y, w, h = box
        m.paste(255, (x, y, x + w, y + h))
        m.save(os.path.join(self.ws, rel))

    def go(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            ce.main(list(args))
        return out.getvalue()

    def refused(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                ce.main(list(args))
        self.assertNotEqual(cm.exception.code, 0)
        return str(cm.exception.code)

    def records(self):
        d = os.path.join(self.staging, "hero")
        out = []
        for f in sorted(os.listdir(d)):
            if f.endswith(".provenance.json"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    out.append(json.load(fh))
        return out


class ServerVerification(Case):
    def test_good_server_accepted(self):
        self.assertEqual(ce.verify_server(GOOD_STATS), ce.EXPECTED_VERSION)

    def test_refusals(self):
        for argv, version in ((["main.py", "--listen", "127.0.0.1"], ce.EXPECTED_VERSION),            # no --offline
                              (["main.py", "--listen", "0.0.0.0", "--offline"], ce.EXPECTED_VERSION),  # not loopback
                              (["main.py", "--offline"], ce.EXPECTED_VERSION),                         # default listen
                              (["main.py", "--listen", "127.0.0.1", "--offline"], "0.45.0"),           # other version
                              (["main.py", "--listen", "127.0.0.1", "--listen", "0.0.0.0", "--offline"], ce.EXPECTED_VERSION),
                              (["main.py", "--listen=0.0.0.0", "--offline"], ce.EXPECTED_VERSION)):
            with self.assertRaises(SystemExit):
                ce.verify_server({"system": {"argv": argv, "comfyui_version": version}})
        with self.assertRaises(SystemExit):
            ce.verify_server(None)


class Arguments(Case):
    def test_refused_arguments(self):
        self.noise("art_src/in.png", (256, 256))
        self.mask("art_src/m.png", (256, 256), (10, 10, 20, 20))
        base = ["--asset", "hero", "--input", "art_src/in.png", "--prompt", "p"]
        self.assertIn("not supported", self.refused("inpaint", "--model", "flux", "--mask", "art_src/m.png", *base))
        self.assertIn("denoise", self.refused("img2img", "--model", "sdxl", "--denoise", "0.9", *base))
        self.assertIn("denoise", self.refused("inpaint", "--model", "sdxl", "--mask", "art_src/m.png", "--denoise", "0.1", *base))
        self.assertIn("count", self.refused("img2img", "--model", "sdxl", "--count", "5", *base))
        self.assertIn("steps", self.refused("img2img", "--model", "sdxl", "--steps", "100", *base))
        self.assertIn("backdrop", self.refused("img2img", "--model", "sdxl", "--backdrop", "0", "0", "300", *base))
        self.assertIn("asset", self.refused("img2img", "--model", "sdxl", "--asset", "../x", "--input", "art_src/in.png", "--prompt", "p"))
        self.assertIn("2000", self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--prompt", "x" * 2001))

    def test_refused_inputs(self):
        self.noise("docs/in.png", (256, 256))                       # workspace, but not an art folder
        self.assertIn("assets/slice/ or art_src/", self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "docs/in.png", "--prompt", "p"))
        out = os.path.join(self.tmp, "outside", "in.png")
        Image.new("RGBA", (256, 256)).save(out)
        self.assertIn("outside", self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", out, "--prompt", "p"))
        self.noise("art_src/odd.png", (250, 256))
        self.assertIn("multiple of 16", self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/odd.png", "--prompt", "p"))
        self.noise("art_src/big.png", (2064, 256))
        self.assertIn("between 256 and 2048", self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/big.png", "--prompt", "p"))
        Image.new("RGBA", (256, 256)).save(os.path.join(self.ws, "art_src", "in.webp"), "WEBP")
        self.assertIn("PNG", self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.webp", "--prompt", "p"))

    def test_refused_masks(self):
        self.noise("art_src/in.png", (256, 256))
        self.mask("art_src/small.png", (128, 128), (0, 0, 10, 10))
        self.assertIn("not 256x256", self.refused("inpaint", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--mask", "art_src/small.png", "--prompt", "p"))
        Image.new("L", (256, 256), 0).save(os.path.join(self.ws, "art_src", "empty.png"))
        self.assertIn("selects nothing", self.refused("inpaint", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--mask", "art_src/empty.png", "--prompt", "p"))

    def test_no_run_folder_or_output_after_refusal(self):
        self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/missing.png", "--prompt", "p")
        self.assertEqual(os.listdir(ce.comfy_input_dir()), [])


class Runs(Case):
    def test_inpaint_restores_outside_exactly_and_records_provenance(self):
        orig = self.noise("art_src/in.png", self.size, seed=2)
        self.mask("art_src/m.png", self.size, (40, 50, 60, 70))
        out = self.go("inpaint", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png",
                       "--mask", "art_src/m.png", "--prompt", "a lantern", "--seed", "9", "--count", "2")
        self.assertIn("provenance", out)
        recs = self.records()
        self.assertEqual(len(recs), 2)
        for r in recs:
            self.assertEqual(r["outside_mask_changed"], 0)
            self.assertEqual(r["template"], "inpaint")
            self.assertEqual(len(r["input_sha256"]), 64); self.assertEqual(len(r["mask_sha256"]), 64)
            with Image.open(os.path.join(self.staging, "hero", r["workflow"].replace(".workflow.json", ".png"))) as im:
                res = np.asarray(im.convert("RGBA"))
            m = np.zeros(self.size[::-1], bool); m[50:120, 40:100] = True
            self.assertTrue((res[~m] == orig[~m]).all())                 # alpha too, outside the mask
            self.assertTrue((res[m] != orig[m]).any())
        self.assertEqual(sorted(r["seed"] for r in recs), [9, 10])
        wf = self.workflows[0]
        self.assertEqual(wf["12"]["class_type"], "LoadImageMask")
        self.assertEqual(wf["3"]["inputs"]["latent_image"], ["13", 0])
        self.assertTrue(wf["10"]["inputs"]["image"].startswith("edit/hero/"))

    def test_img2img_and_cleanup(self):
        self.noise("art_src/in.png", self.size)
        self.go("img2img", "--model", "flux", "--asset", "hero", "--input", "art_src/in.png", "--prompt", "p", "--denoise", "0.3")
        self.assertEqual(self.records()[0]["denoise"], 0.3)
        self.assertNotIn("12", self.workflows[0])
        self.assertEqual(os.listdir(os.path.join(ce.comfy_input_dir(), "edit")), [])   # run folder and asset folder gone
        self.assertEqual(os.listdir(ce.comfy_output_dir()), [])                        # this run's outputs gone

    def test_cleanup_after_failure(self):
        self.noise("art_src/in.png", self.size)

        def boom(wf):
            self.workflows.append(wf)
            open(os.path.join(ce.comfy_output_dir(), wf["9"]["inputs"]["filename_prefix"] + "_1.png"), "wb").close()
            raise SystemExit("comfy-edit: ComfyUI reported error")
        ce.run_prompt = boom
        self.refused("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--prompt", "p")
        self.assertEqual(os.listdir(os.path.join(ce.comfy_input_dir(), "edit")), [])
        self.assertEqual(os.listdir(ce.comfy_output_dir()), [])

    def test_runs_are_isolated(self):
        self.noise("art_src/in.png", self.size)
        self.go("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--prompt", "p")
        self.go("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--prompt", "p")
        a, b = (w["10"]["inputs"]["image"] for w in self.workflows)
        self.assertNotEqual(a.split("/")[2], b.split("/")[2])

    def test_transparent_input_is_flattened_for_the_model(self):
        Image.new("RGBA", self.size, (0, 0, 0, 0)).save(os.path.join(self.ws, "art_src", "t.png"))
        seen = {}

        def capture(wf):
            p = os.path.join(ce.comfy_input_dir(), *wf["10"]["inputs"]["image"].split("/"))
            with Image.open(p) as im:
                seen["mode"], seen["px"] = im.mode, im.getpixel((0, 0))
            return [{"filename": "x.png", "subfolder": "", "type": "output"}]
        ce.run_prompt = capture
        self.go("img2img", "--model", "sdxl", "--asset", "hero", "--input", "art_src/t.png", "--prompt", "p", "--backdrop", "10", "20", "30")
        self.assertEqual(seen, {"mode": "RGB", "px": (10, 20, 30)})


class RestoreFailure(Case):
    def test_nothing_kept_when_the_restore_check_fails(self):
        self.noise("art_src/in.png", self.size)
        self.mask("art_src/m.png", self.size, (10, 10, 20, 20))
        saved = ce.restore_outside
        ce.restore_outside = lambda o, e, m: (o, 3)
        try:
            self.assertIn("outside the mask", self.refused("inpaint", "--model", "sdxl", "--asset", "hero", "--input", "art_src/in.png", "--mask", "art_src/m.png", "--prompt", "p"))
        finally:
            ce.restore_outside = saved
        self.assertEqual(os.listdir(os.path.join(self.staging, "hero")), [])
        self.assertEqual(os.listdir(os.path.join(ce.comfy_input_dir(), "edit")), [])


class Restore(unittest.TestCase):
    def test_feathered_mask_exact_at_zero(self):
        rng = np.random.default_rng(3)
        o = Image.fromarray(rng.integers(0, 256, (40, 40, 4)).astype("uint8"), "RGBA")
        e = Image.fromarray(rng.integers(0, 256, (40, 40, 3)).astype("uint8"), "RGB")
        m = Image.fromarray(np.clip(rng.normal(0, 120, (40, 40)), 0, 255).astype("uint8"), "L")
        out, changed = ce.restore_outside(o, e, m)
        self.assertEqual(changed, 0)
        z = np.asarray(m) == 0
        self.assertTrue((np.asarray(out)[z] == np.asarray(o)[z]).all())
        full = np.asarray(m) == 255
        self.assertTrue((np.asarray(out)[full][:, :3] == np.asarray(e)[full]).all())


if __name__ == "__main__":
    unittest.main(verbosity=1)
