# CharacteristicAIProject
かわいいAIアシスタントを作ろう

 Neuro Chat AI

RAG（検索拡張生成）記憶システムを備えた、キャラクター性のあるAIチャットボット

## 特徴

- 🧠 **長期記憶**: RAGシステムで過去の会話を記憶
- 👤 **キャラクター性**: カスタマイズ可能な性格と話し方
- 💾 **ユーザー別記憶**: 各ユーザーとの関係性を個別管理
- 🔄 **短期・長期記憶**: セッション記憶と永続記憶の二層構造

## セットアップ

### 1. リポジトリのクローン

\`\`\`bash
git clone <repository-url>
cd neuro-chat-ai
\`\`\`

### 2. 仮想環境の作成

\`\`\`bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
\`\`\`

### 3. 依存関係のインストール

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 4. 環境変数の設定

\`\`\`bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
\`\`\`

### 5. 実行

\`\`\`bash
python main.py
\`\`\`

## プロジェクト構造

\`\`\`
neuro-chat-ai/
├── config/              # 設定ファイル
│   └── character_config.json
├── src/                 # ソースコード
│   ├── memory/          # RAG記憶システム
│   ├── character/       # キャラクター定義
│   └── bot/             # ボット本体
├── data/                # データ保存
└── main.py              # エントリーポイント
\`\`\`

## キャラクターのカスタマイズ

\`config/character_config.json\` を編集してキャラクターを変更できます。

## コマンド

- \`exit\` / \`quit\`: チャット終了
- \`clear\`: 短期記憶をクリア（長期記憶は保持）

## ライセンス

MIT
"""