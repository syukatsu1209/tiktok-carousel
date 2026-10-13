"""TikTokカルーセル レンダラー
usage: python render.py posts/2026-10-13.json
出力: out/<post_id>/slide_01.png ... (すべて 1080x1440 / 3:4 固定) と caption.txt
"""
import json, os, sys, html, pathlib
from PIL import Image, ImageFilter, ImageEnhance
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent.resolve()
W, H = 1080, 1440
FONT = ROOT / 'node_modules/@fontsource'


def smoke(src, dst, blur=5, white=0.52):
    """背景にスモーク（ぼかし＋白フィルム）をかける"""
    im = Image.open(src).convert('RGB').resize((W, H))
    im = im.filter(ImageFilter.GaussianBlur(blur))
    im = ImageEnhance.Color(im).enhance(0.85)
    im = Image.blend(im, Image.new('RGB', (W, H), (246, 248, 252)), white)
    im.save(dst)
    return dst


def e(s):
    return html.escape(str(s))


BASE_CSS = f"""
@import url('file://{FONT}/m-plus-rounded-1c/800.css');
@import url('file://{FONT}/m-plus-rounded-1c/900.css');
@import url('file://{FONT}/noto-sans-jp/500.css');
@import url('file://{FONT}/noto-sans-jp/700.css');
@import url('file://{FONT}/noto-sans-jp/900.css');
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:'Noto Sans JP','Noto Color Emoji',sans-serif;color:#1b1f2e;
  background-size:cover;background-position:center;--k:1;
  -webkit-font-smoothing:antialiased}}
.emo{{font-family:'Noto Color Emoji';font-weight:400}}
:root{{--red:#e8343a;--navy:#14204a;--ink:#1b1f2e;--muted:#6b7280;--line:#e4e7ee}}
"""

COVER_CSS = """
.wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:64px;padding:0 40px}
.block{display:flex;flex-direction:column;align-items:center}
.line{background:#fff;border-radius:30px;padding:22px 44px 26px;margin-top:-26px;
  font-family:'M PLUS Rounded 1c','Noto Color Emoji';font-weight:900;font-size:96px;
  line-height:1.12;letter-spacing:.01em;white-space:nowrap;color:#111;
  box-shadow:0 10px 30px rgba(0,0,0,.18)}
.line:first-child{margin-top:0}
.line + .line{box-shadow:0 14px 30px rgba(0,0,0,.18)}
"""

