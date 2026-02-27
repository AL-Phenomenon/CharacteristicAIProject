# Neuro Chat AI

RAG（検索拡張生成）記憶システムを備えた、キャラクター性のあるAIチャットボット

Neuro-samaのような個性的なAIキャラクターを作成できるフレームワークです。

## ✨ 特徴

- 🧠 **長期記憶システム**: RAGでユーザーとの過去の会話を記憶
- 👤 **カスタマイズ可能なキャラクター**: JSON設定で性格・話し方を自由に変更
- 💾 **ユーザー別記憶管理**: 各ユーザーとの関係性を個別に記録
- 🔄 **二層記憶構造**: 短期記憶（セッション）+ 長期記憶（永続化）
- 🎯 **関連性ベースの記憶検索**: 現在の話題に関連する過去の会話を自動取得
- 🖥️ **2つのインターフェース**: CLI（コマンドライン）とGUI（ウィンドウ）
- 🚀 **拡張可能な設計**: Discord Bot、音声、ビジュアルへの拡張が容易

## 📋 システム要件

- Python 3.10以上
- 4GB以上のRAM（エンベディングモデル用）
- **Claude API使用時**: Anthropic APIキー
- **LM Studio使用時**: GPU推奨（VRAM 8GB以上）、またはCPU

## 🔌 LLMプロバイダーの選択

このプロジェクトは2つのLLMプロバイダーに対応しています：

### オプション1: Claude API
- ✅ 高品質な応答
- ✅ セットアップが簡単
- ❌ 従量課金（月額500-2000円程度）

### オプション2: LM Studio
- ✅ 完全無料
- ✅ プライバシー保護（データがローカルに保存）
- ✅ オフライン動作
- ❌ GPUが必要（推奨）
- ❌ セットアップがやや複雑

**詳しいLM Studioのセットアップ方法は [`LM_STUDIO_SETUP.md`](LM_STUDIO_SETUP.md) を参照してください。**

## 🚀 クイックスタート

### 方法A: 自動セットアップ（推奨）

#### venvなし版（シンプル）

**Linux/Mac:**
```bash
chmod +x install_simple.sh
./install_simple.sh
python3 main.py
```

**Windows:**
```cmd
install_simple.bat
python main.py
```

#### venv使用版

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
source venv/bin/activate  # 仮想環境を有効化
# 表示された指示に従ってパッケージをインストール
python main.py
```

**Windows:**
```cmd
install.bat
python main.py
```

### 方法B: 手動セットアップ（venvなし）

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd neuro-chat-ai
```

### 2. 依存関係のインストール

**基本パッケージ:**
```bash
pip install chromadb sentence-transformers torch python-dotenv pydantic
```

**LLMライブラリ（使用するものを選択）:**
```bash
# LM Studio使用の場合
pip install openai

# Claude API使用の場合
pip install anthropic

# 両方使いたい場合
pip install openai anthropic
```

### 3. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
# --- LM Studio使用の場合 ---
# LLM_PROVIDER=openai
# OPENAI_BASE_URL=http://localhost:1234/v1

# --- Claude API使用の場合 ---
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
```

### 4. 実行

```bash
python main.py  # または python3 main.py
```

---

### 方法C: 手動セットアップ（venv使用）

<details>
<summary>クリックして展開</summary>

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd neuro-chat-ai
```

### 2. 仮想環境の作成と有効化

```bash
# Linux/Mac
python -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. 依存関係のインストール

**まず、基本パッケージをインストール:**
```bash
pip install -r requirements.txt
```

**次に、使用するLLMプロバイダーに応じてインストール:**

```bash
# Claude API使用の場合
pip install anthropic

# LM Studio使用の場合
pip install openai

# 両方使いたい場合
pip install anthropic openai
```

### 4. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
# --- Claude API使用の場合 ---
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# --- LM Studio使用の場合 ---
# LLM_PROVIDER=openai
# OPENAI_BASE_URL=http://localhost:1234/v1
```

**LM Studio使用時の追加設定**: [`LM_STUDIO_SETUP.md`](LM_STUDIO_SETUP.md)を参照

### 5. 実行

**CLIモード（コマンドライン）:**
```bash
python main.py
```

**GUIモード（ウィンドウ）:**
```bash
python main_gui.py
```

