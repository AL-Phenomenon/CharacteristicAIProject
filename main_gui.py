"""
Chat AI - GUIモード エントリーポイント
ウィンドウでチャットできるGUIインターフェース
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.memory.rag_system import RAGMemorySystem
from src.character.character import Character
from src.bot.chatbot import ChatBot
from src.bot.gui_interface import run_gui


def load_environment():
    """環境変数をロード"""
    load_dotenv()
    
    # LLMプロバイダーの選択
    llm_provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    
    # プロバイダーに応じたAPIキーチェック
    if llm_provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("エラー: ANTHROPIC_API_KEY環境変数が設定されていません")
            print("\n.envファイルを作成し、以下を設定してください:")
            print("ANTHROPIC_API_KEY=your_api_key_here")
            sys.exit(1)
        base_url = None
    
    elif llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "not-needed")
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
        print(f"OpenAI互換API使用: {base_url}")
    
    else:
        print(f"エラー: 未知のLLMプロバイダー: {llm_provider}")
        print("LLM_PROVIDERは 'anthropic' または 'openai' を指定してください")
        sys.exit(1)
    
    return {
        "llm_provider": llm_provider,
        "api_key": api_key,
        "base_url": base_url,
        "model_name": os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"),
        "max_tokens": int(os.getenv("MAX_TOKENS", "1000")),
        "compact_prompt": os.getenv("COMPACT_PROMPT", "true").lower() == "true",
        "chroma_db_path": os.getenv("CHROMA_DB_PATH", "./data/chroma_db"),
        "collection_name": os.getenv("COLLECTION_NAME", "chat_memory"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"),
        "max_memory_results": int(os.getenv("MAX_MEMORY_RESULTS", "5")),
        "short_term_memory_size": int(os.getenv("SHORT_TERM_MEMORY_SIZE", "5")),
    }


def initialize_system(config: dict):
    """システムを初期化"""
    print("=" * 60)
    print(" Chat AI HAL - 初期化中（GUIモード）...")
    print("=" * 60)
    
    # 1. 記憶システムの初期化
    print("\n[1/3] 記憶システムを初期化中...")
    memory_system = RAGMemorySystem(
        db_path=config["chroma_db_path"],
        collection_name=config["collection_name"],
        embedding_model=config["embedding_model"]
    )
    
    # 2. キャラクターのロード
    print("\n[2/3] キャラクター設定を読み込み中...")
    character_config_path = project_root / "config" / "character_config.json"
    
    if character_config_path.exists():
        character = Character.from_file(str(character_config_path))
        print(f"✓ キャラクター '{character.name}' をロードしました")
    else:
        print("⚠️  キャラクター設定ファイルが見つかりません")
        print(f"   {character_config_path}")
        print("   デフォルトのキャラクターを使用します")
        character = Character.create_default()
    
    # 3. チャットボットの初期化
    print("\n[3/3] チャットボットを初期化中...")
    chatbot = ChatBot(
        character=character,
        memory_system=memory_system,
        llm_provider=config["llm_provider"],
        api_key=config["api_key"],
        base_url=config.get("base_url"),
        model_name=config["model_name"],
        max_tokens=config["max_tokens"],
        short_term_memory_size=config["short_term_memory_size"],
        max_memory_results=config["max_memory_results"],
        compact_prompt=config["compact_prompt"]
    )
    
    prompt_mode = "簡潔版" if config["compact_prompt"] else "詳細版"
    print(f"✓ システムプロンプト: {prompt_mode}")
    print("\n✓ 初期化完了！")
    print("GUIウィンドウを起動します...\n")
    
    return chatbot


def main():
    """メイン関数"""
    try:
        # 環境変数のロード
        config = load_environment()
        
        # システムの初期化
        chatbot = initialize_system(config)
        
        # GUIインターフェースの起動
        print("=" * 60)
        run_gui(chatbot)
        
    except KeyboardInterrupt:
        print("\n\nプログラムを終了します。")
        sys.exit(0)
    
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()