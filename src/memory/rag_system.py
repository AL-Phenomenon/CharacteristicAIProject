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
        min_relevance: float = 0.0
    ) -> List[Memory]:
        """
        関連する記憶を検索
        
        Args:
            query: 検索クエリ
            user_id: ユーザーID
            n_results: 取得する記憶の最大数
            min_relevance: 最小関連度スコア（0-1）
        
        Returns:
            関連する記憶のリスト
        """
        # クエリのエンベディング生成
        query_embedding = self.embedding_model.encode(query).tolist()
        
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