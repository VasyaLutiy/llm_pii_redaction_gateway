# api/routes/chat.py

import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
from llm_pii_proxy.core.models import ChatRequest, ChatResponse
from llm_pii_proxy.core.exceptions import PIIProcessingError, LLMProviderError, ConfigurationError, ValidationError
from llm_pii_proxy.services.llm_service import LLMService
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway
from llm_pii_proxy.observability import logger as obs_logger

# Настраиваем логгер
logger = obs_logger.get_logger(__name__)

router = APIRouter()

# For now, instantiate dependencies here (in production, use DI)
# 🕵️‍♂️ ЭКСПЕРИМЕНТ: Переключение между Azure и Ollama
import os
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"

if USE_OLLAMA:
    from llm_pii_proxy.providers.ollama_provider import OllamaProvider
    llm_provider = OllamaProvider()
    logger.debug("🦙 ЭКСПЕРИМЕНТ: Используем Ollama provider (притворяется Azure)")
else:
    llm_provider = AzureOpenAIProvider()
    logger.debug("☁️ Используем Azure OpenAI provider")

pii_gateway = AsyncPIISecurityGateway()
llm_service = LLMService(llm_provider, pii_gateway)

MAX_MESSAGES = 50  # Лимит сообщений для LLM

def validate_chat_request(request: ChatRequest) -> None:
    """Валидация входящего запроса"""
    if not request.messages:
        raise ValidationError("Messages cannot be empty")
    
    if len(request.messages) > 1000:  # Разумный лимит
        raise ValidationError("Too many messages (max 1000)")
    
    for i, message in enumerate(request.messages):
        # Разрешаем пустые сообщения для tool calls и assistant сообщений
        if message.role not in ["tool", "assistant"] and (not message.content or not message.content.strip()):
            raise ValidationError(f"Message {i+1} content cannot be empty")
        
        if message.content and len(message.content) > 50000:  # Разумный лимит на размер сообщения
            raise ValidationError(f"Message {i+1} is too long (max 50000 characters)")
    
    if request.temperature is not None and (request.temperature < 0 or request.temperature > 2):
        raise ValidationError("Temperature must be between 0 and 2")
    
    if request.max_tokens is not None and (request.max_tokens < 1 or request.max_tokens > 4000):
        raise ValidationError("Max tokens must be between 1 and 4000")

