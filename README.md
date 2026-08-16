# test

## bulkvid — 구매대행 숏폼 영상 대량 생성기

상품 CSV + 상품 사진 → 세로 1080×1920 숏폼 영상 + 업로드용 캡션을 한 번에 만듭니다.

```bash
pip install pillow                          # + ffmpeg 설치 필요
python3 scripts/make_sample_images.py       # 데모용 사진
cp data/products.example.csv data/products.csv
python3 make_videos.py --handle @myshop
```

사용법은 **[BULKVID.md](BULKVID.md)** 를 보세요.

```
bulkvid/         렌더 엔진 (config / models / imaging / scenes / video / captions / pipeline)
make_videos.py   CLI 진입점
data/            상품 CSV
assets/          상품 사진, 배경음악
tests/           단위 테스트 (python3 -m unittest discover -s tests)
```

## Midjourney Prompt Generator

`test.py` — ChatGPT로 미드저니 프롬프트를 만드는 Streamlit 앱.

```bash
streamlit run test.py
```
