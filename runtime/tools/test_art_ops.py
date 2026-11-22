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


class CoverResizeBounds(ArtOpsCase):
    """Finding (PR #87 re-review): --fit cover must not allocate an image larger than the target."""

    def setUp(self):
        super().setUp()
        self.sizes = []
        real = Image.Image.resize
        test = self

        def spy(im, size, *args, **kwargs):
            test.sizes.append(tuple(size))
            return real(im, size, *args, **kwargs)
        Image.Image.resize = spy
        self.addCleanup(setattr, Image.Image, "resize", real)

    def check(self, src, fit, target=(64, 64)):
        self.img(self.st("a.png"), src, (10, 20, 30, 255))
        self.run_ok("resize", self.st("a.png"), self.st("b.png"), "--size", *map(str, target), "--fit", fit)
        self.assertEqual(self.rgba(self.st("b.png")).size, target)
        self.assertTrue(self.sizes)
        for w, h in self.sizes:
            self.assertLessEqual(w, target[0], self.sizes)
            self.assertLessEqual(h, target[1], self.sizes)

    def test_cover_tall_strip(self):
        self.check((1, 4000), "cover")

    def test_cover_wide_strip(self):
        self.check((4000, 1), "cover")

    def test_cover_wide_strip_to_tall_target(self):
        self.check((4000, 3), "cover", (16, 200))

    def test_contain_extreme_ratios(self):
        self.check((1, 4000), "contain")
        self.sizes.clear()
        self.check((4000, 1), "contain")

    def test_cover_keeps_the_centre(self):
        im = self.img(self.st("a.png"), (30, 10), (0, 0, 255, 255))
        for x in range(10, 20):
            for y in range(10):
                im.putpixel((x, y), (255, 0, 0, 255))
        im.save(self.st("a.png"))
        self.run_ok("resize", self.st("a.png"), self.st("b.png"), "--size", "10", "10", "--fit", "cover",
                    "--filter", "nearest")
        out = self.rgba(self.st("b.png"))
        self.assertEqual({out.getpixel((x, y)) for x in range(10) for y in range(10)}, {(255, 0, 0, 255)})


