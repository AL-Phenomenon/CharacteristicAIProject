"""
プロンプト構築ユーティリティ
記憶とコンテキストを統合してLLMに渡すプロンプトを生成
"""

from typing import List, Dict
from ..memory.rag_system import Memory


class ConversationMessage:
    """会話メッセージ"""
    
    def __init__(self, role: str, content: str, timestamp: str = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp
    
    def __repr__(self):
        return f"Message(role={self.role})"


class PromptBuilder:
    """プロンプト構築クラス"""
    
    @staticmethod
    def build_context_from_memories(
        memories: List[Memory],
        short_term_history: List[ConversationMessage],
        current_message: str
    ) -> str:
        """
        記憶と会話履歴からコンテキストを構築
        
        Args:
            memories: RAGから取得した長期記憶
            short_term_history: セッション内の短期記憶
            current_message: 現在のユーザーメッセージ
        
        Returns:
            構築されたコンテキスト文字列
        """
        context_parts = []
        
        # 長期記憶（RAG）
        if memories:
            context_parts.append("## 関連する過去の記憶:")
            for i, memory in enumerate(memories, 1):
                timestamp = PromptBuilder._format_timestamp(memory.timestamp)
                relevance_indicator = "★" * int(memory.relevance * 3)  # 関連度を★で表示
                
                role_name = "ユーザー" if memory.role == "user" else "あなた"
                context_parts.append(
                    f"{i}. [{timestamp}] {relevance_indicator} {role_name}: {memory.content}"
                )
            context_parts.append("")  # 空行
        
        # 短期記憶（現在のセッション）
        if short_term_history:
            context_parts.append("## 現在の会話の流れ:")
            for msg in short_term_history:
                role_name = "ユーザー" if msg.role == "user" else "あなた"
                context_parts.append(f"{role_name}: {msg.content}")
            context_parts.append("")  # 空行
        
        # どちらもない場合
        if not memories and not short_term_history:
            context_parts.append("（初めての会話です）")
            context_parts.append("")
        
        # 現在のメッセージ
        context_parts.append("---")
        context_parts.append(f"現在のユーザーのメッセージ: {current_message}")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def build_simple_prompt(message: str) -> str:
        """
        シンプルなプロンプトを構築（記憶なし）
        
        Args:
            message: ユーザーメッセージ
        
        Returns:
            プロンプト文字列
        """
        return f"ユーザー: {message}"
    
    @staticmethod
    def _format_timestamp(timestamp_str: str) -> str:
        """タイムスタンプを読みやすい形式にフォーマット"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%Y/%m/%d %H:%M")
        except:
            return timestamp_str
    
    @staticmethod
    def extract_conversation_summary(
        short_term_history: List[ConversationMessage],
        max_messages: int = 10
    ) -> str:
        """
        会話の要約を抽出（長い会話の場合）
        
        Args:
            short_term_history: 短期記憶
            max_messages: 最大メッセージ数
        
        Returns:
            要約文字列
        """
        if len(short_term_history) <= max_messages:
            return ""
        
        # 古いメッセージを要約
        old_messages = short_term_history[:-max_messages]
        
        summary_parts = [f"（これまでに{len(old_messages)}件のメッセージをやり取りしました）"]
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def format_memory_statistics(
        total_memories: int,
        relevant_count: int
    ) -> str:
        """
        記憶の統計情報をフォーマット
        
        Args:
            total_memories: 総記憶数
            relevant_count: 関連する記憶数
        
        Returns:
            統計情報文字列
        """
        return f"（総記憶数: {total_memories}件、うち関連: {relevant_count}件を参照）"