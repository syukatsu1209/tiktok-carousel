"""連携状況の確認：連携しているTikTokアカウント名と、最新の下書き送信の状態を表示する
usage: python tiktok/check.py
"""
import json, pathlib
from tiktok_api import fresh_token, fetch_status, _req

REPO = pathlib.Path(__file__).resolve().parents[1]

token = fresh_token()
me = _req('GET', '/v2/user/info/?fields=open_id,display_name,avatar_url', token=token)
user = me.get('data', {}).get('user', {})
print('連携中のアカウント表示名:', user.get('display_name'))
print('user/info error:', me.get('error', {}).get('code'), me.get('error', {}).get('message'))

sts = sorted((REPO / 'status').glob('*.json'))
if sts:
    s = json.loads(sts[-1].read_text(encoding='utf-8'))
    if s.get('publish_id'):
        r = fetch_status(token, s['publish_id'])
        print('最新の送信:', s['post_id'], s['publish_id'])
        print('TikTokの現在の状態:', json.dumps(r, ensure_ascii=False))
