#!/usr/bin/env python3
"""
Тест tool calling через LLM PII Proxy
"""

import json
import asyncio
import httpx

async def test_tool_calling():
    """Тест вызова tools через прокси"""
    
    # Простой запрос который ДОЛЖЕН вызвать tool
    test_request = {
        "model": "gpt-4.1",
        "messages": [
            {
                "role": "user", 
                "content": "Прочитай файл llm_pii_proxy/main.py и скажи что в нем"
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Path to file"
                            }
                        },
                        "required": ["filename"]
                    }
                }
            }
        ],
        "tool_choice": "auto",
        "temperature": 0.0,
        "stream": False
    }
    
    print("🚀 Отправляем запрос с tool calling...")
    print(f"📤 REQUEST: {json.dumps(test_request, indent=2, ensure_ascii=False)}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://192.168.0.182:8000/v1/chat/completions",
                json=test_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"📨 RESPONSE STATUS: {response.status_code}")
            print(f"📨 RESPONSE HEADERS: {dict(response.headers)}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"📨 RESPONSE BODY: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                
                # Проверяем tool_calls
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    if "tool_calls" in message and message["tool_calls"]:
                        print(f"🔧 НАЙДЕНЫ TOOL CALLS: {len(message['tool_calls'])}")
                        for i, tc in enumerate(message["tool_calls"]):
                            print(f"   Tool {i+1}: {tc.get('function', {}).get('name', 'unknown')}")
                        return True
                    else:
                        print("❌ НЕТ TOOL CALLS в ответе!")
                        return False
                else:
                    print("❌ НЕТ CHOICES в ответе!")
                    return False
            else:
                print(f"❌ ОШИБКА: {response.status_code}")
                print(f"❌ BODY: {response.text}")
                return False
                
        except Exception as e:
            print(f"💥 EXCEPTION: {e}")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_tool_calling())
    if result:
        print("✅ TOOL CALLING РАБОТАЕТ!")
    else:
        print("❌ TOOL CALLING НЕ РАБОТАЕТ!") 