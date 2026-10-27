"""Conversational Assistant package for multi-turn clinical reasoning."""

from src.conversation.engine import ConversationEngine, get_conversation_engine
from src.conversation.inference_client import (
    BaseInferenceClient,
    MockInferenceClient,
    VLLMInferenceClient,
    get_inference_client,
)
from src.conversation.prompt_builder import PromptBuilder, is_comparison_query
from src.conversation.schemas import ChatRequest, ChatResponse

__all__ = [
    "BaseInferenceClient",
    "ChatRequest",
    "ChatResponse",
    "ConversationEngine",
    "MockInferenceClient",
    "PromptBuilder",
    "VLLMInferenceClient",
    "get_conversation_engine",
    "get_inference_client",
    "is_comparison_query",
]
