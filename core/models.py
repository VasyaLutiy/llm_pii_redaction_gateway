# core/models.py

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, List[Dict[str, Any]]]  # Поддерживаем оба формата
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None  # Для tool сообщений

    @field_validator('content')
    @classmethod
    def normalize_content(cls, v):
        """Конвертируем структурированный content в простую строку"""
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            # Извлекаем text из всех объектов типа "text"
            text_parts = []
            for item in v:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "\n".join(text_parts)
        else:
            return str(v)

class ChatRequest(BaseModel):
    model: str = Field(description="LLM model name")
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)  # Для совместимости
    max_completion_tokens: Optional[int] = Field(default=None, gt=0)
    stream: bool = False
    session_id: Optional[str] = Field(default=None, description="Session ID for PII tracking")
    pii_protection: bool = Field(default=True)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    functions: Optional[List[Dict[str, Any]]] = None
    
    @property 
    def effective_max_tokens(self) -> Optional[int]:
        """Возвращает max_completion_tokens если задан, иначе max_tokens"""
        return self.max_completion_tokens or self.max_tokens

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None
    # Дополнительные метаданные для совместимости с Cursor
    system_fingerprint: Optional[str] = None
    service_tier: Optional[str] = None

class PIIMapping(BaseModel):
    original: str
    masked: str
    type: str
    created_at: datetime

class PIIResult(BaseModel):
    content: str
    mappings: List[PIIMapping]
    session_id: str
    pii_count: int 