"""
キャラクター定義とロード機能
"""

import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SpeechStyle(BaseModel):
    """話し方のスタイル"""
    first_person: List[str] = Field(default_factory=list)
    sentence_endings: List[str] = Field(default_factory=list)
    common_phrases: List[str] = Field(default_factory=list)
    emoji_usage: str = "minimal"


class CharacterConfig(BaseModel):
    """キャラクター設定"""
    name: str
    gender: str
    age: str
    personality: str
    speech_style: SpeechStyle
    background: str
    behavior_rules: List[str] = Field(default_factory=list)


class Character:
    """キャラクタークラス"""
    
    def __init__(self, config: CharacterConfig):
        self.config = config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Character':
        """
        JSONファイルからキャラクターをロード
        
        Args:
            config_path: 設定ファイルのパス
        
        Returns:
            Characterインスタンス
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # speech_styleをSpeechStyleオブジェクトに変換
        if isinstance(data.get('speech_style'), dict):
            data['speech_style'] = SpeechStyle(**data['speech_style'])
        
        config = CharacterConfig(**data)
        return cls(config)
    
    @classmethod
    def create_default(cls) -> 'Character':
        """デフォルトのキャラクターを作成"""
        config = CharacterConfig(
            name="アシスタント",
            gender="中性",
            age="不明",
            personality="親切で助けになることが好き",
            speech_style=SpeechStyle(
                first_person=["私"],
                sentence_endings=["です", "ます"],
                common_phrases=["かしこまりました", "お手伝いします"],
                emoji_usage="minimal"
            ),
            background="ユーザーをサポートするために作られたAI",
            behavior_rules=[
                "ユーザーの質問に丁寧に答える",
                "分かりやすい説明を心がける"
            ]
        )
        return cls(config)
    
    @property
    def name(self) -> str:
        """キャラクター名"""
        return self.config.name
    
    def get_system_prompt(self) -> str:
        """
        システムプロンプトを生成
        
        Returns:
            システムプロンプト文字列
        """
        speech_style_text = self._format_speech_style()
        behavior_rules_text = self._format_behavior_rules()
        
        prompt = f"""あなたは{self.config.name}です。

## 基本設定
- 性別: {self.config.gender}
- 年齢: {self.config.age}
- 性格: {self.config.personality}

## 話し方の特徴
{speech_style_text}

## 背景設定
{self.config.background}

## 行動指針
{behavior_rules_text}

この設定に基づいて、一貫したキャラクターとして振る舞ってください。
ユーザーとの過去の会話記憶が提供される場合は、それを考慮して応答してください。"""
        
        return prompt
    
    def _format_speech_style(self) -> str:
        """話し方の特徴をフォーマット"""
        style = self.config.speech_style
        lines = []
        
        if style.first_person:
            lines.append(f"- 一人称: {' または '.join([f'「{p}」' for p in style.first_person])}")
        
        if style.sentence_endings:
            lines.append(f"- 語尾: {' / '.join([f'「{e}」' for e in style.sentence_endings])}")
        
        if style.common_phrases:
            lines.append("- 特徴的な表現:")
            for phrase in style.common_phrases:
                lines.append(f"  * 「{phrase}」")
        
        if style.emoji_usage:
            emoji_desc = {
                "minimal": "絵文字はほぼ使わない（使っても1つまで）",
                "moderate": "適度に絵文字を使用",
                "frequent": "頻繁に絵文字を使用"
            }.get(style.emoji_usage, style.emoji_usage)
            lines.append(f"- {emoji_desc}")
        
        return "\n".join(lines) if lines else "特に制約なし"
    
    def _format_behavior_rules(self) -> str:
        """行動指針をフォーマット"""
        if not self.config.behavior_rules:
            return "特に制約なし"
        
        lines = []
        for i, rule in enumerate(self.config.behavior_rules, 1):
            lines.append(f"{i}. {rule}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """辞書形式で取得"""
        return self.config.model_dump()
    
    def __repr__(self):
        return f"Character(name='{self.name}')"