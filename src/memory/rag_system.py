"""
RAGベースの記憶システム
過去の会話をベクトルDBに保存し、関連情報を検索する
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class Memory:
    """単一の記憶を表すデータクラス"""
    
    def __init__(self, content: str, metadata: Dict, relevance: float):
        self.content = content
        self.metadata = metadata
        self.relevance = relevance
        self.timestamp = metadata.get('timestamp', '')
        self.role = metadata.get('role', 'unknown')
    
    def __repr__(self):
        return f"Memory(role={self.role}, relevance={self.relevance:.3f})"


class RAGMemorySystem:
    """RAGベースの記憶システム"""
    
    def __init__(
        self,
        db_path: str = "./data/chroma_db",
        collection_name: str = "chat_memory",
        embedding_model: str = "intfloat/multilingual-e5-base"
    ):
        """
        Args:
            db_path: ChromaDBの保存パス
            collection_name: コレクション名
            embedding_model: エンベディングモデル名
        """
        self.db_path = db_path
        self.collection_name = collection_name
        
        # データディレクトリの作成
        os.makedirs(db_path, exist_ok=True)
        
        # ChromaDBクライアントの初期化
        self.client = chromadb.PersistentClient(path=db_path)
        
        # エンベディングモデルのロード
        print(f"エンベディングモデルをロード中: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # コレクションの取得または作成
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "会話記憶とユーザー情報"}
        )
        
        print(f"記憶システム初期化完了: {self.collection.count()}件の記憶")
    
    def encode_query(self, text: str) -> list:
        """テキストのエンベディングを計算（結果を使い回し可能）"""
        return self.embedding_model.encode(text).tolist()
    
    def add_memory(
        self,
        user_id: str,
        message: str,
        role: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        会話を記憶に追加
        
        Args:
            user_id: ユーザーID
            message: メッセージ内容
            role: ロール（user/assistant）
            metadata: 追加のメタデータ
        
        Returns:
            記憶ID
        """
        timestamp = datetime.now().isoformat()
        
        # メタデータの構築
        meta = {
            "user_id": user_id,
            "role": role,
            "timestamp": timestamp,
        }
        if metadata:
            meta.update(metadata)
        
        # エンベディング生成
        embedding = self.embedding_model.encode(message).tolist()
        
        # ドキュメントIDの生成
        doc_id = f"{user_id}_{role}_{timestamp}"
        
        # ChromaDBに追加
        self.collection.add(
            embeddings=[embedding],
            documents=[message],
            metadatas=[meta],
            ids=[doc_id]
        )
        
        return doc_id
    
    def search_memories(
        self,
        query: str,
        user_id: str,
        n_results: int = 5,
        min_relevance: float = 0.0,
        query_embedding: list = None
    ) -> List[Memory]:
        """
        関連する記憶を検索
        
        Args:
            query: 検索クエリ
            user_id: ユーザーID
            n_results: 取得する記憶の最大数
            min_relevance: 最小関連度スコア（0-1）
            query_embedding: 事前計算済みエンベディング（省略時は自動計算）
        
        Returns:
            関連する記憶のリスト
        """
        # エンベディング（事前計算済みがあればそれを使用）
        if query_embedding is None:
            query_embedding = self.encode_query(query)
        
        # 検索実行
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"user_id": user_id}
        )
        
        # 結果を Memory オブジェクトに変換
        memories = []
        if results['documents'][0]:
            for doc, meta, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                relevance = 1 - distance  # 距離を類似度に変換
                
                # 最小関連度でフィルタリング
                if relevance >= min_relevance:
                    memories.append(Memory(
                        content=doc,
                        metadata=meta,
                        relevance=relevance
                    ))
        
        return memories
    
    def get_user_memory_count(self, user_id: str) -> int:
        """ユーザーの記憶数を取得"""
        results = self.collection.get(
            where={"user_id": user_id}
        )
        return len(results['ids'])
    
    def delete_user_memories(self, user_id: str) -> int:
        """ユーザーの全記憶を削除"""
        # ユーザーの記憶を取得
        results = self.collection.get(
            where={"user_id": user_id}
        )
        
        # 削除実行
        if results['ids']:
            self.collection.delete(ids=results['ids'])
        
        return len(results['ids'])
    
    def get_recent_memories(
        self,
        user_id: str,
        n_results: int = 10
    ) -> List[Memory]:
        """最近の記憶を時系列順で取得"""
        results = self.collection.get(
            where={"user_id": user_id}
        )
        
        if not results['ids']:
            return []
        
        # タイムスタンプでソート
        memories = []
        for doc, meta in zip(results['documents'], results['metadatas']):
            memories.append(Memory(
                content=doc,
                metadata=meta,
                relevance=1.0  # 時系列検索なので関連度は最大
            ))
        
        # タイムスタンプでソート（新しい順）
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        return memories[:n_results]
    
    def get_statistics(self) -> Dict:
        """記憶システムの統計情報を取得"""
        total_memories = self.collection.count()
        
        # ユーザーごとの記憶数を計算
        all_results = self.collection.get()
        user_counts = {}
        if all_results['metadatas']:
            for meta in all_results['metadatas']:
                user_id = meta.get('user_id', 'unknown')
                user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        return {
            "total_memories": total_memories,
            "unique_users": len(user_counts),
            "user_counts": user_counts
        }
    
    # ========================================
    # PDF コレクション検索（既存データに影響なし）
    # ========================================
    
    PDF_COLLECTION_PREFIX = "pdf_"
    
    def get_pdf_collection_names(self) -> List[str]:
        """pdf_ プレフィックス付きのコレクション名を一覧取得"""
        collections = self.client.list_collections()
        return [
            c.name for c in collections
            if c.name.startswith(self.PDF_COLLECTION_PREFIX)
        ]
    
    def search_pdf_collections(
        self,
        query: str,
        n_results: int = 3,
        min_relevance: float = 0.0,
        query_embedding: list = None
    ) -> List[Memory]:
        """
        全てのPDFコレクションを横断検索
        
        Args:
            query: 検索クエリ
            n_results: 各コレクションから取得する最大件数
            min_relevance: 最小関連度スコア（0-1）
            query_embedding: 事前計算済みエンベディング（省略時は自動計算）
        
        Returns:
            関連するPDFチャンクのリスト（Memoryオブジェクト）
        """
        pdf_collections = self.get_pdf_collection_names()
        
        if not pdf_collections:
            return []
        
        # エンベディング（事前計算済みがあればそれを使用）
        if query_embedding is None:
            query_embedding = self.encode_query(query)
        
        all_results = []
        
        for col_name in pdf_collections:
            try:
                collection = self.client.get_collection(col_name)
                
                # コレクションが空の場合スキップ
                if collection.count() == 0:
                    continue
                
                # n_results=0は「上限なし」＝コレクション全件を対象にする
                fetch_count = collection.count() if n_results == 0 else min(n_results, collection.count())
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=fetch_count
                )
                
                if results['documents'][0]:
                    for doc, meta, distance in zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    ):
                        relevance = 1 - distance
                        
                        if relevance >= min_relevance:
                            # PDFソースであることを明示するメタデータを追加
                            meta['source_type'] = 'pdf'
                            meta['collection_name'] = col_name
                            
                            all_results.append(Memory(
                                content=doc,
                                metadata=meta,
                                relevance=relevance
                            ))
            except Exception as e:
                print(f"PDF検索エラー（{col_name}）: {e}")
                continue
        
        # 関連度でソートして返す（n_results=0は上限なし）
        all_results.sort(key=lambda m: m.relevance, reverse=True)
        return all_results if n_results == 0 else all_results[:n_results]