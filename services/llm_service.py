# services/llm_service.py

import logging
import time
import os
import uuid
from typing import Dict, Any
from llm_pii_proxy.core.models import ChatRequest, ChatResponse
from llm_pii_proxy.core.exceptions import PIIProcessingError, LLMProviderError
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway
from llm_pii_proxy.config.settings import settings, Settings

# Настраиваем логгер
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, llm_provider: AzureOpenAIProvider, pii_gateway: AsyncPIISecurityGateway):
        self.llm_provider = llm_provider
        self.pii_gateway = pii_gateway
        # Используем централизованные настройки
        self.debug_mode = settings.pii_proxy_debug
        # Создаем свойство для динамической проверки PII
        
        logger.info(f"🔧 LLMService инициализирован", extra={
            "debug_mode": self.debug_mode,
            "pii_enabled": self.pii_enabled,
            "pii_timeout_minutes": settings.pii_session_timeout_minutes
        })
    
    @property
    def pii_enabled(self) -> bool:
        """Динамически проверяем состояние PII защиты"""
        return Settings().pii_protection_enabled

    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        request_id = f"req_{int(time.time() * 1000)}"  # Простой ID для трекинга
        
        # Генерируем session_id если не передан
        session_id = request.session_id or uuid.uuid4().hex
        
        logger.info(f"🚀 [{request_id}] Начинаем обработку chat request", extra={
            "request_id": request_id,
            "session_id": session_id,
            "model": request.model,
            "messages_count": len(request.messages),
            "pii_enabled_global": self.pii_enabled,
            "pii_protection_requested": request.pii_protection
        })
        
        try:
            # Определяем нужно ли включать PII защиту
            should_protect_pii = self.pii_enabled and request.pii_protection
            
            if should_protect_pii:
                logger.info(f"🔒 [{request_id}] PII защита ВКЛЮЧЕНА")
                
                # 1. Mask PII in messages
                masked_messages = []
                total_pii_count = 0
                
                for i, message in enumerate(request.messages):
                    if message.content:  # Только если есть контент
                        try:
                            pii_result = await self.pii_gateway.mask_sensitive_data(
                                content=message.content,
                                session_id=session_id
                            )
                            
                            masked_message = message.model_copy()
                            masked_message.content = pii_result.content
                            masked_messages.append(masked_message)
                            total_pii_count += pii_result.pii_count
                            
                            if pii_result.pii_count > 0:
                                logger.info(f"🔍 [{request_id}] Сообщение {i+1}: найдено {pii_result.pii_count} PII элементов")
                            
                        except Exception as e:
                            logger.error(f"❌ [{request_id}] Ошибка маскирования сообщения {i+1}: {e}")
                            # В случае ошибки используем оригинальное сообщение
                            masked_messages.append(message)
                    else:
                        # Сообщение без контента
                        masked_messages.append(message)
                
                if total_pii_count > 0:
                    logger.info(f"🔒 [{request_id}] Всего замаскировано {total_pii_count} PII элементов")
                
                masked_request = request.model_copy()
                masked_request.messages = masked_messages
            else:
                logger.info(f"⚠️ [{request_id}] PII защита ОТКЛЮЧЕНА (глобально: {self.pii_enabled}, запрос: {request.pii_protection})")
                masked_request = request
                total_pii_count = 0

            # 2. Call LLM provider with masked request
            logger.info(f"🌐 [{request_id}] Этап 2: Отправка запроса к внешней LLM...")
            
            # Показываем что именно отправляем в LLM
            if self.debug_mode:
                logger.debug(f"📤 [{request_id}] Отправляем в LLM следующие сообщения:")
                for i, msg in enumerate(masked_request.messages):
                    logger.debug(f"    {i+1}. {msg.role}: {msg.content}")
            
            start_time = time.time()
            response = await self.llm_provider.create_chat_completion(masked_request)
            llm_duration = time.time() - start_time

            # 3. Unmask PII in response if protection was enabled
            if should_protect_pii and total_pii_count > 0:
                logger.info(f"🔓 [{request_id}] Этап 3: Демаскирование ответа...")
                
                try:
                    # Демаскируем контент в ответах
                    for choice in response.choices:
                        if choice.get("message", {}).get("content"):
                            original_content = choice["message"]["content"]
                            unmasked_content = await self.pii_gateway.unmask_sensitive_data(
                                content=original_content,
                                session_id=session_id
                            )
                            choice["message"]["content"] = unmasked_content
                            
                            if original_content != unmasked_content:
                                logger.info(f"🔄 [{request_id}] Демаскирован контент ответа")
                        
                        # Демаскируем tool calls если есть
                        if choice.get("message", {}).get("tool_calls"):
                            for tool_call in choice["message"]["tool_calls"]:
                                if tool_call.get("function", {}).get("arguments"):
                                    original_args = tool_call["function"]["arguments"]
                                    unmasked_args = await self.pii_gateway.unmask_sensitive_data(
                                        content=original_args,
                                        session_id=session_id
                                    )
                                    tool_call["function"]["arguments"] = unmasked_args
                                    
                                    if original_args != unmasked_args:
                                        logger.info(f"🔄 [{request_id}] Демаскированы аргументы tool call")
                    
                    # Очищаем сессию после обработки
                    await self.pii_gateway.clear_session(session_id)
                    logger.info(f"🧹 [{request_id}] PII сессия очищена")
                    
                except Exception as e:
                    logger.error(f"❌ [{request_id}] Ошибка демаскирования: {e}")
                    # В случае ошибки возвращаем замаскированный ответ
            else:
                logger.info(f"ℹ️ [{request_id}] Демаскирование не требуется")

            # После получения ответа от Azure, если model начинается с 'gpt-4.1', подменяем на 'gpt-4.1' для Cursor
            if hasattr(response, 'model') and isinstance(response.model, str) and response.model.startswith('gpt-4.1'):
                response.model = 'gpt-4.1'

            logger.info(f"🎉 [{request_id}] Обработка завершена успешно!", extra={
                "request_id": request_id,
                "total_pii_found": total_pii_count,
                "llm_duration_ms": round(llm_duration * 1000, 2),
                "pii_protection_used": should_protect_pii
            })

            return response
            
        except Exception as e:
            logger.error(f"❌ [{request_id}] Ошибка при обработке запроса: {str(e)}", extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            # Перебрасываем специфичные исключения как есть
            if isinstance(e, (PIIProcessingError, LLMProviderError)):
                raise
            # Остальные исключения оборачиваем
            raise PIIProcessingError(f"LLMService error: {str(e)}") 

    async def process_chat_request_stream(self, request: ChatRequest):
        """
        Аналог process_chat_request, но возвращает async-генератор ChatResponse-чанков для stream-режима.
        """
        request_id = f"req_{int(time.time() * 1000)}"
        session_id = request.session_id or uuid.uuid4().hex
        
        # Определяем нужно ли включать PII защиту
        should_protect_pii = self.pii_enabled and request.pii_protection
        
        logger.info(f"🚀 [STREAM {request_id}] Начинаем обработку chat request (stream)", extra={
            "request_id": request_id,
            "session_id": session_id,
            "model": request.model,
            "messages_count": len(request.messages),
            "pii_protection_enabled": should_protect_pii
        })
        
        try:
            if should_protect_pii:
                logger.info(f"🔒 [STREAM {request_id}] PII защита ВКЛЮЧЕНА для streaming")
                
                # Маскируем сообщения
                masked_messages = []
                total_pii_count = 0
                
                for i, message in enumerate(request.messages):
                    if message.content:
                        try:
                            pii_result = await self.pii_gateway.mask_sensitive_data(
                                content=message.content,
                                session_id=session_id
                            )
                            
                            masked_message = message.model_copy()
                            masked_message.content = pii_result.content
                            masked_messages.append(masked_message)
                            total_pii_count += pii_result.pii_count
                            
                        except Exception as e:
                            logger.error(f"❌ [STREAM {request_id}] Ошибка маскирования: {e}")
                            masked_messages.append(message)
                    else:
                        masked_messages.append(message)
                
                masked_request = request.model_copy()
                masked_request.messages = masked_messages
                
                # Собираем все chunks для последующего демаскирования
                accumulated_content = ""
                accumulated_tool_calls = []
                
                async for chunk in self.llm_provider.create_chat_completion_stream(masked_request):
                    # Аккумулируем контент для демаскирования
                    if chunk.choices and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            accumulated_content += delta["content"]
                        if delta.get("tool_calls"):
                            accumulated_tool_calls.extend(delta["tool_calls"])
                    
                    # Отдаем chunk как есть (пока замаскированный)
                    yield chunk
                
                # После завершения streaming демаскируем аккумулированный контент
                if should_protect_pii and total_pii_count > 0:
                    logger.info(f"🔓 [STREAM {request_id}] Демаскирование завершенного streaming контента...")
                    
                    try:
                        # Демаскируем аккумулированный контент (опционально)
                        if accumulated_content:
                            unmasked_content = await self.pii_gateway.unmask_sensitive_data(
                                content=accumulated_content,
                                session_id=session_id
                            )
                            logger.info(f"🔄 [STREAM {request_id}] Демаскирован streaming контент")
                        
                        # Очищаем сессию
                        await self.pii_gateway.clear_session(session_id)
                        logger.info(f"🧹 [STREAM {request_id}] PII сессия очищена")
                        
                    except Exception as e:
                        logger.error(f"❌ [STREAM {request_id}] Ошибка демаскирования streaming: {e}")
                
            else:
                logger.info(f"⚠️ [STREAM {request_id}] PII защита ОТКЛЮЧЕНА для streaming")
                
                # Простое проксирование без PII защиты
                async for chunk in self.llm_provider.create_chat_completion_stream(request):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"❌ [STREAM {request_id}] Ошибка при обработке stream-запроса: {str(e)}", extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise 