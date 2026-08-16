# bulkvid — 구매대행 상품 CSV → 숏폼 영상 대량 생성

상품 목록(CSV) + 상품 사진만 있으면 인스타 릴스 / 유튜브 쇼츠 / 틱톡용
**세로 1080×1920 영상**과 **업로드용 캡션**을 한 번에 쏟아냅니다.
영상 1편당 편집 시간은 0초, 렌더 시간만 듭니다.

```
data/products.csv          →   out/video/camp-lamp.mp4     (14초 세로 영상)
assets/images/*.jpg            out/caption/camp-lamp.txt   (제목·본문·해시태그)
assets/bgm/*.mp3               out/manifest.csv            (전체 목록)
```

---

## 1. 설치

```bash
# 1) ffmpeg
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu

# 2) 파이썬 라이브러리
pip install pillow

# 3) 한글 폰트 (macOS/Windows는 기본 폰트를 자동으로 씁니다)
sudo apt install fonts-noto-cjk   # Ubuntu만
```

## 2. 5분 만에 돌려보기

```bash
python3 scripts/make_sample_images.py      # 데모용 가짜 상품 사진 생성
cp data/products.example.csv data/products.csv
python3 make_videos.py --handle @myshop
```

`out/video/`에 mp4 3개, `out/caption/`에 캡션 3개가 생깁니다.

## 3. 실제로 쓰기

1. **상품 사진**을 `assets/images/`에 넣습니다. (또는 CSV에 이미지 URL을 그대로 적어도 됩니다 — 자동으로 받아서 캐시합니다)
2. **`data/products.csv`**를 채웁니다. 엑셀·구글시트에서 편집하고 CSV로 저장하면 됩니다.
3. **배경음악**을 `assets/bgm/`에 넣습니다. 여러 개 넣으면 상품마다 돌아가며 배정됩니다.
4. 실행합니다.

```bash
python3 make_videos.py --handle @myshop --jobs 4
```

---

## 4. CSV 컬럼

| 컬럼 | 필수 | 설명 |
|---|---|---|
| `id` | ✅ | 파일 이름이 됩니다. 영문/숫자/하이픈 권장. 중복 불가 |
| `name` | ✅ | 상품명 |
| `deal_price` | ✅ | 구매대행가. `21900`, `21,900원`, `₩21900` 다 됩니다 |
| `images` | ✅ | 상품 사진. `|`로 여러 장. 로컬 경로(CSV 위치 기준) 또는 http(s) URL |
| `hook` | | 첫 화면 문구. 비우면 상품명·할인율로 자동 생성. `|`는 줄바꿈 |
| `domestic_price` | | 국내 판매가. 넣으면 "국내가 → 직구가" 비교 화면이 생깁니다 |
| `currency` | | 기본 `원` |
| `points` | | 셀링포인트. `|`로 구분, **최대 3개**가 각각 한 장면이 됩니다 |
| `cta` | | 마지막 화면 문구. 비우면 "프로필 링크에서 바로 확인하세요" |
| `link` | | 캡션에만 들어갑니다 (영상에는 안 나옴) |
| `tags` | | 해시태그. `|`로 구분 |

```csv
id,name,hook,domestic_price,deal_price,currency,points,cta,link,images,tags
camp-lamp,감성 캠핑 랜턴,국내 89000원짜리 이 랜턴|직구하면 얼마게요,89000,21900,원,밝기 3단계 무단 조절|USB-C 충전 8시간|IPX4 생활방수,프로필 링크에서 주문하세요,https://example.com/lamp,../assets/images/camp-lamp-1.jpg|../assets/images/camp-lamp-2.jpg,캠핑용품|감성캠핑
```

> 이미지 경로는 **CSV 파일 기준 상대경로**입니다. CSV가 `data/`에 있으면 `../assets/images/...`가 됩니다.

---

## 5. 영상 구성

| 장면 | 길이 | 내용 |
|---|---|---|
| 훅 | 2.8초 | `hook` 문구 + 대표 사진 + "N% 싸게 사는 법 ↓" |
| 가격 | 3.4초 | 국내가(취소선) → 구매대행가 + 절약액 뱃지 |
| 포인트 ×N | 2.5초 | `points` 한 줄씩 + 사진 |
| 갤러리 | 2.5초 | 쓰고 남은 사진이 있을 때만 |
| CTA | 2.4초 | 가격 + `cta` + 계정명 + 관세 별도 고지 |

포인트 3개 기준 **약 14초**입니다.

---

## 6. 실행 옵션

```bash
python3 make_videos.py [옵션]
```

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--csv` | `data/products.csv` | 상품 CSV 경로 |
| `--out` | `out` | 결과 폴더 |
| `--bgm` | `assets/bgm` | 배경음악 폴더 |
| `--handle` | (없음) | 영상에 박을 계정명. 예: `@myshop` |
| `--jobs` | `2` | 동시 렌더 개수. CPU 코어 수 정도까지 올리세요 |
| `--limit` | `0` | 앞에서 N개만 |
| `--only` | | 특정 id만. 예: `--only camp-lamp,kettle` |
| `--scenes-only` | | 영상 없이 **장면 PNG만** — 시안을 초 단위로 확인할 때 |
| `--keep-scenes` | | 렌더 후에도 장면 PNG를 남김 |
| `--no-motion` | | 줌/팬 끄기. 렌더가 3~4배 빨라집니다 |
| `--hashtags` | | 모든 캡션에 공통으로 붙일 해시태그. 예: `--hashtags 직구,해외배송` |
| `--crf` | `20` | 화질. 낮을수록 고화질·큰 용량 (18~24 권장) |

### 자주 쓰는 조합

```bash
# 문구·레이아웃만 빠르게 확인 (영상 렌더 안 함)
python3 make_videos.py --scenes-only

# 한 개만 다시 렌더
python3 make_videos.py --only camp-lamp

# 100개 밤새 돌리기
python3 make_videos.py --jobs 8 --crf 22
```

---

## 7. 같은 영상처럼 안 보이게 만드는 장치

플랫폼은 똑같은 템플릿이 반복되면 중복 콘텐츠로 보고 노출을 줄입니다.
그래서 상품마다 **자동으로 다르게** 만듭니다.

- **색 테마 5종**이 상품별로 배정되고, 연속된 상품끼리는 절대 같은 색이 안 나옵니다
- **장면 전환 8종**, **줌/팬 5방향**이 상품 id 기준으로 매번 다르게 뽑힙니다
- **배경음악**은 폴더에 넣은 순서대로 돌아가며 배정되고, 시작 지점도 매번 다릅니다
- **훅 문구**도 비워두면 3가지 패턴 중에서 골라 씁니다
- 배경은 그 상품 사진을 흐려서 깔기 때문에 상품마다 배경색이 다릅니다

같은 상품을 다시 렌더하면 결과가 똑같이 나옵니다 (id 기준 고정 시드).
느낌을 바꾸고 싶으면 `id`를 바꾸세요.

---

## 8. 운영 팁

- **훅(첫 1초)만 손보세요.** 조회수는 거의 다 여기서 갈립니다. 나머지는 자동이어도 됩니다.
- **`--scenes-only`로 먼저 돌려서** 문구가 잘렸는지, 가격이 맞는지 PNG로 확인한 뒤 본 렌더를 도세요.
- **BGM은 5개 이상** 넣어두세요. 하나만 넣으면 전부 같은 음악이 됩니다. 저작권 문제 없는 음원만 쓰세요.
- **하루 업로드는 3~5개로 나누세요.** 한 번에 30개 올리면 스팸으로 잡힙니다.
- **상품 사진은 가공해서 쓰세요.** 해외 판매자 사진을 그대로 쓰면 저작권·계정 정지 이슈가 있습니다.
- 관세·배송비 별도 고지는 마지막 장면과 캡션에 자동으로 들어갑니다. **가격 표기는 직접 한 번 더 확인하세요.**

## 9. 문제 해결

| 증상 | 해결 |
|---|---|
| `ffmpeg를 찾지 못했습니다` | ffmpeg 설치 후 PATH 확인. 또는 `BULKVID_FFMPEG=/경로/ffmpeg` |
| `한글 폰트를 찾지 못했습니다` | `BULKVID_FONT_BOLD=/경로/폰트.ttf`, `BULKVID_FONT_REGULAR=...` 지정 (ttc는 `경로#인덱스`) |
| 글자가 화면 밖으로 잘림 | `bulkvid/scenes.py`의 `SIDE_MARGIN`을 키우거나 `bulkvid/video.py`의 `MAX_ZOOM`을 낮추세요 |
| 한 상품만 실패 | 나머지는 그대로 진행됩니다. `out/manifest.csv`의 `error` 칸에 이유가 적힙니다 |
| 렌더가 너무 느림 | `--no-motion --jobs <코어수> --crf 23` |
| 음악이 너무 큼/작음 | `bulkvid/config.py`의 `RenderSettings.bgm_volume` (기본 0.28) |

## 10. 결과물 구조

```
out/
├── video/<id>.mp4        업로드할 영상
├── caption/<id>.txt      제목 + 본문 + 해시태그
├── scenes/<id>/*.png     --keep-scenes 또는 --scenes-only일 때만
└── manifest.csv          id, 상태, 길이, 테마, 사용한 BGM, 실패 사유
```

## 11. 테스트

```bash
python3 -m unittest discover -s tests -v
```
