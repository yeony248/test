"""상품 CSV 로딩과 검증."""

from __future__ import annotations

import csv
import hashlib
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

# CSV에서 읽는 컬럼. id / name / deal_price / images 만 필수.
REQUIRED = ("id", "name", "deal_price", "images")

MULTI_SEP = "|"


class ProductError(ValueError):
    """한 줄짜리 상품 데이터가 잘못된 경우."""


@dataclass
class Product:
    id: str
    name: str
    deal_price: int
    images: list[str]
    hook: str = ""
    domestic_price: int = 0
    currency: str = "원"
    points: list[str] = field(default_factory=list)
    cta: str = ""
    link: str = ""
    tags: list[str] = field(default_factory=list)
    row: int = 0

    # ── 파생값 ────────────────────────────────────────────────────────
    @property
    def discount(self) -> int:
        """국내가 대비 할인율(%). 국내가가 없으면 0."""
        if self.domestic_price <= 0 or self.deal_price <= 0:
            return 0
        if self.deal_price >= self.domestic_price:
            return 0
        return round((1 - self.deal_price / self.domestic_price) * 100)

    @property
    def saved(self) -> int:
        if self.discount == 0:
            return 0
        return self.domestic_price - self.deal_price

    @property
    def seed(self) -> int:
        """상품마다 고정된 난수 시드. 같은 상품은 항상 같은 스타일로 나온다."""
        return int(hashlib.sha1(self.id.encode("utf-8")).hexdigest()[:8], 16)

    def rng(self) -> random.Random:
        return random.Random(self.seed)

    def money(self, value: int) -> str:
        return f"{value:,}{self.currency}"


def _int(value: str, field_name: str, row: int) -> int:
    """'89,000' / '₩89000' / '89000원' 같은 표기를 정수로."""
    if value is None:
        return 0
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        if str(value).strip():
            raise ProductError(f"{row}행 {field_name}: 숫자를 읽을 수 없습니다 ({value!r})")
        return 0
    return int(digits)


def _split(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(MULTI_SEP) if part.strip()]


def _resolve_images(raw: list[str], base: Path) -> list[str]:
    """상대 경로는 CSV 파일 위치 기준으로 절대 경로로 바꾼다. URL은 그대로."""
    out = []
    for item in raw:
        if item.startswith(("http://", "https://")):
            out.append(item)
        else:
            path = Path(item)
            out.append(str(path if path.is_absolute() else (base / path).resolve()))
    return out


def load_products(csv_path: str | Path) -> list[Product]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV를 찾을 수 없습니다: {csv_path}")

    base = csv_path.parent
    products: list[Product] = []
    seen_ids: set[str] = set()

    with csv_path.open(encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ProductError("CSV에 헤더 줄이 없습니다.")
        missing = [c for c in REQUIRED if c not in reader.fieldnames]
        if missing:
            raise ProductError(
                f"CSV에 필수 컬럼이 없습니다: {', '.join(missing)}\n"
                f"  현재 헤더: {', '.join(reader.fieldnames)}"
            )

        for row_no, row in enumerate(reader, start=2):
            row = {k: (v or "").strip() for k, v in row.items() if k}
            if not row.get("id") and not row.get("name"):
                continue  # 빈 줄
            pid = row.get("id") or f"row{row_no}"
            if pid in seen_ids:
                raise ProductError(f"{row_no}행 id 중복: {pid}")
            seen_ids.add(pid)

            images = _resolve_images(_split(row.get("images", "")), base)
            if not images:
                raise ProductError(f"{row_no}행 images: 이미지가 최소 1장 필요합니다.")

            products.append(
                Product(
                    id=pid,
                    name=row.get("name", ""),
                    deal_price=_int(row.get("deal_price"), "deal_price", row_no),
                    images=images,
                    # hook/cta 안의 "|"는 줄바꿈으로 쓴다
                    hook=row.get("hook", "").replace(MULTI_SEP, "\n"),
                    domestic_price=_int(row.get("domestic_price"), "domestic_price", row_no),
                    currency=row.get("currency") or "원",
                    points=_split(row.get("points", "")),
                    cta=row.get("cta", "").replace(MULTI_SEP, "\n"),
                    link=row.get("link", ""),
                    tags=_split(row.get("tags", "")),
                    row=row_no,
                )
            )

    if not products:
        raise ProductError("CSV에 상품이 한 개도 없습니다.")
    return products
