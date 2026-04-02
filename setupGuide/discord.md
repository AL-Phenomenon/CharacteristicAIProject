# Discord Bot セットアップガイド

HARKAをDiscord Botとして動かす方法を説明します。

## 📋 必要なもの

- Discordアカウント
- 管理権限のあるDiscordサーバー（テスト用）
- Python環境（既にセットアップ済み）

---

## ステップ1: Discord Botの作成

### 1. Discord Developer Portalにアクセス

[Discord Developer Portal](https://discord.com/developers/applications)を開く

### 2. 新しいアプリケーションを作成

1. 「New Application」をクリック
2. 名前に「HARKA」と入力
3. 「Create」をクリック

### 3. Botを追加

1. 左メニューから「Bot」をクリック
2. 「Add Bot」→「Yes, do it!」をクリック
3. Bot名を「HARKA」に変更（任意）

### 4. トークンを取得

1. 「Token」セクションで「Reset Token」をクリック
2. 表示されたトークンを**コピーして保存**
   
   ⚠️ **重要**: このトークンは二度と表示されません！安全な場所に保存してください

### 5. 必須設定を有効化

「Bot」ページで以下をONにする：

- ✅ **MESSAGE CONTENT INTENT**（必須！）
- ✅ PRESENCE INTENT
- ✅ SERVER MEMBERS INTENT

「Save Changes」をクリック

### 6. 招待リンクを生成

1. 左メニューから「OAuth2」→「URL Generator」
2. **SCOPES**:
   - ✅ `bot`
   
3. **BOT PERMISSIONS**:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Read Message History
   - ✅ Embed Links（埋め込み表示用）
   - ✅ Attach Files（将来の拡張用）

4. 下部の「GENERATED URL」をコピー

### 7. Botをサーバーに招待

1. コピーしたURLをブラウザで開く
2. Botを追加したいサーバーを選択
3. 「認証」をクリック

---

## ステップ2: 環境設定

### 1. discord.pyをインストール

```bash
pip install discord.py
```

### 2. .envファイルを編集

`.env`ファイルに以下を追加：

```bash
# インターフェースモードをdiscordに変更
INTERFACE_MODE=discord

# Discord Botトークンを設定
DISCORD_BOT_TOKEN=あなたのトークンをここに貼り付け

# ステータスメッセージ（任意）
DISCORD_STATUS_MESSAGE=HARKAと会話中
```

完全な.envの例：

```bash
# LLM設定
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://localhost:1234/v1
MODEL_NAME=local-model
MAX_TOKENS=1000
COMPACT_PROMPT=true

# インターフェース設定
INTERFACE_MODE=discord

# Discord設定
DISCORD_BOT_TOKEN=あなたのトークン
DISCORD_STATUS_MESSAGE=HARKAと会話中

# 記憶設定
MAX_MEMORY_RESULTS=5
SHORT_TERM_MEMORY_SIZE=5
CHROMA_DB_PATH=./data/chroma_db
COLLECTION_NAME=chat_memory
EMBEDDING_MODEL=intfloat/multilingual-e5-base
```

---

## ステップ3: 起動

### 1. LM Studioを起動

LM Studioでモデルをロードし、サーバーを起動してください。

### 2. Botを起動

```bash
python main.py
```

成功すると以下のように表示されます：

```
====================================================
  HARKA - 初期化中（Discord Botモード）...
====================================================

Discord Bot 'HARKA' が起動しました
====================================================
Bot名: HARKA
Bot ID: 123456789...
接続サーバー数: 1
====================================================
```

---

## 使い方

### 会話の仕方

HARKAと会話する方法は3つあります：

#### 1. メンション

```
@HARKA こんにちは！
```

#### 2. リプライ

HARKAのメッセージに返信する

#### 3. DM（ダイレクトメッセージ）

HARKAに直接メッセージを送る

### コマンド一覧

| コマンド | 説明 |
|---------|------|
| `!ping` | 応答速度を確認 |
| `!stats` | あなたの統計情報を表示 |
| `!clear` | 会話履歴をクリア |
| `!help` | ヘルプを表示 |

---

## 機能

### ✅ 実装済み

- メンション、リプライ、DMで会話
- RAG記憶システム（ユーザーごと）
- 長文自動分割（2000文字制限対応）
- タイピングインジケーター表示
- 統計情報の表示
- 会話履歴のクリア

### 🔜 今後の拡張予定

- スラッシュコマンド対応
- 画像認識
- 音声チャンネル対応
- サーバーごとの設定

---

## トラブルシューティング

### Botが反応しない

**原因**: MESSAGE CONTENT INTENTが有効になっていない

**解決方法**:
1. Discord Developer Portalの「Bot」ページ
2. MESSAGE CONTENT INTENTをONにする
3. Save Changes
4. Botを再起動

### トークンエラー

```
❌ エラー: Discord Botトークンが無効です
```

**解決方法**:
1. `.env`のDISCORD_BOT_TOKENを確認
2. トークンが正しくコピーされているか確認
3. 余分なスペースがないか確認

### 応答が遅い

**原因**: LM Studioのモデルが重い、またはGPU使用率が高い

**解決方法**:
1. より小さいモデルに変更
2. GPU Offloadを減らす
3. `COMPACT_PROMPT=true`に設定

### 長文が途切れる

Discordの2000文字制限により、長文は自動的に分割されて送信されます。これは正常な動作です。

---

## セキュリティ注意事項

⚠️ **重要**: Botトークンは絶対に公開しないでください

- GitHubにプッシュしない（.gitignoreで除外済み）
- スクリーンショットに含めない
- 他人に教えない

もしトークンが漏洩した場合：
1. Discord Developer Portalで「Regenerate」
2. 新しいトークンを`.env`に設定
3. Botを再起動

---

## 補足

### 複数サーバーで使用

同じBotを複数のサーバーに招待できます。ユーザーIDはDiscord全体で一意なので、どのサーバーでも同じ記憶が共有されます。

### サーバーごとに記憶を分けたい場合

将来の拡張で対応予定です。現在はユーザー単位で記憶を管理しています。

---

質問があれば、GitHubのIssueで気軽に聞いてください！