class KeyFloodFill(ArtOpsCase):
    """Finding (PR #87 re-review): bounded, efficient border flood fill."""

    def corridor(self, n):
        """n x n: a red subject everywhere except a 1-px green corridor that winds as a serpentine from
        the top-left border through every other row; its only opening is at (0, 1)."""
        import numpy as np
        a = np.zeros((n, n, 4), dtype=np.uint8)
        a[...] = (200, 0, 0, 255)
        green = (0, 200, 0, 255)
        for y in range(1, n - 1, 2):
            a[y, 1:n - 1] = green                      # a long horizontal corridor row
            if y + 2 < n - 1:
                x = n - 2 if (y // 2) % 2 == 0 else 1  # alternate ends join the next corridor row
                a[y + 1, x] = green
        a[1, 0] = green                                # the only opening to the border
        return a

    def test_long_winding_background_is_keyed(self):
        import numpy as np
        n = 257
        a = self.corridor(n)
        Image.fromarray(a, "RGBA").save(self.st("a.png"))
        self.run_ok("key", self.st("a.png"), self.st("b.png"), "--color", "0", "200", "0")
        out = np.asarray(self.rgba(self.st("b.png")))
        green = (a[..., 1] == 200)
        # every corridor pixel is reachable from the border through the serpentine, so all are keyed;
        # the path is far longer than the image side, which the old capped loop never finished.
        self.assertTrue((out[..., 3][green] == 0).all())
        self.assertTrue((out[..., 3][~green] == 255).all())

    def test_enclosed_pocket_stays_opaque(self):
        import numpy as np
        a = np.full((40, 40, 4), (0, 200, 0, 255), dtype=np.uint8)
        a[10:30, 10:30] = (200, 0, 0, 255)
        a[15:25, 15:25] = (0, 200, 0, 255)
        Image.fromarray(a, "RGBA").save(self.st("a.png"))
        self.run_ok("key", self.st("a.png"), self.st("b.png"))
        out = np.asarray(self.rgba(self.st("b.png")))
        self.assertEqual(out[0, 0, 3], 0)
        self.assertEqual(out[20, 20, 3], 255)

    def test_matches_reference_on_random_masks(self):
        import numpy as np
        from collections import deque
        rng = np.random.default_rng(7)
        for _ in range(20):
            bg = rng.random((23, 31)) < 0.55
            got = art_ops.border_connected(bg)
            ref = np.zeros_like(bg)
            q = deque((y, x) for y in range(bg.shape[0]) for x in range(bg.shape[1])
                      if bg[y, x] and (y in (0, bg.shape[0] - 1) or x in (0, bg.shape[1] - 1)))
            for y, x in q:
                ref[y, x] = True
            while q:
                y, x = q.popleft()
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < bg.shape[0] and 0 <= nx < bg.shape[1] and bg[ny, nx] and not ref[ny, nx]:
                        ref[ny, nx] = True
                        q.append((ny, nx))
            self.assertTrue((got == ref).all())

    def test_worst_case_run_count_is_fast(self):
        import time
        import numpy as np
        n = 1024
        bg = np.indices((n, n)).sum(0) % 2 == 0      # checkerboard: the most runs per pixel
        bg[::7, :] = True                            # with full rows to connect them
        t = time.perf_counter()
        art_ops.border_connected(bg)
        self.assertLess(time.perf_counter() - t, 20)

    def test_large_serpentine_is_fast(self):
        import time
        a = self.corridor(1025)[..., 1] == 200
        t = time.perf_counter()
        got = art_ops.border_connected(a)
        self.assertLess(time.perf_counter() - t, 5)
        self.assertTrue(got[a].all())


class CanonicalPathsAndHardLinks(ArtOpsCase):
    def setUp(self):
        super().setUp()
        self.img(self.st("a.png"), (2, 2), (1, 1, 1, 255))

    def hardlink(self, src, dst):
        try:
            os.link(src, dst)
        except (OSError, NotImplementedError):
            self.skipTest("hard links not supported here")

    def test_hard_linked_input_refused(self):
        outside = os.path.join(self.outside, "secret.png")
        self.img(outside, (2, 2), (9, 9, 9, 255))
        self.hardlink(outside, os.path.join(self.ws, "art_src", "in.png"))
        self.assertIn("hard-linked", self.refused("info", os.path.join("art_src", "in.png")))

    def test_hard_linked_output_refused_and_target_untouched(self):
        outside = os.path.join(self.outside, "victim.png")
        self.img(outside, (5, 5), (9, 9, 9, 255))
        self.hardlink(outside, os.path.join(self.ws, "art_src", "out.png"))
        self.refused("trim", self.st("a.png"), os.path.join("art_src", "out.png"), "--pad", "0")
        self.assertEqual(self.rgba(outside).size, (5, 5))

    def test_overwrite_replaces_file_and_leaves_no_temp(self):
        out = os.path.join(self.ws, "art_src", "o.png")
        self.img(out, (7, 7))
        self.run_ok("trim", self.st("a.png"), os.path.join("art_src", "o.png"), "--pad", "0")
        self.assertEqual(self.rgba(out).size, (2, 2))
        self.assertEqual(sorted(os.listdir(os.path.dirname(out))), ["o.png"])

    def test_returns_canonical_paths(self):
        self.img(os.path.join(self.ws, "art_src", "x.png"), (2, 2))
        got = art_ops.check_in(os.path.join("art_src", ".", "x.png"))
        self.assertEqual(got, os.path.realpath(os.path.join(self.ws, "art_src", "x.png")))
        self.assertTrue(os.path.isabs(art_ops.check_out(os.path.join("art_src", "new.png"))))


class MaskComposeDiff(ArtOpsCase):
    """Phase 2B subset (2026-11-22): mask, compose, diff."""
    np = art_ops.np

    def L(self, path):
        with Image.open(path) as im:
            return self.np.asarray(im.convert("L"))

    def noise(self, path, size, seed):
        a = self.np.random.default_rng(seed).integers(0, 256, (size[1], size[0], 4)).astype("uint8")
        Image.fromarray(a, "RGBA").save(path)
        return a

    def test_rect_ellipse_polygon_geometry(self):
        self.run_ok("mask", self.st("m.png"), "--size", "20", "10", "--rect", "2", "3", "4", "2")
        m = self.L(self.st("m.png"))
        self.assertEqual(m.shape, (10, 20))
        self.assertEqual(int((m == 255).sum()), 8)
        self.assertTrue((m[3:5, 2:6] == 255).all())
        self.assertEqual(set(self.np.unique(m)), {0, 255})
        self.run_ok("mask", self.st("e.png"), "--size", "21", "21", "--ellipse", "0", "0", "21", "21")
        e = self.L(self.st("e.png"))
        self.assertEqual(e[10, 10], 255); self.assertEqual(e[0, 0], 0); self.assertEqual(e[10, 0], 255)
        self.run_ok("mask", self.st("p.png"), "--size", "10", "10", "--polygon", "0", "0", "9", "0", "0", "9")
        p = self.L(self.st("p.png"))
        self.assertEqual(p[1, 1], 255); self.assertEqual(p[9, 9], 0)

    def test_grow_shrink_invert_feather(self):
        self.run_ok("mask", self.st("g.png"), "--size", "11", "11", "--rect", "5", "5", "1", "1", "--grow", "2")
        self.assertEqual(int((self.L(self.st("g.png")) == 255).sum()), 25)
        self.run_ok("mask", self.st("s.png"), "--size", "11", "11", "--rect", "2", "2", "7", "7", "--shrink", "2")
        self.assertEqual(int((self.L(self.st("s.png")) == 255).sum()), 9)
        self.run_ok("mask", self.st("i.png"), "--size", "4", "4", "--rect", "0", "0", "2", "4", "--invert")
        i = self.L(self.st("i.png"))
        self.assertTrue((i[:, :2] == 0).all() and (i[:, 2:] == 255).all())
        self.run_ok("mask", self.st("f.png"), "--size", "40", "40", "--rect", "10", "10", "20", "20", "--feather", "3")
        f = self.L(self.st("f.png"))
        self.assertGreater(len(self.np.unique(f)), 3)
        self.assertEqual(f[20, 20], 255); self.assertEqual(f[0, 0], 0)

    def test_from_alpha_and_from_color(self):
        im = Image.new("RGBA", (6, 6), (0, 0, 0, 0))
        im.putpixel((1, 1), (10, 200, 10, 255)); im.putpixel((2, 2), (200, 10, 10, 40))
        im.save(self.st("src.png"))
        self.run_ok("mask", self.st("a.png"), "--like", self.st("src.png"), "--from-alpha", self.st("src.png"), "--threshold", "50")
        a = self.L(self.st("a.png"))
        self.assertEqual(a[1, 1], 255); self.assertEqual(a[2, 2], 0)
        self.run_ok("mask", self.st("c.png"), "--like", self.st("src.png"), "--from-color", self.st("src.png"), "10", "200", "10", "--tolerance", "5")
        c = self.L(self.st("c.png"))
        self.assertEqual(int((c == 255).sum()), 1); self.assertEqual(c[1, 1], 255)

    def test_mask_refusals(self):
        self.img(self.st("x.png"), (4, 4))
        self.refused("mask", self.st("m.png"), "--size", "4", "4")                       # nothing selected
        self.refused("mask", self.st("m.png"), "--rect", "0", "0", "1", "1")             # no size
        self.refused("mask", self.st("m.png"), "--size", "4", "4", "--like", self.st("x.png"), "--rect", "0", "0", "1", "1")
        self.refused("mask", self.st("m.png"), "--size", "4", "4", "--polygon", "0", "0", "1", "1")
        self.refused("mask", self.st("m.png"), "--size", "4", "4", "--rect", "0", "0", "1", "1", "--grow", "65")
        self.refused("mask", self.st("m.png"), "--size", "4", "4", "--rect", "0", "0", "0", "1")
        self.refused("mask", self.st("m.png"), "--size", "8192", "8192", "--rect", "0", "0", "1", "1")   # over the pixel limit
        self.refused("mask", self.st("m.png"), "--size", "8", "8", "--from-alpha", self.st("x.png"))   # size mismatch
        many = []
        for _ in range(art_ops.MAX_SHAPES + 1):
            many += ["--rect", "0", "0", "1", "1"]
        self.refused("mask", self.st("m.png"), "--size", "4", "4", *many)
        self.refused("mask", os.path.join(self.outside, "m.png"), "--size", "4", "4", "--rect", "0", "0", "1", "1")

    def test_compose_over_position_and_opacity(self):
        self.img(self.st("base.png"), (4, 4), (0, 0, 255, 255))
        self.img(self.st("over.png"), (2, 2), (255, 0, 0, 255))
        self.run_ok("compose", self.st("c.png"), "--base", self.st("base.png"), "--over", self.st("over.png"), "--at", "3", "3")
        self.assertEqual(self.px(self.st("c.png"), (3, 3)), (255, 0, 0, 255))     # clipped at the edge
        self.assertEqual(self.px(self.st("c.png"), (2, 2)), (0, 0, 255, 255))
        self.assertEqual(self.rgba(self.st("c.png")).size, (4, 4))
        self.run_ok("compose", self.st("h.png"), "--base", self.st("base.png"), "--over", self.st("over.png"), "--opacity", "0.5")
        r, g, b, a = self.px(self.st("h.png"), (0, 0))
        self.assertTrue(120 <= r <= 136 and 120 <= b <= 136 and a == 255)

    def test_compose_with_mask_restores_outside_exactly(self):
        base = self.noise(self.st("orig.png"), (32, 24), 1)
        self.noise(self.st("edit.png"), (32, 24), 2)
        self.run_ok("mask", self.st("m.png"), "--size", "32", "24", "--ellipse", "4", "2", "24", "20", "--feather", "1.5")
        self.run_ok("compose", self.st("out.png"), "--base", self.st("orig.png"), "--over", self.st("edit.png"), "--mask", self.st("m.png"))
        out = self.np.asarray(self.rgba(self.st("out.png")))
        m = self.L(self.st("m.png"))
        self.assertTrue((out[m == 0] == base[m == 0]).all())
        self.assertGreater(int((m == 0).sum()), 0); self.assertGreater(int((m > 0).sum()), 0)
        self.assertGreater(int((m == 255).sum()), 0)
        self.assertTrue((out[m > 0] != base[m > 0]).any())
        msg = self.run_ok("diff", self.st("d.png"), self.st("orig.png"), self.st("out.png"), "--mask", self.st("m.png"), "--fail-outside")
        self.assertIn("changed 0", msg)

    def test_compose_mask_size_must_match(self):
        self.img(self.st("b.png"), (4, 4), (1, 2, 3, 255)); self.img(self.st("o.png"), (4, 4))
        self.run_ok("mask", self.st("m.png"), "--size", "5", "5", "--rect", "0", "0", "1", "1")
        self.refused("compose", self.st("c.png"), "--base", self.st("b.png"), "--over", self.st("o.png"), "--mask", self.st("m.png"))
        self.refused("compose", self.st("c.png"), "--base", self.st("b.png"), "--over", self.st("o.png"), "--opacity", "2")

    def test_diff_numbers_and_fail_outside(self):
        self.img(self.st("a.png"), (4, 4), (10, 10, 10, 255))
        im = Image.new("RGBA", (4, 4), (10, 10, 10, 255)); im.putpixel((0, 0), (30, 10, 10, 255)); im.save(self.st("b.png"))
        msg = self.run_ok("diff", self.st("d.png"), self.st("a.png"), self.st("b.png"))
        self.assertIn("1 of 16 px changed", msg); self.assertIn("R: max 20", msg); self.assertIn("G: max 0", msg)
        self.assertEqual(self.px(self.st("d.png"), (0, 0))[0], 64); self.assertEqual(self.px(self.st("d.png"), (1, 1))[0], 0)
        self.run_ok("mask", self.st("m.png"), "--size", "4", "4", "--rect", "2", "2", "2", "2")
        self.refused("diff", self.st("d.png"), self.st("a.png"), self.st("b.png"), "--mask", self.st("m.png"), "--fail-outside")
        self.refused("diff", self.st("d.png"), self.st("a.png"), self.st("b.png"), "--fail-outside")
        self.img(self.st("c.png"), (5, 4))
        self.refused("diff", self.st("d.png"), self.st("a.png"), self.st("c.png"))

    def test_large_grow_is_bounded_in_time(self):
        import time
        self.run_ok("mask", self.st("m.png"), "--size", "1024", "1024", "--rect", "500", "500", "4", "4")
        t = time.perf_counter()
        self.run_ok("mask", self.st("g.png"), "--size", "1024", "1024", "--rect", "500", "500", "4", "4", "--grow", "64")
        self.assertLess(time.perf_counter() - t, 10)
        self.assertEqual(int((self.L(self.st("g.png")) == 255).sum()), (4 + 128) ** 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
