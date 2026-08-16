#!/usr/bin/env python3
"""상품 CSV를 세로형(1080x1920) 숏폼 영상으로 대량 렌더링.

    python3 make_videos.py --csv data/products.csv --handle @myshop --jobs 4

자세한 사용법은 BULKVID.md 참고.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from bulkvid import config
from bulkvid.models import ProductError, load_products
from bulkvid.pipeline import Result, run_batch


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="상품 CSV → 세로형 숏폼 영상 대량 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", default="data/products.csv", help="상품 CSV 경로")
    parser.add_argument("--out", default="out", help="결과 폴더 (기본: out)")
    parser.add_argument("--bgm", default="assets/bgm", help="배경음악 폴더")
    parser.add_argument("--handle", default="", help="영상에 박을 계정명 (예: @myshop)")
    parser.add_argument("--limit", type=int, default=0, help="앞에서 N개만 렌더")
    parser.add_argument("--only", default="", help="특정 id만 (쉼표로 구분)")
    parser.add_argument("--jobs", type=int, default=2, help="동시 렌더 개수 (기본 2)")
    parser.add_argument("--hashtags", default="", help="캡션에 추가할 해시태그 (쉼표 구분)")
    parser.add_argument("--scenes-only", action="store_true",
                        help="영상 없이 장면 PNG와 캡션만 (빠른 시안 확인용)")
    parser.add_argument("--keep-scenes", action="store_true", help="장면 PNG를 남긴다")
    parser.add_argument("--no-motion", action="store_true",
                        help="켄번스 줌/팬 끄기 (렌더 3~4배 빠름)")
    parser.add_argument("--crf", type=int, default=20, help="화질 (낮을수록 고화질, 18~24)")
    parser.add_argument("--preset", default="veryfast", help="x264 preset")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.scenes_only:
        config.check_ffmpeg()

    try:
        products = load_products(args.csv)
    except (ProductError, FileNotFoundError) as exc:
        print(f"[에러] {exc}", file=sys.stderr)
        return 1

    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        products = [p for p in products if p.id in wanted]
        missing = wanted - {p.id for p in products}
        if missing:
            print(f"[경고] CSV에 없는 id: {', '.join(sorted(missing))}", file=sys.stderr)
    if args.limit > 0:
        products = products[: args.limit]

    if not products:
        print("[에러] 렌더할 상품이 없습니다.", file=sys.stderr)
        return 1

    settings = config.RenderSettings(
        crf=args.crf,
        preset=args.preset,
        handle=args.handle,
        keep_scenes=args.keep_scenes,
        motion=not args.no_motion,
        extra_hashtags=[t.strip() for t in args.hashtags.split(",") if t.strip()],
    )

    bgm_dir = Path(args.bgm)
    from bulkvid.video import find_bgm

    bgm_files = find_bgm(bgm_dir)
    if not bgm_files and not args.scenes_only:
        print(f"[알림] {bgm_dir}에 음원이 없어 무음으로 렌더합니다. "
              f"mp3를 넣으면 자동으로 돌아가며 배정됩니다.")

    print(f"상품 {len(products)}개 · 동시 {args.jobs}개 렌더 시작\n")
    started = time.time()

    def on_done(index: int, total: int, result: Result) -> None:
        mark = "✓" if result.status != "fail" else "✗"
        detail = result.error if result.status == "fail" else (
            f"{result.duration:.1f}s · {result.theme}"
            + (f" · {result.bgm}" if result.bgm else "")
        )
        print(f"  [{index + 1}/{total}] {mark} {result.product.id} — {detail}")

    results = run_batch(products, args.out, settings, bgm_dir,
                        jobs=args.jobs, scenes_only=args.scenes_only,
                        on_done=on_done)

    ok = [r for r in results if r.status != "fail"]
    failed = [r for r in results if r.status == "fail"]
    elapsed = time.time() - started

    print(f"\n완료: {len(ok)}개 성공, {len(failed)}개 실패 · {elapsed:.1f}초")
    print(f"  영상   {Path(args.out) / 'video'}")
    print(f"  캡션   {Path(args.out) / 'caption'}")
    print(f"  목록   {Path(args.out) / 'manifest.csv'}")
    if failed:
        print("\n실패 목록:")
        for r in failed:
            print(f"  - {r.product.id} ({r.product.row}행): {r.error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
