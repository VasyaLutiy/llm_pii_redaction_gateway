#!/usr/bin/env python3
"""
Симуляция поведения Cursor при tool calling
"""

import json
import asyncio
import httpx

async def test_cursor_simulation():
    """Имитирует поведение Cursor"""
    
    # Сначала проверим модели
    print("🔍 Проверяем доступные модели...")
    async with httpx.AsyncClient() as client:
        models_response = await client.get("http://192.168.0.182:8000/v1/models")
        print(f"📋 Модели: {models_response.status_code}")
        if models_response.status_code == 200:
            models = models_response.json()
            for model in models["data"]:
                print(f"   - {model['id']}: tools={model.get('capabilities', {}).get('tools', False)}")
    
    # Теперь делаем запрос как Cursor
    print("\n🚀 Делаем запрос как Cursor...")
    
    cursor_request = {
        "model": "gpt-4.1",
        "messages": [
            {
                "role": "user",
                "content": "Прочитай файл README.md и скажи что в нем"
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "properties": {
                            "target_file": {
                                "description": "The path of the file to read",
                                "type": "string"
                            },
                            "should_read_entire_file": {
                                "description": "Whether to read the entire file",
                                "type": "boolean"
                            },
                            "start_line_one_indexed": {
                                "description": "The one-indexed line number to start reading from",
                                "type": "integer"
                            },
                            "end_line_one_indexed_inclusive": {
                                "description": "The one-indexed line number to end reading at",
                                "type": "integer"
                            }
                        },
                        "required": [
                            "target_file",
                            "should_read_entire_file",
                            "start_line_one_indexed", 
                            "end_line_one_indexed_inclusive"
                        ],
                        "type": "object"
                    }
                }
            }
        ],
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 4000,
        "stream": False
    }
    
    print(f"📤 Отправляем запрос...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://192.168.0.182:8000/v1/chat/completions",
                json=cursor_request,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer fake-key",
                    "User-Agent": "cursor-vscode"
                },
                timeout=30.0
            )
            
            print(f"📨 Статус: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📨 Ответ получен!")
                
                # Проверяем структуру ответа
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    
                    print(f"   Role: {message.get('role', 'unknown')}")
                    print(f"   Content: {message.get('content', '')[:100]}...")
                    print(f"   Tool calls: {len(message.get('tool_calls', []))}")
                    
                    if message.get("tool_calls"):
                        for i, tc in enumerate(message["tool_calls"]):
                            print(f"     Tool {i+1}: {tc.get('function', {}).get('name', 'unknown')}")
                            print(f"     Args: {tc.get('function', {}).get('arguments', '')[:100]}...")
                        
                        # Теперь симулируем выполнение tool и отправку результата
                        print("\n🔧 Симулируем выполнение tool...")
                        
                        tool_call = message["tool_calls"][0]
                        tool_result = "Содержимое файла README.md:\n\n# Test file\nThis is a test file."
                        
                        # Второй запрос с результатом tool
                        second_request = {
                            "model": "gpt-4.1",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Прочитай файл README.md и скажи что в нем"
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
                            "tools": cursor_request["tools"],
                            "tool_choice": "auto",
                            "temperature": 0.0,
                            "max_tokens": 4000,
                            "stream": False
                        }
                        
                        print("📤 Отправляем второй запрос с результатом tool...")
                        
                        response2 = await client.post(
                            "http://192.168.0.182:8000/v1/chat/completions",
                            json=second_request,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": "Bearer fake-key",
                                "User-Agent": "cursor-vscode"
                            },
                            timeout=30.0
                        )
                        
                        print(f"📨 Второй ответ: {response2.status_code}")
                        
                        if response2.status_code == 200:
                            data2 = response2.json()
                            message2 = data2["choices"][0]["message"]
                            print(f"🎉 Финальный ответ: {message2.get('content', '')[:200]}...")
                            return True
                        else:
                            print(f"❌ Ошибка во втором запросе: {response2.text}")
                            return False
                    else:
                        print("❌ Нет tool calls в ответе")
                        return False
                else:
                    print("❌ Нет choices в ответе")
                    return False
            else:
                print(f"❌ Ошибка: {response.status_code}")
                print(f"❌ Тело: {response.text}")
                return False
                
        except Exception as e:
            print(f"💥 Исключение: {e}")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_cursor_simulation())
    if result:
        print("\n✅ СИМУЛЯЦИЯ CURSOR УСПЕШНА!")
    else:
        print("\n❌ СИМУЛЯЦИЯ CURSOR ПРОВАЛЕНА!") 