# 📚 API Reference

## Chat Completions API

### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint with PII protection.

#### Request

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer your-api-key
```

#### Request Body

```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "user",
      "content": "Your message here"
    }
  ],
  "pii_protection": true,
  "max_tokens": 150,
  "temperature": 0.7,
  "stream": false,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "function_name",
        "description": "Function description",
        "parameters": {
          "type": "object",
          "properties": {
            "param1": {"type": "string"}
          },
          "required": ["param1"]
        }
      }
    }
  ]
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | Yes | - | Model name (e.g., "gpt-4") |
| `messages` | array | Yes | - | Array of message objects |
| `pii_protection` | boolean | No | `false` | Enable PII protection for this request |
| `max_tokens` | integer | No | `1000` | Maximum tokens in response |
| `temperature` | float | No | `0.7` | Sampling temperature (0-2) |
| `stream` | boolean | No | `false` | Enable streaming response |
| `tools` | array | No | - | Available tools for function calling |
| `session_id` | string | No | auto-generated | PII session identifier |

#### Response

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response content",
        "tool_calls": [
          {
            "id": "call_123",
            "type": "function",
            "function": {
              "name": "function_name",
              "arguments": "{\"param1\": \"value\"}"
            }
          }
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

## Models API

### GET /v1/models

List available models.

#### Response

```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1677610602,
      "owned_by": "azure-openai",
      "capabilities": {
        "tools": true,
        "streaming": true,
        "pii_protection": true
      }
    }
  ]
}
```

## Health Check API

### GET /health

Server health check endpoint.

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-07-06T21:37:06.122940",
  "version": "1.0.0",
  "pii_protection": {
    "enabled": true,
    "patterns_loaded": 12,
    "session_timeout_minutes": 60
  }
}
```

## Error Responses

### Error Format

```json
{
  "error": {
    "message": "Error description",
    "type": "error_type",
    "code": "error_code"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `invalid_request_error` | 400 | Invalid request format |
| `authentication_error` | 401 | Invalid API key |
| `rate_limit_error` | 429 | Rate limit exceeded |
| `server_error` | 500 | Internal server error |
| `pii_processing_error` | 500 | PII processing failed |
| `llm_provider_error` | 502 | LLM provider error |

## PII Protection

### PII Session Management

- **Session Creation**: Automatic on first PII detection
- **Session Timeout**: Configurable (default: 60 minutes)
- **Session Cleanup**: Automatic cleanup of expired sessions

### Supported PII Types

| Type | Pattern | Example |
|------|---------|---------|
| `aws_key` | `AKIA[0-9A-Z]{16,20}` | `AKIAEXAMPLE12345678` |
| `ip_address` | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | `192.168.1.100` |
| `password` | Context-aware | `MySecretPassword123` |
| `api_key` | Various patterns | `sk_live_abc123...` |
| `connection_string` | URL patterns | `mongodb://user:pass@host` |

### PII Masking Format

- **Mask Pattern**: `<type_randomhex>`
- **Example**: `<aws_key_abc12345>`
- **Uniqueness**: Each PII instance gets unique mask
- **Reversibility**: Masks can be reversed to original values 