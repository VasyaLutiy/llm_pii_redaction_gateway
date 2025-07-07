import os
import time
import uuid
import json
from typing import AsyncIterator, List, Dict, Any

import httpx

from llm_pii_proxy.core.models import ChatRequest, ChatResponse
from llm_pii_proxy.core.exceptions import LLMProviderError
from llm_pii_proxy.core.interfaces import LLMProvider
from llm_pii_proxy.config.settings import settings
from llm_pii_proxy.observability import logger as obs_logger

logger = obs_logger.get_logger(__name__)


class OpenRouterProvider(LLMProvider):
    """Simple and reliable OpenRouter provider without smart switching."""

    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise LLMProviderError("OPENROUTER_API_KEY is missing in environment")

        self.base_url: str = settings.openrouter_base_url.rstrip("/") + "/chat/completions"
        self.model: str = settings.openrouter_model
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cursor.sh",
                "X-Title": "LLM PII Proxy",
            },
        )

        logger.info(f"🛤️ OpenRouter Provider initialized: {self.model}")

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def _convert_anthropic_tools_to_openai(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Anthropic format tools to OpenAI format."""
        converted_tools = []
        
        for tool in tools:
            if isinstance(tool, dict):
                # Anthropic format: {name, description, input_schema}
                if 'name' in tool and 'input_schema' in tool:
                    converted_tool = {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool["input_schema"]
                        }
                    }
                    converted_tools.append(converted_tool)
                else:
                    # Already OpenAI format, ensure type is present
                    fixed_tool = tool.copy()
                    if "type" not in fixed_tool:
                        fixed_tool["type"] = "function"
                    converted_tools.append(fixed_tool)
            else:
                converted_tools.append(tool)
        
        return converted_tools

    def _build_payload(self, request: ChatRequest, stream: bool) -> Dict[str, Any]:
        """Build request payload for OpenRouter API."""
        messages = []
        
        for msg in request.messages:
            msg_dict = {
                "role": msg.role,
                "content": msg.content,
            }
            
            # Preserve tool calls and IDs
            if msg.role == "assistant" and msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.role == "tool" and msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
                
            messages.append(msg_dict)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": stream,
        }
        
        # Add max_completion_tokens if specified
        if request.effective_max_tokens is not None:
            payload["max_completion_tokens"] = request.effective_max_tokens
            
        # Convert and add tools
        if request.tools:
            payload["tools"] = self._convert_anthropic_tools_to_openai(request.tools)
            
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
            
        return payload

    def _openai_to_chat_response(self, data: Dict[str, Any], streaming: bool = False) -> ChatResponse:
        """Transform OpenRouter JSON response to internal ChatResponse model."""
        choices = []
        
        for ch in data.get("choices", []):
            if streaming:
                choices.append({
                    "index": ch.get("index", 0),
                    "delta": ch.get("delta", {}),
                    "finish_reason": ch.get("finish_reason"),
                })
            else:
                choices.append({
                    "index": ch.get("index", 0),
                    "message": ch.get("message", {}),
                    "finish_reason": ch.get("finish_reason"),
                })

        return ChatResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:29]}"),
            model=data.get("model", self.model),
            choices=choices,
            usage=data.get("usage"),
        )

    async def create_chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Create a non-streaming chat completion."""
        start_time = time.time()
        
        try:
            payload = self._build_payload(request, stream=False)
            
            response = await self.client.post(self.base_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            chat_resp = self._openai_to_chat_response(data)
            
            duration = time.time() - start_time
            logger.info(f"✅ OpenRouter completion received in {duration:.2f}s")
            
            return chat_resp
            
        except Exception as e:
            logger.error(f"💥 OpenRouter error: {str(e)}")
            raise LLMProviderError(f"OpenRouter error: {str(e)}")

    async def create_chat_completion_stream(self, request: ChatRequest) -> AsyncIterator[ChatResponse]:
        """Create a streaming chat completion."""
        # Claude Sonnet 4 doesn't work well with streaming + tools
        # Fall back to non-streaming and simulate streaming
        if (self.model == "anthropic/claude-sonnet-4" and 
            request.tools and len(request.tools) > 0):
            logger.info(f"🔧 Claude Sonnet 4 with {len(request.tools)} tools: using non-streaming mode")
            
            try:
                # Get non-streaming response
                response = await self.create_chat_completion(request)
                
                # Simulate streaming by yielding content in chunks
                if response.choices and response.choices[0].get("message"):
                    content = response.choices[0]["message"].get("content", "")
                    tool_calls = response.choices[0]["message"].get("tool_calls")
                    
                    # Stream content word by word if it exists
                    if content:
                        words = content.split()
                        for i, word in enumerate(words):
                            chunk_content = word + (" " if i < len(words) - 1 else "")
                            yield ChatResponse(
                                id=response.id,
                                model=response.model,
                                choices=[{
                                    "index": 0,
                                    "delta": {"content": chunk_content},
                                    "finish_reason": None
                                }],
                                usage=None,
                            )
                    
                    # Add tool calls if present
                    if tool_calls:
                        yield ChatResponse(
                            id=response.id,
                            model=response.model,
                            choices=[{
                                "index": 0,
                                "delta": {"tool_calls": tool_calls},
                                "finish_reason": None
                            }],
                            usage=None,
                        )
                
                # Final chunk
                yield ChatResponse(
                    id=response.id,
                    model=response.model,
                    choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    usage=response.usage,
                )
                return
                
            except Exception as e:
                logger.error(f"💥 OpenRouter non-streaming fallback error: {str(e)}")
                raise LLMProviderError(f"OpenRouter non-streaming fallback error: {str(e)}")
        
        # Normal streaming for other cases
        try:
            payload = self._build_payload(request, stream=True)
            
            async with self.client.stream(
                "POST",
                self.base_url,
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as resp:
                resp.raise_for_status()
                
                # Process Server-Sent Events stream
                buffer = ""
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        buffer += chunk.decode('utf-8', errors='ignore')
                        
                        # Process complete lines from buffer
                        while '\n' in buffer:
                            line_end = buffer.find('\n')
                            line = buffer[:line_end].strip()
                            buffer = buffer[line_end + 1:]
                            
                            # Skip empty lines and SSE comments
                            if not line or line.startswith(':'):
                                continue
                                
                            # Process data lines
                            if line.startswith('data: '):
                                chunk_data = line[6:]
                                if chunk_data.strip() == '[DONE]':
                                    break
                                    
                                try:
                                    chunk_json = json.loads(chunk_data)
                                    yield self._openai_to_chat_response(chunk_json, streaming=True)
                                except json.JSONDecodeError:
                                    continue

            # Send final completion chunk
            yield ChatResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                model=self.model,
                choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                usage=None,
            )
            
        except Exception as e:
            logger.error(f"💥 OpenRouter streaming error: {str(e)}")
            raise LLMProviderError(f"OpenRouter streaming error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if OpenRouter is accessible."""
        try:
            response = await self.client.get(settings.openrouter_base_url.rstrip("/") + "/models")
            return response.status_code == 200
        except Exception:
            return False 