# core/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None  # Для tool сообщений

class ChatRequest(BaseModel):
    model: str = Field(description="LLM model name")
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    stream: bool = False
    session_id: Optional[str] = Field(default=None, description="Session ID for PII tracking")
    pii_protection: bool = Field(default=True)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    functions: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
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