"""
キャラクターモジュール
"""

from .character import Character, CharacterConfig, SpeechStyle
from .prompt_builder import PromptBuilder, ConversationMessage

__all__ = [
    'Character',
    'CharacterConfig', 
    'SpeechStyle',
    'PromptBuilder',
    'ConversationMessage'
]