#!/usr/bin/env python3
"""데모용 가짜 상품 사진을 만든다. (실제 상품 사진이 준비되기 전 파이프라인 확인용)

    python3 scripts/make_sample_images.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bulkvid import config  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "assets" / "images"

SAMPLES = [
    ("camp-lamp-1", (250, 246, 238), (36, 40, 48), "circle"),
    ("camp-lamp-2", (238, 242, 248), (52, 62, 82), "rect"),
    ("camp-lamp-3", (246, 240, 232), (120, 84, 48), "circle"),
    ("earbuds-1", (244, 244, 246), (28, 28, 32), "rect"),
    ("earbuds-2", (232, 238, 244), (60, 90, 130), "circle"),
    ("kettle-1", (248, 244, 236), (150, 60, 40), "rect"),
    ("kettle-2", (240, 236, 228), (90, 70, 60), "circle"),
]

SIZE = 1200


def make(name: str, bg: tuple, fg: tuple, shape: str) -> Path:
    img = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(img)

    # 바닥 그림자
    draw.ellipse((260, 880, 940, 1010), fill=tuple(max(0, c - 22) for c in bg))
    img = img.filter(ImageFilter.GaussianBlur(14))
    draw = ImageDraw.Draw(img)

    if shape == "circle":
        draw.ellipse((330, 280, 870, 820), fill=fg)
        draw.ellipse((420, 360, 600, 540), fill=tuple(min(255, c + 70) for c in fg))
    else:
        draw.rounded_rectangle((340, 300, 860, 860), radius=70, fill=fg)
        draw.rounded_rectangle((410, 380, 640, 470), radius=30,
                               fill=tuple(min(255, c + 70) for c in fg))

    fnt = config.font(40, "bold")
    draw.text((60, SIZE - 100), f"SAMPLE / {name}", font=fnt,
              fill=tuple(max(0, c - 90) for c in bg))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.jpg"
    img.save(path, quality=92)
    return path


def main() -> int:
    for args in SAMPLES:
        print("  ", make(*args))
    print(f"\n샘플 사진 {len(SAMPLES)}장 생성 완료 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
