"""
PDF読み込み・テキスト抽出モジュール
外部PDFファイルをRAGデータとしてインポートするための処理
"""

import os
import re
from datetime import datetime
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
    def _parse_pdf_date(date_value) -> str:
        """
        PDFの日付フィールドを読みやすい文字列に変換

        PDFの日付形式: D:YYYYMMDDHHmmSSOHH'mm' (例: D:20240315143000+09'00')
        または datetime オブジェクトの場合もある

        Args:
            date_value: PDFメタデータの日付値

        Returns:
            "YYYY/MM/DD" 形式の文字列、パース失敗時は空文字列
        """
        if date_value is None:
            return ""

        # datetime オブジェクトの場合（PyPDF2が自動変換する場合がある）
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y/%m/%d")

        date_str = str(date_value)

        # "D:" プレフィックスを除去
        if date_str.startswith("D:"):
            date_str = date_str[2:]

        # タイムゾーン情報を除去してパース
        # 形式: YYYYMMDDHHmmSS+HH'mm' or YYYYMMDDHHmmSSZ
        date_str = re.sub(r"[Z+-].*$", "", date_str)

        # 様々な長さに対応
        formats = [
            ("%Y%m%d%H%M%S", 14),
            ("%Y%m%d%H%M", 12),
            ("%Y%m%d", 8),
            ("%Y%m", 6),
            ("%Y", 4),
        ]

        for fmt, length in formats:
            if len(date_str) >= length:
                try:
                    dt = datetime.strptime(date_str[:length], fmt)
                    return dt.strftime("%Y/%m/%d")
                except ValueError:
                    continue

        return ""

    @staticmethod
    def _extract_pdf_metadata(reader) -> Dict[str, str]:
        """
        PDFのメタデータ（日付等）を抽出

        Args:
            reader: PyPDF2の PdfReader オブジェクト

        Returns:
            日付情報を含むメタデータ辞書
        """
        date_meta = {}

        try:
            metadata = reader.metadata
            if metadata is None:
                return date_meta

            # 作成日
            creation_date = PDFLoader._parse_pdf_date(
                getattr(metadata, 'creation_date', None)
                or metadata.get('/CreationDate')
            )
            if creation_date:
                date_meta["creation_date"] = creation_date

            # 更新日
            mod_date = PDFLoader._parse_pdf_date(
                getattr(metadata, 'modification_date', None)
                or metadata.get('/ModDate')
            )
            if mod_date:
                date_meta["mod_date"] = mod_date

            # タイトル（あれば）
            title = getattr(metadata, 'title', None) or metadata.get('/Title')
            if title and str(title).strip():
                date_meta["pdf_title"] = str(title).strip()

        except Exception as e:
            print(f"  ⚠️ PDFメタデータの読み取りに失敗: {e}")

        return date_meta

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

        # PDFメタデータから日付情報を抽出
        pdf_date_meta = PDFLoader._extract_pdf_metadata(reader)
        if pdf_date_meta:
            date_info = []
            if 'creation_date' in pdf_date_meta:
                date_info.append(f"作成日: {pdf_date_meta['creation_date']}")
            if 'mod_date' in pdf_date_meta:
                date_info.append(f"更新日: {pdf_date_meta['mod_date']}")
            if 'pdf_title' in pdf_date_meta:
                date_info.append(f"タイトル: {pdf_date_meta['pdf_title']}")
            print(f"    📅 {', '.join(date_info)}")

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
                    **pdf_date_meta,
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
