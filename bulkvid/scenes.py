"""상품 하나를 여러 장의 정지 화면(장면)으로 그린다.

각 장면은 1080x1920 PNG로 저장되고, video.py가 여기에 켄번스 움직임과
장면 전환을 얹어 하나의 영상으로 만든다. 글자를 ffmpeg drawtext가 아니라
Pillow로 그리기 때문에 한글 줄바꿈/따옴표 이스케이프 문제가 없다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import config, imaging
from .models import Product

MAX_POINTS = 3
# 켄번스 줌/팬이 가장자리를 잘라내므로 좌우 여백을 넉넉히 둔다.
# video.MAX_ZOOM을 올리면 이 값도 같이 키워야 글자가 안 잘린다.
SIDE_MARGIN = 110
TEXT_W = config.WIDTH - SIDE_MARGIN * 2  # 글자가 들어갈 수 있는 최대 가로폭


@dataclass
class Scene:
    kind: str
    image: Image.Image
    duration: float
    motion: str
    path: Path | None = None


# ── 문구 생성 ────────────────────────────────────────────────────────────
def _hook_text(p: Product, rng: random.Random) -> str:
    if p.hook:
        return p.hook
    if p.discount:
        options = [
            f"{p.name}\n국내가 {p.money(p.domestic_price)}인데",
            f"{p.name}\n직구하면 {p.discount}% 싸요",
            f"{p.name}\n이 가격 실화인가요",
        ]
    else:
        options = [
            f"{p.name}\n이 가격 실화인가요",
            f"{p.name}\n지금 이 가격",
        ]
    return rng.choice(options)


def _teaser_text(p: Product) -> str:
    return f"{p.discount}% 싸게 사는 법 ↓" if p.discount else "가격 확인 ↓"


def _cta_text(p: Product) -> str:
    return p.cta or "프로필 링크에서\n바로 확인하세요"


# ── 장면 ─────────────────────────────────────────────────────────────────
def _hook(p: Product, img: Image.Image, theme: config.Theme,
          settings: config.RenderSettings, rng: random.Random) -> Image.Image:
    canvas = imaging.backdrop(img, theme).convert("RGBA")

    fnt, lines = imaging.fit(_hook_text(p, rng), TEXT_W, 3, 92, 58)
    end = imaging.draw_lines(canvas, lines, fnt, 320, theme.fg, stroke=4,
                             stroke_fill=(0, 0, 0))

    imaging.pill(canvas, _teaser_text(p), end + 60, config.font(44, "bold"),
                 theme.accent, theme.accent_fg)
    imaging.paste_card(canvas, img, 880, 720, 1120, theme)
    imaging.watermark(canvas, settings.handle, theme)
    return canvas.convert("RGB")


def _price(p: Product, img: Image.Image, theme: config.Theme,
           settings: config.RenderSettings) -> Image.Image:
    canvas = imaging.backdrop(img, theme).convert("RGBA")
    y = 320

    if p.discount:
        y = imaging.pill(canvas, "국내 판매가", y, config.font(40, "bold"),
                         (255, 255, 255, 38), theme.sub) + 34
        y = imaging.strike(canvas, p.money(p.domestic_price),
                           config.font(78, "bold"), y, theme.sub) + 8
        y = imaging.draw_lines(canvas, ["↓"], config.font(58, "bold"), y, theme.sub) + 6
        label = "구매대행가"
    else:
        label = "판매가"
        y = imaging.pill(canvas, label, y, config.font(40, "bold"),
                         (255, 255, 255, 38), theme.sub) + 40

    fnt_price, lines = imaging.fit(p.money(p.deal_price), TEXT_W, 1, 150, 90)
    y = imaging.draw_lines(canvas, lines, fnt_price, y, theme.accent, stroke=5,
                           stroke_fill=(0, 0, 0)) + 24

    if p.discount:
        y = imaging.pill(canvas, f"{p.discount}% 싸게 · {p.money(p.saved)} 절약",
                         y + 40, config.font(42, "bold"), theme.accent,
                         theme.accent_fg) + 40

    card_h = max(360, 1500 - y)
    imaging.paste_card(canvas, img, 760, min(card_h, 560), y + min(card_h, 560) // 2, theme)
    imaging.watermark(canvas, settings.handle, theme)
    return canvas.convert("RGB")


def _point(p: Product, img: Image.Image, text: str, index: int,
           theme: config.Theme, settings: config.RenderSettings) -> Image.Image:
    canvas = imaging.backdrop(img, theme).convert("RGBA")
    imaging.pill(canvas, f"POINT {index}", 330, config.font(40, "bold"),
                 theme.accent, theme.accent_fg)
    imaging.paste_card(canvas, img, 880, 740, 880, theme)
    fnt, lines = imaging.fit(text, TEXT_W, 2, 68, 44)
    imaging.draw_lines(canvas, lines, fnt, 1310, theme.fg, stroke=4,
                       stroke_fill=(0, 0, 0))
    imaging.watermark(canvas, settings.handle, theme)
    return canvas.convert("RGB")


def _gallery(p: Product, img: Image.Image, theme: config.Theme,
             settings: config.RenderSettings) -> Image.Image:
    canvas = imaging.backdrop(img, theme).convert("RGBA")
    imaging.paste_card(canvas, img, 960, 1080, 940, theme)
    imaging.pill(canvas, p.name, 1420, config.font(46, "bold"),
                 (0, 0, 0, 150), theme.fg)
    imaging.watermark(canvas, settings.handle, theme)
    return canvas.convert("RGB")


def _cta(p: Product, img: Image.Image, theme: config.Theme,
         settings: config.RenderSettings) -> Image.Image:
    canvas = imaging.backdrop(img, theme).convert("RGBA")

    y = imaging.pill(canvas, "지금 이 가격", 470, config.font(42, "bold"),
                     theme.accent, theme.accent_fg) + 40
    fnt_price, price_lines = imaging.fit(p.money(p.deal_price), TEXT_W, 1, 120, 76)
    y = imaging.draw_lines(canvas, price_lines, fnt_price, y, theme.fg, stroke=5,
                           stroke_fill=(0, 0, 0)) + 50

    fnt, lines = imaging.fit(_cta_text(p), TEXT_W, 3, 74, 48)
    y = imaging.draw_lines(canvas, lines, fnt, y, theme.fg, stroke=4,
                           stroke_fill=(0, 0, 0)) + 40

    if settings.handle:
        y = imaging.draw_lines(canvas, [settings.handle], config.font(52, "bold"),
                               y, theme.accent) + 30

    notice = "※ 해외 구매대행 상품 · 관세와 배송비는 별도입니다\n현지 재고에 따라 가격이 달라질 수 있습니다"
    fnt_n, notice_lines = imaging.fit(notice, TEXT_W, 3, 34, 26, "regular")
    imaging.draw_lines(canvas, notice_lines, fnt_n, 1400, theme.sub, line_gap=1.4)
    return canvas.convert("RGB")


# ── 조립 ─────────────────────────────────────────────────────────────────
def build_scenes(p: Product, theme: config.Theme, settings: config.RenderSettings,
                 cache_dir: Path) -> list[Scene]:
    rng = p.rng()
    images = [imaging.load_image(src, cache_dir) for src in p.images]

    def pick(i: int) -> Image.Image:
        return images[i % len(images)]

    scenes: list[Scene] = [
        Scene("hook", _hook(p, pick(0), theme, settings, rng), config.DUR_HOOK, ""),
        Scene("price", _price(p, pick(0), theme, settings), config.DUR_PRICE, ""),
    ]

    points = p.points[:MAX_POINTS]
    for i, text in enumerate(points, start=1):
        scenes.append(
            Scene("point", _point(p, pick(i), text, i, theme, settings),
                  config.DUR_POINT, "")
        )

    # 쓰지 않고 남은 사진이 있으면 한 장면 더 (같은 템플릿 반복을 줄인다)
    used = 1 + len(points)
    if len(images) > used:
        scenes.append(
            Scene("gallery", _gallery(p, images[used], theme, settings),
                  config.DUR_POINT, "")
        )

    scenes.append(Scene("cta", _cta(p, pick(0), theme, settings), config.DUR_CTA, ""))

    # 움직임 배정: 바로 옆 장면과 같은 방향이 겹치지 않게
    prev = ""
    for scene in scenes:
        choices = [m for m in config.MOTIONS if m != prev]
        scene.motion = rng.choice(choices) if settings.motion else "none"
        prev = scene.motion
    return scenes


def save_scenes(scenes: list[Scene], work_dir: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    for i, scene in enumerate(scenes):
        path = work_dir / f"{i:02d}_{scene.kind}.png"
        scene.image.save(path)
        scene.path = path