</details>

## 📁 プロジェクト構造

```
neuro-chat-ai/
├── README.md                    # このファイル
├── requirements.txt             # 依存関係
├── .env.example                 # 環境変数テンプレート
├── .env                         # 環境変数（要作成、gitignore済み）
├── .gitignore                   # Git除外設定
├── main.py                      # CLIモード エントリーポイント
├── main_gui.py                  # GUIモード エントリーポイント
│
├── config/                      # 設定ファイル
│   └── character_config.json    # キャラクター設定
│
├── src/                         # ソースコード
│   ├── __init__.py
│   │
│   ├── memory/                  # 記憶システム
│   │   ├── __init__.py
│   │   └── rag_system.py        # RAG実装
│   │
│   ├── character/               # キャラクター管理
│   │   ├── __init__.py
│   │   ├── character.py         # キャラクター定義
│   │   └── prompt_builder.py   # プロンプト構築
│   │
│   └── bot/                     # ボット本体
│       ├── __init__.py
│       ├── chatbot.py           # チャットボットロジック
│       ├── cli_interface.py    # CLIインターフェース
│       └── gui_interface.py    # GUIインターフェース
│
└── data/                        # データ保存（自動生成）
    └── chroma_db/               # ベクトルDB
```

## 🎮 使い方

### CLIモード（コマンドライン）

```bash
python main.py
```

#### 基本的な会話

```
あなた: こんにちは！
ネウロちゃん: こんにちは！初めまして、ネウロです...
```

#### 利用可能なコマンド

| コマンド | 説明 |
|---------|------|
| `exit`, `quit`, `bye` | チャット終了 |
| `clear`, `reset` | 短期記憶をクリア（長期記憶は保持） |
| `stats`, `info` | 統計情報を表示 |
| `history`, `recent` | 最近の会話を表示 |
| `help`, `h`, `?` | ヘルプを表示 |
| `delete`, `purge` | すべてのデータを削除（要確認） |

---

### GUIモード（ウィンドウ）

```bash
python main_gui.py
```

#### 特徴

- 💬 **LINEのようなチャット画面**: 吹き出し形式で会話を表示
- 📜 **会話履歴**: 過去の会話が自動でスクロール
- ⚡ **非同期処理**: AIが考え中でもUIがフリーズしない
- ⌨️ **ショートカット**: Ctrl+Enter で送信

#### 使い方

1. ウィンドウが開いたら、下の入力ボックスにメッセージを入力
2. 「送信」ボタンをクリック、またはCtrl+Enter
3. AIの応答が吹き出しで表示されます

![GUI Screenshot](docs/gui_screenshot.png)
*GUIモードのイメージ*

## ⚙️ カスタマイズ

### キャラクター設定の変更

`config/character_config.json` を編集:

```json
{
  "name": "あなたのキャラクター名",
  "personality": "性格の説明",
  "speech_style": {
    "first_person": ["僕", "俺"],
    "sentence_endings": ["だぜ", "だな"],
    "common_phrases": ["よろしくな", "まかせろ"]
  },
  ...
}
```

### 環境変数の調整

`.env` ファイルで以下を調整可能:

```bash
# より多くの記憶を参照（精度向上、コスト増）
MAX_MEMORY_RESULTS=10

# より長い会話履歴を保持
SHORT_TERM_MEMORY_SIZE=10

# より高性能なモデルを使用
MODEL_NAME=claude-opus-4-20250514
```

## 🔧 技術スタック

- **LLM**: Claude API (Anthropic) / ローカルLLM (LM Studio)
- **ベクトルDB**: ChromaDB
- **エンベディング**: Sentence Transformers (multilingual-e5-base)
- **言語**: Python 3.10+
- **API互換**: OpenAI互換APIサポート

## 📊 コスト見積もり

### Claude API使用時

Claude Sonnet 4の料金体系:
- 入力: $3 / 100万トークン
- 出力: $15 / 100万トークン

想定コスト（月1000メッセージ）:
- **月額約500-2000円**

コスト削減のヒント:
- `MAX_MEMORY_RESULTS` を減らす
- `MAX_TOKENS` を制限する
- 短い応答を推奨するようプロンプト調整

### LM Studio使用時

