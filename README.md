# TikTok カルーセル自動下書きシステム

毎朝、就活インターン情報のカルーセル（1080×1440）を自動で作り、TikTok の受信箱に下書きとして届けます。
あなたがやるのは **週1回のリサーチ記入** と **毎朝の投稿ボタン** だけです。

```
Claude（毎朝 6:40）          GitHub Actions（自動）                    あなた
リサーチシートを読む   →    背景写真を取得・スモーク              →   TikTokの受信箱を開く
企業を調べる（出典付き）     スライドを作る（1080×1440）                音源をつけて投稿
specs/今日.json を保存       画像を公開URLに置く（GitHub Pages）
                             TikTokの下書きに送る
```

---

## セットアップ（最初の1回だけ・合計30〜40分）

以下の `<ユーザー名>` はあなたの GitHub ユーザー名です。

### 1. GitHub（5分）
1. https://github.com でアカウントを作る
2. 右上「＋」→「New repository」
   - Repository name：`tiktok-carousel`
   - **Public** を選ぶ（無料で画像を公開URLに置くため。中に秘密の情報は入りません）
   - 「Add a README」などのチェックは**すべて外す**
3. 作ったリポジトリ名を Claude に伝える → Claude がコード一式を入れます
4. リポジトリの「Settings」→「Pages」→ Source を **GitHub Actions** にする

### 2. Pexels（3分・背景写真用）
1. https://www.pexels.com/api/ で無料登録し、API キーをコピー
2. GitHub リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」
   - Name：`PEXELS_API_KEY` / Secret：コピーしたキー

> 自分の写真を使いたいときは `carousel/bg/user/` に `night_1.jpg`（夜景）や `day_1.jpg`（青空）の名前で入れると、そちらが優先されます。

### 3. TikTok 開発者アプリ（15〜20分）
1. https://developers.tiktok.com に TikTok アカウントでログイン →「Manage apps」→「Connect an app」（個人で登録）
2. **App details** に入力
   | 項目 | 入力する値 |
   |---|---|
   | App name | Carousel Drafter（好きな名前でOK） |
   | Category | Utilities など |
   | Description | `Personal tool that sends photo carousels about student internships to my own TikTok inbox as drafts.` |
   | Terms of Service URL | `https://<ユーザー名>.github.io/tiktok-carousel/terms.html` |
   | Privacy Policy URL | `https://<ユーザー名>.github.io/tiktok-carousel/privacy.html` |
   | Platforms | **Web**（Website URL：`https://<ユーザー名>.github.io/tiktok-carousel/`） |
3. **Add products** で次の2つを追加
   - **Login Kit**：Redirect URI に `https://<ユーザー名>.github.io/tiktok-carousel/auth/`（最後の `/` まで）
   - **Content Posting API**：Direct Post は**オフのまま**でOK（下書き送信だけ使います）
4. **Scopes**：`user.info.basic` と `video.upload` の2つだけ
5. **URL properties**（画像URLの所有権確認）
   1. 「URL prefix」に `https://<ユーザー名>.github.io/tiktok-carousel/` を追加 →「Verify」
   2. 表示された確認用ファイルをダウンロード
   3. GitHub の「Actions」→「③ TikTokの所有権確認ファイルを置く」→「Run workflow」
      - ファイル名と、ファイルの中身（テキスト）をそのまま貼り付けて実行
   4. 1〜2分待って、TikTok 側で「Verify」を押す
6. **Sandbox** を作り、「Target users」に自分の TikTok アカウントを追加（審査前のテスト用）
7. Sandbox（審査後は本番）の **Client key** と **Client secret** を GitHub Secrets に登録
   - `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET`
   - ⚠️ この2つはチャットには貼らないでください

### 4. TikTok と連携（3分）
1. GitHub「Actions」→「サイトを更新」→「Run workflow」（キーをサイトに反映）
2. `https://<ユーザー名>.github.io/tiktok-carousel/auth/` を開き「TikTokでログイン」→ 許可
3. 表示されたコードをコピー → GitHub「Actions」→「② TikTokと連携」に貼り付けて実行（数分以内に）

### 5. テスト送信（5分）
1. GitHub「Actions」→「① 投稿を作って下書きに送る」→「Run workflow」
2. 5分ほどで TikTok アプリの受信箱に通知が届けば成功
3. 結果は `status/` フォルダにも記録されます。画像は各実行の「Artifacts」からダウンロードできます

### 6. リサーチシートをドライブに置く（2分）
1. Claude から受け取った `リサーチシート.xlsx` を Google ドライブにアップロード
2. 開いて「ファイル」→「Google スプレッドシートとして保存」
3. 名前を **TikTokリサーチシート** にする

### 7. Claude に「準備できた」と伝える
毎朝 6:40 に動くスケジュールタスクを Claude が設定します。

---

## TikTok の審査について
- 審査前のアプリから送った投稿は**非公開扱い**になります。テスト中はアカウントを非公開にするか、早めに審査を申請してください（目安1〜2週間）。
- 申請時は、ログイン→下書き送信→受信箱で投稿、の流れを録画したデモ動画が必要です。説明文の例：

> This is a single-user tool. The operator logs in with Login Kit (user.info.basic, video.upload), and the tool sends photo carousels created by the operator to the operator's own TikTok inbox using the Content Posting API in MEDIA_UPLOAD mode. The operator reviews and publishes each post manually in the TikTok app. No other users' data is accessed.

## 制限
- 未投稿の下書きは 24 時間で 5 件まで。受信箱にためすぎないでください
- TikTok アプリは 31.8 以上が必要
- 365 日間まったく使わないと再ログインが必要（手順4をもう一度）

## 中身
| 場所 | 役割 |
|---|---|
| `carousel/specs/` | 毎日の投稿データ（Claude が書く） |
| `carousel/compose.py` | ページ数・構成を組み立てる |
| `carousel/render.py` | スライドを 1080×1440 で書き出す |
| `carousel/bg_fetch.py` | 背景写真の取得（手持ち写真 → Pexels → 仮背景の順） |
| `tiktok/` | TikTok のログインと下書き送信 |
| `docs/` | 公開サイト（連携ページ・プライバシーポリシー・利用規約） |
| `status/` | 下書き送信の結果 |
| `AUTOMATION.md` | 毎朝の Claude への指示書 |
