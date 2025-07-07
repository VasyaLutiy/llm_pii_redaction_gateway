import pytest
import logging
from unittest.mock import patch
from starlette.testclient import TestClient

from llm_pii_proxy.main import create_app

@pytest.fixture
def no_azure_calls():
    """
    Заглушка, чтобы вызовы к Azure не ломали тест, если они происходят на этапе запуска.
    """
    with patch("llm_pii_proxy.providers.azure_provider.AzureOpenAIProvider.health_check", return_value=True):
        yield

@pytest.mark.parametrize("log_level, debug_flag", [
    ("WARNING", "false"),
    ("DEBUG", "true"),
])
def test_logging_env(monkeypatch, caplog, no_azure_calls, log_level, debug_flag):
    """
    Тестируем, что при установке PII_PROXY_LOG_LEVEL и PII_PROXY_DEBUG
    уровень логирования действительно меняется при запуске приложения.
    """
    # Устанавливаем переменные окружения
    monkeypatch.setenv("PII_PROXY_LOG_LEVEL", log_level)
    monkeypatch.setenv("PII_PROXY_DEBUG", debug_flag)

    # Создаём FastAPI-приложение
    app = create_app()

    # Регистрируем фиктивный маршрут /ping
    @app.get("/ping")
    def ping():
        logging.debug("DEBUG log from /ping")
        logging.info("INFO log from /ping")
        logging.warning("WARNING log from /ping")
        return {"message": "pong"}

    client = TestClient(app)

    # Вместо caplog.at_level(logging.DEBUG), просто вызываем get("/ping")
    response = client.get("/ping")
    assert response.status_code == 200, "Expected 200 from /ping"

    # Убираем логи asyncio или других внешних библиотек
    filtered_records = []
    for r in caplog.records:
        if r.name == "root" or r.name.startswith("llm_pii_proxy"):
            filtered_records.append(r)

    debug_logs = [r for r in filtered_records if r.levelno == logging.DEBUG]
    info_logs = [r for r in filtered_records if r.levelno == logging.INFO]
    warning_logs = [r for r in filtered_records if r.levelno == logging.WARNING]

    if log_level == "WARNING" and debug_flag == "false":
        assert len(debug_logs) == 0, "DEBUG logs should not appear at WARNING level"
        assert len(info_logs) == 0, "INFO logs should not appear at WARNING level"
        assert len(warning_logs) > 0, "Expected at least one WARNING log"
    elif log_level == "DEBUG" and debug_flag == "true":
        assert len(debug_logs) > 0, "No DEBUG logs found at DEBUG level"
        assert len(info_logs) > 0, "No INFO logs found at DEBUG level"
        assert len(warning_logs) > 0, "No WARNING logs found at DEBUG level" 