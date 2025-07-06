# 🏗️ LLM PII PROXY - ARCHITECTURAL PLAN

**Project:** LLM PII Proxy with Security Gateway  
**Version:** 1.0.0  
**Date:** January 31, 2025  
**Architecture Pattern:** Clean Architecture + Dependency Injection

## 🎯 EXECUTIVE SUMMARY

The LLM PII Proxy is a security-first HTTP proxy server that sits between Cursor IDE and external LLM providers (Azure OpenAI, OpenAI, etc.). It automatically masks PII data in outbound requests and unmasks responses, preventing sensitive data leaks to external AI services.

## 🏛️ ARCHITECTURAL PRINCIPLES

### Core Design Principles
- **SOLID Principles** - Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion
- **Clean Architecture** - Domain-driven design with clear layer separation
- **Dependency Injection** - Loose coupling through interface-based design
- **Async First** - Full async/await support for high performance
- **Type Safety** - Complete type hints with Pydantic validation
- **Observability** - Structured logging, metrics, and tracing
- **Configuration as Code** - Environment-based configuration with validation

### Technology Stack
```yaml
Core Framework: FastAPI (async HTTP server)
Validation: Pydantic v2 (data validation & serialization)
DI Container: dependency-injector (dependency injection)
Security: Custom PII Gateway + Azure OpenAI
Monitoring: structlog (structured logging)
Testing: pytest + pytest-asyncio
Type Checking: mypy
Linting: ruff (modern Python linter)
```

## 🏗️ SYSTEM ARCHITECTURE

### High-Level Component Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cursor IDE    │───▶│  LLM PII Proxy  │───▶│ Azure OpenAI    │
│                 │    │                 │    │ GPT-4.1         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │ PII Security    │
                       │ Gateway         │
                       └─────────────────┘
```

### Layer Architecture
```
┌─────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ HTTP Routes │  │ Middleware  │  │ WebSocket   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ LLM Service │  │ PII Service │  │Auth Service │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│                   DOMAIN LAYER                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Chat Models │  │ PII Models  │  │Config Models│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│                INFRASTRUCTURE LAYER                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │Azure Client │  │PII Redactor │  │Config Loader│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 📦 PROJECT STRUCTURE

```
llm_pii_proxy/
├── pyproject.toml              # Modern Python project config
├── README.md                   # Project documentation
├── docker-compose.yml          # Container orchestration
├── .env.example               # Environment template
├── llm_pii_proxy/
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry point
│   ├── core/                  # Core domain interfaces
│   │   ├── __init__.py
│   │   ├── interfaces.py      # Abstract base classes
│   │   ├── models.py          # Domain models
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── constants.py       # Application constants
│   ├── services/              # Application services
│   │   ├── __init__.py
│   │   ├── llm_service.py     # LLM orchestration
│   │   ├── pii_service.py     # PII processing
│   │   └── auth_service.py    # Authentication
│   ├── providers/             # External LLM providers
│   │   ├── __init__.py
│   │   ├── base.py           # Provider interface
│   │   ├── azure_provider.py # Azure OpenAI
│   │   └── openai_provider.py# OpenAI direct
│   ├── security/              # PII & Security components
│   │   ├── __init__.py
│   │   ├── pii_gateway.py    # PII redaction logic
│   │   ├── auth_handler.py   # Authentication logic
│   │   └── rate_limiter.py   # Rate limiting
│   ├── api/                   # HTTP API layer
│   │   ├── __init__.py
│   │   ├── routes/           # API routes
│   │   │   ├── __init__.py
│   │   │   ├── chat.py      # Chat completions
│   │   │   └── health.py    # Health checks
│   │   ├── middleware/       # HTTP middleware
│   │   │   ├── __init__.py
│   │   │   ├── logging.py   # Request logging
│   │   │   ├── cors.py      # CORS handling
│   │   │   └── error.py     # Error handling
│   │   └── dependencies.py  # FastAPI dependencies
│   ├── config/               # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py      # Application settings
│   │   └── container.py     # DI container
│   ├── observability/        # Monitoring & logging
│   │   ├── __init__.py
│   │   ├── logger.py        # Structured logging
│   │   ├── metrics.py       # Performance metrics
│   │   └── tracer.py        # Request tracing
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── helpers.py       # Common utilities
│       └── validators.py    # Data validators
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # End-to-end tests
└── scripts/                 # Development scripts
    ├── start_dev.py        # Development server
    ├── run_tests.py        # Test runner
    └── deploy.py           # Deployment script
```

## 🎭 CORE INTERFACES DESIGN

### 1. LLM Provider Interface
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
from llm_pii_proxy.core.models import ChatRequest, ChatResponse

