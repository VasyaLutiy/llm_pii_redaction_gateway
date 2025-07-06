# services/llm_service.py

import time
import os
import uuid
from typing import Dict, Any, List, Tuple
from llm_pii_proxy.core.models import ChatRequest, ChatResponse
from llm_pii_proxy.core.exceptions import PIIProcessingError, LLMProviderError
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway
from llm_pii_proxy.config.settings import settings, Settings
import asyncio
import re
from llm_pii_proxy.observability import logger as obs_logger

# Настраиваем логгер
logger = obs_logger.get_logger(__name__)

class LLMService:
    def __init__(self, llm_provider: AzureOpenAIProvider, pii_gateway: AsyncPIISecurityGateway):
        self.llm_provider = llm_provider
        self.pii_gateway = pii_gateway
        # Используем централизованные настройки
        self.debug_mode = settings.pii_proxy_debug
        # Создаем свойство для динамической проверки PII
        # Менеджер lock-ов для сериализации tool-запросов по session_id
        self._tool_call_locks: Dict[str, asyncio.Lock] = {}
        # Менеджер lock-ов для строгой последовательности tool-запросов по (session_id, tool_call_id)
        self._tool_call_pair_locks: Dict[Tuple[str, str], asyncio.Lock] = {}
        logger.info(f"🔧 LLMService инициализирован", extra={
            "debug_mode": self.debug_mode,
            "pii_enabled": self.pii_enabled,
            "pii_timeout_minutes": settings.pii_session_timeout_minutes
        })
    
    @property
    def pii_enabled(self) -> bool:
        """Динамически проверяем состояние PII защиты"""
        return Settings().pii_protection_enabled

    def validate_and_correct_messages(self, messages: List[Any]) -> List[Any]:
        """
        Валидация и коррекция массива messages:
        - Для каждого 'tool' сообщения ищет предыдущее assistant с tool_calls и совпадающим tool_call_id.
        - Если не найдено — удаляет лишний 'tool'.
        - Можно доработать под merge/объединение, если потребуется.
        """
        corrected = []
        last_assistant_with_tool_calls = None
        tool_call_ids = set()
        for i, msg in enumerate(messages):
            if getattr(msg, 'role', None) == 'assistant' and hasattr(msg, 'tool_calls') and msg.tool_calls:
                last_assistant_with_tool_calls = msg
                # Собираем все tool_call_id из tool_calls
                for tc in msg.tool_calls:
                    tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                    if tc_id:
                        tool_call_ids.add(tc_id)
                corrected.append(msg)
            elif getattr(msg, 'role', None) == 'tool':
                # Проверяем, есть ли подходящий assistant/tool_calls
                tool_call_id = getattr(msg, 'tool_call_id', None)
                if tool_call_id and tool_call_id in tool_call_ids:
                    corrected.append(msg)
                else:
                    logger.warning(f"Удалено некорректное сообщение 'tool' с tool_call_id={tool_call_id}")
            else:
                corrected.append(msg)
        return corrected

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
                        # Логируем, если найден mermaid-блок
                        if re.search(r'```mermaid', message.content):
                            logger.info(f"[{request_id}] В сообщении {i+1} обнаружен mermaid-блок! Пропускаем маскирование.")
                            masked_messages.append(message)
                            continue
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

            # Валидация и коррекция массива messages
            masked_request.messages = self.validate_and_correct_messages(masked_request.messages)

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
        
        # --- fix: объявляем переменные заранее ---
        accumulated_content = ""
        accumulated_tool_calls = []
        
        # Определяем нужно ли включать PII защиту
        should_protect_pii = self.pii_enabled and request.pii_protection
        
        logger.info(f"🚀 [STREAM {request_id}] Начинаем обработку chat request (stream)", extra={
            "request_id": request_id,
            "session_id": session_id,
            "model": request.model,
            "messages_count": len(request.messages),
            "pii_protection_enabled": should_protect_pii
        })
        
        lock = self._tool_call_locks.setdefault(session_id, asyncio.Lock())
        logger.debug(f"🔒 [STREAM {request_id}] Ожидание lock для session_id={session_id}")
        try:
            async with lock:
                logger.debug(f"✅ [STREAM {request_id}] Lock захвачен для session_id={session_id}")
                if should_protect_pii:
                    logger.info(f"🔒 [STREAM {request_id}] PII защита ВКЛЮЧЕНА для streaming")
                    
                    # Маскируем сообщения
                    masked_messages = []
                    total_pii_count = 0
                    
                    for i, message in enumerate(request.messages):
                        if message.content:
                            # Логируем, если найден mermaid-блок
                            if re.search(r'```mermaid', message.content):
                                logger.info(f"[{request_id}] В сообщении {i+1} обнаружен mermaid-блок! Пропускаем маскирование.")
                                masked_messages.append(message)
                                continue
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

                    # Валидация и коррекция массива messages
                    masked_request.messages = self.validate_and_correct_messages(masked_request.messages)

                    # --- Новый блок: строгая последовательность tool-запросов ---
                    # Если в messages есть tool, то для каждого tool_call_id создаём отдельный lock
                    tool_msgs = [m for m in masked_request.messages if getattr(m, 'role', None) == 'tool']
                    if tool_msgs:
                        # Собираем все tool_call_id для создания locks, но запрос делаем ОДИН раз
                        tool_call_ids = []
                        for tool_msg in tool_msgs:
                            tool_call_id = getattr(tool_msg, 'tool_call_id', None)
                            if tool_call_id:
                                tool_call_ids.append(tool_call_id)
                        
                        # Создаем locks для всех tool_call_id
                        pair_locks = []
                        for tool_call_id in tool_call_ids:
                            pair_lock = self._tool_call_pair_locks.setdefault((session_id, tool_call_id), asyncio.Lock())
                            pair_locks.append((tool_call_id, pair_lock))
                        
                        # Захватываем ВСЕ locks одновременно
                        acquired_locks = []
                        try:
                            for tool_call_id, pair_lock in pair_locks:
                                logger.debug(f"🔒 [STREAM {request_id}] Ожидание pair_lock для (session_id={session_id}, tool_call_id={tool_call_id})")
                                await pair_lock.acquire()
                                acquired_locks.append((tool_call_id, pair_lock))
                                logger.debug(f"✅ [STREAM {request_id}] pair_lock захвачен для (session_id={session_id}, tool_call_id={tool_call_id})")
                            
                            # ОДИН запрос для ВСЕХ tool calls
                            async for chunk in self.llm_provider.create_chat_completion_stream(masked_request):
                                if chunk.choices and len(chunk.choices) > 0:
                                    choice = chunk.choices[0]
                                    delta = choice.get("delta", {})
                                    if delta.get("content"):
                                        accumulated_content += delta["content"]
                                    if delta.get("tool_calls"):
                                        accumulated_tool_calls.extend(delta["tool_calls"])
                                yield chunk
                        finally:
                            # Освобождаем все locks
                            for tool_call_id, pair_lock in acquired_locks:
                                pair_lock.release()
                                # Удаляем lock из словаря
                                self._tool_call_pair_locks.pop((session_id, tool_call_id), None)
                        
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
                        return
                    # --- Конец блока ---
                    # Если нет tool сообщений, обычная обработка
                    async for chunk in self.llm_provider.create_chat_completion_stream(masked_request):
                        if chunk.choices and len(chunk.choices) > 0:
                            choice = chunk.choices[0]
                            delta = choice.get("delta", {})
                            if delta.get("content"):
                                accumulated_content += delta["content"]
                            if delta.get("tool_calls"):
                                accumulated_tool_calls.extend(delta["tool_calls"])
                        yield chunk
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
        finally:
            logger.debug(f"🔓 [STREAM {request_id}] Lock освобожден для session_id={session_id}") 