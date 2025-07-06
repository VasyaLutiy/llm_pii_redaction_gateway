# providers/azure_provider.py - ПРОСТАЯ ВЕРСИЯ С ПОЛНЫМ СТРИМИНГОМ

import asyncio
import os
import time
from typing import AsyncIterator
from openai import AsyncAzureOpenAI
from llm_pii_proxy.core.models import ChatRequest, ChatResponse
from llm_pii_proxy.core.interfaces import LLMProvider
from llm_pii_proxy.core.exceptions import LLMProviderError
from llm_pii_proxy.config.settings import settings
from llm_pii_proxy.observability import logger as obs_logger

logger = obs_logger.get_logger(__name__)

class AzureOpenAIProvider(LLMProvider):
    def __init__(self):
        # Используем settings вместо прямых переменных окружения
        self.api_key = settings.azure_openai_api_key
        self.endpoint = settings.azure_openai_endpoint
        self.deployment_name = settings.azure_completions_model
        self.api_version = settings.azure_openai_api_version
        
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
        
        logger.debug("☁️ Azure OpenAI Provider инициализирован", extra={
            "endpoint": self.endpoint,
            "deployment": self.deployment_name,
            "api_version": self.api_version
        })

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    async def create_chat_completion(self, request: ChatRequest) -> ChatResponse:
        start_time = time.time()
        
        logger.debug("📤 Отправляем запрос к Azure OpenAI", extra={
            "model": self.deployment_name,
            "messages_count": len(request.messages),
            "session_id": request.session_id
        })
        
        try:
            # ПРОЗРАЧНОЕ преобразование сообщений - БЕЗ ФИЛЬТРАЦИИ!
            azure_messages = []
            for msg in request.messages:
                azure_msg = {"role": msg.role, "content": msg.content}
                
                # Добавляем tool_calls если есть в assistant сообщении
                if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    azure_msg["tool_calls"] = msg.tool_calls
                
                # Добавляем tool_call_id если есть в tool сообщении
                if msg.role == "tool" and hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                    azure_msg["tool_call_id"] = msg.tool_call_id
                
                azure_messages.append(azure_msg)
            
            # Формируем payload
            payload = {
                "model": self.deployment_name,
                "messages": azure_messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": False
            }
            
            # Добавляем tools если есть
            if request.tools:
                payload["tools"] = request.tools
                logger.debug(f"🔧 Добавлены tools: {len(request.tools)}")
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice
                logger.debug(f"🎯 Добавлен tool_choice: {request.tool_choice}")
            
            logger.debug(f"📤 Отправляем {len(azure_messages)} сообщений в Azure OpenAI")
            
            # 🔍 ПОЛНАЯ ОТЛАДКА ВХОДЯЩИХ СООБЩЕНИЙ
            logger.debug("🔍 ПОЛНЫЙ PAYLOAD ДЛЯ AZURE OPENAI:")
            import json
            logger.debug(json.dumps(payload, indent=2, ensure_ascii=False))
            
            response = await self.client.chat.completions.create(**payload)
            
            duration = time.time() - start_time
            logger.debug("📨 Получен ответ от Azure OpenAI", extra={
                "duration_ms": round(duration * 1000, 2),
                "choices": len(response.choices)
            })
            
            # 🔍 ПОЛНАЯ ОТЛАДКА ОТВЕТА ОТ AZURE
            logger.debug("🔍 ПОЛНЫЙ RAW ОТВЕТ ОТ AZURE OPENAI:")
            logger.debug(f"   ID: {response.id}")
            logger.debug(f"   Model: {response.model}")
            logger.debug(f"   Object: {response.object}")
            logger.debug(f"   Created: {response.created}")
            logger.debug(f"   Choices count: {len(response.choices)}")
            
            for i, choice in enumerate(response.choices):
                logger.debug(f"   Choice {i}:")
                logger.debug(f"     Index: {choice.index}")
                logger.debug(f"     Finish reason: {choice.finish_reason}")
                logger.debug(f"     Message role: {choice.message.role}")
                logger.debug(f"     Message content: {choice.message.content}")
                
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    logger.debug(f"     Tool calls: {len(choice.message.tool_calls)}")
                    for j, tc in enumerate(choice.message.tool_calls):
                        logger.debug(f"       Tool call {j}: ID={tc.id}, Type={tc.type}")
                        logger.debug(f"       Function: {tc.function.name}")
                        logger.debug(f"       Arguments: {tc.function.arguments}")
                else:
                    logger.debug(f"     Tool calls: None")
            
            if response.usage:
                logger.debug(f"   Usage: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}")
            
            # 🔍 ПОЛНЫЙ JSON DUMP
            import json
            try:
                response_dict = response.model_dump()
                logger.debug("🔍 AZURE RESPONSE JSON:")
                logger.debug(json.dumps(response_dict, indent=2, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"Не удалось сериализовать ответ: {e}")
                logger.debug(f"🔍 AZURE RESPONSE STR: {str(response)}")
            
            # ПРОЗРАЧНОЕ преобразование ответа
            choices = []
            for choice in response.choices:
                message = {
                    "role": choice.message.role,
                    "content": choice.message.content or ""
                }
                
                # Добавляем tool_calls если есть
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    message["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in choice.message.tool_calls
                    ]
                    logger.debug(f"🔧 Ответ содержит {len(choice.message.tool_calls)} tool_calls")
                
                choices.append({
                    "index": choice.index,
                    "message": message,
                    "finish_reason": choice.finish_reason
                })
            
            final_response = ChatResponse(
                id=response.id,
                model=response.model,
                choices=choices,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None
            )
            
            # 🔍 ПОЛНАЯ ОТЛАДКА ФИНАЛЬНОГО ОТВЕТА
            logger.debug("🔍 ФИНАЛЬНЫЙ ОТВЕТ ДЛЯ КЛИЕНТА:")
            logger.debug(json.dumps(final_response.model_dump(), indent=2, ensure_ascii=False))
            
            return final_response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("💥 Ошибка при запросе к Azure OpenAI", extra={
                "error": str(e),
                "duration_ms": round(duration * 1000, 2)
            })
            raise LLMProviderError(f"Azure OpenAI error: {str(e)}")

    async def create_chat_completion_stream(self, request: ChatRequest) -> AsyncIterator[ChatResponse]:
        start_time = time.time()
        
        logger.debug("🔄 Начинаем стриминг к Azure OpenAI", extra={
            "model": self.deployment_name,
            "messages_count": len(request.messages),
            "session_id": request.session_id
        })
        
        try:
            # ПРОЗРАЧНОЕ преобразование сообщений - БЕЗ ФИЛЬТРАЦИИ!
            azure_messages = []
            for msg in request.messages:
                azure_msg = {"role": msg.role, "content": msg.content}
                
                # Добавляем tool_calls если есть в assistant сообщении
                if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    azure_msg["tool_calls"] = msg.tool_calls
                
                # Добавляем tool_call_id если есть в tool сообщении
                if msg.role == "tool" and hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                    azure_msg["tool_call_id"] = msg.tool_call_id
                
                azure_messages.append(azure_msg)
            
            # Формируем payload для стриминга
            payload = {
                "model": self.deployment_name,
                "messages": azure_messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True
            }
            
            # Добавляем tools если есть
            if request.tools:
                payload["tools"] = request.tools
                logger.debug(f"🔧 STREAMING: Добавлены tools: {len(request.tools)}")
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice
                logger.debug(f"🎯 STREAMING: Добавлен tool_choice: {request.tool_choice}")
            
            logger.debug(f"🔄 STREAMING: Отправляем {len(azure_messages)} сообщений в Azure OpenAI")
            
            # 🔍 ПОЛНАЯ ОТЛАДКА STREAMING PAYLOAD
            logger.debug("🔍 STREAMING PAYLOAD ДЛЯ AZURE OPENAI:")
            import json
            logger.debug(json.dumps(payload, indent=2, ensure_ascii=False))
            
            chunk_count = 0
            stream = await self.client.chat.completions.create(**payload)
            
            async for response in stream:
                chunk_count += 1
                if chunk_count == 1:
                    first_chunk_time = time.time() - start_time
                    logger.debug(f"⚡ Первый chunk получен за {round(first_chunk_time * 1000, 2)}ms")
                
                # 🔍 ОТЛАДКА КАЖДОГО CHUNK
                logger.debug(f"🔍 CHUNK {chunk_count} ОТ AZURE:")
                try:
                    chunk_dict = response.model_dump()
                    logger.debug(json.dumps(chunk_dict, indent=2, ensure_ascii=False))
                except Exception as e:
                    logger.warning(f"Не удалось сериализовать chunk: {e}")
                    logger.debug(f"🔍 CHUNK {chunk_count} STR: {str(response)}")
                
                # Формируем choices для streaming response
                choices = []
                for choice in response.choices:
                    delta = {}
                    
                    # Добавляем role только если он есть
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'role') and choice.delta.role:
                        delta["role"] = choice.delta.role
                    
                    # Добавляем content только если он есть
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content') and choice.delta.content:
                        delta["content"] = choice.delta.content
                    
                    # Добавляем tool_calls только если они есть
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                        delta["tool_calls"] = []
                        for tc in choice.delta.tool_calls:
                            tool_call = {
                                "index": getattr(tc, 'index', 0),
                                "id": getattr(tc, 'id', None),
                                "type": getattr(tc, 'type', 'function'),
                                "function": {}
                            }
                            
                            # Добавляем function данные только если они есть
                            if hasattr(tc, 'function') and tc.function:
                                if hasattr(tc.function, 'name') and tc.function.name is not None:
                                    tool_call["function"]["name"] = tc.function.name
                                if hasattr(tc.function, 'arguments') and tc.function.arguments is not None:
                                    tool_call["function"]["arguments"] = tc.function.arguments
                            
                            # ВСЕГДА добавляем tool_call если он есть в chunk от Azure
                            # Cursor соберет все части самостоятельно
                            delta["tool_calls"].append(tool_call)
                    
                    choices.append({
                        "index": choice.index,
                        "delta": delta,
                        "finish_reason": choice.finish_reason
                    })
                
                final_chunk = ChatResponse(
                    id=response.id,
                    model=response.model,
                    choices=choices,
                    usage=None  # Usage обычно приходит в последнем chunk
                )
                
                # 🔍 ОТЛАДКА ФИНАЛЬНОГО CHUNK ДЛЯ КЛИЕНТА
                logger.debug(f"🔍 ФИНАЛЬНЫЙ CHUNK {chunk_count} ДЛЯ КЛИЕНТА:")
                logger.debug(json.dumps(final_chunk.model_dump(), indent=2, ensure_ascii=False))
                
                yield final_chunk
            
            total_duration = time.time() - start_time
            logger.debug("✅ Стриминг завершен", extra={
                "chunks_received": chunk_count,
                "total_duration_ms": round(total_duration * 1000, 2)
            })
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("💥 Ошибка при стриминге Azure OpenAI", extra={
                "error": str(e),
                "duration_ms": round(duration * 1000, 2)
            })
            raise LLMProviderError(f"Azure OpenAI streaming error: {str(e)}")

    async def health_check(self) -> bool:
        logger.debug("🏥 Проверка здоровья Azure OpenAI...")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            logger.debug("💚 Azure OpenAI health check успешен")
            return True
            
        except Exception as e:
            logger.warning(f"🔴 Azure OpenAI health check неуспешен: {str(e)}")
            return False 