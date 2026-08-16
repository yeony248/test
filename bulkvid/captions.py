"""업로드용 제목·본문·해시태그 생성."""

from __future__ import annotations

import random
import re

from .models import Product

BASE_TAGS = ["해외직구", "구매대행", "직구추천", "해외구매대행", "직구꿀템"]

NOTICE = "※ 해외 구매대행 상품입니다. 관세·배송비 별도이며 현지 재고에 따라 가격이 변동될 수 있습니다."


def _title(p: Product, rng: random.Random) -> str:
    if p.discount:
        options = [
            f"{p.name}, 국내가보다 {p.discount}% 싸게 사는 법",
            f"국내 {p.money(p.domestic_price)} → 직구 {p.money(p.deal_price)} | {p.name}",
            f"{p.name} 직구하면 {p.money(p.saved)} 아낍니다",
        ]
    else:
        options = [
            f"{p.name} {p.money(p.deal_price)}",
            f"이 가격 실화? {p.name}",
        ]
    return rng.choice(options)


def _hashtags(p: Product, extra: list[str]) -> list[str]:
    tags: list[str] = []
    for raw in [*p.tags, *extra, *BASE_TAGS]:
        tag = re.sub(r"[^\w가-힣]", "", raw.lstrip("#"))
        if tag and tag not in tags:
            tags.append(tag)
    # 상품명 첫 두 단어도 태그로
    for word in p.name.split()[:2]:
        tag = re.sub(r"[^\w가-힣]", "", word)
        if len(tag) >= 2 and tag not in tags:
            tags.append(tag)
    return tags[:15]


def build_caption(p: Product, extra_hashtags: list[str] | None = None,
                  handle: str = "") -> str:
    rng = p.rng()
    extra = extra_hashtags or []

    lines = [_title(p, rng), ""]

    if p.discount:
        lines.append(f"✔ 국내 {p.money(p.domestic_price)} → {p.money(p.deal_price)} "
                     f"({p.discount}%↓ / {p.money(p.saved)} 절약)")
    else:
        lines.append(f"✔ {p.money(p.deal_price)}")

    for point in p.points:
        lines.append(f"✔ {point}")

    lines.append("")
    lines.append(p.cta or "구매는 프로필 링크에서 확인하세요.")
    if p.link:
        lines.append(p.link)
    if handle:
        lines.append(handle)

    lines += ["", NOTICE, "", " ".join(f"#{t}" for t in _hashtags(p, extra))]
    return "\n".join(lines)
