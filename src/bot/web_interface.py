"""
Webインターフェース
FastAPI + 静的ファイルによるLAN公開用チャットUI
"""

import os
import socket
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .chatbot import ChatBot

# リクエスト/レスポンスモデル
class ChatRequest(BaseModel):
    message: str
    user_id: str = "web_user"

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    character_name: str

class ClearRequest(BaseModel):
    user_id: str = "web_user"


def create_app(chatbot: ChatBot) -> FastAPI:
    """
    FastAPIアプリケーションを作成

    Args:
        chatbot: チャットボットインスタンス

    Returns:
        FastAPIアプリケーション
    """
    app = FastAPI(
        title=f"{chatbot.character.name} - Web Chat",
        description="LAN公開用チャットボットWebインターフェース"
    )

    # 静的ファイルのパス
    static_dir = Path(__file__).parent.parent.parent / "static"

    # --- API エンドポイント ---

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """メッセージを送信し、AI応答を返す"""
        # ChatBotはsync関数なので、スレッドプールで実行して
        # 他のリクエストをブロックしないようにする
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            chatbot.chat,
            request.user_id,
            request.message
        )

        # Noneや空文字列の場合のフォールバック
        if not response:
            print(f"[WARNING] 空の応答が返されました (user={request.user_id})")
            response = "（応答を生成できませんでした。もう一度お試しください。）"
        else:
            print(f"[CHAT] 応答生成完了: {len(response)}文字 (user={request.user_id})")

        return ChatResponse(
            response=response,
            timestamp=datetime.now().isoformat(),
            character_name=chatbot.character.name
        )

    @app.post("/api/clear")
    async def clear_memory(request: ClearRequest):
        """短期記憶をクリア"""
        chatbot.clear_short_term_memory(request.user_id)
        return {"status": "ok", "message": "短期記憶をクリアしました"}

    @app.get("/api/stats")
    async def get_stats(user_id: str = "web_user"):
        """ユーザー統計情報を取得"""
        stats = chatbot.get_user_stats(user_id)
        memory_stats = chatbot.memory.get_statistics()
        return {
            "user": stats,
            "system": memory_stats
        }

    @app.get("/api/character")
    async def get_character():
        """キャラクター情報を取得"""
        return {
            "name": chatbot.character.name,
            "description": getattr(chatbot.character, 'description', ''),
        }

    # --- 静的ファイル配信 ---

    @app.get("/")
    async def serve_index():
        """メインページを返す"""
        return FileResponse(static_dir / "index.html")

    # 静的ファイル（CSS, JS等）
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


def get_local_ip() -> str:
    """LAN内のローカルIPアドレスを取得"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_web(
    chatbot: ChatBot,
    host: str = "0.0.0.0",
    port: int = 8080
):
    """
    Webインターフェースを起動

    Args:
        chatbot: チャットボットインスタンス
        host: バインドするホスト（デフォルト: 0.0.0.0 = 全インターフェース）
        port: ポート番号（デフォルト: 8080）
    """
    import uvicorn

    app = create_app(chatbot)
    local_ip = get_local_ip()

    print("=" * 60)
    print(f"  {chatbot.character.name} - Web Chat Server")
    print("=" * 60)
    print(f"\n  ローカル:     http://localhost:{port}")
    print(f"  LAN内アクセス: http://{local_ip}:{port}")
    print(f"\n  同じネットワーク内の端末から上記URLでアクセスできます")
    print(f"  終了するには Ctrl+C を押してください")
    print("=" * 60)

    uvicorn.run(app, host=host, port=port, log_level="info")
