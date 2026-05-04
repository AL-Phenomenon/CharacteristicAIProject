"""
PDF読み込み・テキスト抽出モジュール
外部PDFファイルをRAGデータとしてインポートするための処理
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PDFChunk:
    """PDFから抽出されたテキストチャンク"""
    text: str
    metadata: Dict[str, str]


class PDFLoader:
    """PDFファイルからテキストを抽出し、ページ単位のチャンクに分割する"""

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> List[PDFChunk]:
        """
        PDFファイルからページ単位でテキストを抽出

        Args:
            pdf_path: PDFファイルのパス

        Returns:
            PDFChunkのリスト（1ページ = 1チャンク）
        """
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError(
                "PyPDF2がインストールされていません。\n"
                "以下のコマンドでインストールしてください:\n"
                "pip install PyPDF2"
            )

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")

        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"PDFファイルではありません: {pdf_path}")

        reader = PdfReader(str(pdf_path))
        chunks = []

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()

            # 空ページをスキップ
            if not text or not text.strip():
                continue

            # テキストの正規化（余分な空白を整理）
            text = text.strip()

            chunk = PDFChunk(
                text=text,
                metadata={
                    "source_file": pdf_path.name,
                    "page_number": str(page_num),
                    "total_pages": str(len(reader.pages)),
                }
            )
            chunks.append(chunk)

        return chunks

    @staticmethod
    def load_pdf_folder(folder_path: str) -> Dict[str, List[PDFChunk]]:
        """
        フォルダ内の全PDFファイルをロード

        Args:
            folder_path: PDFファイルが含まれるフォルダパス

        Returns:
            {ファイル名: チャンクリスト} の辞書
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"フォルダが見つかりません: {folder}")

        if not folder.is_dir():
            raise ValueError(f"ディレクトリではありません: {folder}")

        pdf_files = sorted(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"⚠️  PDFファイルが見つかりません: {folder}")
            return {}

        all_chunks = {}
        for pdf_file in pdf_files:
            try:
                print(f"  読み込み中: {pdf_file.name}")
                chunks = PDFLoader.extract_text_from_pdf(str(pdf_file))
                all_chunks[pdf_file.name] = chunks
                print(f"    ✓ {len(chunks)}ページ抽出")
            except Exception as e:
                print(f"    ✗ エラー: {e}")

        return all_chunks
