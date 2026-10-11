"""公開済みの画像URLを TikTok の下書き（受信箱）に送り、結果を status/<post_id>.json に残す
usage: python tiktok/post_draft.py <post_id> <base_url>
  base_url 例: https://<ユーザー名>.github.io/<リポジトリ名>/media/
"""
import json, pathlib, sys, time, urllib.request
from tiktok_api import fresh_token, send_photo_draft, fetch_status

REPO = pathlib.Path(__file__).resolve().parents[1]


def wait_public(urls, timeout=600):
    """GitHub Pages に画像が出るまで待つ（リダイレクトなしの200が必要）"""
    end = time.time() + timeout
    for u in urls:
        while True:
            try:
                req = urllib.request.Request(u, method='HEAD', headers={'User-Agent': 'tiktok-carousel'})
                with urllib.request.urlopen(req, timeout=20) as r:
                    if r.status == 200 and r.geturl() == u:
                        break
            except Exception:
                pass
            if time.time() > end:
                raise SystemExit(f'画像が公開されませんでした: {u}')
            time.sleep(10)


def main(post_id, base_url):
    post = json.loads((REPO / 'carousel/posts' / f'{post_id}.json').read_text(encoding='utf-8'))
    n = len(post['slides'])
    base = base_url.rstrip('/') + f'/{post_id}/'
    urls = [f'{base}{i:02d}.jpg' for i in range(1, n + 1)]
    wait_public(urls)

    caption = post.get('caption', '')
    title = caption.splitlines()[0] if caption else post_id
    status = {'post_id': post_id, 'pages': n, 'urls': urls, 'sent_at': time.strftime('%Y-%m-%d %H:%M:%S')}
    try:
        token = fresh_token()
        pid = send_photo_draft(token, urls, title, caption)
        status['publish_id'] = pid
        for _ in range(18):  # 最大3分ほど状態を確認
            time.sleep(10)
            st = fetch_status(token, pid)
            s = st.get('data', {}).get('status')
            status['tiktok_status'] = s
            if s in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE', 'FAILED'):
                status['fail_reason'] = st.get('data', {}).get('fail_reason')
                break
        status['result'] = 'ok' if status.get('tiktok_status') in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE') else 'check'
    except (RuntimeError, SystemExit) as e:
        status['result'] = 'error'
        status['error'] = str(e)
    out = REPO / 'status' / f'{post_id}.json'
    out.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(status, ensure_ascii=False, indent=2))
    if status['result'] == 'error':
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