CARD_CSS = """
.stack{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;
  align-items:center;gap:calc(30px*var(--k));padding:34px 0}
.card{width:932px;background:rgba(255,255,255,.97);border-radius:30px;
  padding:calc(30px*var(--k)) 44px calc(28px*var(--k));
  box-shadow:0 14px 40px rgba(20,32,74,.16),0 0 0 2px rgba(255,255,255,.7) inset}
.brand{display:flex;align-items:baseline;justify-content:center;gap:20px;margin-bottom:calc(8px*var(--k))}
.wm{font-family:'M PLUS Rounded 1c';font-weight:900;font-size:calc(60px*var(--k));
  letter-spacing:.01em;line-height:1}
.tag{font-weight:700;font-size:calc(22px*var(--k));padding:4px 12px;border-radius:8px;
  line-height:1.3}
.name{display:flex;align-items:center;gap:14px;font-family:'M PLUS Rounded 1c','Noto Color Emoji';font-weight:900;
  font-size:calc(42px*var(--k));color:var(--navy);line-height:1.2;margin-bottom:calc(10px*var(--k))}
.name .emo{font-size:calc(40px*var(--k))}
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:calc(14px*var(--k))}
.chip{font-family:'M PLUS Rounded 1c';font-weight:900;font-size:calc(27px*var(--k));white-space:nowrap;
  border-radius:12px;padding:5px 16px 7px;line-height:1.25}
.chip.prog{background:var(--red);color:#fff}
.chip.dl{background:#fff1f1;color:var(--red);box-shadow:0 0 0 2.5px var(--red) inset}
.chip.sel{background:#e9f8ef;color:#13804a;box-shadow:0 0 0 2.5px #2fae6a inset}
.chip.sel.on{background:#eef2ff;color:#3546a8;box-shadow:0 0 0 2.5px #5b6bd1 inset}
.stats{display:grid;grid-template-columns:1fr 1fr 1fr;align-items:center}
.stat{display:flex;align-items:center;gap:14px;padding:0 6px 0 16px;border-left:2px solid var(--line)}
.stat:first-child{border-left:0;padding-left:0}
.stat .emo{font-size:calc(50px*var(--k));line-height:1}
.lbl{font-weight:700;font-size:calc(23px*var(--k));color:var(--ink);line-height:1.1}
.val{font-family:'M PLUS Rounded 1c';font-weight:900;color:var(--red);
  font-size:calc(56px*var(--k));line-height:1.05;letter-spacing:-.01em;white-space:nowrap}
.val small{font-size:.52em;margin-left:2px}
.val.txt{font-size:calc(44px*var(--k))}
.note{text-align:right;font-size:calc(16.5px*var(--k));color:var(--muted);margin:calc(8px*var(--k)) 0 calc(12px*var(--k));
  font-weight:500;letter-spacing:-.01em}
.hr{height:2px;background:var(--line);margin-bottom:calc(14px*var(--k))}
.h{display:flex;align-items:center;gap:10px;font-family:'M PLUS Rounded 1c','Noto Color Emoji';font-weight:900;
  font-size:calc(34px*var(--k));color:var(--navy);margin-bottom:calc(10px*var(--k))}
.pts{list-style:none;display:flex;flex-direction:column;gap:calc(9px*var(--k))}
.pts li{display:flex;gap:16px;align-items:flex-start;font-weight:500;font-size:calc(25px*var(--k));
  line-height:1.42;color:#262b3a}
.pts li .emo{font-size:calc(28px*var(--k));line-height:1.3;flex:none;width:36px;text-align:center}
"""

DETAIL_CSS = """
.card.detail{width:880px}
.sec{border-radius:20px;padding:calc(16px*var(--k)) 26px calc(18px*var(--k));margin-top:calc(14px*var(--k))}
.sec-h{display:inline-flex;align-items:center;gap:10px;font-family:'M PLUS Rounded 1c','Noto Color Emoji';
  font-weight:900;font-size:calc(30px*var(--k));padding:6px 22px;border-radius:999px;margin-bottom:calc(10px*var(--k))}
.sec.pt{background:#f1f5fd}
.sec.pt .sec-h{background:#dfe8fb;color:#1d3b8a}
.sec.fit{background:#fff4f6}
.sec.fit .sec-h{background:#ffe0e6;color:#b4234a}
.sec.unfit{background:#f2f5fb}
.sec.unfit .sec-h{background:#dde5f5;color:#24418f}
.dots{list-style:none;display:flex;flex-direction:column;gap:calc(6px*var(--k))}
.dots li{display:flex;gap:14px;align-items:flex-start;font-size:calc(25px*var(--k));font-weight:500;line-height:1.42}
.dots li::before{content:'';flex:none;width:11px;height:11px;border-radius:50%;background:#2d56c8;margin-top:calc(14px*var(--k))}
.fingers li::before{display:none}
.fingers li .emo{font-size:calc(27px*var(--k));line-height:1.35}
"""

