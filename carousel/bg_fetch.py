"""背景写真を用意する（1080x1440 にトリミングして bg/night.png, bg/day.png, bg/mine.png を作る）

優先順位
  1. bg/user/ にあなたが入れた写真（night_*.jpg / day_*.jpg / その他は mine 用）
  2. Pexels API（環境変数 PEXELS_API_KEY がある場合）から縦長のビル写真をランダム取得
  3. 同梱の仮背景（bg/fallback_*.png）

usage: python bg_fetch.py <seed>
"""
import os, sys, json, random, pathlib, urllib.request, urllib.parse, io
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).parent.resolve()
BG = ROOT / 'bg'
W, H = 1080, 1440
QUERIES = {
    'night': ['city skyscraper night', 'office building dusk', 'tokyo building night', 'skyscraper blue hour'],
    'day': ['skyscraper blue sky', 'office building looking up', 'glass building sky', 'tokyo office building'],
}
CREDITS = []


def fit(img):
    img = ImageOps.exif_transpose(img).convert('RGB')
    return ImageOps.fit(img, (W, H), Image.LANCZOS, centering=(0.5, 0.45))


def from_user(kind, rnd):
    pats = {'night': 'night_*', 'day': 'day_*', 'mine': '*'}
    files = [p for p in (BG / 'user').glob(pats[kind]) if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')]
    if not files:
        return None
    p = rnd.choice(files)
    CREDITS.append(f'{kind}: 手持ち写真 {p.name}')
    return fit(Image.open(p))


def from_pexels(kind, rnd):
    key = os.environ.get('PEXELS_API_KEY')
    if not key or kind not in QUERIES:
        return None
    q = rnd.choice(QUERIES[kind])
    url = 'https://api.pexels.com/v1/search?' + urllib.parse.urlencode(
        {'query': q, 'orientation': 'portrait', 'per_page': 40, 'page': rnd.randint(1, 3)})
    req = urllib.request.Request(url, headers={'Authorization': key, 'User-Agent': 'tiktok-carousel'})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
        photos = [p for p in data.get('photos', []) if p['height'] > p['width']]
        if not photos:
            return None
        ph = rnd.choice(photos)
        raw = urllib.request.urlopen(urllib.request.Request(
            ph['src']['large2x'], headers={'User-Agent': 'tiktok-carousel'}), timeout=60).read()
        CREDITS.append(f'{kind}: Pexels / {ph["photographer"]} {ph["url"]}')
        return fit(Image.open(io.BytesIO(raw)))
    except Exception as e:  # 取得に失敗しても投稿は止めない
        print(f'[warn] Pexels取得失敗 ({kind}): {e}')
        return None


def main(seed):
    rnd = random.Random(seed)
    for kind in ('night', 'day', 'mine'):
        img = from_user(kind, rnd) if kind == 'mine' else (from_user(kind, rnd) or from_pexels(kind, rnd))
        if img is None:
            fb = BG / f'fallback_{"day" if kind == "day" else "night"}.png'
            img = fit(Image.open(fb))
            CREDITS.append(f'{kind}: 仮背景 {fb.name}')
        img.save(BG / f'{kind}.png')
    (BG / 'credits.txt').write_text('\n'.join(CREDITS) + '\n', encoding='utf-8')
    print('\n'.join(CREDITS))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'x')
