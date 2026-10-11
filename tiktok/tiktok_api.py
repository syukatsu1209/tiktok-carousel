"""TikTok API の共通処理（トークン保存・更新、写真の下書き送信、状態確認）

トークンは tiktok/token.enc に暗号化して保存する。
暗号鍵は GitHub Secrets の TIKTOK_CLIENT_SECRET から作るので、リポジトリが公開でも中身は読めない。
"""
import base64, hashlib, json, os, pathlib, time, urllib.parse, urllib.request, urllib.error
from cryptography.fernet import Fernet

API = 'https://open.tiktokapis.com'
TOKEN_FILE = pathlib.Path(__file__).parent / 'token.enc'


def env(name):
    v = os.environ.get(name, '').strip()
    if not v:
        raise SystemExit(f'GitHub Secrets に {name} が登録されていません')
    return v


def _fernet():
    key = hashlib.sha256(('tiktok-carousel:' + env('TIKTOK_CLIENT_SECRET')).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def save_token(tok):
    tok = dict(tok, saved_at=int(time.time()))
    TOKEN_FILE.write_bytes(_fernet().encrypt(json.dumps(tok).encode()))


def load_token():
    if not TOKEN_FILE.exists():
        raise SystemExit('TikTokの初回ログインがまだです（README の「TikTokと連携する」を参照）')
    return json.loads(_fernet().decrypt(TOKEN_FILE.read_bytes()))


def _req(method, path, data=None, token=None, form=False):
    headers = {'User-Agent': 'tiktok-carousel'}
    body = None
    if form:
        body = urllib.parse.urlencode(data).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    elif data is not None:
        body = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json; charset=UTF-8'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors='replace')
        try:
            return json.loads(txt)
        except ValueError:
            raise SystemExit(f'TikTok API エラー {e.code}: {txt[:500]}')


def exchange_code(code, redirect_uri):
    res = _req('POST', '/v2/oauth/token/', {
        'client_key': env('TIKTOK_CLIENT_KEY'), 'client_secret': env('TIKTOK_CLIENT_SECRET'),
        'code': code, 'grant_type': 'authorization_code', 'redirect_uri': redirect_uri}, form=True)
    if 'access_token' not in res:
        raise SystemExit(f'ログインコードの交換に失敗しました: {res}')
    save_token(res)
    return res


def fresh_token():
    """リフレッシュトークンで毎回アクセストークンを取り直す（24時間で切れるため）"""
    tok = load_token()
    res = _req('POST', '/v2/oauth/token/', {
        'client_key': env('TIKTOK_CLIENT_KEY'), 'client_secret': env('TIKTOK_CLIENT_SECRET'),
        'grant_type': 'refresh_token', 'refresh_token': tok['refresh_token']}, form=True)
    if 'access_token' not in res:
        raise SystemExit(f'トークン更新に失敗しました。もう一度ログインが必要かもしれません: {res}')
    save_token(res)
    return res['access_token']


def send_photo_draft(token, urls, title, description):
    """写真カルーセルを TikTok の受信箱（下書き）に送る"""
    body = {
        'post_info': {'title': title[:90], 'description': description[:4000]},
        'source_info': {'source': 'PULL_FROM_URL', 'photo_cover_index': 0, 'photo_images': urls},
        'post_mode': 'MEDIA_UPLOAD',
        'media_type': 'PHOTO',
    }
    res = _req('POST', '/v2/post/publish/content/init/', body, token=token)
    if res.get('error', {}).get('code') != 'ok':
        raise RuntimeError(json.dumps(res, ensure_ascii=False))
    return res['data']['publish_id']


def fetch_status(token, publish_id):
    return _req('POST', '/v2/post/publish/status/fetch/', {'publish_id': publish_id}, token=token)
