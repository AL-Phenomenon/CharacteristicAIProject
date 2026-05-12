"""
チャットボットのメインロジック
"""

import os
import threading
from typing import Dict, List, Optional, Literal, Any
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
        max_memory_results: int = 5,
        max_pdf_results: int = 2,
        pdf_min_relevance: float = 0.3,
        compact_prompt: bool = True,
        disable_thinking: bool = False
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
            max_pdf_results: PDF検索で取得する最大件数
            pdf_min_relevance: PDF検索の最小関連度閾値
            compact_prompt: システムプロンプトを簡潔化するか
            disable_thinking: Qwen3等のthinkingモードを無効化するか
        """
        self.llm_provider = llm_provider
        self.character = character
        self.memory = memory_system
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.short_term_memory_size = short_term_memory_size
        self.max_memory_results = max_memory_results
        self.max_pdf_results = max_pdf_results
        self.pdf_min_relevance = pdf_min_relevance
        self.compact_prompt = compact_prompt
        self.disable_thinking = disable_thinking
        
        # LLMクライアントの初期化
        if llm_provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "anthropicライブラリがインストールされていません。\n"
                    "以下のコマンドでインストールしてください:\n"
                    "pip install anthropic"
                )
        elif llm_provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=api_key or "not-needed",  # LM StudioではダミーでもOK
                    base_url=base_url or "http://localhost:1234/v1"
                )
            except ImportError:
                raise ImportError(
                    "openaiライブラリがインストールされていません。\n"
                    "以下のコマンドでインストールしてください:\n"
                    "pip install openai"
                )
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")
        
        # ユーザーごとの短期記憶（セッション内のみ）
        self.conversation_history: Dict[str, List[ConversationMessage]] = {}
        
        print(f"チャットボット初期化完了: {character.name} (Provider: {llm_provider})")
    
    def chat(self, user_id: str, message: str, is_creator: bool = False) -> str:
        """
        ユーザーとチャット
        
        Args:
            user_id: ユーザーID
            message: ユーザーメッセージ
        
        Returns:
            AIの応答
        """
        # ★案3: エンベディングを1回だけ計算して使い回す
        query_embedding = self.memory.encode_query(message)
        
        # 1. RAGで関連する長期記憶を取得
        long_term_memories = self.memory.search_memories(
            query=message,
            user_id=user_id,
            n_results=self.max_memory_results,
            query_embedding=query_embedding
        )
        
        # 2. PDF資料から関連情報を検索（★案5: 関連度閾値でフィルタリング）
        pdf_memories = self.memory.search_pdf_collections(
            query=message,
            n_results=self.max_pdf_results,
            min_relevance=self.pdf_min_relevance,
            query_embedding=query_embedding
        )
        
        # 3. 短期記憶を取得
        short_term_history = self._get_short_term_history(user_id)
        
        # 4. プロンプト構築
        creator_name = getattr(self.character.config, 'creator', None)
        context = PromptBuilder.build_context_from_memories(
            memories=long_term_memories,
            short_term_history=short_term_history,
            current_message=message,
            pdf_memories=pdf_memories,
            is_creator=is_creator,
            creator_name=creator_name
        )
        
        # 5. LLM APIで応答生成
        response = self._generate_response(context)
        
        # 6. ★案4: 記憶保存をバックグラウンドで実行（応答を先に返す）
        self._save_to_short_term(user_id, message, "user")
        self._save_to_short_term(user_id, response, "assistant")
        threading.Thread(
            target=self._save_to_long_term_memory,
            args=(user_id, message, response),
            daemon=True
        ).start()
        
        return response
    
    def _generate_response(self, context: str) -> str:
        """LLM APIで応答を生成"""
        try:
            # システムプロンプトを取得（compact設定に応じて）
            system_prompt = self.character.get_system_prompt(compact=self.compact_prompt)
            
            if self.llm_provider == "anthropic":
                # Anthropic Claude API（thinkingはAPIオプションで制御）
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": context}
                    ]
                )
                raw_response = response.content[0].text
            
            elif self.llm_provider == "openai":
                # OpenAI互換API (LM Studio/Ollama等)
                # DISABLE_THINKING=trueの場合、chat_template_kwargsでthinkingを無効化
                # これは /no_think プロンプトよりもトークナイザーレベルで確実に動作する
                extra_body = {}
                if self.disable_thinking:
                    extra_body["chat_template_kwargs"] = {"enable_thinking": False}
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context}
                    ],
                    temperature=0.7,  # 創造性のバランス
                    extra_body=extra_body if extra_body else None,
                )
                raw_response = response.choices[0].message.content
            
            # <think>タグとその内容を削除（念のため残す）
            cleaned_response = self._remove_think_tags(raw_response)
            
            return cleaned_response
        
        except Exception as e:
            print(f"API呼び出しエラー: {e}")
            return f"申し訳ありません、応答の生成中にエラーが発生しました: {str(e)}"
    
    def _remove_think_tags(self, text: str) -> str:
        """
        応答から<think>タグとその内容を削除
        
        Args:
            text: 元のテキスト
        
        Returns:
            <think>タグを削除したテキスト
        """
        import re
        
        if not text:
            return text
        
        # <think>...</think>を削除（改行を含む場合も対応）
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        # 閉じタグなしの<think>（トークン制限で切れた場合）も削除
        cleaned = re.sub(r'<think>.*$', '', cleaned, flags=re.DOTALL)
        
        # 前後の空白や改行を整理
        cleaned = cleaned.strip()
        
        # 複数の連続する改行を1つにまとめる
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        
        if not cleaned and text:
            print(f"[WARNING] thinkタグ除去後に応答が空になりました。元の長さ: {len(text)}文字")
        
        return cleaned
    
    def _get_short_term_history(self, user_id: str) -> List[ConversationMessage]:
        """短期記憶を取得"""
        if user_id not in self.conversation_history:
            return []
        
        # 最新のN件のみ返す
        return self.conversation_history[user_id][-self.short_term_memory_size:]
    
    def _save_to_short_term(self, user_id: str, message: str, role: str):
        """短期記憶に保存（インメモリ、即完了）"""
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append(
            ConversationMessage(role=role, content=message, timestamp=timestamp)
        )
    
    def _save_to_long_term_memory(self, user_id: str, user_message: str, ai_response: str):
        """長期記憶（RAG）にバックグラウンドで保存"""
        try:
            self.memory.add_memory(
                user_id=user_id,
                message=user_message,
                role="user"
            )
            self.memory.add_memory(
                user_id=user_id,
                message=ai_response,
                role="assistant"
            )
        except Exception as e:
            print(f"[WARNING] 長期記憶の保存に失敗: {e}")
    
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