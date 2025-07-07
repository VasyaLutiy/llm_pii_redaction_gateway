import pytest
import logging
from starlette.testclient import TestClient

from llm_pii_proxy.main import create_app

@pytest.mark.parametrize("log_level, debug_flag", [
    ("WARNING", "false"),  # Only WARNING+ messages, no DEBUG or INFO
    ("DEBUG", "true"),     # DEBUG level messages allowed
])
def test_logging_level(monkeypatch, caplog, log_level, debug_flag):
    """
    Test that PII_PROXY_LOG_LEVEL and PII_PROXY_DEBUG properly set the global log level.
    """
    # Set environment variables
    monkeypatch.setenv("PII_PROXY_LOG_LEVEL", log_level)
    monkeypatch.setenv("PII_PROXY_DEBUG", debug_flag)

    # Create the FastAPI app
    app = create_app()
    client = TestClient(app)

    # Capture logs at DEBUG level so we can see if they're actually produced
    with caplog.at_level(logging.DEBUG):
        response = client.get("/health")
        assert response.status_code == 200, "Health-check should return 200"

    # Separate logs by level
    debug_logs = [rec for rec in caplog.records if rec.levelno == logging.DEBUG]
    info_logs = [rec for rec in caplog.records if rec.levelno == logging.INFO]
    warning_logs = [rec for rec in caplog.records if rec.levelno == logging.WARNING]

    if log_level == "WARNING" and debug_flag == "false":
        assert len(debug_logs) == 0, "DEBUG logs should not appear with WARNING level"
        assert len(info_logs) == 0, "INFO logs should not appear with WARNING level"
        # Might or might not see some WARNING logs depending on whether the code logs any
    elif log_level == "DEBUG" and debug_flag == "true":
        assert len(debug_logs) > 0, "DEBUG logs should appear with DEBUG level" 