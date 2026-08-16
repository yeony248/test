"""렌더링 상수, 테마 팔레트, 폰트 탐색."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache

from PIL import ImageFont

# ── 캔버스 ────────────────────────────────────────────────────────────────
WIDTH = 1080
HEIGHT = 1920
FPS = 30

# 인스타/틱톡/쇼츠 UI가 가리는 영역. 이 안에는 글자를 넣지 않는다.
SAFE_TOP = 260
SAFE_BOTTOM = 430

# 장면 기본 길이(초)
DUR_HOOK = 2.8
DUR_PRICE = 3.4
DUR_POINT = 2.5
DUR_CTA = 2.4

XFADE = 0.35  # 장면 전환 길이(초)

# ── 폰트 ─────────────────────────────────────────────────────────────────
# (경로, ttc 인덱스) 순서대로 시도한다. BULKVID_FONT_BOLD / _REGULAR 환경변수로
# 덮어쓸 수 있다. 값은 "경로" 또는 "경로#인덱스" 형식.
_FONT_CANDIDATES = {
    "bold": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 8),  # macOS, Bold
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 0),
        ("C:/Windows/Fonts/malgunbd.ttf", 0),  # Windows
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 1),  # KR face
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 1),
        ("/usr/share/fonts/opentype/noto/NotoSansKR-Bold.otf", 0),
    ],
    "regular": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 2),  # macOS, Regular
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 0),
        ("C:/Windows/Fonts/malgun.ttf", 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 1),
        ("/usr/share/fonts/opentype/noto/NotoSansKR-Regular.otf", 0),
    ],
}


def _from_env(weight: str):
    raw = os.environ.get(f"BULKVID_FONT_{weight.upper()}")
    if not raw:
        return None
    path, _, idx = raw.partition("#")
    return (path, int(idx) if idx else 0)


@lru_cache(maxsize=None)
def font_file(weight: str = "bold") -> tuple[str, int]:
    """설치된 한글 폰트 경로와 ttc 인덱스를 찾는다."""
    candidates = []
    env = _from_env(weight)
    if env:
        candidates.append(env)
    candidates += _FONT_CANDIDATES[weight]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                ImageFont.truetype(path, 20, index=index)
                return path, index
            except OSError:
                continue
    raise RuntimeError(
        "한글 폰트를 찾지 못했습니다.\n"
        "  macOS  : 기본 설치된 AppleSDGothicNeo를 자동으로 씁니다.\n"
        "  Ubuntu : sudo apt install fonts-noto-cjk\n"
        "  직접 지정: BULKVID_FONT_BOLD=/path/to/font.ttf 환경변수"
    )


@lru_cache(maxsize=None)
def font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    path, index = font_file(weight)
    return ImageFont.truetype(path, size, index=index)


# ── 테마 ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Theme:
    name: str
    tint: tuple[int, int, int]  # 배경 블러 위에 깔리는 색
    tint_alpha: int  # 0-255. 높을수록 배경이 어두워지고 글자가 잘 보인다
    fg: tuple[int, int, int]  # 기본 글자색
    sub: tuple[int, int, int]  # 보조 글자색
    accent: tuple[int, int, int]  # 강조(직구가, 뱃지)
    accent_fg: tuple[int, int, int]  # 강조 배경 위 글자색
    card: tuple[int, int, int]  # 상품 이미지 카드 배경


THEMES: list[Theme] = [
    Theme("ink", (12, 14, 20), 205, (255, 255, 255), (176, 182, 196),
          (255, 92, 58), (255, 255, 255), (250, 250, 252)),
    Theme("mint", (8, 32, 30), 200, (255, 255, 255), (162, 205, 196),
          (0, 214, 160), (8, 32, 30), (248, 252, 250)),
    Theme("violet", (24, 14, 42), 205, (255, 255, 255), (188, 174, 216),
          (168, 120, 255), (255, 255, 255), (250, 248, 255)),
    Theme("sunset", (38, 16, 12), 200, (255, 255, 255), (216, 178, 166),
          (255, 176, 32), (34, 20, 8), (255, 251, 245)),
    Theme("navy", (10, 20, 44), 205, (255, 255, 255), (160, 180, 214),
          (64, 156, 255), (255, 255, 255), (247, 250, 255)),
]

# 장면 전환 효과 후보 (ffmpeg xfade transition 이름)
TRANSITIONS = [
    "fade", "fadeblack", "wipeleft", "slideup",
    "smoothleft", "circleopen", "dissolve", "slideleft",
]

# 켄번스(느린 줌/팬) 움직임 후보
MOTIONS = ["in", "out", "left", "right", "up"]


@dataclass
class RenderSettings:
    """CLI에서 넘어오는 렌더 설정."""

    width: int = WIDTH
    height: int = HEIGHT
    fps: int = FPS
    crf: int = 20
    preset: str = "veryfast"
    bgm_volume: float = 0.28
    xfade: float = XFADE
    handle: str = ""  # 화면 구석에 박히는 계정명 (예: "@myshop")
    keep_scenes: bool = False
    motion: bool = True  # False면 켄번스 끔 (렌더 3~4배 빠름)
    extra_hashtags: list[str] = field(default_factory=list)


def ffmpeg_bin() -> str:
    return os.environ.get("BULKVID_FFMPEG", "ffmpeg")


def check_ffmpeg() -> None:
    import shutil

    if shutil.which(ffmpeg_bin()) is None:
        sys.exit(
            "ffmpeg를 찾지 못했습니다.\n"
            "  macOS  : brew install ffmpeg\n"
            "  Ubuntu : sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html 설치 후 PATH 등록"
        )
