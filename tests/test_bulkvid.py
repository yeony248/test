"""bulkvid 단위 테스트.

    python3 -m unittest discover -s tests -v

ffmpeg 실행은 하지 않는다 (명령어 조립까지만 검증).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bulkvid import captions, config, scenes, video  # noqa: E402
from bulkvid.models import Product, ProductError, load_products  # noqa: E402
from bulkvid.pipeline import assign_themes  # noqa: E402

HEADER = "id,name,hook,domestic_price,deal_price,currency,points,cta,link,images,tags\n"


def write_csv(tmp: Path, body: str, name: str = "p.csv") -> Path:
    path = tmp / name
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def sample_image(tmp: Path, name: str = "img.jpg") -> Path:
    from PIL import Image

    path = tmp / name
    Image.new("RGB", (900, 1200), (200, 120, 90)).save(path)
    return path


class TestLoad(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.img = sample_image(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parses_prices_with_symbols(self) -> None:
        csv_path = write_csv(
            self.tmp,
            f"a,램프,,\"89,000원\",₩21900,원,,,,{self.img.name},\n",
        )
        (product,) = load_products(csv_path)
        self.assertEqual(product.domestic_price, 89000)
        self.assertEqual(product.deal_price, 21900)
        self.assertEqual(product.discount, 75)
        self.assertEqual(product.saved, 67100)

    def test_relative_image_paths_resolve_against_csv(self) -> None:
        csv_path = write_csv(self.tmp, f"a,램프,,0,1000,원,,,,{self.img.name},\n")
        (product,) = load_products(csv_path)
        self.assertEqual(Path(product.images[0]), self.img.resolve())

    def test_urls_are_left_alone(self) -> None:
        csv_path = write_csv(self.tmp, "a,램프,,0,1000,원,,,,https://x.test/a.jpg,\n")
        (product,) = load_products(csv_path)
        self.assertEqual(product.images[0], "https://x.test/a.jpg")

    def test_pipe_splits_points_and_breaks_hook_lines(self) -> None:
        csv_path = write_csv(
            self.tmp,
            f"a,램프,첫줄|둘째줄,0,1000,원,포인트1|포인트2,사줘|지금,,{self.img.name},태그1|태그2\n",
        )
        (product,) = load_products(csv_path)
        self.assertEqual(product.hook, "첫줄\n둘째줄")
        self.assertEqual(product.cta, "사줘\n지금")
        self.assertEqual(product.points, ["포인트1", "포인트2"])
        self.assertEqual(product.tags, ["태그1", "태그2"])

    def test_missing_column_is_reported(self) -> None:
        path = self.tmp / "bad.csv"
        path.write_text("id,name\na,램프\n", encoding="utf-8")
        with self.assertRaises(ProductError) as ctx:
            load_products(path)
        self.assertIn("deal_price", str(ctx.exception))

    def test_duplicate_id_is_rejected(self) -> None:
        csv_path = write_csv(
            self.tmp,
            f"a,램프,,0,1000,원,,,,{self.img.name},\n"
            f"a,다른램프,,0,2000,원,,,,{self.img.name},\n",
        )
        with self.assertRaises(ProductError):
            load_products(csv_path)

    def test_row_without_image_is_rejected(self) -> None:
        csv_path = write_csv(self.tmp, "a,램프,,0,1000,원,,,,,\n")
        with self.assertRaises(ProductError) as ctx:
            load_products(csv_path)
        self.assertIn("images", str(ctx.exception))

    def test_blank_rows_are_skipped(self) -> None:
        csv_path = write_csv(
            self.tmp, f"a,램프,,0,1000,원,,,,{self.img.name},\n,,,,,,,,,,\n"
        )
        self.assertEqual(len(load_products(csv_path)), 1)


class TestProduct(unittest.TestCase):
    def make(self, **kwargs) -> Product:
        base = dict(id="a", name="램프", deal_price=1000, images=["x.jpg"])
        base.update(kwargs)
        return Product(**base)

    def test_no_discount_when_domestic_price_missing(self) -> None:
        self.assertEqual(self.make().discount, 0)

    def test_no_discount_when_deal_price_is_higher(self) -> None:
        self.assertEqual(self.make(domestic_price=900).discount, 0)

    def test_seed_is_stable_for_same_id(self) -> None:
        self.assertEqual(self.make().seed, self.make(name="다른이름").seed)

    def test_money_formats_with_currency(self) -> None:
        self.assertEqual(self.make(currency="원").money(21900), "21,900원")


class TestCaption(unittest.TestCase):
    def test_caption_has_prices_points_and_notice(self) -> None:
        product = Product(id="a", name="캠핑 랜턴", deal_price=21900,
                          domestic_price=89000, images=["x.jpg"],
                          points=["밝기 3단계"], tags=["캠핑용품"])
        text = captions.build_caption(product, ["직구"], "@shop")
        self.assertIn("21,900원", text)
        self.assertIn("89,000원", text)
        self.assertIn("밝기 3단계", text)
        self.assertIn("#캠핑용품", text)
        self.assertIn("#직구", text)
        self.assertIn("관세", text)
        self.assertIn("@shop", text)

    def test_caption_is_stable_across_calls(self) -> None:
        product = Product(id="a", name="램프", deal_price=1000, images=["x.jpg"])
        self.assertEqual(captions.build_caption(product),
                         captions.build_caption(product))


class TestScenes(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.img = str(sample_image(self.tmp))
        self.settings = config.RenderSettings(handle="@shop")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def build(self, **kwargs) -> list[scenes.Scene]:
        base = dict(id="a", name="캠핑 랜턴", deal_price=21900,
                    domestic_price=89000, images=[self.img])
        base.update(kwargs)
        return scenes.build_scenes(Product(**base), config.THEMES[0],
                                   self.settings, self.tmp)

    def test_scene_count_and_canvas_size(self) -> None:
        built = self.build(points=["p1", "p2"])
        self.assertEqual([s.kind for s in built],
                         ["hook", "price", "point", "point", "cta"])
        for scene in built:
            self.assertEqual(scene.image.size, (config.WIDTH, config.HEIGHT))

    def test_points_are_capped(self) -> None:
        built = self.build(points=[f"p{i}" for i in range(9)])
        self.assertEqual(sum(1 for s in built if s.kind == "point"), scenes.MAX_POINTS)

    def test_leftover_photo_becomes_a_gallery_scene(self) -> None:
        second = str(sample_image(self.tmp, "b.jpg"))
        built = self.build(images=[self.img, second], points=[])
        self.assertIn("gallery", [s.kind for s in built])

    def test_neighbouring_scenes_do_not_repeat_motion(self) -> None:
        built = self.build(points=["p1", "p2", "p3"])
        motions = [s.motion for s in built]
        self.assertTrue(all(a != b for a, b in zip(motions, motions[1:])))

    def test_no_motion_setting_disables_movement(self) -> None:
        still = config.RenderSettings(motion=False)
        built = scenes.build_scenes(
            Product(id="a", name="램프", deal_price=1000, images=[self.img]),
            config.THEMES[0], still, self.tmp)
        self.assertTrue(all(s.motion == "none" for s in built))

    def test_works_without_domestic_price(self) -> None:
        built = self.build(domestic_price=0)
        self.assertEqual(built[1].kind, "price")


class TestVideoCommand(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.settings = config.RenderSettings()
        self.scenes = []
        for i, dur in enumerate([3.0, 2.0, 4.0]):
            path = self.tmp / f"{i}.png"
            path.write_bytes(b"x")
            self.scenes.append(scenes.Scene("s", None, dur, "in", path))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_duration_subtracts_each_transition(self) -> None:
        _, total = video.build_command(self.scenes, self.tmp / "o.mp4", self.settings)
        self.assertAlmostEqual(total, 9.0 - 2 * self.settings.xfade, places=3)

    def test_one_input_per_scene_plus_audio(self) -> None:
        cmd, _ = video.build_command(self.scenes, self.tmp / "o.mp4", self.settings)
        self.assertEqual(cmd.count("-loop"), 3)
        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=44100", cmd)

    def test_xfade_offsets_are_cumulative(self) -> None:
        cmd, _ = video.build_command(self.scenes, self.tmp / "o.mp4", self.settings,
                                     transitions=["fade", "wipeleft"])
        graph = cmd[cmd.index("-filter_complex") + 1]
        xf = self.settings.xfade
        self.assertIn(f"offset={3.0 - xf:.3f}", graph)
        self.assertIn(f"offset={3.0 + 2.0 - 2 * xf:.3f}", graph)
        self.assertIn("transition=wipeleft", graph)

    def test_single_scene_skips_xfade(self) -> None:
        cmd, total = video.build_command(self.scenes[:1], self.tmp / "o.mp4",
                                         self.settings)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertNotIn("xfade", graph)
        self.assertAlmostEqual(total, 3.0, places=3)

    def test_bgm_input_uses_loop_and_offset(self) -> None:
        bgm = self.tmp / "t.mp3"
        bgm.write_bytes(b"x")
        cmd, _ = video.build_command(self.scenes, self.tmp / "o.mp4", self.settings,
                                     bgm=bgm, bgm_offset=12.5)
        self.assertIn("-stream_loop", cmd)
        self.assertIn("12.50", cmd)

    def test_no_motion_produces_plain_scale(self) -> None:
        for scene in self.scenes:
            scene.motion = "none"
        cmd, _ = video.build_command(self.scenes, self.tmp / "o.mp4", self.settings)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertNotIn("zoompan", graph)

    def test_unsaved_scene_is_rejected(self) -> None:
        self.scenes[0].path = None
        with self.assertRaises(video.RenderError):
            video.build_command(self.scenes, self.tmp / "o.mp4", self.settings)

    def test_find_bgm_only_returns_audio(self) -> None:
        (self.tmp / "a.mp3").write_bytes(b"x")
        (self.tmp / "readme.txt").write_text("x")
        self.assertEqual([p.name for p in video.find_bgm(self.tmp)], ["a.mp3"])

    def test_find_bgm_tolerates_missing_folder(self) -> None:
        self.assertEqual(video.find_bgm(self.tmp / "nope"), [])
        self.assertEqual(video.find_bgm(None), [])


class TestThemes(unittest.TestCase):
    def test_neighbours_never_share_a_theme(self) -> None:
        products = [Product(id=f"p{i}", name="x", deal_price=1, images=["a"])
                    for i in range(40)]
        names = [t.name for t in assign_themes(products)]
        self.assertTrue(all(a != b for a, b in zip(names, names[1:])))


class TestZoomSafety(unittest.TestCase):
    def test_side_margin_covers_worst_case_crop(self) -> None:
        """줌/팬으로 잘려나가는 폭이 글자 여백보다 작아야 글자가 안 잘린다."""
        zoom = video.MAX_ZOOM
        lo, hi = video.PAN_RANGE
        crop_each_side = config.WIDTH * (1 - 1 / zoom) / 2
        pan_shift = config.WIDTH * (1 - 1 / zoom) * (max(hi, 1 - lo) - 0.5)
        self.assertLess(crop_each_side + pan_shift, scenes.SIDE_MARGIN)


if __name__ == "__main__":
    unittest.main()
