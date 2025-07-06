import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway

@pytest.mark.asyncio
async def test_async_pii_gateway_mask_unmask():
    gateway = AsyncPIISecurityGateway()
    session_id = "test-session-1"
    test_content = "My AWS key is AKIA1234567890EXAMPLE and password: secret123."
    # Mask PII
    result = await gateway.mask_sensitive_data(test_content, session_id)
    assert result.pii_count >= 2
    assert "AKIA" not in result.content
    assert "secret123" not in result.content
    masked_content = result.content

    # Unmask PII
    unmasked = await gateway.unmask_sensitive_data(masked_content, session_id)
    assert "AKIA1234567890EXAMPLE" in unmasked
    assert "secret123" in unmasked

    # Clear session
    await gateway.clear_session(session_id)
    assert session_id not in gateway.sessions 