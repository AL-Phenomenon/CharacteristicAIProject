"""
CLIインターフェース
コマンドラインでチャットボットと対話する
"""

import sys
from typing import Optional
from .chatbot import ChatBot


class CLIInterface:
    """CLIインターフェースクラス"""
    
    def __init__(self, chatbot: ChatBot, user_id: str = "user_001"):
        """
        Args:
            chatbot: チャットボットインスタンス
            user_id: ユーザーID
        """
        self.chatbot = chatbot
        self.user_id = user_id
        self.running = False
    
    def start(self):
        """CLIチャットを開始"""
        self.running = True
        
        self._print_header()
        self._print_help()
        
        while self.running:
            try:
                user_input = input("\nあなた: ").strip()
                
                if not user_input:
                    continue
                
                # コマンド処理
                if self._handle_command(user_input):
                    continue
                
                # 通常のチャット
                response = self.chatbot.chat(self.user_id, user_input)
                print(f"\n{self.chatbot.character.name}: {response}")
                
            except KeyboardInterrupt:
                print("\n\nチャットを終了します。")
                self.running = False
                break
            
            except Exception as e:
                print(f"\nエラーが発生しました: {e}")
                import traceback
                traceback.print_exc()
    
    def _handle_command(self, user_input: str) -> bool:
        """
        コマンドを処理
        
        Returns:
            True: コマンドとして処理した
            False: 通常のメッセージとして扱う
        """
        command = user_input.lower()
        
        # 終了コマンド
        if command in ['exit', 'quit', 'bye']:
            print("\nまたね！")
            self.running = False
            return True
        
        # ヘルプ
        if command in ['help', 'h', '?']:
            self._print_help()
            return True
        
        # 短期記憶クリア
        if command in ['clear', 'reset']:
            self.chatbot.clear_short_term_memory(self.user_id)
            print("✓ 会話履歴をクリアしました（長期記憶は保持されます）")
            return True
        
        # 統計情報
        if command in ['stats', 'info', 'status']:
            self._show_stats()
            return True
        
        # 最近の会話
        if command in ['history', 'recent']:
            self._show_recent_history()
            return True
        
        # データ削除（慎重な操作）
        if command in ['delete', 'purge']:
            self._delete_user_data()
            return True
        
        return False
    
    def _print_header(self):
        """ヘッダーを表示"""
        name = self.chatbot.character.name
        print("=" * 60)
        print(f"  {name} チャットボット")
        print("=" * 60)
    
    def _print_help(self):
        """ヘルプを表示"""
        print("\n【コマンド一覧】")
        print("  exit, quit, bye  - チャット終了")
        print("  clear, reset     - 会話履歴をクリア")
        print("  stats, info      - 統計情報を表示")
        print("  history, recent  - 最近の会話を表示")
        print("  help, h, ?       - このヘルプを表示")
        print("  delete, purge    - すべてのデータを削除")
    
    def _show_stats(self):
        """統計情報を表示"""
        stats = self.chatbot.get_user_stats(self.user_id)
        memory_stats = self.chatbot.memory.get_statistics()
        
        print("\n【統計情報】")
        print(f"  ユーザーID: {stats['user_id']}")
        print(f"  長期記憶数: {stats['long_term_memories']}件")
        print(f"  短期記憶数: {stats['short_term_messages']}件")
        print(f"\n【システム全体】")
        print(f"  総記憶数: {memory_stats['total_memories']}件")
        print(f"  ユーザー数: {memory_stats['unique_users']}人")
    
    def _show_recent_history(self):
        """最近の会話を表示"""
        conversation = self.chatbot.get_recent_conversation(self.user_id, n=10)
        
        if not conversation:
            print("\n会話履歴がありません。")
            return
        
        print("\n【最近の会話】")
        for msg in reversed(conversation):  # 古い順に表示
            role_name = "あなた" if msg['role'] == "user" else self.chatbot.character.name
            timestamp = self._format_timestamp(msg['timestamp'])
            print(f"\n[{timestamp}] {role_name}:")
            print(f"  {msg['content']}")
    
    def _delete_user_data(self):
        """ユーザーデータを削除"""
        print("\n⚠️  警告: すべての会話データが削除されます。")
        confirm = input("本当に削除しますか？ (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y']:
            result = self.chatbot.delete_user_data(self.user_id)
            print(f"\n✓ {result['deleted_memories']}件の記憶を削除しました")
        else:
            print("キャンセルしました。")
    
    @staticmethod
    def _format_timestamp(timestamp_str: str) -> str:
        """タイムスタンプを読みやすい形式にフォーマット"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%m/%d %H:%M")
        except:
            return timestamp_str


def run_cli(chatbot: ChatBot, user_id: Optional[str] = None):
    """
    CLIインターフェースを実行
    
    Args:
        chatbot: チャットボットインスタンス
        user_id: ユーザーID（省略可）
    """
    if user_id is None:
        user_id = "user_001"
    
    cli = CLIInterface(chatbot, user_id)
    cli.start()