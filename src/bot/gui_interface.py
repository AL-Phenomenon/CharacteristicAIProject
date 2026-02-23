"""
GUIインターフェース
LINEのようなチャット画面を提供
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime
from typing import Optional
from .chatbot import ChatBot


class ChatGUI:
    """チャットGUIクラス"""
    
    def __init__(self, chatbot: ChatBot, user_id: str = "user_001"):
        """
        Args:
            chatbot: チャットボットインスタンス
            user_id: ユーザーID
        """
        self.chatbot = chatbot
        self.user_id = user_id
        self.window = None
        self.chat_display = None
        self.input_box = None
        self.send_button = None
        self.status_label = None
        self.processing = False
        
    def start(self):
        """GUIを起動"""
        self.window = tk.Tk()
        self.window.title(f"{self.chatbot.character.name} - チャット")
        self.window.geometry("600x700")
        self.window.configure(bg="#f0f0f0")
        
        self._create_widgets()
        self._setup_layout()
        self._bind_events()
        
        # 初期メッセージ
        self._add_system_message(
            f"{self.chatbot.character.name}との会話を開始します。\n"
            f"何でも話しかけてください！"
        )
        
        self.window.mainloop()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = tk.Frame(self.window, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ヘッダー
        header_frame = tk.Frame(main_frame, bg="#4a90e2", height=60)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text=self.chatbot.character.name,
            font=("Arial", 16, "bold"),
            bg="#4a90e2",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # チャット表示エリア
        chat_frame = tk.Frame(main_frame, bg="white", relief=tk.SUNKEN, bd=2)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # スクロール付きテキストエリア
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg="white",
            fg="black",
            state=tk.DISABLED,
            cursor="arrow"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # タグの設定（吹き出しスタイル）
        self.chat_display.tag_config("user", 
                                     justify=tk.RIGHT,
                                     foreground="#ffffff",
                                     background="#4a90e2",
                                     relief=tk.RAISED,
                                     borderwidth=1)
        self.chat_display.tag_config("user_bubble",
                                     background="#e8f4ff")
        self.chat_display.tag_config("assistant",
                                     justify=tk.LEFT,
                                     foreground="#000000",
                                     background="#f0f0f0",
                                     relief=tk.RAISED,
                                     borderwidth=1)
        self.chat_display.tag_config("assistant_bubble",
                                     background="#ffffff")
        self.chat_display.tag_config("system",
                                     justify=tk.CENTER,
                                     foreground="#666666",
                                     font=("Arial", 9, "italic"))
        self.chat_display.tag_config("timestamp",
                                     foreground="#999999",
                                     font=("Arial", 8))
        
        # 入力エリア
        input_frame = tk.Frame(main_frame, bg="#f0f0f0")
        input_frame.pack(fill=tk.X)
        
        # 入力ボックス
        self.input_box = tk.Text(
            input_frame,
            height=3,
            font=("Arial", 10),
            wrap=tk.WORD,
            relief=tk.SOLID,
            bd=1
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 送信ボタン
        self.send_button = tk.Button(
            input_frame,
            text="送信",
            font=("Arial", 10, "bold"),
            bg="#4a90e2",
            fg="white",
            width=8,
            height=3,
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self._on_send_click
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # ステータスバー
        status_frame = tk.Frame(main_frame, bg="#f0f0f0")
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_label = tk.Label(
            status_frame,
            text="準備完了",
            font=("Arial", 8),
            fg="#666666",
            bg="#f0f0f0",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X)
    
    def _setup_layout(self):
        """レイアウトを設定"""
        pass
    
    def _bind_events(self):
        """イベントをバインド"""
        # Ctrl+Enter / Cmd+Enter で送信
        self.input_box.bind("<Control-Return>", lambda e: self._on_send_click())
        self.input_box.bind("<Command-Return>", lambda e: self._on_send_click())
        
        # ウィンドウクローズ時の処理
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _on_send_click(self):
        """送信ボタンがクリックされた時の処理"""
        if self.processing:
            return
        
        message = self.input_box.get("1.0", tk.END).strip()
        if not message:
            return
        
        # 入力をクリア
        self.input_box.delete("1.0", tk.END)
        
        # ユーザーメッセージを表示
        self._add_user_message(message)
        
        # AI応答を非同期で取得
        self.processing = True
        self.send_button.config(state=tk.DISABLED, text="処理中...")
        self.status_label.config(text="AIが考え中...")
        
        thread = threading.Thread(target=self._get_ai_response, args=(message,))
        thread.daemon = True
        thread.start()
    
    def _get_ai_response(self, message: str):
        """AI応答を取得（別スレッド）"""
        try:
            response = self.chatbot.chat(self.user_id, message)
            
            # メインスレッドで表示を更新
            self.window.after(0, self._add_assistant_message, response)
            
        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.window.after(0, self._add_system_message, error_msg)
        
        finally:
            # UI要素を元に戻す
            self.window.after(0, self._reset_ui)
    
    def _reset_ui(self):
        """UIを元の状態に戻す"""
        self.processing = False
        self.send_button.config(state=tk.NORMAL, text="送信")
        self.status_label.config(text="準備完了")
        self.input_box.focus_set()
    
    def _add_user_message(self, message: str):
        """ユーザーメッセージを追加"""
        timestamp = datetime.now().strftime("%H:%M")
        
        self.chat_display.config(state=tk.NORMAL)
        
        # タイムスタンプ
        self.chat_display.insert(tk.END, f"{timestamp}\n", "timestamp")
        
        # メッセージ（右寄せ）
        self.chat_display.insert(tk.END, "                    ")  # スペースで右寄せ
        self.chat_display.insert(tk.END, f" {message} ", "user")
        self.chat_display.insert(tk.END, "\n\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def _add_assistant_message(self, message: str):
        """AIメッセージを追加"""
        timestamp = datetime.now().strftime("%H:%M")
        
        self.chat_display.config(state=tk.NORMAL)
        
        # キャラクター名
        self.chat_display.insert(tk.END, f"{self.chatbot.character.name}\n", "timestamp")
        
        # メッセージ（左寄せ）
        self.chat_display.insert(tk.END, f" {message} ", "assistant")
        self.chat_display.insert(tk.END, f"\n{timestamp}\n\n", "timestamp")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def _add_system_message(self, message: str):
        """システムメッセージを追加"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"━━━ {message} ━━━\n\n", "system")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def _on_closing(self):
        """ウィンドウを閉じる時の処理"""
        if self.processing:
            if tk.messagebox.askokcancel("確認", "AI処理中ですが終了しますか？"):
                self.window.destroy()
        else:
            self.window.destroy()


def run_gui(chatbot: ChatBot, user_id: Optional[str] = None):
    """
    GUIインターフェースを実行
    
    Args:
        chatbot: チャットボットインスタンス
        user_id: ユーザーID（省略可）
    """
    if user_id is None:
        user_id = "user_001"
    
    gui = ChatGUI(chatbot, user_id)
    gui.start()