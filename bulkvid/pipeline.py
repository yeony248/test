"""CSV 한 줄 → 영상 한 편. 그리고 그 전체를 병렬로 돌리는 배치 러너."""

from __future__ import annotations

import csv
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import captions, config, scenes as scenes_mod, video
from .models import Product

MANIFEST_FIELDS = ["id", "name", "status", "video", "caption", "duration",
                   "theme", "bgm", "scenes", "error"]


@dataclass
class Result:
    product: Product
    status: str = "ok"
    video_path: Path | None = None
    caption_path: Path | None = None
    duration: float = 0.0
    theme: str = ""
    bgm: str = ""
    scene_count: int = 0
    error: str = ""


@dataclass
class Paths:
    root: Path
    video: Path = field(init=False)
    caption: Path = field(init=False)
    scenes: Path = field(init=False)
    work: Path = field(init=False)
    cache: Path = field(init=False)

    def __post_init__(self) -> None:
        self.video = self.root / "video"
        self.caption = self.root / "caption"
        self.scenes = self.root / "scenes"
        self.work = self.root / ".work"
        self.cache = self.root / ".cache"

    def prepare(self) -> None:
        for path in (self.video, self.caption, self.work, self.cache):
            path.mkdir(parents=True, exist_ok=True)


def assign_themes(products: list[Product]) -> list[config.Theme]:
    """상품마다 테마를 배정한다.

    기본은 상품 id 해시(= 같은 상품은 늘 같은 색)지만, 앞 상품과 겹치면 한 칸
    밀어서 연속 업로드가 똑같은 색으로 도배되지 않게 한다.
    """
    themes: list[config.Theme] = []
    prev = -1
    for p in products:
        i = p.seed % len(config.THEMES)
        if i == prev:
            i = (i + 1) % len(config.THEMES)
        themes.append(config.THEMES[i])
        prev = i
    return themes


def render_product(p: Product, index: int, paths: Paths,
                   settings: config.RenderSettings, bgm_files: list[Path],
                   theme: config.Theme, scenes_only: bool = False) -> Result:
    rng = p.rng()
    result = Result(product=p, theme=theme.name)

    try:
        built = scenes_mod.build_scenes(p, theme, settings, paths.cache)
        result.scene_count = len(built)

        scene_dir = (paths.scenes / p.id) if (settings.keep_scenes or scenes_only) \
            else (paths.work / p.id)
        scenes_mod.save_scenes(built, scene_dir)

        caption_path = paths.caption / f"{p.id}.txt"
        caption_path.write_text(
            captions.build_caption(p, settings.extra_hashtags, settings.handle),
            encoding="utf-8",
        )
        result.caption_path = caption_path

        if scenes_only:
            result.status = "scenes"
            return result

        bgm = bgm_files[index % len(bgm_files)] if bgm_files else None
        result.bgm = bgm.name if bgm else ""
        transitions = [rng.choice(config.TRANSITIONS) for _ in range(max(0, len(built) - 1))]

        out_path = paths.video / f"{p.id}.mp4"
        result.duration = video.render(built, out_path, settings, bgm, rng, transitions)
        result.video_path = out_path
    except Exception as exc:
        result.status = "fail"
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        if not settings.keep_scenes and not scenes_only:
            shutil.rmtree(paths.work / p.id, ignore_errors=True)

    return result


def run_batch(products: list[Product], out_dir: str | Path,
              settings: config.RenderSettings, bgm_dir: str | Path | None = None,
              jobs: int = 2, scenes_only: bool = False,
              on_done=None) -> list[Result]:
    paths = Paths(Path(out_dir))
    paths.prepare()
    bgm_files = video.find_bgm(bgm_dir)
    themes = assign_themes(products)

    lock = threading.Lock()
    results: list[Result | None] = [None] * len(products)

    def work(pair: tuple[int, Product]) -> None:
        index, product = pair
        result = render_product(product, index, paths, settings, bgm_files,
                                themes[index], scenes_only)
        results[index] = result
        if on_done:
            with lock:
                on_done(index, len(products), result)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        list(pool.map(work, enumerate(products)))

    final = [r for r in results if r is not None]
    write_manifest(final, paths.root / "manifest.csv")
    return final


def write_manifest(results: list[Result], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "id": r.product.id,
                "name": r.product.name,
                "status": r.status,
                "video": str(r.video_path) if r.video_path else "",
                "caption": str(r.caption_path) if r.caption_path else "",
                "duration": f"{r.duration:.2f}" if r.duration else "",
                "theme": r.theme,
                "bgm": r.bgm,
                "scenes": r.scene_count,
                "error": r.error,
            })
