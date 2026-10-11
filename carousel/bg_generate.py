"""背景画像ジェネレーター（仮素材用）
本番では Pexels / Unsplash API または手持ち写真フォルダから取得する。
このサンドボックスは画像サイトに接続できないため、ビル街の背景を描画して代用する。

usage: python bg_generate.py <scene: dusk|day> <seed> <out.png>
"""
import sys, random, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1440
S = 2  # supersampling
w, h = W * S, H * S


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_c(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def hexc(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def vgrad(c_top, c_bot, size):
    ww, hh = size
    t = np.linspace(0, 1, hh)[:, None]
    a = np.array(c_top)[None, None, :]
    b = np.array(c_bot)[None, None, :]
    arr = a + (b - a) * t[..., None]
    arr = np.repeat(arr, ww, axis=1)
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def bil(q, u, v):
    """q = (BL, BR, TR, TL); u: 0..1 左→右, v: 0..1 下→上"""
    BL, BR, TR, TL = q
    bx = lerp(BL[0], BR[0], u); by = lerp(BL[1], BR[1], u)
    tx = lerp(TL[0], TR[0], u); ty = lerp(TL[1], TR[1], u)
    return (lerp(bx, tx, v), lerp(by, ty, v))


def persp(t, k=2.3):
    return t * k / (1 + (k - 1) * t)


def facade(draw, q, rows, cols, base, mull, rnd, lit=0.0, lit_col=(255, 214, 160),
           vary=14, band_top=None, stripe=False, grad=None):
    # 下地
    draw.polygon([q[0], q[1], q[2], q[3]], fill=mull)
    for r in range(rows):
        v0 = persp(r / rows); v1 = persp((r + 1) / rows)
        gap_v = (v1 - v0) * (0.10 if not stripe else 0.45)
        for c in range(cols):
            u0 = c / cols; u1 = (c + 1) / cols
            gap_u = (u1 - u0) * (0.08 if not stripe else 0.02)
            pts = [bil(q, u0 + gap_u, v0 + gap_v), bil(q, u1 - gap_u, v0 + gap_v),
                   bil(q, u1 - gap_u, v1 - gap_v), bil(q, u0 + gap_u, v1 - gap_v)]
            if rnd.random() < lit:
                col = lerp_c(lit_col, (255, 240, 210), rnd.random() * 0.5)
            else:
                g = grad(v0, u0) if grad else base
                d = rnd.randint(-vary, vary)
                col = tuple(max(0, min(255, g[i] + d)) for i in range(3))
            draw.polygon(pts, fill=col)


def clouds(img, rnd, n=26):
    layer = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        cx = rnd.uniform(0.15, 0.85) * w
        cy = rnd.uniform(0.0, 0.85) * h
        for _ in range(rnd.randint(6, 14)):
            rx = rnd.uniform(40, 170) * S
            ry = rx * rnd.uniform(0.35, 0.6)
            ox = cx + rnd.uniform(-160, 160) * S
            oy = cy + rnd.uniform(-40, 40) * S
            d.ellipse([ox - rx, oy - ry, ox + rx, oy + ry], fill=rnd.randint(90, 200))
    layer = layer.filter(ImageFilter.GaussianBlur(28 * S))
    white = Image.new('RGB', img.size, (250, 252, 255))
    return Image.composite(white, img, layer)


def trees(img, rnd, regions):
    d = ImageDraw.Draw(img)
    for (x0, y0, x1, y1, n) in regions:
        centers = [(rnd.uniform(x0, x1) * w, rnd.uniform(y0, y1) * h, rnd.uniform(40, 110) * S)
                   for _ in range(max(3, n // 60))]
        for _ in range(n):
            ccx, ccy, cr = rnd.choice(centers)
            cx = rnd.gauss(ccx, cr)
            cy = rnd.gauss(ccy, cr * 0.8)
            r = rnd.uniform(6, 26) * S
            col = (rnd.randint(8, 22), rnd.randint(14, 30), rnd.randint(14, 26))
            # 葉っぱの形（5点の星型を丸めた多角形）
            pts = []
            k = rnd.randint(5, 7)
            for i in range(k * 2):
                a = i * math.pi / k + rnd.uniform(-0.2, 0.2)
                rr = r if i % 2 == 0 else r * 0.55
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            d.polygon(pts, fill=col)


def glow(img, pts, color, radius):
    layer = Image.new('RGB', img.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (x, y, r) in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    a = np.asarray(img).astype(np.float32)
    b = np.asarray(layer).astype(np.float32)
    out = 255 - (255 - a) * (255 - b) / 255  # screen
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def finish(img, rnd, warm=0.0):
    img = img.resize((W, H), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    # 斜めの光の反射（写真っぽさ）
    yy0, xx0 = np.mgrid[0:H, 0:W]
    diag = (xx0 * 0.8 + yy0 * 0.45) / (W * 0.8 + H * 0.45)
    sheen = np.exp(-((diag - rnd.uniform(0.3, 0.6)) / 0.12) ** 2) * 22
    a += sheen[..., None]
    # ビネット
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = 1 - 0.22 * np.clip(dist - 0.55, 0, 1)
    a *= vig[..., None]
    # グレイン
    noise = np.random.default_rng(rnd.randint(0, 10 ** 6)).normal(0, 4.0, a.shape[:2])
    a += noise[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def scene_day(seed):
    rnd = random.Random(seed)
    img = vgrad(hexc('#2f6fd0'), hexc('#a9d0f7'), (w, h))
    img = clouds(img, rnd)
    d = ImageDraw.Draw(img)
    # 中景の細いタワー（中央奥）
    cx = rnd.uniform(0.44, 0.56) * w
    q = [(cx - 70 * S, h), (cx + 70 * S, h), (cx + 46 * S, h * 0.80), (cx - 46 * S, h * 0.80)]
    facade(d, q, 16, 6, (205, 214, 226), (150, 160, 175), rnd, vary=10)
    # 左タワー（側面→正面）
    lb, lt = rnd.uniform(0.40, 0.48), rnd.uniform(0.30, 0.37)
    top_y = rnd.uniform(0.0, 0.06) * h
    side = [(-0.05 * w, h), (0.06 * w, h), (0.10 * w, top_y + 30 * S), (0.02 * w, top_y + 40 * S)]
    facade(d, side, 46, 5, (120, 150, 190), (70, 92, 125), rnd, vary=12)
    front = [(0.06 * w, h), (lb * w, h), (lt * w, top_y), (0.10 * w, top_y + 30 * S)]
    sky_ref = lambda v, u: lerp_c((150, 190, 235), (70, 120, 190), v)
    facade(d, front, 54, 14, (120, 160, 210), (60, 85, 120), rnd, vary=16, grad=sky_ref)
    # 右タワー（ストライプ外装 + ガラス）
    rb, rt = rnd.uniform(0.60, 0.66), rnd.uniform(0.70, 0.75)
    ry = rnd.uniform(0.10, 0.20) * h
    front_r = [(rb * w, h), (0.94 * w, h), (0.90 * w, ry + 20 * S), (rt * w, ry)]
    facade(d, front_r, 40, 10, (160, 170, 182), (120, 128, 140), rnd, vary=10, stripe=True,
           grad=lambda v, u: lerp_c((175, 185, 198), (140, 150, 165), v))
    side_r = [(0.94 * w, h), (1.05 * w, h), (1.05 * w, ry + 60 * S), (0.90 * w, ry + 20 * S)]
    facade(d, side_r, 40, 4, (95, 105, 120), (60, 66, 78), rnd, vary=8, stripe=True)
    # 信号機・街路のシルエット
    d.rectangle([0.07 * w, 0.93 * h, 0.075 * w, h], fill=(30, 30, 34))
    img = glow(img, [(0.072 * w, 0.935 * h, 9 * S)], (255, 40, 30), 6 * S)
    return finish(img, rnd)


def scene_dusk(seed):
    rnd = random.Random(seed)
    img = vgrad(hexc('#1d3366'), hexc('#7d96cf'), (w, h))
    d = ImageDraw.Draw(img)
    # 遠景
    for i in range(4):
        x0 = rnd.uniform(0.35, 0.9) * w
        bw = rnd.uniform(90, 160) * S
        top = rnd.uniform(0.38, 0.6) * h
        q = [(x0, h), (x0 + bw, h), (x0 + bw * 0.92, top), (x0 + bw * 0.08, top)]
        facade(d, q, 30, 9, (40, 52, 80), (28, 36, 58), rnd, lit=0.22, vary=8)
    # 右の高層（格子ビル）
    q = [(0.78 * w, h), (1.02 * w, h), (1.0 * w, 0.33 * h), (0.83 * w, 0.34 * h)]
    facade(d, q, 44, 12, (36, 44, 66), (70, 76, 92), rnd, lit=0.22, vary=8)
    # 中央の大きなガラスタワー
    cx0, cx1 = 0.12, 0.66
    q = [(cx0 * w, h), (cx1 * w, h), (cx1 * 0.96 * w, -0.02 * h), (cx0 * 1.4 * w, -0.02 * h)]
    facade(d, q, 58, 16, (24, 36, 62), (14, 22, 40), rnd, lit=0.14, vary=12,
           grad=lambda v, u: lerp_c((38, 56, 92), (22, 32, 58), v))
    # 右側のストライプ面
    q = [(0.66 * w, h), (0.76 * w, h), (0.73 * w, -0.02 * h), (0.635 * w, -0.02 * h)]
    facade(d, q, 70, 3, (150, 160, 180), (60, 66, 84), rnd, vary=6, stripe=True)
    # 左手前の低層（ガラス＋暖色ロビー）
    q = [(-0.02 * w, h), (0.42 * w, h), (0.40 * w, 0.34 * h), (-0.02 * w, 0.30 * h)]
    facade(d, q, 18, 9, (20, 28, 46), (10, 14, 26), rnd, lit=0.16, vary=10)
    # 足元：石造りの低層（暖色ライトアップ）
    d.rectangle([0, 0.86 * h, 0.5 * w, h], fill=(120, 92, 58))
    for i in range(9):
        x = (0.01 + i * 0.055) * w
        d.rectangle([x, 0.86 * h, x + 0.012 * w, h], fill=(40, 30, 22))
    img = glow(img, [(rnd.uniform(0, 0.5) * w, rnd.uniform(0.8, 1.0) * h, rnd.uniform(20, 60) * S)
                     for _ in range(16)], (255, 190, 110), 40 * S)
    # 街路樹
    trees(img, rnd, [(0.80, -0.04, 1.04, 0.10, 700), (0.50, 0.78, 1.0, 1.02, 1500),
                     (0.40, -0.04, 0.58, 0.02, 220)])
    img = glow(img, [(0.72 * w, 0.75 * h, 10 * S)], (255, 230, 170), 12 * S)
    return finish(img, rnd)


if __name__ == '__main__':
    scene, seed, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    img = scene_day(seed) if scene == 'day' else scene_dusk(seed)
    img.save(out, quality=95)
    print(out, img.size)
