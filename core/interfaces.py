# core/interfaces.py

from abc import ABC, abstractmethod
from typing import AsyncIterator
from .models import ChatRequest, ChatResponse, PIIResult

class LLMProvider(ABC):
    @abstractmethod
    async def create_chat_completion(self, request: ChatRequest) -> ChatResponse:
        pass

    @abstractmethod
    async def create_chat_completion_stream(self, request: ChatRequest) -> AsyncIterator[ChatResponse]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

class PIISecurityGateway(ABC):
    @abstractmethod
    async def mask_sensitive_data(self, content: str, session_id: str) -> PIIResult:
        pass

    @abstractmethod
    async def unmask_sensitive_data(self, content: str, session_id: str) -> str:
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        pass 