- **月額: 0円（完全無料）**
- 初期コスト: なし（LM Studioは無料）
- 電気代のみ（GPU使用時、月数百円程度）

## 🚀 今後の拡張案

### Phase 1: 現在地（✅ 完了）
- ✅ RAG記憶システム
- ✅ キャラクター性のあるチャット
- ✅ CLI インターフェース
- ✅ GUI インターフェース（LINEライク）

### Phase 2: GUI機能拡張
- [ ] メッセージ検索機能
- [ ] 会話履歴のエクスポート
- [ ] テーマ切り替え（ダーク/ライトモード）
- [ ] メッセージの編集・削除
- [ ] 画像添付機能

### Phase 3: 機能拡張
- [ ] Discord Bot化
- [ ] Web インターフェース
- [ ] マルチユーザー管理
- [ ] 音声入力・出力

### Phase 4: 高度な機能
- [ ] 音声合成（TTS）
- [ ] 感情システム
- [ ] 記憶の要約・整理
- [ ] 画像認識（マルチモーダル）

### Phase 5: ビジュアル化
- [ ] Live2D アバター連携
- [ ] VTube Studio 統合
- [ ] 配信システム

## 🤝 コントリビューション

プルリクエスト大歓迎です！

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

MIT License

## 🙏 謝辞

- [Neuro-sama](https://www.twitch.tv/vedal987) - インスピレーション元
- Anthropic - Claude API
- ChromaDB - ベクトルデータベース

## ⚠️ 免責事項

このプロジェクトは教育目的で作成されています。商用利用の場合は適切なライセンスと利用規約を確認してください。

---

## 🔧 トラブルシューティング

### ImportError: No module named 'anthropic' / 'openai'

**原因**: 必要なLLMライブラリがインストールされていません

**解決方法**:
```bash
# 必要なライブラリをインストール
pip install anthropic  # Claude API使用時
pip install openai     # LM Studio使用時
```

### venv関連のエラー

**venvを使いたくない場合**:
- `install_simple.sh` / `install_simple.bat` を使用
- または手動で `pip install` を直接実行

**venvを使う場合**:
```bash
# 仮想環境を有効化
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# (venv) がプロンプトに表示されることを確認
```

### Windows PowerShellで実行ポリシーエラー

```powershell
# 実行ポリシーを変更
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# その後、再度有効化
venv\Scripts\Activate.ps1
```

### 権限エラー (Permission Denied)

**Linuxの場合**:
```bash
# ユーザーディレクトリにインストール
pip install --user chromadb sentence-transformers torch python-dotenv pydantic openai
```

**または sudo を使う（非推奨）**:
```bash
sudo pip install ...
```

### エンベディングモデルのダウンロードが遅い

初回起動時、約500MBのモデルがダウンロードされます。インターネット接続を確認してください。

### LM Studioに接続できない

1. LM Studioのサーバーが起動しているか確認
2. `.env`の`OPENAI_BASE_URL`が`http://localhost:1234/v1`になっているか確認
3. ファイアウォールでポート1234が開いているか確認

### コンテキスト長エラー（KVキャッシュエラー）

```
Error: the last position stored in the memory module of the context...
```

このエラーが出た場合は、**[CONTEXT_ERROR_FIX.md](CONTEXT_ERROR_FIX.md)** を参照してください。

**クイックフィックス**:
1. LM Studioのサーバーを再起動
2. **Qwen3-VLを使わない**（通常版のQwen 2.5 Instructに変更）
3. `.env`で`MAX_TOKENS=500`、`MAX_MEMORY_RESULTS=2`に設定
4. LM Studioで「Keep Entire Prompt」をOFFに設定

### GUIが起動しない・表示がおかしい

**tkinterがインストールされていない場合**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS (Homebrewでインストールしたpythonの場合)
brew install python-tk

# Windows
# 通常は標準で含まれているが、なければPythonを再インストール
```

**ウィンドウが真っ白/表示がおかしい場合**:
- ディスプレイスケーリングを100%に設定してみる
- グラフィックドライバーを最新に更新

### GUIで日本語が文字化けする

```bash
# システムフォントを確認
# Windowsの場合は通常問題なし
# Linuxの場合は日本語フォントをインストール
sudo apt-get install fonts-noto-cjk
```