import pytest
import os
import dotenv
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from httpx import AsyncClient, ASGITransport
from llm_pii_proxy.main import create_app
from llm_pii_proxy.core.models import ChatRequest, ChatMessage

dotenv.load_dotenv("azure.env")

@pytest.mark.asyncio
async def test_health_check():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            assert resp.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_chat_completions():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        req = ChatRequest(
            model=os.environ.get("AZURE_COMPLETIONS_MODEL", "gpt-4"),
            messages=[ChatMessage(role="user", content="My AWS key is AKIA1234567890EXAMPLE and password is secret123.")],
            session_id="integration-test-session"
        )
        resp = await ac.post("/v1/chat/completions", json=req.model_dump())
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        # Проверяем, что получили какой-то ответ от LLM
        assert len(data["choices"][0]["message"]["content"]) > 0
        # Проверяем структуру ответа
        assert "id" in data
        assert "model" in data 