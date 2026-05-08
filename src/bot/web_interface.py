"""
Webインターフェース
FastAPI + 静的ファイルによるLAN公開用チャットUI
"""

import os
import socket
import asyncio
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
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

class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    response: Optional[str] = None
    timestamp: Optional[str] = None
    character_name: Optional[str] = None

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
    
    # 進行中のタスクを保持する辞書
    tasks: Dict[str, Any] = {}

    async def generate_response_task(task_id: str, user_id: str, message: str):
        """バックグラウンドでLLMに応答を生成させるタスク"""
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                chatbot.chat,
                user_id,
                message
            )
            
            if not response:
                print(f"[WARNING] 空の応答が返されました (user={user_id})")
                response = "（応答を生成できませんでした。もう一度お試しください。）"
            else:
                print(f"[CHAT] 応答生成完了: {len(response)}文字 (user={user_id}, task={task_id})")
                
            tasks[task_id] = {
                "status": "completed",
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "character_name": chatbot.character.name
            }
        except Exception as e:
            print(f"[ERROR] 応答生成エラー: {e}")
            tasks[task_id] = {
                "status": "error",
                "response": f"（エラーが発生しました: {str(e)}）",
                "timestamp": datetime.now().isoformat(),
                "character_name": chatbot.character.name
            }

    @app.post("/api/chat", response_model=TaskSubmitResponse)
    async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
        """メッセージを受け付け、タスクIDを返す"""
        task_id = str(uuid.uuid4())
        tasks[task_id] = {"status": "processing"}
        
        # バックグラウンドタスクとして生成を開始
        background_tasks.add_task(
            generate_response_task,
            task_id,
            request.user_id,
            request.message
        )
        
        return TaskSubmitResponse(task_id=task_id, status="processing")

    @app.get("/api/chat/status/{task_id}", response_model=TaskStatusResponse)
    async def chat_status(task_id: str):
        """タスクのステータスと、完了していれば結果を返す"""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
            
        task_data = tasks[task_id]
        
        if task_data["status"] == "processing":
            return TaskStatusResponse(task_id=task_id, status="processing")
        else:
            # 完了（またはエラー）の場合は結果を返す
            # 一度返したらメモリから消す（または一定時間後に消すロジックでもよいが、ここでは取得時に削除する）
            response_data = tasks.pop(task_id)
            return TaskStatusResponse(
                task_id=task_id,
                status=response_data["status"],
                response=response_data["response"],
                timestamp=response_data["timestamp"],
                character_name=response_data["character_name"]
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