CTA_CSS = """
.cta{width:900px;text-align:center;padding:56px 54px 50px}
.pr{position:absolute;top:44px;right:44px;background:#1b1f2e;color:#fff;font-weight:700;font-size:24px;
  padding:6px 16px;border-radius:8px}
.cta .kick{font-family:'M PLUS Rounded 1c';font-weight:900;font-size:40px;color:var(--navy);line-height:1.35}
.cta .big{font-family:'M PLUS Rounded 1c';font-weight:900;font-size:74px;line-height:1.18;margin:18px 0 30px;color:#111}
.cta .big em{font-style:normal;color:var(--red);background:linear-gradient(transparent 62%,#ffe066 62%)}
.feat{display:flex;flex-direction:column;gap:18px;text-align:left;margin-bottom:34px}
.feat div{display:flex;gap:18px;align-items:center;background:#f4f7fd;border-radius:18px;padding:18px 24px;
  font-weight:700;font-size:30px;line-height:1.35}
.feat b{flex:none;width:52px;height:52px;border-radius:50%;background:var(--red);color:#fff;
  display:grid;place-items:center;font-family:'M PLUS Rounded 1c';font-weight:900;font-size:30px}
.btn{display:inline-block;background:var(--red);color:#fff;font-family:'M PLUS Rounded 1c','Noto Color Emoji';font-weight:900;
  font-size:36px;padding:24px 44px;border-radius:999px;box-shadow:0 10px 0 #b8242a;white-space:nowrap}
.svc{margin-top:28px;font-size:22px;color:var(--muted);font-weight:500}
"""

FIT_JS = """
() => {
  const b = document.body; let k = 1;
  const over = () => [...document.querySelectorAll('.stack')].some(s => s.scrollHeight > s.clientHeight + 1);
  while (over() && k > 0.72) { k -= 0.01; b.style.setProperty('--k', k.toFixed(2)); }
  // 表紙：1行が横幅からはみ出す場合は文字を縮小
  document.querySelectorAll('.line').forEach(l => {
    let fs = parseFloat(getComputedStyle(l).fontSize);
    while (l.offsetWidth > 990 && fs > 48) { fs -= 2; l.style.fontSize = fs + 'px'; }
  });
  // ラベル（チップ）が2行に折り返す場合は縮小
  document.querySelectorAll('.chips').forEach(c => {
    const chips = [...c.children];
    let fs = parseFloat(getComputedStyle(chips[0]).fontSize);
    const wrapped = () => new Set(chips.map(x => x.offsetTop)).size > 1;
    while (wrapped() && fs > 18) { fs -= 1; chips.forEach(x => x.style.fontSize = fs + 'px'); }
  });
  // ランキング：社名や文字ロゴがはみ出す場合は縮小（文字ロゴは最大幅 300px）
  document.querySelectorAll('.wmk').forEach(w => {
    let fs = parseFloat(getComputedStyle(w).fontSize);
    const t = w.closest('.rtop');
    while ((w.offsetWidth > 250 || (t && t.scrollWidth > t.clientWidth + 1)) && fs > 18) { fs -= 1; w.style.fontSize = fs + 'px'; }
  });
  document.querySelectorAll('.rtop').forEach(t => {
    const r = t.querySelector('.rank');
    let fs = parseFloat(getComputedStyle(r).fontSize);
    while (r.scrollWidth > r.parentElement.clientWidth + 1 && fs > 20) { fs -= 1; r.style.fontSize = fs + 'px'; }
  });
  return k;
}
"""


def emo(s):
    return f'<span class="emo">{e(s)}</span>'


def mixed(text):
    """絵文字と文字が混在する行。絵文字はカラー絵文字フォントで描画される"""
    return e(text)


def stat_html(s):
    icons = {'年収': '💰', '初任給': '💰', '休日': '📅', '残業': '🕒'}
    v = s['value']
    is_num = any(ch.isdigit() for ch in v)
    val = f'<div class="val">{e(v)}<small>{e(s.get("unit", ""))}</small></div>' if is_num \
        else f'<div class="val txt">{e(v)}</div>'
    return (f'<div class="stat">{emo(icons.get(s["label"], "📌"))}'
            f'<div><div class="lbl">{e(s["label"])}</div>{val}</div></div>')


