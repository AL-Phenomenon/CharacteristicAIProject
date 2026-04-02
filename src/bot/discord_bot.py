"""
Discord Botインターフェース
DiscordでHARKAと会話できるようにする
"""

import discord
from discord.ext import commands
import asyncio
from typing import Optional
from .chatbot import ChatBot


class DiscordBot:
    """Discord Botクラス"""
    
    def __init__(
        self,
        chatbot: ChatBot,
        token: str,
        command_prefix: str = "!",
        status_message: str = None
    ):
        """
        Args:
            chatbot: チャットボットインスタンス
            token: Discord Botトークン
            command_prefix: コマンドプレフィックス
            status_message: Botのステータスメッセージ
        """
        self.chatbot = chatbot
        self.token = token
        self.status_message = status_message or f"{chatbot.character.name}と会話中"
        
        # Intentsの設定（メッセージ内容を読み取るために必要）
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Botの初期化
        self.bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None  # デフォルトのhelpコマンドを無効化
        )
        
        # イベントハンドラを登録
        self._setup_events()
        self._setup_commands()
    
    def _setup_events(self):
        """イベントハンドラを設定"""
        
        @self.bot.event
        async def on_ready():
            """Bot起動時の処理"""
            print(f"\n{'=' * 60}")
            print(f"  Discord Bot '{self.chatbot.character.name}' が起動しました")
            print(f"{'=' * 60}")
            print(f"Bot名: {self.bot.user.name}")
            print(f"Bot ID: {self.bot.user.id}")
            print(f"接続サーバー数: {len(self.bot.guilds)}")
            print(f"{'=' * 60}\n")
            
            # ステータスを設定
            await self.bot.change_presence(
                activity=discord.Game(name=self.status_message)
            )
        
        @self.bot.event
        async def on_message(message: discord.Message):
            """メッセージ受信時の処理"""
            # Bot自身のメッセージは無視
            if message.author.bot:
                return
            
            # コマンドの処理を優先
            await self.bot.process_commands(message)
            
            # メンション、リプライ、DMの場合のみ応答
            is_mentioned = self.bot.user in message.mentions
            is_reply = message.reference is not None
            is_dm = isinstance(message.channel, discord.DMChannel)
            
            if is_mentioned or is_reply or is_dm:
                # メンションを削除
                content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                if not content:
                    return
                
                # タイピングインジケーターを表示
                async with message.channel.typing():
                    # ユーザーIDを取得（Discord固有のID）
                    user_id = f"discord_{message.author.id}"
                    
                    # チャットボットで応答を生成
                    response = await asyncio.to_thread(
                        self.chatbot.chat,
                        user_id,
                        content
                    )
                    
                    # 応答を送信（2000文字制限対応）
                    await self._send_long_message(message.channel, response)
    
    def _setup_commands(self):
        """コマンドを設定"""
        
        @self.bot.command(name='ping')
        async def ping_command(ctx):
            """応答速度を確認"""
            latency = round(self.bot.latency * 1000)
            await ctx.send(f"🏓 Pong! 応答速度: {latency}ms")
        
        @self.bot.command(name='stats')
        async def stats_command(ctx):
            """統計情報を表示"""
            user_id = f"discord_{ctx.author.id}"
            stats = self.chatbot.get_user_stats(user_id)
            memory_stats = self.chatbot.memory.get_statistics()
            
            embed = discord.Embed(
                title=f"📊 {self.chatbot.character.name} 統計情報",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="あなたの記憶",
                value=f"長期記憶: {stats['long_term_memories']}件\n短期記憶: {stats['short_term_messages']}件",
                inline=False
            )
            embed.add_field(
                name="システム全体",
                value=f"総記憶数: {memory_stats['total_memories']}件\nユーザー数: {memory_stats['unique_users']}人",
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='clear')
        async def clear_command(ctx):
            """短期記憶をクリア"""
            user_id = f"discord_{ctx.author.id}"
            self.chatbot.clear_short_term_memory(user_id)
            await ctx.send("✅ 会話履歴をクリアしました（長期記憶は保持されます）")
        
        @self.bot.command(name='help')
        async def help_command(ctx):
            """ヘルプを表示"""
            embed = discord.Embed(
                title=f"📖 {self.chatbot.character.name} ヘルプ",
                description="HARKAとの会話方法とコマンド一覧",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="💬 会話の仕方",
                value="• メンション: @HARKAをつけてメッセージ\n• リプライ: HARKAのメッセージに返信\n• DM: ダイレクトメッセージで直接会話",
                inline=False
            )
            
            embed.add_field(
                name="🔧 コマンド",
                value="`!ping` - 応答速度を確認\n`!stats` - 統計情報を表示\n`!clear` - 会話履歴をクリア\n`!help` - このヘルプを表示",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    async def _send_long_message(self, channel, text: str):
        """
        長いメッセージを分割して送信（Discord 2000文字制限対応）
        
        Args:
            channel: 送信先チャンネル
            text: 送信するテキスト
        """
        max_length = 2000
        
        if len(text) <= max_length:
            await channel.send(text)
            return
        
        # 2000文字ごとに分割
        chunks = []
        while len(text) > max_length:
            # 改行で分割できる位置を探す
            split_pos = text.rfind('\n', 0, max_length)
            if split_pos == -1:
                split_pos = max_length
            
            chunks.append(text[:split_pos])
            text = text[split_pos:].lstrip()
        
        if text:
            chunks.append(text)
        
        # 順番に送信
        for chunk in chunks:
            await channel.send(chunk)
            await asyncio.sleep(0.5)  # レート制限対策
    
    def run(self):
        """Botを起動"""
        try:
            print("Discord Botを起動中...")
            self.bot.run(self.token)
        except discord.LoginFailure:
            print("\n❌ エラー: Discord Botトークンが無効です")
            print("DISCORD_BOT_TOKENを確認してください")
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            import traceback
            traceback.print_exc()


def run_discord_bot(chatbot: ChatBot, token: str, status_message: Optional[str] = None):
    """
    Discord Botを実行
    
    Args:
        chatbot: チャットボットインスタンス
        token: Discord Botトークン
        status_message: ステータスメッセージ
    """
    discord_bot = DiscordBot(chatbot, token, status_message=status_message)
    discord_bot.run()