# security/pii_gateway.py

# PII redaction logic will go here. 

import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict
from llm_pii_proxy.core.models import PIIResult, PIIMapping
from llm_pii_proxy.core.interfaces import PIISecurityGateway
from llm_pii_proxy.core.exceptions import PIISessionNotFoundError, PIIProcessingError
from .pii_redaction import PIIRedactionGateway, RedactionMapping
import asyncio

# Настраиваем логгер
logger = logging.getLogger(__name__)

class AsyncPIISecurityGateway(PIISecurityGateway):
    def __init__(self, session_timeout_minutes: int = 60):
        self.redaction_gateway = PIIRedactionGateway()
        self.sessions: Dict[str, dict] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.debug_mode = os.getenv('PII_PROXY_DEBUG', 'false').lower() == 'true'
        logger.info(f"🔐 PII Gateway инициализирован с timeout {session_timeout_minutes} минут")

    async def _cleanup_expired_sessions(self):
        """Очищает истекшие сессии"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if current_time - session_data["last_accessed"] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"🧹 Автоочистка истекшей сессии: {session_id}")
            self.sessions.pop(session_id, None)
        
        if expired_sessions:
            logger.info(f"🧹 Очищено {len(expired_sessions)} истекших сессий")

    async def mask_sensitive_data(self, content: str, session_id: str) -> PIIResult:
        start_time = time.time()
        
        # Валидация входных данных
        if not session_id:
            raise PIIProcessingError("Session ID cannot be empty")
        
        # Разрешаем пустой контент (может быть в streaming режиме)
        if not content:
            logger.debug(f"ℹ️ [{session_id}] Пустой контент, возвращаем как есть")
            return PIIResult(
                content="",
                mappings=[],
                session_id=session_id,
                pii_count=0
            )
        
        # Очистка истекших сессий
        await self._cleanup_expired_sessions()
        
        logger.debug(f"🔍 [{session_id}] Начинаем маскирование PII данных", extra={
            "session_id": session_id,
            "content_length": len(content),
            "content_preview": content[:50] + "..." if len(content) > 50 else content
        })
        
        # Не логируем полный контент даже в DEBUG режиме для безопасности
        if self.debug_mode:
            logger.debug(f"📄 [{session_id}] Обрабатываем контент длиной {len(content)} символов")
        
        # Create session if needed
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": datetime.now(),
                "last_accessed": datetime.now(),
                "mappings": {}
            }
            logger.info(f"📝 [{session_id}] Создана новая PII сессия")
        else:
            logger.debug(f"🔄 [{session_id}] Используем существующую PII сессию")
        
        try:
            # Clear previous mappings before processing new content
            self.redaction_gateway.clear_mapping()
            
            # Use existing PII gateway (sync, so run in thread pool)
            loop = asyncio.get_event_loop()
            masked_content = await loop.run_in_executor(None, self.redaction_gateway.mask_sensitive_data, content)
        except Exception as e:
            raise PIIProcessingError(f"Failed to mask PII data: {str(e)}")
        
        # Store mappings in session
        session = self.sessions[session_id]
        session["mappings"] = {
            masked: {
                "original": mapping.original,
                "masked": mapping.masked,
                "type": mapping.type,
                "created_at": getattr(mapping, "created_at", datetime.now())
            }
            for masked, mapping in self.redaction_gateway._mapping.items()
        }
        session["last_accessed"] = datetime.now()
        
        processing_time = (time.time() - start_time) * 1000
        pii_count = len(self.redaction_gateway._mapping)
        
        # Безопасное логирование найденных PII типов (без оригинальных данных)
        pii_types = {}
        for masked, mapping in self.redaction_gateway._mapping.items():
            pii_type = mapping.type
            pii_types[pii_type] = pii_types.get(pii_type, 0) + 1
        
        if pii_count > 0:
            logger.info(f"🔒 [{session_id}] Маскирование завершено - найдено {pii_count} PII элементов", extra={
                "session_id": session_id,
                "pii_count": pii_count,
                "pii_types": pii_types,
                "processing_time_ms": round(processing_time, 2),
                "content_length_before": len(content),
                "content_length_after": len(masked_content),
                "content_changed": content != masked_content
            })
            
            # Показываем детали найденных PII элементов
            if self.debug_mode:
                logger.debug(f"🔍 [{session_id}] Детали найденных PII элементов:")
                for i, (masked, mapping) in enumerate(self.redaction_gateway._mapping.items()):
                    logger.debug(f"    {i+1}. НАЙДЕНО: '{mapping.original}' → ЗАМЕНЕНО на: '{mapping.masked}' (тип: {mapping.type})")
            else:
                logger.info(f"🔍 [{session_id}] Найденные PII элементы (безопасно):")
                for i, (masked, mapping) in enumerate(self.redaction_gateway._mapping.items()):
                    logger.info(f"    {i+1}. [СКРЫТО] → '{mapping.masked}' (тип: {mapping.type})")
        else:
            logger.info(f"✅ [{session_id}] Маскирование завершено - PII данные не найдены")
        
        mappings = [PIIMapping(
            original=mapping["original"],
            masked=masked,
            type=mapping["type"],
            created_at=mapping["created_at"]
        ) for masked, mapping in session["mappings"].items()]
        
        return PIIResult(
            content=masked_content,
            mappings=mappings,
            session_id=session_id,
            pii_count=pii_count
        )

    async def unmask_sensitive_data(self, content: str, session_id: str) -> str:
        start_time = time.time()
        
        # Разрешаем пустой контент (может быть в streaming режиме)
        if not content:
            logger.debug(f"ℹ️ [{session_id}] Пустой контент для демаскирования, возвращаем как есть")
            return ""
        
        logger.debug(f"🔓 [{session_id}] Начинаем демаскирование PII данных", extra={
            "session_id": session_id,
            "content_length": len(content)
        })
        
        if self.debug_mode:
            logger.debug(f"📄 [{session_id}] ИСХОДНЫЙ текст для демаскирования: {content}")
        
        if session_id not in self.sessions:
            logger.error(f"❌ [{session_id}] PII сессия не найдена!")
            raise PIISessionNotFoundError(f"PII session not found: {session_id}")
        
        session = self.sessions[session_id]
        mappings_count = len(session["mappings"])
        
        logger.debug(f"📋 [{session_id}] Найдено {mappings_count} PII мапингов в сессии")
        
        # Показываем доступные мапинги
        if self.debug_mode and mappings_count > 0:
            logger.debug(f"🗂️ [{session_id}] Доступные мапинги для демаскирования:")
            for i, (masked_token, mapping_data) in enumerate(session["mappings"].items()):
                logger.debug(f"    {i+1}. '{masked_token}' → '{mapping_data['original']}' (тип: {mapping_data['type']})")
        
        # Restore gateway mapping
        self.redaction_gateway._mapping.clear()
        for masked_token, mapping_data in session["mappings"].items():
            self.redaction_gateway._mapping[masked_token] = RedactionMapping(
                original=mapping_data["original"],
                masked=masked_token,
                type=mapping_data["type"]
            )
        
        loop = asyncio.get_event_loop()
        unmasked_content = await loop.run_in_executor(None, self.redaction_gateway.unmask_sensitive_data, content)
        
        session["last_accessed"] = datetime.now()
        processing_time = (time.time() - start_time) * 1000
        
        if self.debug_mode:
            logger.debug(f"🔓 [{session_id}] РЕЗУЛЬТАТ демаскирования: {unmasked_content}")
        
        content_changed = content != unmasked_content
        if content_changed:
            logger.info(f"🔓 [{session_id}] Демаскирование завершено - данные восстановлены!", extra={
                "session_id": session_id,
                "mappings_applied": mappings_count,
                "processing_time_ms": round(processing_time, 2),
                "content_length_before": len(content),
                "content_length_after": len(unmasked_content),
                "content_changed": content_changed
            })
            
            if self.debug_mode:
                logger.debug(f"🔀 [{session_id}] Изменения при демаскировании:")
                logger.debug(f"    ДО:  {content}")
                logger.debug(f"    ПОСЛЕ: {unmasked_content}")
        else:
            logger.info(f"ℹ️ [{session_id}] Демаскирование не требуется - маски не найдены в тексте")
        
        return unmasked_content

    async def clear_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            session = self.sessions[session_id]
            mappings_count = len(session["mappings"])
            session_age = datetime.now() - session["created_at"]
            
            logger.info(f"🧹 [{session_id}] Очистка PII сессии", extra={
                "session_id": session_id,
                "mappings_count": mappings_count,
                "session_age_seconds": session_age.total_seconds()
            })
            
            if self.debug_mode and mappings_count > 0:
                logger.debug(f"🗑️ [{session_id}] Удаляем следующие мапинги:")
                for i, (masked_token, mapping_data) in enumerate(session["mappings"].items()):
                    logger.debug(f"    {i+1}. '{masked_token}' → '{mapping_data['original']}' (тип: {mapping_data['type']})")
            
            self.sessions.pop(session_id, None)
        else:
            logger.warning(f"⚠️ [{session_id}] Попытка очистить несуществующую сессию") 