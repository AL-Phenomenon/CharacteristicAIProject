"""
PDF RAG管理ツール
PDFファイルのインポート・一覧表示・削除を管理する

使用方法:
    # PDFフォルダを一括インポート
    python add_pdf.py add ../docs --name 研究資料_2026

    # 単一PDFファイルをインポート
    python add_pdf.py add ../docs/論文.pdf --name 論文A

    # 登録済みPDFコレクション一覧
    python add_pdf.py list

    # PDFコレクション削除
    python add_pdf.py delete 研究資料_2026
"""

import os
import sys
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# コレクション名のプレフィックス（PDF専用）
PDF_COLLECTION_PREFIX = "pdf_"

# 保護対象のコレクション（絶対に削除しない）
PROTECTED_COLLECTIONS = {"chat_memory"}


def get_chroma_client(db_path: str):
    """ChromaDBクライアントを取得"""
    import chromadb
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path)


def get_embedding_model(model_name: str):
    """エンベディングモデルをロード"""
    from sentence_transformers import SentenceTransformer
    print(f"エンベディングモデルをロード中: {model_name}")
    return SentenceTransformer(model_name)


def cmd_add(args):
    """PDFをインポートしてRAGデータに追加"""
    from src.memory.pdf_loader import PDFLoader

    source_path = Path(args.path).resolve()
    collection_name = f"{PDF_COLLECTION_PREFIX}{args.name}"

    print("=" * 60)
    print(f"  PDF RAGインポート")
    print(f"  コレクション名: {collection_name}")
    print("=" * 60)

    # 1. PDFの読み込み
    print(f"\n[1/3] PDFを読み込み中: {source_path}")

    if source_path.is_dir():
        all_chunks = PDFLoader.load_pdf_folder(str(source_path))
    elif source_path.is_file() and source_path.suffix.lower() == '.pdf':
        chunks = PDFLoader.extract_text_from_pdf(str(source_path))
        all_chunks = {source_path.name: chunks}
    else:
        print(f"エラー: 有効なPDFファイルまたはフォルダではありません: {source_path}")
        sys.exit(1)

    if not all_chunks:
        print("エラー: インポートするPDFデータがありません")
        sys.exit(1)

    total_chunks = sum(len(chunks) for chunks in all_chunks.values())
    print(f"\n  合計: {len(all_chunks)}ファイル, {total_chunks}ページ")

    # 2. エンベディングモデルのロード
    load_dotenv()
    embedding_model_name = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
    db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")

    print(f"\n[2/3] エンベディングの生成中...")
    embedding_model = get_embedding_model(embedding_model_name)

    # 3. ChromaDBに保存
    print(f"\n[3/3] ChromaDBに保存中...")
    client = get_chroma_client(db_path)

    # コレクションの作成（既存の場合は上書き確認）
    existing_collections = [c.name for c in client.list_collections()]
    if collection_name in existing_collections:
        print(f"\n⚠️  コレクション '{collection_name}' は既に存在します。")
        response = input("上書きしますか？ (y/N): ").strip().lower()
        if response != 'y':
            print("中止しました。")
            sys.exit(0)
        client.delete_collection(collection_name)

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "description": f"PDF資料: {args.name}",
            "source_type": "pdf",
        }
    )

    # チャンクを追加
    imported_count = 0
    for filename, chunks in all_chunks.items():
        for i, chunk in enumerate(chunks):
            doc_id = f"pdf_{args.name}_{filename}_page{chunk.metadata['page_number']}"

            # エンベディング生成
            embedding = embedding_model.encode(chunk.text).tolist()

            # メタデータにコレクション識別情報を追加
            metadata = {
                **chunk.metadata,
                "collection_label": collection_name,
                "source_type": "pdf",
                "import_name": args.name,
            }

            collection.add(
                embeddings=[embedding],
                documents=[chunk.text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            imported_count += 1

        print(f"  ✓ {filename}: {len(chunks)}ページ保存完了")

    print(f"\n{'=' * 60}")
    print(f"  インポート完了！")
    print(f"  コレクション: {collection_name}")
    print(f"  保存件数: {imported_count}ページ")
    print(f"{'=' * 60}")
    print(f"\n削除する場合: python add_pdf.py delete {args.name}")


def cmd_list(args):
    """登録済みPDFコレクションを一覧表示"""
    load_dotenv()
    db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")

    client = get_chroma_client(db_path)
    collections = client.list_collections()

    pdf_collections = [
        c for c in collections
        if c.name.startswith(PDF_COLLECTION_PREFIX)
    ]

    print("=" * 60)
    print("  登録済みPDFコレクション一覧")
    print("=" * 60)

    if not pdf_collections:
        print("\n  PDFコレクションはありません。")
        print(f"\n  インポート方法: python add_pdf.py add <フォルダ/ファイルパス> --name <名前>")
        return

    for col in pdf_collections:
        display_name = col.name[len(PDF_COLLECTION_PREFIX):]  # pdf_ プレフィックスを除去
        count = col.count()
        description = col.metadata.get("description", "説明なし") if col.metadata else "説明なし"
        print(f"\n  📄 {display_name}")
        print(f"     コレクション名: {col.name}")
        print(f"     説明: {description}")
        print(f"     データ件数: {count}件")

    print(f"\n{'=' * 60}")
    print(f"  合計: {len(pdf_collections)}コレクション")

    # 保護コレクションの情報も表示
    protected = [c for c in collections if c.name in PROTECTED_COLLECTIONS]
    if protected:
        print(f"\n  ℹ️  会話記憶（保護対象）:")
        for c in protected:
            print(f"     🔒 {c.name}: {c.count()}件")


def cmd_delete(args):
    """PDFコレクションを削除"""
    load_dotenv()
    db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")

    collection_name = f"{PDF_COLLECTION_PREFIX}{args.name}"

    # 保護チェック
    if collection_name in PROTECTED_COLLECTIONS or args.name in PROTECTED_COLLECTIONS:
        print(f"エラー: '{args.name}' は保護されたコレクションです。削除できません。")
        sys.exit(1)

    client = get_chroma_client(db_path)
    existing_collections = [c.name for c in client.list_collections()]

    if collection_name not in existing_collections:
        print(f"エラー: コレクション '{collection_name}' が見つかりません。")
        print(f"\n登録済みコレクション一覧を確認: python add_pdf.py list")
        sys.exit(1)

    # 削除前の確認
    col = client.get_collection(collection_name)
    count = col.count()

    print(f"以下のコレクションを削除します:")
    print(f"  コレクション名: {collection_name}")
    print(f"  データ件数: {count}件")

    response = input("\n本当に削除しますか？ (y/N): ").strip().lower()
    if response != 'y':
        print("中止しました。")
        sys.exit(0)

    client.delete_collection(collection_name)

    print(f"\n✓ コレクション '{collection_name}' を削除しました（{count}件）")

    # 会話記憶が無事であることを確認
    try:
        chat_col = client.get_collection("chat_memory")
        print(f"✓ 会話記憶（chat_memory）: {chat_col.count()}件 - 影響なし")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="PDF RAG管理ツール - PDFファイルをAIアシスタントの知識として追加・管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python add_pdf.py add ../docs --name 研究資料_2026     # フォルダ一括インポート
  python add_pdf.py add ./paper.pdf --name 論文A          # 単一ファイルインポート
  python add_pdf.py list                                   # コレクション一覧
  python add_pdf.py delete 研究資料_2026                  # コレクション削除
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # add コマンド
    add_parser = subparsers.add_parser("add", help="PDFをRAGデータにインポート")
    add_parser.add_argument("path", help="PDFファイルまたはフォルダのパス")
    add_parser.add_argument("--name", "-n", required=True,
                           help="コレクション名（後で削除時に使用する識別名）")

    # list コマンド
    subparsers.add_parser("list", help="登録済みPDFコレクションを一覧表示")

    # delete コマンド
    delete_parser = subparsers.add_parser("delete", help="PDFコレクションを削除")
    delete_parser.add_argument("name", help="削除するコレクション名（pdf_プレフィックスなし）")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "add":
        cmd_add(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "delete":
        cmd_delete(args)


if __name__ == "__main__":
    main()
