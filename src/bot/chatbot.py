"""
チャットボットのメインロジック
"""

import os
from typing import Dict, List, Optional, Literal
import anthropic
from openai import OpenAI
from ..memory.rag_system import RAGMemorySystem
from ..character.character import Character
from ..character.prompt_builder import PromptBuilder, ConversationMessage


class ChatBot:
    """キャラクター性を持ったAIチャットボット"""
    
    def __init__(
        self,
        character: Character,
        memory_system: RAGMemorySystem,
        llm_provider: Literal["anthropic", "openai"] = "anthropic",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1000,
        short_term_memory_size: int = 5,
        max_memory_results: int = 5
    ):
        """
        Args:
            character: キャラクター設定
            memory_system: RAGメモリーシステム
            llm_provider: LLMプロバイダー ("anthropic" or "openai")
            api_key: APIキー
            base_url: ベースURL (OpenAI互換APIの場合)
            model_name: 使用するモデル名
            max_tokens: 最大トークン数
            short_term_memory_size: 短期記憶のサイズ
            max_memory_results: RAG検索で取得する記憶数
        """
        self.llm_provider = llm_provider
        self.character = character
        self.memory = memory_system
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.short_term_memory_size = short_term_memory_size
        self.max_memory_results = max_memory_results
        
        # LLMクライアントの初期化
        if llm_provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=api_key)
        elif llm_provider == "openai":
            self.client = OpenAI(
                api_key=api_key or "not-needed",  # LM StudioではダミーでもOK
                base_url=base_url or "http://localhost:1234/v1"
            )
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")
        
        # ユーザーごとの短期記憶（セッション内のみ）
        self.conversation_history: Dict[str, List[ConversationMessage]] = {}
        
        print(f"チャットボット初期化完了: {character.name} (Provider: {llm_provider})")
    
    def chat(self, user_id: str, message: str) -> str:
        """
        ユーザーとチャット
        
        Args:
            user_id: ユーザーID
            message: ユーザーメッセージ
        
        Returns:
            AIの応答
        """
        # 1. RAGで関連する長期記憶を取得
        long_term_memories = self.memory.search_memories(
            query=message,
            user_id=user_id,
            n_results=self.max_memory_results
        )
        
        # 2. 短期記憶を取得
        short_term_history = self._get_short_term_history(user_id)
        
        # 3. プロンプト構築
        context = PromptBuilder.build_context_from_memories(
            memories=long_term_memories,
            short_term_history=short_term_history,
            current_message=message
        )
        
        # 4. LLM APIで応答生成
        response = self._generate_response(context)
        
        # 5. 記憶に保存（短期・長期両方）
        self._save_to_memory(user_id, message, "user")
        self._save_to_memory(user_id, response, "assistant")
        
        return response
    
    def _generate_response(self, context: str) -> str:
        """LLM APIで応答を生成"""
        try:
            if self.llm_provider == "anthropic":
                # Anthropic Claude API
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    system=self.character.get_system_prompt(),
                    messages=[
                        {"role": "user", "content": context}
                    ]
                )
                return response.content[0].text
            
            elif self.llm_provider == "openai":
                # OpenAI互換API (LM Studio等)
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": self.character.get_system_prompt()},
                        {"role": "user", "content": context}
                    ],
                    temperature=0.7,  # 創造性のバランス
                )
                return response.choices[0].message.content
        
        except Exception as e:
            print(f"API呼び出しエラー: {e}")
            return f"申し訳ありません、応答の生成中にエラーが発生しました: {str(e)}"
    
    def _get_short_term_history(self, user_id: str) -> List[ConversationMessage]:
        """短期記憶を取得"""
        if user_id not in self.conversation_history:
            return []
        
        # 最新のN件のみ返す
        return self.conversation_history[user_id][-self.short_term_memory_size:]
    
    def _save_to_memory(self, user_id: str, message: str, role: str):
        """記憶に保存（短期・長期両方）"""
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        # 短期記憶に追加
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append(
            ConversationMessage(role=role, content=message, timestamp=timestamp)
        )
        
        # 長期記憶（RAG）に追加
        self.memory.add_memory(
            user_id=user_id,
            message=message,
            role=role
        )
    
    def clear_short_term_memory(self, user_id: str):
        """短期記憶をクリア（長期記憶は残る）"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            print(f"ユーザー {user_id} の短期記憶をクリアしました")
    
    def get_user_stats(self, user_id: str) -> Dict:
        """ユーザーの統計情報を取得"""
        memory_count = self.memory.get_user_memory_count(user_id)
        short_term_count = len(self.conversation_history.get(user_id, []))
        
        return {
            "user_id": user_id,
            "long_term_memories": memory_count,
            "short_term_messages": short_term_count
        }
    
    def delete_user_data(self, user_id: str) -> Dict:
        """ユーザーのデータを完全削除"""
        # 短期記憶削除
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
        
        # 長期記憶削除
        deleted_count = self.memory.delete_user_memories(user_id)
        
        return {
            "user_id": user_id,
            "deleted_memories": deleted_count,
            "status": "completed"
        }
    
    def get_recent_conversation(self, user_id: str, n: int = 5) -> List[Dict]:
        """最近の会話を取得"""
        memories = self.memory.get_recent_memories(user_id, n_results=n)
        
        conversation = []
        for memory in memories:
            conversation.append({
                "role": memory.role,
                "content": memory.content,
                "timestamp": memory.timestamp
            })
        
        return conversation