import pytest
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.core.models import ChatMessage, ChatRequest

@pytest.mark.asyncio
async def test_azure_openai_provider_chat_completion():
    # Skip test if required env vars are missing
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_COMPLETIONS_MODEL"
    ]
    if not all(var in os.environ for var in required_vars):
        pytest.skip("Azure OpenAI credentials not set in environment.")

    provider = AzureOpenAIProvider()
    request = ChatRequest(
        model=os.environ["AZURE_COMPLETIONS_MODEL"],
        messages=[
            ChatMessage(role="user", content="Say hello world.")
        ],
        temperature=0.0,
        max_tokens=10,
        stream=False,
        session_id="test-session"
    )
    response = await provider.create_chat_completion(request)
    assert response.id
    assert response.model
    assert response.choices
    assert isinstance(response.choices, list)
    assert "content" in response.choices[0]["message"]
    print("Azure OpenAI response:", response.choices[0]["message"]["content"]) 