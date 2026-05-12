"""
Webインターフェース
FastAPI + 静的ファイルによるLAN公開用チャットUI
"""

import os
import socket
import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, Set
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .chatbot import ChatBot

# リクエスト/レスポンスモデル
class ChatRequest(BaseModel):
    message: str
    user_id: str = "web_user"
    is_creator: bool = False

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

class AuthRequest(BaseModel):
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    creator_name: Optional[str] = None


def create_app(chatbot: ChatBot, creator_password: str = "") -> FastAPI:
    """
    FastAPIアプリケーションを作成

    Args:
        chatbot: チャットボットインスタンス
        creator_password: 制作者認証用パスワード

    Returns:
        FastAPIアプリケーション
    """
    # 進行中のタスクを保持する辞書
    # 構造: {task_id: {"status": str, "created_at": datetime, ...}}
    tasks: Dict[str, Any] = {}

    # タスク有効期限の設定
    COMPLETED_TASK_TTL = timedelta(minutes=10)  # 完了済みタスクは10分後に削除
    PROCESSING_TASK_TTL = timedelta(minutes=30)  # 処理中タスクは30分後に強制削除（LLMがハングした場合）

    async def cleanup_expired_tasks():
        """期限切れタスクを定期的に削除するバックグラウンドループ"""
        while True:
            await asyncio.sleep(60)  # 1分ごとにチェック
            now = datetime.now()
            expired_ids = []
            for task_id, task_data in tasks.items():
                created_at = task_data.get("created_at", now)
                status = task_data.get("status", "")
                if status in ("completed", "error"):
                    if now - created_at > COMPLETED_TASK_TTL:
                        expired_ids.append(task_id)
                elif status == "processing":
                    if now - created_at > PROCESSING_TASK_TTL:
                        expired_ids.append(task_id)
                        print(f"[WARN] タスクが長時間処理中のため強制削除: {task_id}")
            for task_id in expired_ids:
                tasks.pop(task_id, None)
            if expired_ids:
                print(f"[CLEANUP] 期限切れタスクを削除: {len(expired_ids)}件")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """アプリ起動・終了時の処理"""
        cleanup_task = asyncio.create_task(cleanup_expired_tasks())
        print("[CLEANUP] タスク自動削除スレッドを起動しました")
        yield
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    app = FastAPI(
        title=f"{chatbot.character.name} - Web Chat",
        description="LAN公開用チャットボットWebインターフェース",
        lifespan=lifespan
    )

    # 静的ファイルのパス
    static_dir = Path(__file__).parent.parent.parent / "static"

    async def generate_response_task(task_id: str, user_id: str, message: str, is_creator: bool = False):
        """バックグラウンドでLLMに応答を生成させるタスク"""
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: chatbot.chat(user_id, message, is_creator=is_creator)
            )
            
            if not response:
                print(f"[WARNING] 空の応答が返されました (user={user_id})")
                response = "（応答を生成できませんでした。もう一度お試しください。）"
            else:
                creator_tag = " [CREATOR]" if is_creator else ""
                print(f"[CHAT] 応答生成完了: {len(response)}文字 (user={user_id}{creator_tag}, task={task_id})")
                
            tasks[task_id] = {
                "status": "completed",
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "character_name": chatbot.character.name,
                "created_at": datetime.now()
            }
        except Exception as e:
            print(f"[ERROR] 応答生成エラー: {e}")
            tasks[task_id] = {
                "status": "error",
                "response": f"（エラーが発生しました: {str(e)}）",
                "timestamp": datetime.now().isoformat(),
                "character_name": chatbot.character.name,
                "created_at": datetime.now()
            }

    @app.post("/api/auth", response_model=AuthResponse)
    async def authenticate(request: AuthRequest):
        """制作者認証エンドポイント"""
        if not creator_password:
            return AuthResponse(success=False, message="認証機能が設定されていません")
        
        if request.password == creator_password:
            creator_name = getattr(chatbot.character.config, 'creator', None) or "制作者"
            print(f"[AUTH] 制作者認証成功: {creator_name}")
            return AuthResponse(
                success=True,
                message=f"認証成功！{creator_name}さん、おかえりなさい。",
                creator_name=creator_name
            )
        else:
            print(f"[AUTH] 制作者認証失敗")
            return AuthResponse(success=False, message="パスワードが違います")

    @app.post("/api/chat", response_model=TaskSubmitResponse)
    async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
        """メッセージを受け付け、タスクIDを返す"""
        task_id = str(uuid.uuid4())
        tasks[task_id] = {"status": "processing", "created_at": datetime.now()}
        
        # バックグラウンドタスクとして生成を開始
        background_tasks.add_task(
            generate_response_task,
            task_id,
            request.user_id,
            request.message,
            request.is_creator
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
            "has_creator_auth": bool(creator_password),
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
    port: int = 8080,
    creator_password: str = ""
):
    """
    Webインターフェースを起動

    Args:
        chatbot: チャットボットインスタンス
        host: バインドするホスト（デフォルト: 0.0.0.0 = 全インターフェース）
        port: ポート番号（デフォルト: 8080）
        creator_password: 制作者認証用パスワード
    """
    import uvicorn

    app = create_app(chatbot, creator_password=creator_password)
    local_ip = get_local_ip()

    print("=" * 60)
    print(f"  {chatbot.character.name} - Web Chat Server")
    print("=" * 60)
    print(f"\n  ローカル:     http://localhost:{port}")
    print(f"  LAN内アクセス: http://{local_ip}:{port}")
    if creator_password:
        print(f"\n  制作者認証:   有効（パスワード設定済み）")
    print(f"\n  同じネットワーク内の端末から上記URLでアクセスできます")
    print(f"  終了するには Ctrl+C を押してください")
    print("=" * 60)

    uvicorn.run(app, host=host, port=port, log_level="info")