@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, request_body: Request):
    start_time = time.time()
    
    # Обрезаем историю сообщений до MAX_MESSAGES
    original_count = len(request.messages)
    if original_count > MAX_MESSAGES:
        request.messages = request.messages[-MAX_MESSAGES:]
        logger.info(f"[Cursor] История сообщений обрезана с {original_count} до {MAX_MESSAGES}")
    
    # Получаем raw body для детального логирования
    body = await request_body.body()
    raw_request = body.decode('utf-8')
    
    # Получаем заголовки
    headers = dict(request_body.headers)
    
    logger.debug("🌟 Получен новый запрос к chat completions", extra={
        "endpoint": "/v1/chat/completions",
        "session_id": request.session_id,
        "model": request.model,
        "messages_count": len(request.messages),
        "total_input_length": sum(len(msg.content) for msg in request.messages),
        "has_tools": request.tools is not None,
        "has_tool_choice": request.tool_choice is not None,
        "has_functions": request.functions is not None,
        "stream": getattr(request, 'stream', False),
        "user_agent": headers.get("user-agent", "unknown"),
        "client_ip": headers.get("x-forwarded-for", "unknown")
    })
    
    # Логируем raw request для отладки
    logger.debug(f"📥 RAW REQUEST FROM CLIENT: {raw_request}")
    logger.debug(f"📥 REQUEST HEADERS: {headers}")
    
    # 🔍 ПОЛНАЯ ОТЛАДКА ВХОДЯЩЕГО ЗАПРОСА
    logger.debug("🔍 ПОЛНЫЙ PARSED REQUEST:")
    logger.debug(json.dumps(request.model_dump(), indent=2, ensure_ascii=False))
    
    # Если есть tools, логируем их
    if request.tools:
        logger.debug(f"🔧 TOOLS в запросе: {len(request.tools)} tools")
        for i, tool in enumerate(request.tools):
            logger.debug(f"    Tool {i+1}: {tool.get('function', {}).get('name', 'unknown')}")
    
    if request.tool_choice:
        logger.debug(f"🎯 TOOL_CHOICE в запросе: {request.tool_choice}")
    
    if request.functions:
        logger.debug(f"⚙️ FUNCTIONS в запросе: {len(request.functions)} functions")
    
    # Детальное логирование сообщений
    logger.debug("📝 ДЕТАЛЬНЫЕ СООБЩЕНИЯ:")
    for i, msg in enumerate(request.messages):
        logger.debug(f"    Сообщение {i+1}:")
        logger.debug(f"      Role: {msg.role}")
        logger.debug(f"      Content: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            logger.debug(f"      Tool calls: {len(msg.tool_calls)}")
        if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
            logger.debug(f"      Tool call ID: {msg.tool_call_id}")
    
    # Логируем только количество сообщений для мониторинга Cursor
    logger.info(f"[Cursor] Количество сообщений в запросе: {len(request.messages)}")
    
    try:
        # Валидация входных данных
        validate_chat_request(request)
        
        if getattr(request, 'stream', False):
            async def event_generator():
                async for chunk in llm_service.process_chat_request_stream(request):
                    # Формируем OpenAI-совместимый stream-чанк
                    choices = []
                    for choice in chunk.choices:
                        delta = {}
                        
                        # Добавляем все поля из delta, если они есть
                        if "delta" in choice:
                            if "role" in choice["delta"] and choice["delta"]["role"]:
                                delta["role"] = choice["delta"]["role"]
                            if "content" in choice["delta"] and choice["delta"]["content"] is not None:
                                delta["content"] = choice["delta"]["content"]
                            if "tool_calls" in choice["delta"] and choice["delta"]["tool_calls"]:
                                delta["tool_calls"] = choice["delta"]["tool_calls"]
                        
                        choices.append({
                            "delta": delta,
                            "index": choice["index"],
                            "finish_reason": choice.get("finish_reason")
                        })
                    
                    stream_chunk = {
                        "id": chunk.id,
                        "object": "chat.completion.chunk",
                        "created": chunk.created,
                        "model": chunk.model,
                        "choices": choices
                    }
                    
                    yield f"data: {json.dumps(stream_chunk, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)  # для совместимости
                
                # Отправляем финальный чанк [DONE]
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        
        # Обычный режим
        response = await llm_service.process_chat_request(request)
        
        duration = time.time() - start_time
        logger.debug("✨ Запрос успешно обработан", extra={
            "session_id": request.session_id,
            "total_duration_ms": round(duration * 1000, 2),
            "response_choices": len(response.choices),
            "response_id": response.id
        })
        
        # Логируем финальный ответ
        logger.debug("📤 RESPONSE TO CLIENT: %s", response.json())
        print("📤 RESPONSE TO CLIENT:", response.json())
        
        return response
        
    except ValidationError as e:
        logger.warning(f"❌ Валидация не пройдена: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except PIIProcessingError as e:
        logger.error(f"❌ Ошибка обработки PII: {str(e)}")
        raise HTTPException(status_code=500, detail="PII processing error")
    except LLMProviderError as e:
        logger.error(f"❌ Ошибка LLM провайдера: {str(e)}")
        raise HTTPException(status_code=502, detail="LLM provider error")
    except ConfigurationError as e:
        logger.error(f"❌ Ошибка конфигурации: {str(e)}")
        raise HTTPException(status_code=500, detail="Configuration error")
    except Exception as e:
        duration = time.time() - start_time
        logger.error("💥 Неожиданная ошибка при обработке запроса", extra={
            "session_id": request.session_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": round(duration * 1000, 2)
        })
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/v1/models")
async def list_models():
    """OpenAI-compatible endpoint for model listing."""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4.1",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "azure-openai",
                "permission": [],
                "capabilities": {
                    "tools": True,
                    "tool_choice": True,
                    "functions": True,
                    "function_calling": True,
                    "streaming": True
                }
            },
            {
                "id": "pii_llm_v1",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "pii-proxy",
                "permission": [],
                "capabilities": {
                    "tools": True,
                    "tool_choice": True,
                    "functions": True,
                    "function_calling": True,
                    "streaming": True
                }
            }
        ]
    } 