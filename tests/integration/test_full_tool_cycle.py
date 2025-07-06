#!/usr/bin/env python3
"""
Тест ПОЛНОГО ЦИКЛА tool calling через LLM PII Proxy
"""

import json
import asyncio
import httpx

async def test_full_tool_cycle():
    """Тест полного цикла tool calling"""
    
    # Шаг 1: Первый запрос - получаем tool_calls
    print("🚀 ШАГ 1: Отправляем запрос который должен вызвать tool...")
    
    first_request = {
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
    
    async with httpx.AsyncClient() as client:
        # Первый запрос
        response1 = await client.post(
            "http://192.168.0.182:8000/v1/chat/completions",
            json=first_request,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        
        if response1.status_code != 200:
            print(f"❌ ОШИБКА В ПЕРВОМ ЗАПРОСЕ: {response1.status_code}")
            return False
        
        data1 = response1.json()
        print(f"✅ ШАГ 1 УСПЕШЕН: Получили tool_calls")
        
        # Извлекаем tool_calls
        message1 = data1["choices"][0]["message"]
        if not message1.get("tool_calls"):
            print("❌ НЕТ TOOL CALLS!")
            return False
        
        tool_call = message1["tool_calls"][0]
        print(f"🔧 Tool call: {tool_call['function']['name']}")
        print(f"🔧 Arguments: {tool_call['function']['arguments']}")
        
        # Шаг 2: Симулируем выполнение tool (как это делает Cursor)
        print("\n🚀 ШАГ 2: Симулируем выполнение tool...")
        
        # Читаем файл (симулируем tool execution)
        try:
            with open("llm_pii_proxy/main.py", "r", encoding="utf-8") as f:
                file_content = f.read()
            tool_result = f"Содержимое файла llm_pii_proxy/main.py:\n\n{file_content}"
        except Exception as e:
            tool_result = f"Ошибка чтения файла: {str(e)}"
        
        print(f"✅ ШАГ 2 УСПЕШЕН: Файл прочитан ({len(tool_result)} символов)")
        
        # Шаг 3: Отправляем результат tool execution обратно
        print("\n🚀 ШАГ 3: Отправляем результат tool execution...")
        
        second_request = {
            "model": "gpt-4.1",
            "messages": [
                {
                    "role": "user", 
                    "content": "Прочитай файл llm_pii_proxy/main.py и скажи что в нем"
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_call]
                },
                {
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call["id"]
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
        
        response2 = await client.post(
            "http://192.168.0.182:8000/v1/chat/completions",
            json=second_request,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        
        if response2.status_code != 200:
            print(f"❌ ОШИБКА ВО ВТОРОМ ЗАПРОСЕ: {response2.status_code}")
            print(f"❌ BODY: {response2.text}")
            return False
        
        data2 = response2.json()
        print(f"✅ ШАГ 3 УСПЕШЕН: Получили финальный ответ")
        
        # Проверяем финальный ответ
        message2 = data2["choices"][0]["message"]
        if message2.get("tool_calls"):
            print("❌ ПОЛУЧИЛИ ЕЩЕ TOOL CALLS вместо финального ответа!")
            return False
        
        if not message2.get("content"):
            print("❌ НЕТ СОДЕРЖИМОГО в финальном ответе!")
            return False
        
        print(f"🎉 ФИНАЛЬНЫЙ ОТВЕТ: {message2['content'][:200]}...")
        return True

if __name__ == "__main__":
    result = asyncio.run(test_full_tool_cycle())
    if result:
        print("\n✅ ПОЛНЫЙ ЦИКЛ TOOL CALLING РАБОТАЕТ!")
    else:
        print("\n❌ ПОЛНЫЙ ЦИКЛ TOOL CALLING НЕ РАБОТАЕТ!") 