def card_head(c):
    brand = c.get('brand', '#14204a')
    sel_cls = 'sel' + ('' if '選考なし' in c.get('selection', '') else ' on')
    logo = (f'<img src="file://{ROOT / c["logo"]}" style="height:calc(72px*var(--k))">' if c.get('logo')
            else f'<span class="wm" style="color:{brand}">{e(c["wordmark"])}</span>')
    return f"""
    <div class="brand">{logo}<span class="tag" style="color:{brand};background:{brand}14">{e(c['tagline'])}</span></div>
    <div class="name">{emo(c['icon'])}<span>{e(c['name'])}</span></div>
    <div class="chips"><span class="chip prog">{e(c['program'])}</span>
      <span class="chip dl">{e(c['deadline'])}</span>
      <span class="chip {sel_cls}">{e(c['selection'])}</span></div>
    <div class="stats">{''.join(stat_html(s) for s in c['stats'])}</div>
    <div class="note">（{e(c['note'])}）</div>
    <div class="hr"></div>"""


def card_html(c):
    pts = ''.join(f'<li>{emo(i)}<span>{e(t)}</span></li>' for i, t in c['points'])
    return f"""<div class="card">{card_head(c)}
      <div class="h">{emo('🔍')}<span>深掘りポイント</span></div>
      <ul class="pts">{pts}</ul></div>"""


def detail_html(c):
    pts = ''.join(f'<li><span>{e(t)}</span></li>' for t in c['points'])
    fit = ''.join(f'<li>{emo("👉")}<span>{e(t)}</span></li>' for t in c['fit'])
    unfit = ''.join(f'<li>{emo("👉")}<span>{e(t)}</span></li>' for t in c['unfit'])
    return f"""<div class="card detail">{card_head(c)}
      <div class="sec pt" style="margin-top:0"><div class="sec-h">{emo('⭐')}<span>深掘りポイント</span></div>
        <ul class="dots">{pts}</ul></div>
      <div class="sec fit"><div class="sec-h">{emo('🙆')}<span>向いてる人</span></div>
        <ul class="dots fingers">{fit}</ul></div>
      <div class="sec unfit"><div class="sec-h">{emo('🙅')}<span>向いてない人</span></div>
        <ul class="dots fingers">{unfit}</ul></div></div>"""


def cta_html():
    return f"""<div class="pr">PR</div><div class="stack"><div class="card cta">
      <div class="kick">インターンの次は本選考。</div>
      <div class="big">書類選考なしで<br><em>大手・優良企業</em>へ</div>
      <div class="feat">
        <div><b>1</b><span>書類選考なし＆3次選考まで免除の<br>「特別推薦ルート」</span></div>
        <div><b>2</b><span>最短3日で内定（卒年により異なる）</span></div>
        <div><b>3</b><span>希望に合う企業だけを紹介。無理な推薦なし</span></div>
      </div>
      <div class="btn">プロフィールのリンクから無料登録 👆</div>
      <div class="svc">キャリアパーク！就職エージェント<br>※紹介企業・選考条件は人により異なります</div>
    </div></div>"""


LOGO_DIR = ROOT / 'logos'


UA = {'User-Agent': 'tiktok-carousel/1.0 (https://github.com/syukatsu1209/tiktok-carousel)'}


