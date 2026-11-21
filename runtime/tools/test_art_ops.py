"""Tests for art-ops.py. Needs Pillow and NumPy, so run them with ComfyUI's embedded Python:

    & "$HOME/game-studio-workspace/tools/ComfyUI_windows_portable/python_embeded/python.exe" -I -s runtime/tools/test_art_ops.py

Every test works in a temporary Task Workspace (a folder with `.git`) and a temporary staging folder.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("art_ops", os.path.join(HERE, "art-ops.py"))
art_ops = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(art_ops)
Image = art_ops.Image

SEMI = (200, 50, 10, 128)           # a semi-transparent pixel that must survive exactly


class ArtOpsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="art-ops-test-")
        self.ws = os.path.join(self.tmp, "ws")
        self.staging = os.path.join(self.tmp, "staging", "art")
        self.outside = os.path.join(self.tmp, "outside")
        for d in (os.path.join(self.ws, ".git"), os.path.join(self.staging, "hero_idle"), self.outside,
                  os.path.join(self.ws, "art_src"), os.path.join(self.ws, "assets", "slice")):
            os.makedirs(d)
        self._cwd = os.getcwd()
        os.chdir(self.ws)
        self._saved = {k: getattr(art_ops, k) for k in ("STAGING", "MAX_INPUT_PIXELS", "MAX_FILES", "MAX_SIDE")}
        art_ops.STAGING = self.staging

    def tearDown(self):
        os.chdir(self._cwd)
        for k, v in self._saved.items():
            setattr(art_ops, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers
    def st(self, name):
        return os.path.join(self.staging, "hero_idle", name)

    def img(self, path, size, color=(0, 0, 0, 0)):
        im = Image.new("RGBA", size, color)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        im.save(path)
        return im

    def run_ok(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            art_ops.main(list(args))
        return out.getvalue()

    def refused(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                art_ops.main(list(args))
        self.assertNotEqual(cm.exception.code, 0)
        return str(cm.exception.code)

    def px(self, path, xy):
        return self.rgba(path).getpixel(xy)

    def rgba(self, path):
        with Image.open(path) as im:
            return im.convert("RGBA")


class RgbaPreservation(ArtOpsCase):
    def test_canvas_copies_semi_transparent_pixels_exactly(self):
        self.img(self.st("a.png"), (2, 2), SEMI)
        self.run_ok("canvas", self.st("a.png"), self.st("b.png"), "--size", "4", "4", "--anchor", "center")
        self.assertEqual(self.px(self.st("b.png"), (1, 1)), SEMI)
        self.assertEqual(self.px(self.st("b.png"), (0, 0)), (0, 0, 0, 0))

    def test_sheet_copies_semi_transparent_pixels_exactly(self):
        self.img(self.st("f.png"), (2, 2), SEMI)
        self.run_ok("sheet", self.st("s.png"), "--cols", "1", "--cell", "2", "2", self.st("f.png"))
        self.assertEqual(self.px(self.st("s.png"), (0, 0)), SEMI)

    def test_resize_contain_keeps_alpha(self):
        self.img(self.st("a.png"), (2, 1), SEMI)
        self.run_ok("resize", self.st("a.png"), self.st("b.png"), "--size", "4", "4", "--filter", "nearest")
        self.assertEqual(self.px(self.st("b.png"), (0, 1)), SEMI)
        self.assertEqual(self.px(self.st("b.png"), (0, 0)), (0, 0, 0, 0))   # padding stays transparent

    def test_lanczos_resize_does_not_bleed_transparent_colour(self):
        im = self.img(self.st("a.png"), (2, 2))
        im.putpixel((0, 0), (255, 0, 0, 255)); im.putpixel((1, 0), (0, 255, 0, 0)); im.save(self.st("a.png"))
        self.run_ok("resize", self.st("a.png"), self.st("b.png"), "--size", "1", "1", "--fit", "stretch")
        r, g, b, a = self.px(self.st("b.png"), (0, 0))
        self.assertGreater(a, 0)
        self.assertEqual(g, 0)

    def test_grade_keeps_alpha(self):
        self.img(self.st("a.png"), (2, 2), SEMI)
        self.run_ok("grade", self.st("a.png"), self.st("b.png"), "--brightness", "1.2")
        self.assertEqual(self.px(self.st("b.png"), (0, 0))[3], 128)

    def test_contact_composites_over_background(self):
        self.img(self.st("a.png"), (2, 2), (255, 255, 255, 128))
        self.run_ok("contact", self.st("c.png"), "--cell", "2", "2", "--bg", "0", "0", "0", "--no-labels",
                    self.st("a.png"))
        self.assertEqual(self.px(self.st("c.png"), (0, 0)), (128, 128, 128, 255))


class Commands(ArtOpsCase):
    def test_sheet_layout_row_major(self):
        colours = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
        frames = []
        for i, c in enumerate(colours):
            self.img(self.st(f"f{i}.png"), (4, 3), c)
            frames.append(self.st(f"f{i}.png"))
        self.run_ok("sheet", self.st("s.png"), "--cols", "2", "--cell", "4", "3", *frames)
        s = self.rgba(self.st("s.png"))
        self.assertEqual(s.size, (8, 6))
        self.assertEqual(self.px(self.st("s.png"), (0, 0)), colours[0])
        self.assertEqual(self.px(self.st("s.png"), (4, 0)), colours[1])
        self.assertEqual(self.px(self.st("s.png"), (0, 3)), colours[2])
        self.assertEqual(self.px(self.st("s.png"), (4, 3)), (0, 0, 0, 0))   # empty cell

    def test_sheet_refuses_wrong_frame_size(self):
        self.img(self.st("f.png"), (5, 3), (1, 1, 1, 255))
        self.assertIn("cell size", self.refused("sheet", self.st("s.png"), "--cols", "1", "--cell", "4", "3", self.st("f.png")))

    def test_canvas_bottom_center_placement(self):
        self.img(self.st("a.png"), (2, 2), (9, 9, 9, 255))
        self.run_ok("canvas", self.st("a.png"), self.st("b.png"), "--size", "6", "5")
        self.assertEqual(self.rgba(self.st("b.png")).getbbox(), (2, 3, 4, 5))

    def test_canvas_refuses_larger_image(self):
        self.img(self.st("a.png"), (8, 8), (9, 9, 9, 255))
        self.refused("canvas", self.st("a.png"), self.st("b.png"), "--size", "4", "4")

    def test_crop_exact_region(self):
        im = self.img(self.st("a.png"), (4, 4), (0, 0, 0, 255))
        im.putpixel((2, 1), (255, 0, 0, 255)); im.save(self.st("a.png"))
        self.run_ok("crop", self.st("a.png"), self.st("b.png"), "--box", "2", "1", "2", "2")
        self.assertEqual(self.rgba(self.st("b.png")).size, (2, 2))
        self.assertEqual(self.px(self.st("b.png"), (0, 0)), (255, 0, 0, 255))

    def test_crop_refuses_box_outside_image(self):
        self.img(self.st("a.png"), (4, 4), (0, 0, 0, 255))
        self.refused("crop", self.st("a.png"), self.st("b.png"), "--box", "3", "3", "2", "2")

    def test_key_removes_border_backdrop_and_keeps_enclosed_colour(self):
        im = self.img(self.st("a.png"), (20, 20), (0, 200, 0, 255))
        for x in range(6, 14):
            for y in range(6, 14):
                im.putpixel((x, y), (200, 0, 0, 255))
        im.putpixel((10, 10), (0, 200, 0, 255))   # backdrop colour enclosed by the subject
        im.save(self.st("a.png"))
        self.run_ok("key", self.st("a.png"), self.st("b.png"))
        self.assertEqual(self.px(self.st("b.png"), (0, 0))[3], 0)
        self.assertEqual(self.px(self.st("b.png"), (8, 8)), (200, 0, 0, 255))
        self.assertEqual(self.px(self.st("b.png"), (10, 10))[3], 255)

    def test_resize_nearest_keeps_pixel_edges(self):
        im = self.img(self.st("a.png"), (2, 2), (0, 0, 0, 255))
        im.putpixel((1, 0), (255, 255, 255, 255)); im.save(self.st("a.png"))
        self.run_ok("resize", self.st("a.png"), self.st("b.png"), "--size", "8", "8", "--filter", "nearest")
        out = self.rgba(self.st("b.png"))
        self.assertEqual({out.getpixel((x, y)) for x in range(4, 8) for y in range(4)}, {(255, 255, 255, 255)})
        self.assertEqual({out.getpixel((x, y)) for x in range(4) for y in range(4)}, {(0, 0, 0, 255)})

    def test_resize_lanczos_is_still_default(self):
        self.img(self.st("a.png"), (2, 2), (0, 0, 0, 255))
        self.run_ok("resize", self.st("a.png"), self.st("b.png"), "--size", "4", "4")
        self.assertEqual(self.rgba(self.st("b.png")).size, (4, 4))

    def test_trim(self):
        im = self.img(self.st("a.png"), (10, 10))
        im.putpixel((5, 5), (1, 2, 3, 255)); im.save(self.st("a.png"))
        self.run_ok("trim", self.st("a.png"), self.st("b.png"), "--pad", "1")
        self.assertEqual(self.rgba(self.st("b.png")).size, (3, 3))

    def test_info(self):
        self.img(self.st("a.png"), (3, 2), SEMI)
        self.assertIn("3x2", self.run_ok("info", self.st("a.png")))


class InvalidArguments(ArtOpsCase):
    def setUp(self):
        super().setUp()
        self.img(self.st("a.png"), (4, 4), (1, 1, 1, 255))

    def test_bad_values(self):
        a, b = self.st("a.png"), self.st("b.png")
        self.refused("resize", a, b, "--size", "0", "4")
        self.refused("resize", a, b, "--size", "-1", "4")
        self.refused("resize", a, b, "--size", "4", "4", "--filter", "bicubic")
        self.refused("canvas", a, b, "--size", str(art_ops.MAX_SIDE + 1), "4")
        self.refused("sheet", b, "--cols", "0", "--cell", "4", "4", a)
        self.refused("key", a, b, "--tolerance", "-1")
        self.refused("key", a, b, "--soft", "0")
        self.refused("key", a, b, "--color", "0", "300", "0")
        self.refused("trim", a, b, "--pad", "-2")
        self.refused("grade", a, b, "--contrast", "9")
        self.refused("contact", b, "--bg", "0", "0", "256", a)
        self.refused("crop", a, b, "--box", "0", "0", "0", "2")

    def test_not_an_image(self):
        with open(self.st("x.png"), "w") as f:
            f.write("not an image")
        self.assertIn("cannot open", self.refused("info", self.st("x.png")))


class ResourceLimits(ArtOpsCase):
    def test_input_pixel_limit(self):
        self.img(self.st("big.png"), (20, 20), (1, 1, 1, 255))
        art_ops.MAX_INPUT_PIXELS = 100
        self.assertIn("limit", self.refused("info", self.st("big.png")))

    def test_file_count_limit(self):
        self.img(self.st("a.png"), (2, 2), (1, 1, 1, 255))
        art_ops.MAX_FILES = 2
        self.refused("sheet", self.st("s.png"), "--cols", "3", "--cell", "2", "2", *[self.st("a.png")] * 3)

    def test_output_side_limit(self):
        self.img(self.st("a.png"), (2, 2), (1, 1, 1, 255))
        art_ops.MAX_SIDE = 3
        self.refused("sheet", self.st("s.png"), "--cols", "2", "--cell", "2", "2", self.st("a.png"), self.st("a.png"))


class PathBoundary(ArtOpsCase):
    def setUp(self):
        super().setUp()
        self.img(self.st("a.png"), (2, 2), (1, 1, 1, 255))

    def test_allowed_outputs(self):
        self.run_ok("trim", self.st("a.png"), os.path.join("art_src", "hero", "a.png"), "--pad", "0")
        self.run_ok("trim", self.st("a.png"), os.path.join("assets", "slice", "a.png"), "--pad", "0")
        self.run_ok("trim", os.path.join("art_src", "hero", "a.png"), self.st("c.png"), "--pad", "0")

    def test_output_outside_roots(self):
        self.refused("trim", self.st("a.png"), os.path.join(self.outside, "a.png"))

    def test_output_in_workspace_but_not_an_art_folder(self):
        self.refused("trim", self.st("a.png"), "a.png")
        self.refused("trim", self.st("a.png"), os.path.join("src", "a.png"))
        self.refused("trim", self.st("a.png"), os.path.join("assets", "a.png"))

    def test_traversal(self):
        self.refused("trim", self.st("a.png"), os.path.join("art_src", "..", "..", "outside", "a.png"))
        self.refused("trim", self.st("a.png"), os.path.join(self.staging, "hero_idle", "..", "..", "..", "outside", "a.png"))

    def test_git_and_paperclip_folders(self):
        self.img(os.path.join(self.ws, ".git", "x.png"), (2, 2), (1, 1, 1, 255))
        self.refused("info", os.path.join(".git", "x.png"))
        self.img(os.path.join(self.ws, ".paperclip", "worktrees", "SOU-1", "art_src", "x.png"), (2, 2), (1, 1, 1, 255))
        self.refused("info", os.path.join(".paperclip", "worktrees", "SOU-1", "art_src", "x.png"))
        self.refused("trim", self.st("a.png"), os.path.join("art_src", ".git", "a.png"))

    def test_staging_needs_an_asset_folder(self):
        self.refused("trim", self.st("a.png"), os.path.join(self.staging, "a.png"))
        self.refused("trim", self.st("a.png"), os.path.join(self.staging, "Bad Id", "a.png"))

    def test_png_only(self):
        self.refused("trim", self.st("a.png"), self.st("a.jpg"))

    def test_must_run_from_workspace_root(self):
        os.chdir(self.outside)
        self.assertIn(".git", self.refused("info", self.st("a.png")))

    def test_unc_device_and_stream_paths(self):
        self.refused("info", r"\\server\share\a.png")
        self.refused("info", r"\\?\C:\a.png")
        self.refused("trim", self.st("a.png"), "art_src/a.png:evil")

    @unittest.skipUnless(os.name == "nt", "Windows drives")
    def test_other_drive(self):
        here = os.path.splitdrive(self.ws)[0].upper()
        other = "Q:" if here != "Q:" else "R:"
        self.refused("trim", self.st("a.png"), other + r"\art_src\a.png")

    @unittest.skipUnless(os.name == "nt", "junctions are Windows only")
    def test_junction_escape(self):
        import _winapi
        _winapi.CreateJunction(self.outside, os.path.join(self.ws, "art_src", "link"))
        self.assertIn("link", self.refused("trim", self.st("a.png"), os.path.join("art_src", "link", "a.png")))
        self.assertFalse(os.path.exists(os.path.join(self.outside, "a.png")))

    def test_symlink_escape(self):
        link = os.path.join(self.ws, "art_src", "sym")
        try:
            os.symlink(self.outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted for this user")
        self.refused("trim", self.st("a.png"), os.path.join("art_src", "sym", "a.png"))
        self.assertFalse(os.path.exists(os.path.join(self.outside, "a.png")))

    def test_output_that_is_a_link_is_refused(self):
        target = os.path.join(self.outside, "t.png")
        self.img(target, (2, 2))
        link = os.path.join(self.ws, "art_src", "o.png")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted for this user")
        self.refused("trim", self.st("a.png"), link)


if __name__ == "__main__":
    unittest.main(verbosity=1)