class LLMProvider(ABC):
    """Abstract interface for LLM providers"""
    
    @abstractmethod
    async def create_chat_completion(
        self, 
        request: ChatRequest
    ) -> ChatResponse:
        """Create a chat completion"""
        pass
    
    @abstractmethod
    async def create_chat_completion_stream(
        self, 
        request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """Create a streaming chat completion"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health"""
        pass
```

### 2. PII Security Interface
```python
from abc import ABC, abstractmethod
from llm_pii_proxy.core.models import PIIResult

class PIISecurityGateway(ABC):
    """Abstract interface for PII protection"""
    
    @abstractmethod
    async def mask_sensitive_data(
        self, 
        content: str
    ) -> PIIResult:
        """Mask PII in content"""
        pass
    
    @abstractmethod
    async def unmask_sensitive_data(
        self, 
        content: str, 
        session_id: str
    ) -> str:
        """Unmask PII using session mapping"""
        pass
    
    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        """Clear PII mapping for session"""
        pass
```

## 🔧 CORE MODELS

### Chat Models
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    model: str = Field(description="LLM model name")
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    stream: bool = False
    session_id: str = Field(description="Session ID for PII tracking")

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
```

### PII Models
```python
class PIIMapping(BaseModel):
    original: str
    masked: str
    type: str
    created_at: datetime

class PIIResult(BaseModel):
    content: str
    mappings: List[PIIMapping]
    session_id: str
    pii_count: int
```

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1)
- [ ] Project structure setup
- [ ] Core interfaces definition
- [ ] Basic FastAPI server
- [ ] Configuration management
- [ ] Dependency injection container

### Phase 2: PII Security (Week 2)
- [ ] PII Gateway implementation
- [ ] Integration with existing PIIRedactionGateway
- [ ] Session management
- [ ] Security testing suite

### Phase 3: LLM Integration (Week 3)
- [ ] Azure OpenAI provider
- [ ] Chat completion endpoints
- [ ] Streaming support
- [ ] Error handling

### Phase 4: Production Features (Week 4)
- [ ] Authentication & authorization
- [ ] Rate limiting
- [ ] Monitoring & observability
- [ ] Docker containerization
- [ ] CI/CD pipeline

## 🔍 QUALITY ASSURANCE

### Testing Strategy
```python
# Unit Tests - 80% coverage minimum
tests/unit/test_pii_service.py
tests/unit/test_llm_service.py
tests/unit/test_azure_provider.py

# Integration Tests
tests/integration/test_api_endpoints.py
tests/integration/test_pii_integration.py

# E2E Tests
tests/e2e/test_cursor_integration.py
tests/e2e/test_security_flow.py
```

### Performance Requirements
- **Latency**: < 100ms proxy overhead
- **Throughput**: 1000+ requests/minute
- **Memory**: < 512MB baseline usage
- **CPU**: < 50% single core usage

### Security Requirements
- **PII Protection**: 100% sensitive data masking
- **Zero Data Retention**: No persistent storage of sensitive data
- **Audit Logging**: All PII operations logged
- **Secure Transport**: HTTPS only in production

## 📊 MONITORING & OBSERVABILITY

### Metrics
```python
# Application Metrics
- request_duration_seconds
- request_total
- pii_operations_total
- llm_provider_errors_total
- active_sessions_gauge

# Business Metrics  
- pii_items_masked_total
- sensitive_data_types_distribution
- session_duration_seconds
```

### Structured Logging
```python
# Log Format
{
    "timestamp": "2025-01-31T15:30:45Z",
    "level": "INFO", 
    "service": "llm-pii-proxy",
    "request_id": "req_123",
    "session_id": "sess_456",
    "event": "pii_masked",
    "pii_count": 3,
    "pii_types": ["aws_key", "password"],
    "latency_ms": 45
}
```

## 🔄 DATA FLOW SPECIFICATION

### Request Flow
```
1. Cursor IDE → POST /v1/chat/completions
2. Auth Middleware → Validate API key
3. PII Service → Mask sensitive data in messages
4. LLM Service → Route to Azure OpenAI
5. Azure Provider → Create chat completion
6. PII Service → Unmask response data
7. Response → Return to Cursor IDE
8. Cleanup → Clear session PII mapping
```

### Security Checkpoints
- ✅ **Checkpoint 1**: Input validation & sanitization
- ✅ **Checkpoint 2**: PII detection & masking
- ✅ **Checkpoint 3**: Secure transmission to LLM
- ✅ **Checkpoint 4**: Response validation
- ✅ **Checkpoint 5**: PII unmasking
- ✅ **Checkpoint 6**: Session cleanup

## 🎯 SUCCESS CRITERIA

### Technical Goals
- [x] Zero PII leaks to external LLMs
- [x] < 100ms latency overhead
- [x] 99.9% uptime
- [x] 100% API compatibility with OpenAI format
- [x] Full test coverage (unit + integration)

### Business Goals
- [x] Secure DevOps workflow automation
- [x] Transparent Cursor IDE integration
- [x] Support for multiple LLM providers
- [x] Enterprise-ready security posture
- [x] Extensible architecture for future features

---

**Next Steps**: Ready to implement Phase 1 foundation components. Proceed with core interfaces and FastAPI server setup. 