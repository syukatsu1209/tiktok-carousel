"""初回ログイン：認可ページで表示されたコードをトークンに交換して保存する
usage: python tiktok/exchange_code.py <code> <redirect_uri>
"""
import sys
from tiktok_api import exchange_code

if __name__ == '__main__':
    code, redirect_uri = sys.argv[1].strip(), sys.argv[2].strip()
    res = exchange_code(code, redirect_uri)
    print('連携できました。scope =', res.get('scope'), '/ open_id =', res.get('open_id', '')[:6] + '…')
