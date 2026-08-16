"""이미지 로딩/가공과 텍스트 배치 헬퍼."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config

USER_AGENT = "Mozilla/5.0 (compatible; bulkvid/1.0)"


class ImageError(RuntimeError):
    pass


# ── 로딩 ─────────────────────────────────────────────────────────────────
def load_image(src: str, cache_dir: Path) -> Image.Image:
    """로컬 경로 또는 URL에서 RGB 이미지를 읽는다. URL은 캐시에 저장한다."""
    if src.startswith(("http://", "https://")):
        path = _download(src, cache_dir)
    else:
        path = Path(src)
        if not path.exists():
            raise ImageError(f"이미지를 찾을 수 없습니다: {src}")
    try:
        with Image.open(path) as img:
            return img.convert("RGB")
    except Exception as exc:  # 손상된 파일, 지원하지 않는 포맷 등
        raise ImageError(f"이미지를 열 수 없습니다: {src} ({exc})") from exc


def _download(url: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    for existing in cache_dir.glob(f"{key}.*"):
        return existing

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ImageError(f"이미지 다운로드 실패: {url} ({exc})") from exc

    ext = {"image/jpeg": ".jpg", "image/png": ".png",
           "image/webp": ".webp", "image/gif": ".gif"}.get(ctype.split(";")[0].strip())
    if ext is None:
        ext = Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
    dest = cache_dir / f"{key}{ext}"
    dest.write_bytes(data)
    return dest


# ── 크기 맞추기 ───────────────────────────────────────────────────────────
def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """가로세로비를 유지한 채 (w,h)를 꽉 채우고 넘치는 부분은 잘라낸다."""
    scale = max(w / img.width, h / img.height)
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    resized = img.resize(size, Image.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


def contain(img: Image.Image, w: int, h: int) -> Image.Image:
    """가로세로비를 유지한 채 (w,h) 안에 들어가도록 축소한다."""
    scale = min(w / img.width, h / img.height)
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    return img.resize(size, Image.LANCZOS)


def rounded(img: Image.Image, radius: int) -> Image.Image:
    """모서리를 둥글린 RGBA 이미지."""
    out = img.convert("RGBA")
    mask = Image.new("L", out.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, out.width - 1, out.height - 1),
                                           radius=radius, fill=255)
    out.putalpha(mask)
    return out


def backdrop(img: Image.Image, theme: config.Theme,
             w: int = config.WIDTH, h: int = config.HEIGHT) -> Image.Image:
    """상품 사진을 크게 흐려서 깐 배경 + 테마 색 오버레이."""
    base = cover(img, w, h).filter(ImageFilter.GaussianBlur(48))
    tint = Image.new("RGB", (w, h), theme.tint)
    return Image.blend(base, tint, theme.tint_alpha / 255)


def paste_card(canvas: Image.Image, img: Image.Image, box_w: int, box_h: int,
               center_y: int, theme: config.Theme, radius: int = 36,
               pad: int = 24) -> tuple[int, int]:
    """상품 사진을 흰 카드 위에 얹어 캔버스 가운데에 붙인다. (top, bottom) 반환."""
    inner = contain(img, box_w - pad * 2, box_h - pad * 2)
    card = Image.new("RGB", (inner.width + pad * 2, inner.height + pad * 2), theme.card)
    card.paste(inner, (pad, pad))
    card_r = rounded(card, radius)

    x = (canvas.width - card_r.width) // 2
    y = center_y - card_r.height // 2

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x + 6, y + 14, x + card_r.width + 6, y + card_r.height + 14),
        radius=radius, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(card_r.convert("RGBA"), (x, y))
    return y, y + card_r.height


# ── 텍스트 ───────────────────────────────────────────────────────────────
def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """픽셀 폭 기준 줄바꿈. 한 단어가 너무 길면 글자 단위로 자른다."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            trial = f"{cur} {word}".strip()
            if _width(trial, fnt) <= max_w or not cur:
                if _width(trial, fnt) > max_w and not cur:
                    # 단어 하나가 이미 넘침 → 글자 단위로 쪼갠다
                    chunk = ""
                    for ch in word:
                        if _width(chunk + ch, fnt) > max_w and chunk:
                            lines.append(chunk)
                            chunk = ch
                        else:
                            chunk += ch
                    cur = chunk
                else:
                    cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return [ln for ln in lines if ln != ""] or [""]


def _width(text: str, fnt: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    bbox = fnt.getbbox(text)
    return bbox[2] - bbox[0]


def fit(text: str, max_w: int, max_lines: int, start: int, minimum: int,
        weight: str = "bold") -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """줄 수 제한 안에 들어갈 때까지 폰트 크기를 줄인다."""
    size = start
    while size > minimum:
        fnt = config.font(size, weight)
        lines = wrap(text, fnt, max_w)
        if len(lines) <= max_lines:
            return fnt, lines
        size -= 4
    fnt = config.font(minimum, weight)
    return fnt, wrap(text, fnt, max_w)[:max_lines]


def draw_lines(canvas: Image.Image, lines: list[str], fnt: ImageFont.FreeTypeFont,
               top: int, fill, line_gap: float = 1.28,
               stroke: int = 0, stroke_fill=(0, 0, 0)) -> int:
    """가운데 정렬로 여러 줄을 그리고 다음 y좌표를 돌려준다."""
    draw = ImageDraw.Draw(canvas, "RGBA")
    step = round(fnt.size * line_gap)
    y = top
    for line in lines:
        w = _width(line, fnt)
        draw.text(((canvas.width - w) // 2, y), line, font=fnt, fill=fill,
                  stroke_width=stroke, stroke_fill=stroke_fill)
        y += step
    return y


def pill(canvas: Image.Image, text: str, center_y: int, fnt: ImageFont.FreeTypeFont,
         bg, fg, pad_x: int = 44, pad_y: int = 20, radius: int | None = None) -> int:
    """알약 모양 뱃지. 아래쪽 y좌표를 돌려준다."""
    draw = ImageDraw.Draw(canvas, "RGBA")
    tw = _width(text, fnt)
    th = round(fnt.size * 1.0)
    w = tw + pad_x * 2
    h = th + pad_y * 2
    x = (canvas.width - w) // 2
    y = center_y - h // 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius or h // 2, fill=bg)
    bbox = fnt.getbbox(text)
    draw.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, font=fnt, fill=fg)
    return y + h


def strike(canvas: Image.Image, text: str, fnt: ImageFont.FreeTypeFont,
           top: int, fill) -> int:
    """취소선 친 가격 (국내가 표시용)."""
    draw = ImageDraw.Draw(canvas, "RGBA")
    w = _width(text, fnt)
    x = (canvas.width - w) // 2
    draw.text((x, top), text, font=fnt, fill=fill)
    mid = top + round(fnt.size * 0.62)
    draw.line((x - 8, mid, x + w + 8, mid), fill=fill, width=max(3, fnt.size // 18))
    return top + round(fnt.size * 1.25)


def watermark(canvas: Image.Image, handle: str, theme: config.Theme) -> None:
    if not handle:
        return
    fnt = config.font(34, "bold")
    draw = ImageDraw.Draw(canvas, "RGBA")
    bbox = fnt.getbbox(handle)
    w = bbox[2] - bbox[0]
    x = canvas.width - w - 110  # 줌/팬에 잘리지 않도록 scenes.SIDE_MARGIN과 맞춘다
    y = config.SAFE_TOP - 50
    draw.text((x, y), handle, font=fnt, fill=(*theme.fg, 150))
