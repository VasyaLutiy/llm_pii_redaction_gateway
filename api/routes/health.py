# api/routes/health.py

from fastapi import APIRouter, HTTPException
from datetime import datetime
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider

router = APIRouter()
llm_provider = AzureOpenAIProvider()

@router.get("/health")
async def health_check():
    is_healthy = await llm_provider.health_check()
    if not is_healthy:
        raise HTTPException(status_code=503, detail="LLM provider unhealthy")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()} 