def _get(url, timeout=20):
    import urllib.request
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def wikidata_logo_url(qid):
    """Wikidata の「ロゴ画像(P154)」から Wikimedia Commons の画像URL（PNG・幅500px）を得る"""
    import urllib.parse
    d = json.loads(_get(f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'))
    ent = next(iter(d['entities'].values()))
    claims = ent.get('claims', {}).get('P154', [])
    # 推奨(preferred)ランクがあればそれ、なければ最初のもの
    claims.sort(key=lambda c: c.get('rank') != 'preferred')
    if not claims:
        raise ValueError(f'{qid} にロゴ画像(P154)が登録されていません')
    fname = claims[0]['mainsnak']['datavalue']['value']
    return 'https://commons.wikimedia.org/wiki/Special:FilePath/' + urllib.parse.quote(fname) + '?width=500'


def wikidata_search(term):
    """社名で Wikidata を検索し、ロゴ画像(P154)を持つ最初の候補の Q番号を返す"""
    import urllib.parse
    q = urllib.parse.urlencode({'action': 'wbsearchentities', 'search': term, 'language': 'ja',
                                'uselang': 'ja', 'type': 'item', 'limit': 5, 'format': 'json'})
    hits = json.loads(_get('https://www.wikidata.org/w/api.php?' + q)).get('search', [])
    for h in hits:
        try:
            wikidata_logo_url(h['id'])
            print(f'  ロゴ検索: {term} → {h["id"]} {h.get("label")} / {h.get("description", "")}')
            return h['id']
        except Exception:
            continue
    raise ValueError(f'Wikidata で「{term}」のロゴが見つかりません')


def logo_src(item):
    """ロゴ画像のパスを返す。
    logo（リポジトリ内の画像）> logo_url（直接URL）> wikidata（Q番号）> 社名で Wikidata 検索 の順。
    取得できなければ None（その場合は社名の文字ロゴで代用）"""
    if item.get('logo') and (ROOT / item['logo']).exists():
        return f'file://{ROOT / item["logo"]}'
    if item.get('logo') is False:          # ロゴを使わない（文字ロゴにする）
        return None
    key = item.get('logo_url') or item.get('wikidata') or ('search:' + item.get('logo_search', item['name']))
    import hashlib
    LOGO_DIR.mkdir(exist_ok=True)
    stem = hashlib.sha1(key.encode()).hexdigest()[:16]
    hit = [x for x in LOGO_DIR.glob(stem + '.*')]
    f = hit[0] if hit else None
    if not f:
        try:
            url = item.get('logo_url') or wikidata_logo_url(
                item.get('wikidata') or wikidata_search(item.get('logo_search', item['name'])))
            data = _get(url)
            if len(data) < 200:
                raise ValueError('画像が小さすぎます')
            ext = '.svg' if data.lstrip()[:1] == b'<' else '.jpg' if data[:2] == b'\xff\xd8' \
                else '.webp' if data[8:12] == b'WEBP' else '.png'
            f = LOGO_DIR / (stem + ext)
            f.write_bytes(data)
        except Exception as ex:
            print(f'[warn] ロゴを取得できませんでした（文字で代用）: {item.get("name")} {ex}')
            return None
    return f'file://{f}'


def logo_html(item, cls='logo'):
    src = logo_src(item)
    if src:
        return f'<img class="{cls}" src="{src}" alt="">'
    brand = item.get('brand', '#14204a')
    return f'<span class="{cls} wmk" style="color:{brand}">{e(item.get("wordmark") or item["name"])}</span>'


RANK_CSS = """
.stack{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:40px 0}
.rcard{width:820px;background:#fff;padding:calc(46px*var(--k)) 52px calc(44px*var(--k));
  box-shadow:0 6px 24px rgba(0,0,0,.10)}
.ritem{position:relative;margin-top:calc(42px*var(--k))}
.ritem:first-child{margin-top:0}
.rtop{display:flex;align-items:center;justify-content:space-between;gap:20px}
.rleft{flex:1;min-width:0}
.rank{display:flex;align-items:center;gap:12px;font-weight:700;font-size:calc(33px*var(--k));line-height:1.5;color:#111;white-space:nowrap}
.rank .emo{font-size:calc(34px*var(--k))}
.rline{display:flex;align-items:center;gap:12px;font-weight:500;font-size:calc(31px*var(--k));line-height:1.6;color:#111}
.rline .emo{font-size:calc(30px*var(--k));width:40px;text-align:center}
.rsub{font-weight:500;font-size:calc(26px*var(--k));line-height:1.55;color:#222;margin-left:4px}
.rpts{list-style:none;margin-top:calc(4px*var(--k))}
.rpts li{font-weight:500;font-size:calc(28px*var(--k));line-height:1.62;color:#111;padding-left:1.1em;text-indent:-1.1em}
.rpts li::before{content:'・'}
.logo{flex:none;max-width:250px;max-height:calc(96px*var(--k));object-fit:contain}
.wmk{font-family:'M PLUS Rounded 1c';font-weight:900;font-size:calc(46px*var(--k));letter-spacing:.01em;
  text-align:right;line-height:1.05;white-space:nowrap}
.rcard.solo{--k:1.12;width:860px;padding-top:calc(70px*var(--k));padding-bottom:calc(80px*var(--k))}
.rcard.solo .logo{max-height:calc(120px*var(--k))}
"""

LIST_CSS = """
.stack{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:40px 0}
.lcard{width:840px;background:#fff;padding:calc(64px*var(--k)) 70px calc(40px*var(--k));box-shadow:0 6px 24px rgba(0,0,0,.10)}
.ltitle{font-weight:700;font-size:calc(36px*var(--k));color:#222;margin-bottom:calc(40px*var(--k));
  display:flex;align-items:center;gap:8px}
.litems{list-style:none;counter-reset:n}
.litems li{counter-increment:n;font-weight:500;font-size:calc(29px*var(--k));line-height:1.55;color:#222;
  padding-left:1.6em;text-indent:-1.6em;margin-bottom:calc(6px*var(--k))}
.litems li::before{content:counter(n, decimal);display:inline-flex;align-items:center;justify-content:center;
  width:1.2em;height:1.2em;margin-right:.35em;border:2px solid #333;border-radius:50%;font-size:.72em;text-indent:0;
  vertical-align:.12em}
.lfoot{text-align:right;font-weight:700;font-size:calc(26px*var(--k));color:#222;margin-top:calc(26px*var(--k))}
"""

TIPS_CSS = """
.stack{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;
  gap:calc(26px*var(--k));padding:60px 70px}
.th{background:#fff;font-weight:500;font-size:calc(50px*var(--k));line-height:1.35;padding:18px 26px;color:#111;
  text-align:center;max-width:960px}
.tb{background:#fff;font-weight:500;font-size:calc(31px*var(--k));line-height:1.45;padding:12px 22px;color:#111;
  text-align:center;max-width:840px}
.tex{display:flex;flex-direction:column;gap:12px;align-items:center}
.tex div{background:#fff;font-weight:500;font-size:calc(30px*var(--k));line-height:1.4;padding:8px 20px;color:#111;text-align:center}
.tsmall{color:#fff;font-weight:900;font-size:calc(27px*var(--k));line-height:1.5;text-align:center;
  text-shadow:0 2px 6px rgba(0,0,0,.55);max-width:820px}
"""


def medal(rank):
    return {1: '🥇', 2: '🥈', 3: '🥉'}.get(int(rank), '✅')


def rank_item_html(it):
    subs = ''.join(f'<div class="rsub">（{e(s)}）</div>' for s in it.get('notes', []))
    pts = ''.join(f'<li>{e(p)}</li>' for p in it.get('points', []))
    return f"""<div class="ritem"><div class="rtop"><div class="rleft">
      <div class="rank">{emo(medal(it['rank']))}<span>{e(it['rank'])}位：{e(it['name'])}</span></div>
      <div class="rline">{emo('👉')}<span>初任給 {e(it['start_pay'])}</span></div>
      </div>{logo_html(it)}</div>{subs}
      <div class="rline">{emo('💰')}<span>平均年収 {e(it['avg_salary'])}</span></div>
      <ul class="rpts">{pts}</ul></div>"""


def rank_html(items, solo=False):
    return f'<div class="stack"><div class="rcard{" solo" if solo else ""}">' + \
        ''.join(rank_item_html(i) for i in items) + '</div></div>'


def list_html(s):
    items = ''.join(f'<li>{e(t)}</li>' for t in s['items'])
    foot = f'<div class="lfoot">{e(s["footnote"])}</div>' if s.get('footnote') else ''
    return f"""<div class="stack"><div class="lcard"><div class="ltitle">{e(s['title'])}</div>
      <ul class="litems">{items}</ul>{foot}</div></div>"""


def tips_html(s):
    body = ''.join(f'<div class="tb">{e(t)}</div>' for t in s.get('body', []))
    ex = ''.join(f'<div>{e(t)}</div>' for t in s.get('examples', []))
    small = f'<div class="tsmall">{e(s["small"])}</div>' if s.get('small') else ''
    return f"""<div class="stack"><div class="th">{e(s['heading'])}</div>{body}
      {f'<div class="tex">{ex}</div>' if ex else ''}{small}</div>"""


def page(body, bg, css):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}{css}</style></head>
<body style="background-image:url('file://{bg}')">{body}</body></html>"""


def build(slide, workdir):
    t = slide['type']
    bg = ROOT / slide['bg']
    if t == 'cover':
        blocks = ''.join('<div class="block">' + ''.join(f'<div class="line">{mixed(l)}</div>' for l in b['lines'])
                         + '</div>' for b in slide['blocks'])
        return page(f'<div class="wrap">{blocks}</div>', bg, COVER_CSS)
    if t in ('rank', 'rank1', 'list', 'tips'):
        # 参考投稿と同じく、背景写真はそのまま（スモークなし）に白カード／白帯を載せる
        if t in ('rank', 'rank1'):
            return page(rank_html(slide['items'], solo=(t == 'rank1')), bg, RANK_CSS)
        if t == 'list':
            return page(list_html(slide), bg, LIST_CSS)
        return page(tips_html(slide), bg, TIPS_CSS)
    sm = smoke(bg, workdir / f'smoke_{bg.stem}.png')
    if t == 'cards':
        return page('<div class="stack">' + ''.join(card_html(c) for c in slide['cards']) + '</div>',
                    sm, CARD_CSS)
    if t == 'detail':
        return page(f'<div class="stack">{detail_html(slide["card"])}</div>', sm, CARD_CSS + DETAIL_CSS)
    if t == 'cta':
        return page(cta_html(), sm, CARD_CSS + CTA_CSS)
    raise ValueError(t)


def main(path):
    post = json.load(open(path, encoding='utf-8'))
    out = ROOT / 'out' / post['post_id']
    out.mkdir(parents=True, exist_ok=True)
    work = out / '_work'; work.mkdir(exist_ok=True)
    for old in out.glob('slide_*.png'):  # ページ数を変えて作り直したときの残骸を消す
        old.unlink()
    # フォントや画像はローカルWebサーバー経由で読み込む（file:// だとブラウザがフォントを拒否するため）
    import functools, threading
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'
    with sync_playwright() as p:
        ch = os.environ.get('BROWSER_CHANNEL')  # GitHub Actions では入っている Chrome を使う
        br = p.chromium.launch(channel=ch) if ch else p.chromium.launch()
        pg = br.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        for i, s in enumerate(post['slides'], 1):
            f = work / f'slide_{i:02d}.html'
            f.write_text(build(s, work).replace(f'file://{ROOT}', base), encoding='utf-8')
            pg.goto(base + '/' + f.relative_to(ROOT).as_posix())
            pg.evaluate('document.fonts.ready')
            pg.wait_for_timeout(200)
            bad = pg.evaluate("[...document.fonts].filter(f => f.status === 'error').length")
            if bad:
                raise SystemExit(f'フォントの読み込みに失敗しました（{bad}件）')
            pg.wait_for_timeout(300)
            k = pg.evaluate(FIT_JS)
            name = f'slide_{i:02d}' + ('_optional' if s.get('optional') else '') + '.png'
            pg.screenshot(path=str(out / name), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
            sz = Image.open(out / name).size
            assert sz == (W, H), sz
            print(name, sz, f'fit={k}')
        br.close()
    cap = post['caption'] + '\n'
    (out / 'caption.txt').write_text(cap, encoding='utf-8')
    src = '\n'.join(f'- {a}: {u}' for a, u in post.get('sources', []))
    (out / 'sources.md').write_text(f'# 出典（{post["post_id"]}）\n\n{src}\n', encoding='utf-8')
    print('done ->', out)


if __name__ == '__main__':
    main(sys.argv[1])
