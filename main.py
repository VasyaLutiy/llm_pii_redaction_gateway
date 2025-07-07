import logging
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from llm_pii_proxy.api.routes.chat import router as chat_router
from llm_pii_proxy.api.routes.health import router as health_router
from llm_pii_proxy.api.routes.cache import router as cache_router
from llm_pii_proxy.observability import logger as obs_logger

obs_logger.setup_logging()

def setup_logging():
    """Настройка логирования для PII Proxy"""
    # Проверяем режим отладки
    debug_mode = os.getenv('PII_PROXY_DEBUG', 'false').lower() == 'true'
    
    # Создаем форматтер для красивого вывода
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    # Настраиваем отдельные логгеры для компонентов приложения
    for logger_name in [
        'llm_pii_proxy.services.llm_service',
        'llm_pii_proxy.api.routes.chat',
        'llm_pii_proxy.security.pii_gateway',
        'llm_pii_proxy.providers.azure_provider',
        'llm_pii_proxy.providers.ollama_provider'
    ]:
        logger = obs_logger.get_logger(logger_name)
        logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Уменьшаем уровень для внешних библиотек
    obs_logger.get_logger('httpx').setLevel(obs_logger.logging.WARNING)
    obs_logger.get_logger('openai').setLevel(obs_logger.logging.WARNING)
    obs_logger.get_logger('urllib3').setLevel(obs_logger.logging.WARNING)
    
    
    if debug_mode:
        logging.info("🔍 DEBUG РЕЖИМ ВКЛЮЧЕН - будут показаны чувствительные данные!")
    logging.info("🚀 Логирование настроено для LLM PII Proxy")
    logging.info("📝 Детальные логи записываются в: /tmp/llm_pii_proxy_debug.log")

def create_app() -> FastAPI:
    """Фабрика приложения."""
    # Установка логирования с учётом окружения.
    log_level_str = os.getenv("PII_PROXY_LOG_LEVEL", "INFO").upper()
    debug_flag = os.getenv("PII_PROXY_DEBUG", "false").lower() == "true"

    # Если debug=true, приоритет - DEBUG.
    if debug_flag:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        # Иначе берем log_level_str.
        accepted_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        logging.getLogger().setLevel(accepted_levels.get(log_level_str, logging.INFO))

    app = FastAPI(
        title="LLM PII Proxy", 
        version="1.0.0",
        description="Прокси-сервер для защиты PII данных при работе с LLM"
    )
    
    # Добавляем CORS middleware для поддержки preflight OPTIONS-запросов
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Разрешить все источники (можно ограничить)
        allow_credentials=True,
        allow_methods=["*"],  # Разрешить все методы
        allow_headers=["*"]   # Разрешить все заголовки
    )

    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(cache_router)
    
    #logger.info("🌐 FastAPI приложение создано и настроено")
    return app 