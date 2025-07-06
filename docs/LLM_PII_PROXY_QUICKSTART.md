# 🚀 LLM PII PROXY - QUICK START GUIDE

**Secure LLM Proxy with PII Protection for Cursor IDE**

## ⚡ QUICK DEPLOYMENT

### 1. Prerequisites
```bash
# Python 3.11+
python --version

# Required packages
pip install fastapi uvicorn python-dotenv openai[azure] httpx pydantic
```

### 2. Configuration Setup
```bash
# Copy your existing azure.env and add proxy settings
cp azure.env llm-proxy.env

# Add these new variables to llm-proxy.env:
echo "AZURE_EXTERNAL_LLM=gpt-4" >> llm-proxy.env
echo "LLM_PROXY_HOST=localhost" >> llm-proxy.env  
echo "LLM_PROXY_PORT=9000" >> llm-proxy.env
echo "LLM_PROXY_DEBUG=true" >> llm-proxy.env
echo "PII_PROTECTION=true" >> llm-proxy.env
echo "PII_SESSION_TIMEOUT=60" >> llm-proxy.env
```

### 3. Start the Proxy Server
```bash
# Method 1: Direct uvicorn
uvicorn LLM_PII_PROXY_IMPLEMENTATIONS:create_app --factory --host 0.0.0.0 --port 9000 --reload

# Method 2: Python script
python -c "
import uvicorn
from LLM_PII_PROXY_IMPLEMENTATIONS import create_app
app = create_app()
uvicorn.run(app, host='0.0.0.0', port=9000, reload=True)
"
```

### 4. Test the Proxy
```bash
# Health check
curl http://localhost:9000/health

# Test chat completion with PII
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "My AWS key is AKIAEXAMPLE12345678"}
    ],
    "pii_protection": true
  }'
```

### 5. Configure Cursor IDE
```json
// Cursor Settings.json
{
  "cursor.general.model": "gpt-4",
  "cursor.general.apiUrl": "http://localhost:9000",
  "cursor.general.apiKey": "not-used-but-required",
  "cursor.general.enableStreaming": false
}
```

## 🛡️ SECURITY VERIFICATION

### Test PII Masking Flow:
```python
import asyncio
import json
from LLM_PII_PROXY_IMPLEMENTATIONS import AsyncPIISecurityGateway

async def test_pii_protection():
    pii_gateway = AsyncPIISecurityGateway()
    
    # Test data with sensitive info
    test_content = """
    AWS Access Key: AKIAEXAMPLE12345678
    Secret: EXAMPLE_SECRET_KEY_NOT_REAL_123456789
    Password: super_secret_123
    IP Address: 192.168.1.100
    """
    
    session_id = "test-session-123"
    
    # 1. Mask PII
    print("🎭 Original content:")
    print(test_content)
    
    pii_result = await pii_gateway.mask_sensitive_data(test_content, session_id)
    print(f"\n🔒 Masked content (sent to Azure OpenAI):")
    print(pii_result["content"])
    print(f"PII items found: {pii_result['pii_count']}")
    
    # 2. Simulate Azure response with masked data
    azure_response = f"Your AWS key {list(pii_result['content'].split())[3]} is properly configured."
    print(f"\n☁️ Azure response (with masked data):")
    print(azure_response)
    
    # 3. Unmask for user
    unmasked_response = await pii_gateway.unmask_sensitive_data(azure_response, session_id)
    print(f"\n🔓 Final response (unmasked for user):")
    print(unmasked_response)
    
    # 4. Cleanup
    await pii_gateway.clear_session(session_id)
    print(f"\n🧹 Session {session_id} cleared")

# Run test
asyncio.run(test_pii_protection())
```

## 🎯 INTEGRATION FLOW

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Cursor IDE  │───▶│ LLM Proxy   │───▶│ Azure OpenAI│
│             │    │ :9000       │    │ GPT-4       │
│ Real Data   │    │ Masked Data │    │ Masked Data │
└─────────────┘    └─────────────┘    └─────────────┘
       ▲                   │                   │
       │                   ▼                   │
       │           ┌─────────────┐             │
       └───────────│ PII Gateway │◀────────────┘
                   │ Unmask      │
                   └─────────────┘
```

## 📊 MONITORING

### Check Logs:
```bash
# PII operations are logged with structured format
tail -f /tmp/pii_protection_debug.log

# Proxy request logs  
# Will show in console where uvicorn is running
```

### Metrics Available:
- Request duration
- PII operations count
- Session management
- Provider health status

## 🔧 DEVELOPMENT MODE

### Hot Reload Development:
```bash
# Start with auto-reload for development
uvicorn LLM_PII_PROXY_IMPLEMENTATIONS:create_app --factory \
  --host 0.0.0.0 --port 9000 --reload --log-level debug
```

### Debug PII Operations:
```python
# Enable detailed PII debugging
import os
os.environ["LLM_PROXY_DEBUG"] = "true"
os.environ["PII_PROTECTION"] = "true"

# Start server with debug mode
```

## 🚨 PRODUCTION DEPLOYMENT

### Docker Setup:
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
COPY azure.env .

EXPOSE 9000
CMD ["uvicorn", "LLM_PII_PROXY_IMPLEMENTATIONS:create_app", "--factory", "--host", "0.0.0.0", "--port", "9000"]
```

### Production Configuration:
```bash
# Production environment variables
AZURE_OPENAI_API_KEY=your_production_key
AZURE_OPENAI_ENDPOINT=https://your-prod-endpoint.openai.azure.com/
AZURE_EXTERNAL_LLM=gpt-4
LLM_PROXY_HOST=0.0.0.0
LLM_PROXY_PORT=9000
LLM_PROXY_DEBUG=false
PII_PROTECTION=true
PII_SESSION_TIMEOUT=30
```

### Health Monitoring:
```bash
# Health check endpoint
curl http://localhost:9000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-01-31T15:30:45Z"
}
```

## 🎓 ARCHITECTURE BENEFITS

### ✅ What This Solves:
- **Zero PII Leaks**: External LLMs never see real sensitive data
- **Transparent Integration**: Cursor works without modifications
- **OpenAI Compatible**: Standard API format
- **Session-Based Security**: Automatic cleanup of sensitive mappings
- **Observability**: Full request/PII operation logging

### 🔒 Security Guarantees:
1. **Input Sanitization**: All user inputs masked before Azure OpenAI
2. **Response Restoration**: Clean unmasked responses returned to user
3. **Session Isolation**: Each conversation has isolated PII mappings
4. **Automatic Cleanup**: Sessions expire and clean up automatically
5. **Audit Trail**: All PII operations logged for compliance

### 🚀 Performance Features:
- **Async Architecture**: Full async/await for high throughput
- **Minimal Latency**: <100ms proxy overhead target
- **Connection Pooling**: Efficient Azure OpenAI connections
- **Session Caching**: Fast PII mapping lookups

## 🔄 NEXT STEPS

1. **Start the proxy server** following steps above
2. **Configure Cursor IDE** to use proxy endpoint
3. **Test with real DevOps queries** containing sensitive data
4. **Monitor PII operations** in logs
5. **Scale as needed** for production workloads

---

**🎯 Result**: Your Cursor IDE now has **ZERO PII LEAK PROTECTION** while maintaining full functionality with Azure OpenAI GPT-4! 