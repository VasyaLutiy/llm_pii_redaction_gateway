# providers/ollama_provider.py

import logging
import time
import uuid
from typing import AsyncIterator
import httpx
from llm_pii_proxy.core.models import ChatRequest, ChatResponse
from llm_pii_proxy.core.exceptions import LLMProviderError
from llm_pii_proxy.core.interfaces import LLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """
    Ollama provider который притворяется Azure OpenAI для обмана Cursor 🕵️‍♂️
    """
    
    def __init__(self):
        self.base_url = "http://192.168.0.182:11434/v1"
        self.model_name = "qwen2.5:32b-instruct"  # Или любая другая модель в Ollama
        self.client = httpx.AsyncClient(timeout=30.0)
        
        logger.info("🦙 Ollama Provider инициализирован (притворяется Azure OpenAI)")
        logger.info(f"🔗 Base URL: {self.base_url}")
        logger.info(f"🤖 Model: {self.model_name}")
    
    def _model_supports_tools(self) -> bool:
        """
        Притворяемся что поддерживаем tools как Azure OpenAI
        """
        return True
    
    @property
    def provider_name(self) -> str:
        return "ollama-fake-azure"
    
    async def create_chat_completion(self, request: ChatRequest) -> ChatResponse:
        start_time = time.time()
        
        logger.info("🦙 Отправляем запрос к Ollama (притворяемся Azure)", extra={
            "model": self.model_name,
            "messages_count": len(request.messages),
            "session_id": request.session_id
        })
        
        try:
            # Формируем запрос для Ollama
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]
            
            payload = {
                "model": self.model_name,
                "messages": ollama_messages,
                "temperature": request.temperature or 0.7,
                "max_tokens": request.max_tokens,
                "stream": False
            }
            
            # Логируем что отправляем в Ollama
            debug_payload = {k: v for k, v in payload.items() if k != "messages"}
            logger.info(f"🦙 Payload для Ollama: {debug_payload}")
            
            # Отправляем запрос в Ollama
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            ollama_response = response.json()
            
            duration = time.time() - start_time
            
            # Логируем что получили от Ollama
            logger.info(f"🦙 RAW OLLAMA RESPONSE: {ollama_response}")
            
            # Извлекаем контент от Ollama
            ollama_content = ""
            if "choices" in ollama_response and len(ollama_response["choices"]) > 0:
                choice = ollama_response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    ollama_content = choice["message"]["content"]
            
            logger.info(f"🦙 Контент от Ollama: {ollama_content[:100]}...")
            
            # ПОДДЕЛЫВАЕМ Azure OpenAI response! 🎭
            fake_azure_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
            fake_azure_response = ChatResponse(
                id=fake_azure_id,
                model="gpt-4.1",  # 🎭 ПРИТВОРЯЕМСЯ что это Azure gpt-4.1
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ollama_content,
                        "tool_calls": []  # Показываем что поддерживаем tools
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": 50,  # Фейковые токены
                    "completion_tokens": len(ollama_content.split()),
                    "total_tokens": 50 + len(ollama_content.split())
                },
                system_fingerprint="fp_ollama_fake_azure",  # 🎭 Фейковый fingerprint
                service_tier="default"
            )
            
            logger.info("🎭 ПОДДЕЛАННЫЙ Azure response создан!", extra={
                "fake_id": fake_azure_id,
                "model": "gpt-4.1",
                "duration_ms": round(duration * 1000, 2),
                "content_length": len(ollama_content)
            })
            
            return fake_azure_response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("💥 Ошибка при запросе к Ollama", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration * 1000, 2),
                "session_id": request.session_id
            })
            raise LLMProviderError(f"Ollama error: {str(e)}")
    
    async def create_chat_completion_stream(self, request: ChatRequest) -> AsyncIterator[ChatResponse]:
        """
        Streaming для Ollama (тоже притворяемся Azure)
        """
        start_time = time.time()
        
        logger.info("🦙 Начинаем стриминг к Ollama (притворяемся Azure)", extra={
            "model": self.model_name,
            "messages_count": len(request.messages),
            "session_id": request.session_id
        })
        
        try:
            # Формируем запрос для Ollama streaming
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]
            
            payload = {
                "model": self.model_name,
                "messages": ollama_messages,
                "temperature": request.temperature or 0.7,
                "max_tokens": request.max_tokens,
                "stream": True
            }
            
            logger.info(f"🦙 STREAMING Payload для Ollama: {payload}")
            
            fake_azure_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
            chunk_count = 0
            
            # Streaming запрос к Ollama
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk_count += 1
                        if chunk_count == 1:
                            first_chunk_time = time.time() - start_time
                            logger.debug(f"🦙 Первый chunk от Ollama за {round(first_chunk_time * 1000, 2)}ms")
                        
                        chunk_data = line[6:]  # Убираем "data: "
                        if chunk_data.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            ollama_chunk = json.loads(chunk_data)
                            
                            # Извлекаем контент из Ollama chunk
                            content = ""
                            if "choices" in ollama_chunk and len(ollama_chunk["choices"]) > 0:
                                choice = ollama_chunk["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                            
                            # ПОДДЕЛЫВАЕМ Azure streaming chunk! 🎭
                            fake_chunk = ChatResponse(
                                id=fake_azure_id,
                                model="gpt-4.1",  # 🎭 ПРИТВОРЯЕМСЯ Azure
                                choices=[{
                                    "index": 0,
                                    "delta": {
                                        "content": content
                                    },
                                    "finish_reason": None
                                }],
                                usage=None
                            )
                            
                            yield fake_chunk
                            
                        except json.JSONDecodeError:
                            continue
            
            # Финальный chunk
            final_chunk = ChatResponse(
                id=fake_azure_id,
                model="gpt-4.1",
                choices=[{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }],
                usage=None
            )
            yield final_chunk
            
            total_duration = time.time() - start_time
            logger.info("🦙 Ollama стриминг завершен", extra={
                "chunks_received": chunk_count,
                "total_duration_ms": round(total_duration * 1000, 2),
                "session_id": request.session_id
            })
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("💥 Ошибка при стриминге Ollama", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration * 1000, 2),
                "session_id": request.session_id
            })
            raise LLMProviderError(f"Ollama streaming error: {str(e)}")
    
    async def health_check(self) -> bool:
        logger.debug("🦙 Проверка здоровья Ollama...")
        start_time = time.time()
        
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            
            duration = time.time() - start_time
            logger.info("🦙 Ollama health check успешен", extra={
                "duration_ms": round(duration * 1000, 2)
            })
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            logger.warning("🔴 Ollama health check неуспешен", extra={
                "error": str(e),
                "duration_ms": round(duration * 1000, 2)
            })
            return False 