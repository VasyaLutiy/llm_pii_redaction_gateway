# observability/logger.py
import logging
import sys
import os
from typing import Optional

def setup_logging(debug_mode: Optional[bool] = None, log_file_path: Optional[str] = None):
    """
    Централизованная настройка логирования для всего приложения.
    :param debug_mode: Включить DEBUG-режим (по умолчанию определяется по переменной окружения PII_PROXY_DEBUG)
    :param log_file_path: Путь к файлу логов (по умолчанию /tmp/llm_pii_proxy_debug.log)
    """
    if debug_mode is None:
        debug_mode = os.getenv('PII_PROXY_DEBUG', 'false').lower() == 'true'
    if log_file_path is None:
        log_file_path = '/tmp/llm_pii_proxy_debug.log'

    # Новый блок: поддержка переменной окружения PII_PROXY_LOG_LEVEL
    log_level_env = os.getenv('PII_PROXY_LOG_LEVEL')
    if log_level_env:
        log_level = getattr(logging, log_level_env.upper(), logging.INFO)
    else:
        log_level = logging.DEBUG if debug_mode else logging.INFO

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Удаляем старые хендлеры, чтобы избежать дублирования
    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Настроить уровни для сторонних библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    if debug_mode:
        root_logger.info("🔍 DEBUG РЕЖИМ ВКЛЮЧЕН - будут показаны чувствительные данные!")
    root_logger.info(f"🚀 Логирование настроено для LLM PII Proxy. Детальные логи: {log_file_path}")

def get_logger(name: Optional[str] = None):
    """
    Получить логгер по имени (или корневой логгер, если имя не указано)
    """
    return logging.getLogger(name)

# Structured logging will go here. 