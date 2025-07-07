import os
import json
import pytest
import asyncio

from types import SimpleNamespace

# Ensure environment variables are present before importing provider
os.environ.setdefault("OPENROUTER_API_KEY", "dummy_key")
os.environ.setdefault("OPENROUTER_MODEL", "gpt-4o")
os.environ.setdefault("USE_OPENROUTER", "true")
# Azure vars to pass validation (not used)
os.environ.setdefault("AZURE_OPENAI_API_KEY", "dummy")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example")

from llm_pii_proxy.providers.openrouter_provider import OpenRouterProvider  # noqa: E402
from llm_pii_proxy.core.models import ChatRequest, ChatMessage


@pytest.mark.asyncio
async def test_create_chat_completion(monkeypatch):
    """Provider should return ChatResponse parsed from regular JSON reply."""

    messages = [ChatMessage(role="user", content="Hello, LLM!")]
    request = ChatRequest(model="gpt-4o", messages=messages)
    provider = OpenRouterProvider()

    # Dummy httpx Response replacement
    class DummyResponse:
        status_code = 200

        def __init__(self, json_payload):
            self._payload = json_payload

        async def aclose(self):
            pass

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload
        
        @property
        def is_success(self):
            return 200 <= self.status_code < 300

    async def fake_post(self, url, json):  # noqa: ANN001
        # ensure correct param used
        assert "max_completion_tokens" in json or json.get("max_completion_tokens") is None
        assert "max_tokens" not in json

        payload = {
            "id": "chatcmpl-test",
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hi there!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9},
        }
        return DummyResponse(payload)

    monkeypatch.setattr(provider.client, "post", fake_post.__get__(provider.client, type(provider.client)))

    resp = await provider.create_chat_completion(request)
    assert resp.choices[0]["message"]["content"] == "Hi there!"
    assert resp.usage["total_tokens"] == 9


@pytest.mark.asyncio
async def test_create_chat_completion_stream(monkeypatch):
    """Streaming method should yield ChatResponse chunks until stop."""

    messages = [ChatMessage(role="user", content="Stream test")]
    request = ChatRequest(model="gpt-4o", messages=messages, stream=True)
    provider = OpenRouterProvider()

    # Build sample streaming data lines
    chunk_json = {
        "id": "chatcmpl-stream",
        "model": "gpt-4o",
        "choices": [
            {"index": 0, "delta": {"content": "partial"}, "finish_reason": None}
        ],
    }
    data_line = "data: " + json.dumps(chunk_json) + "\n"
    done_line = "data: [DONE]\n"

    class DummyStream:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            pass

        async def aiter_lines(self):
            yield data_line.strip("\n")
            yield done_line.strip("\n")

    def fake_stream(self, method, url, json, headers):  # noqa: ANN001
        return DummyStream()

    monkeypatch.setattr(provider.client, "stream", fake_stream.__get__(provider.client, type(provider.client)))

    chunks = []
    async for c in provider.create_chat_completion_stream(request):
        chunks.append(c)

    # Expect at least 2 chunks (one content + final stop)
    assert len(chunks) >= 2
    # First chunk should carry delta.content
    assert chunks[0].choices[0]["delta"]["content"] == "partial"
    # Last chunk finish_reason == stop
    assert chunks[-1].choices[0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_structured_content_support():
    """Provider should handle structured content format from Cursor."""
    
    # Structured content like Cursor sends
    structured_content = [
        {
            "type": "text",
            "text": "User info context",
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text", 
            "text": "Hello from Cursor!"
        }
    ]
    
    messages = [ChatMessage(role="user", content=structured_content)]
    request = ChatRequest(model="gpt-4o", messages=messages)
    
    # Content should be flattened to string
    assert request.messages[0].content == "User info context\nHello from Cursor!"
    
    # Should still work with provider
    provider = OpenRouterProvider()
    payload = provider._build_payload(request, stream=False)
    
    # Check that message content is properly stringified
    assert payload["messages"][0]["content"] == "User info context\nHello from Cursor!" 