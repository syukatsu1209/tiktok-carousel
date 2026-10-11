"""ページ数・構成を指定して投稿データを組み立てる

usage:
  python compose.py specs/2026-10-13.json                 # spec の pages / layout に従う
  python compose.py specs/2026-10-13.json --pages 4       # ページ数だけ上書き
  python compose.py specs/2026-10-13.json --layout 表紙,2社,2社,PR
  python compose.py ... --render                          # そのまま画像まで書き出す

layout に使えるページの種類
  表紙 … ビル写真＋白帯テキスト（covers を上から順に使う）
  2社  … 2社カード（companies を2社ずつ使う。残り1社なら1社だけ）
  1社  … 1社詳細カード（向いてる人／向いてない人つき。detail を順に使う）
  PR   … アフィリエイト誘導スライド
layout を "auto" にすると pages の数に合わせて自動で組む。
"""
import argparse, json, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).parent.resolve()
BG = {'night': 'bg/night.png', 'day': 'bg/day.png', 'mine': 'bg/mine.png'}  # bg_fetch.py が毎回用意する
KIND = {'表紙': 'cover', '2社': 'cards', '1社': 'detail', 'PR': 'cta'}
MIN_PAGES, MAX_PAGES = 2, 35  # TikTok の写真投稿は最大35枚


def auto_layout(pages, spec):
    cta = spec.get('cta', True)
    body = pages - (1 if cta else 0)
    if body < 2:
        raise SystemExit(f'ページ数 {pages} では少なすぎます（表紙＋中身1枚{"＋PR" if cta else ""}が最低）')
    rest = body - 1                      # 1枚目の表紙を除いた枚数
    n_detail = len(spec.get('detail', []))
    n_cover = len(spec.get('covers', []))
    layout = ['表紙']
    if n_detail and n_cover >= 2 and rest >= 3:
        d = min(n_detail, max(1, (rest - 1) // 3))
        layout += ['2社'] * (rest - 1 - d) + ['表紙'] + ['1社'] * d
    elif n_detail and rest >= 2:
        layout += ['2社'] * (rest - 1) + ['1社']
    else:
        layout += ['2社'] * rest
    if cta:
        layout.append('PR')
    return layout


def build(spec, layout):
    covers = list(spec.get('covers', []))
    comps = list(spec.get('companies', []))
    details = list(spec.get('detail', []))
    need = {'表紙': 0, '2社': 0, '1社': 0}
    for k in layout:
        if k not in KIND:
            raise SystemExit(f'不明なページ種類: {k}（使えるのは {"/".join(KIND)}）')
    for k in layout:
        if k == '2社':
            need['2社'] += 2
        elif k in need:
            need[k] += 1
    short = []
    if need['表紙'] > len(covers):
        short.append(f'表紙テキストがあと{need["表紙"] - len(covers)}つ必要')
    if need['2社'] - 1 > len(comps):          # 最後の1枚だけ1社でも可
        short.append(f'2社カード用の企業があと{need["2社"] - 1 - len(comps)}社必要')
    if need['1社'] > len(details):
        short.append(f'1社詳細用の企業があと{need["1社"] - len(details)}社必要')
    if short:
        raise SystemExit('この構成では素材が足りません：' + '、'.join(short))

    slides, bg = [], BG['night']
    for k in layout:
        if k == '表紙':
            c = covers.pop(0)
            bg = BG.get(c.get('bg', 'night'), c.get('bg'))
            slides.append({'type': 'cover', 'bg': bg, 'blocks': c['blocks']})
        elif k == '2社':
            pair = [comps.pop(0)] + ([comps.pop(0)] if comps else [])
            slides.append({'type': 'cards', 'bg': bg, 'cards': pair})
        elif k == '1社':
            slides.append({'type': 'detail', 'bg': bg, 'card': details.pop(0)})
        else:
            slides.append({'type': 'cta', 'bg': bg})
    leftover = len(comps) + len(details)
    if leftover:
        print(f'※ 使われなかった企業が{leftover}社あります（ページ数を増やすと載せられます）')
    return slides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--pages', type=int)
    ap.add_argument('--layout', help='例: 表紙,2社,2社,表紙,1社,PR')
    ap.add_argument('--render', action='store_true')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))

    if a.layout:
        layout = [x.strip() for x in a.layout.split(',') if x.strip()]
    elif spec.get('layout', 'auto') != 'auto' and not a.pages:
        layout = spec['layout']
    else:
        pages = a.pages or spec.get('pages', 5)
        if not MIN_PAGES <= pages <= MAX_PAGES:
            raise SystemExit(f'ページ数は{MIN_PAGES}〜{MAX_PAGES}で指定してください')
        layout = auto_layout(pages, spec)

    post = {k: spec[k] for k in ('post_id', 'affiliate_url', 'caption', 'sources') if k in spec}
    post['layout'] = layout
    post['slides'] = build(spec, layout)
    out = ROOT / 'posts' / f"{spec['post_id']}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(layout)}ページ: ' + ' → '.join(layout))
    print('->', out)
    if a.render:
        subprocess.run([sys.executable, str(ROOT / 'render.py'), str(out)], check=True)


if __name__ == '__main__':
    main()
