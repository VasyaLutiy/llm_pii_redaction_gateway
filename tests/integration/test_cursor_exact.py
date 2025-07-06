#!/usr/bin/env python3
"""
Точная имитация запроса от Cursor
"""

import json
import asyncio
import httpx

async def test_cursor_exact():
    """Точно имитирует запрос от Cursor"""
    
    # Точно такой же запрос как от Cursor
    cursor_request = {
        "model": "gpt-4.1",
        "temperature": 0,
        "user": "389",
        "messages": [
            {
                "role": "system",
                "content": "You are an AI coding assistant, powered by GPT-4.1. You operate in Cursor."
            },
            {
                "role": "user", 
                "content": "привет проанализруй файлы *.md в текушей директории"
            }
        ],
        "stream": True,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "codebase_search",
                    "description": "semantic search that finds code by meaning",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A complete question about what you want to understand"
                            },
                            "target_directories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Prefix directory paths to limit search scope"
                            },
                            "explanation": {
                                "type": "string", 
                                "description": "One sentence explanation"
                            }
                        },
                        "required": ["explanation", "query", "target_directories"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_file": {
                                "type": "string",
                                "description": "The path of the file to read"
                            },
                            "should_read_entire_file": {
                                "type": "boolean",
                                "description": "Whether to read the entire file"
                            },
                            "start_line_one_indexed": {
                                "type": "integer",
                                "description": "The one-indexed line number to start reading from"
                            },
                            "end_line_one_indexed_inclusive": {
                                "type": "integer",
                                "description": "The one-indexed line number to end reading at"
                            },
                            "explanation": {
                                "type": "string",
                                "description": "One sentence explanation"
                            }
                        },
                        "required": ["target_file", "should_read_entire_file", "start_line_one_indexed", "end_line_one_indexed_inclusive"]
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    print("🚀 Отправляем точную копию запроса от Cursor...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://192.168.0.182:8000/v1/chat/completions",
                json=cursor_request,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer 12345",
                    "User-Agent": "axios/1.9.0"
                },
                timeout=30.0
            )
            
            print(f"📨 Статус: {response.status_code}")
            
            if response.status_code == 200:
                # Для streaming читаем построчно
                content = response.text
                print(f"📨 Streaming ответ получен! Длина: {len(content)} символов")
                
                # Парсим streaming chunks
                lines = content.strip().split('\n')
                tool_calls_found = False
                
                for line in lines:
                    if line.startswith('data: '):
                        data_str = line[6:]  # Убираем 'data: '
                        if data_str == '[DONE]':
                            print("✅ Streaming завершен")
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                choice = chunk['choices'][0]
                                if 'delta' in choice:
                                    delta = choice['delta']
                                    if 'tool_calls' in delta:
                                        tool_calls_found = True
                                        print(f"🔧 НАЙДЕНЫ TOOL CALLS в streaming chunk!")
                                        print(f"   Tool calls: {delta['tool_calls']}")
                                    elif 'content' in delta and delta['content']:
                                        print(f"📝 Content chunk: {delta['content'][:100]}...")
                        except json.JSONDecodeError:
                            continue
                
                if tool_calls_found:
                    print("✅ TOOL CALLS найдены в streaming ответе!")
                    return True
                else:
                    print("❌ НЕТ TOOL CALLS в streaming ответе")
                    return False
                    
            else:
                print(f"❌ Ошибка: {response.status_code}")
                print(f"❌ Тело: {response.text}")
                return False
                
        except Exception as e:
            print(f"💥 Исключение: {e}")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_cursor_exact())
    if result:
        print("\n✅ ТОЧНАЯ ИМИТАЦИЯ CURSOR УСПЕШНА!")
    else:
        print("\n❌ ТОЧНАЯ ИМИТАЦИЯ CURSOR ПРОВАЛЕНА!") 