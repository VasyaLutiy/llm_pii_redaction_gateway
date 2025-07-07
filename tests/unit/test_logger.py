import os
import tempfile
import logging
from llm_pii_proxy.observability import logger as obs_logger

def test_setup_logging_and_get_logger(tmp_path):
    log_file = tmp_path / "test_log.log"
    # Настроить логирование с debug_mode=True
    obs_logger.setup_logging(debug_mode=True, log_file_path=str(log_file))
    test_logger = obs_logger.get_logger("test_logger")
    test_logger.debug("debug message")
    test_logger.info("info message")
    test_logger.warning("warning message")
    test_logger.error("error message")
    # Проверяем, что файл создан
    assert log_file.exists(), "Log file was not created"
    content = log_file.read_text(encoding="utf-8")
    # Проверяем, что все уровни логов присутствуют
    assert "debug message" in content
    assert "info message" in content
    assert "warning message" in content
    assert "error message" in content
    # Проверяем формат (дата, уровень, имя логгера)
    assert "test_logger" in content
    assert "DEBUG" in content
    assert "INFO" in content
    assert "WARNING" in content
    assert "ERROR" in content 