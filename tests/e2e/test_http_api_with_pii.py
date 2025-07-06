#!/usr/bin/env python3
"""
🧪 ТЕСТ HTTP API С PII ЗАЩИТОЙ
Проверяем что HTTP API работает с включенной PII защитой
"""

import asyncio
import aiohttp
import json
import time

async def test_http_api_simple_pii():
    """Тест простого запроса через HTTP API с PII"""
    print("🧪 ТЕСТ 1: HTTP API - простой запрос с PII")
    print("=" * 60)
    
    url = "http://192.168.0.182:8000/v1/chat/completions"
    
    payload = {
        "model": "gpt-4.1",
        "messages": [
            {
                "role": "user",
                "content": "Привет! Мой AWS ключ AKIA1234567890EXAMPLE и пароль MySecretPassword123. Можешь сказать что-то о безопасности?"
            }
        ],
        "pii_protection": True,
        "max_tokens": 150
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key"
    }
    
    print(f"📝 Отправляем запрос:")
    print(f"   URL: {url}")
    print(f"   Сообщение: {payload['messages'][0]['content']}")
    print(f"   PII защита: {payload['pii_protection']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.post(url, json=payload, headers=headers) as response:
                duration = time.time() - start_time
                
                print(f"\n✅ Ответ получен!")
                print(f"   Статус: {response.status}")
                print(f"   Время: {duration:.2f}s")
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"   ID ответа: {data.get('id')}")
                    print(f"   Модель: {data.get('model')}")
                    
                    content = data['choices'][0]['message']['content']
                    print(f"   Контент ответа:")
                    print(f"   {content}")
                    
                    # Проверяем что PII данные демаскированы
                    has_original_aws = "AKIA1234567890EXAMPLE" in content
                    has_original_password = "MySecretPassword123" in content
                    has_masked_data = "<aws_key_" in content or "<password_" in content
                    
                    print(f"\n🔍 Анализ ответа:")
                    print(f"   Содержит оригинальный AWS ключ: {has_original_aws}")
                    print(f"   Содержит оригинальный пароль: {has_original_password}")
                    print(f"   Содержит замаскированные данные: {has_masked_data}")
                    
                    if has_original_aws or has_original_password:
                        print(f"   ✅ PII корректно демаскирован в ответе")
                        return True
                    elif has_masked_data:
                        print(f"   ⚠️ В ответе остались замаскированные данные")
                        return False
                    else:
                        print(f"   ℹ️ LLM не упомянул PII данные в ответе (это нормально)")
                        return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Ошибка: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ Ошибка при HTTP запросе: {e}")
        return False

async def test_http_api_tools_pii():
    """Тест tool calls через HTTP API с PII"""
    print("\n🧪 ТЕСТ 2: HTTP API - tool calls с PII")
    print("=" * 60)
    
    url = "http://192.168.0.182:8000/v1/chat/completions"
    
    payload = {
        "model": "gpt-4.1",
        "messages": [
            {
                "role": "user",
                "content": "Создай файл config.json с моим AWS ключом AKIA1234567890EXAMPLE и паролем MySecretPassword123"
            }
        ],
        "pii_protection": True,
        "max_tokens": 200,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "Create a file with given content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["filename", "content"]
                    }
                }
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key"
    }
    
    print(f"📝 Отправляем запрос:")
    print(f"   URL: {url}")
    print(f"   Сообщение: {payload['messages'][0]['content']}")
    print(f"   Tools: {len(payload['tools'])} tool(s)")
    print(f"   PII защита: {payload['pii_protection']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.post(url, json=payload, headers=headers) as response:
                duration = time.time() - start_time
                
                print(f"\n✅ Ответ получен!")
                print(f"   Статус: {response.status}")
                print(f"   Время: {duration:.2f}s")
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"   ID ответа: {data.get('id')}")
                    print(f"   Модель: {data.get('model')}")
                    
                    choice = data['choices'][0]
                    if choice.get('message', {}).get('tool_calls'):
                        print(f"   🔧 Tool calls найдены: {len(choice['message']['tool_calls'])}")
                        
                        for i, tool_call in enumerate(choice['message']['tool_calls']):
                            print(f"\n   Tool call {i+1}:")
                            print(f"     Function: {tool_call['function']['name']}")
                            
                            args = tool_call['function']['arguments']
                            if isinstance(args, str):
                                args_dict = json.loads(args)
                            else:
                                args_dict = args
                            
                            print(f"     Arguments: {json.dumps(args_dict, indent=6, ensure_ascii=False)}")
                            
                            # Проверяем что PII данные демаскированы в tool call
                            args_str = json.dumps(args_dict)
                            has_original_aws = "AKIA1234567890EXAMPLE" in args_str
                            has_original_password = "MySecretPassword123" in args_str
                            has_masked_aws = "<aws_key_" in args_str
                            has_masked_password = "<password_" in args_str
                            
                            print(f"     🔍 Анализ аргументов:")
                            print(f"       Содержит оригинальный AWS ключ: {has_original_aws}")
                            print(f"       Содержит оригинальный пароль: {has_original_password}")
                            print(f"       Содержит замаскированный AWS ключ: {has_masked_aws}")
                            print(f"       Содержит замаскированный пароль: {has_masked_password}")
                            
                            if has_original_aws or has_original_password:
                                print(f"       ✅ PII корректно демаскирован в tool call")
                                return True
                            elif has_masked_aws or has_masked_password:
                                print(f"       ❌ PII остался замаскированным в tool call")
                                return False
                            else:
                                print(f"       ⚠️ PII данные не найдены в tool call аргументах")
                                return False
                    else:
                        print(f"   📝 Обычный ответ (без tool calls)")
                        content = choice.get('message', {}).get('content', '')
                        print(f"   Контент: {content}")
                        
                        # Если нет tool calls, проверяем обычный контент
                        has_original_aws = "AKIA1234567890EXAMPLE" in content
                        has_original_password = "MySecretPassword123" in content
                        return has_original_aws or has_original_password
                else:
                    error_text = await response.text()
                    print(f"   ❌ Ошибка: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ Ошибка при HTTP запросе: {e}")
        return False

async def test_http_api_pii_disabled():
    """Тест с отключенной PII защитой"""
    print("\n🧪 ТЕСТ 3: HTTP API - PII защита отключена")
    print("=" * 60)
    
    url = "http://192.168.0.182:8000/v1/chat/completions"
    
    payload = {
        "model": "gpt-4.1",
        "messages": [
            {
                "role": "user",
                "content": "Мой AWS ключ AKIA1234567890EXAMPLE"
            }
        ],
        "pii_protection": False,  # Отключаем PII защиту
        "max_tokens": 50
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key"
    }
    
    print(f"📝 Отправляем запрос:")
    print(f"   URL: {url}")
    print(f"   Сообщение: {payload['messages'][0]['content']}")
    print(f"   PII защита: {payload['pii_protection']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.post(url, json=payload, headers=headers) as response:
                duration = time.time() - start_time
                
                print(f"\n✅ Ответ получен!")
                print(f"   Статус: {response.status}")
                print(f"   Время: {duration:.2f}s")
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"   ID ответа: {data.get('id')}")
                    print(f"   Модель: {data.get('model')}")
                    
                    content = data['choices'][0]['message']['content']
                    print(f"   Контент ответа:")
                    print(f"   {content}")
                    
                    print(f"\n🔍 Анализ:")
                    print(f"   ✅ Запрос с отключенной PII защитой обработан успешно")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Ошибка: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ Ошибка при HTTP запросе: {e}")
        return False

async def test_http_api_health():
    """Тест health endpoint"""
    print("\n🧪 ТЕСТ 4: HTTP API - health check")
    print("=" * 60)
    
    url = "http://192.168.0.182:8000/health"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"   Статус: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    # Проверяем что есть информация о PII защите
                    has_pii_info = 'pii_protection' in str(data)
                    print(f"   Содержит информацию о PII: {has_pii_info}")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Ошибка: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ Ошибка при HTTP запросе: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ HTTP API С PII ЗАЩИТОЙ")
    print("=" * 70)
    
    # Ждем немного чтобы сервер точно запустился
    print("⏳ Ждем запуска сервера...")
    await asyncio.sleep(3)
    
    # Запускаем тесты
    tests = [
        test_http_api_health,
        test_http_api_pii_disabled,
        test_http_api_simple_pii,
        test_http_api_tools_pii
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Тест провален с ошибкой: {e}")
            results.append(False)
    
    # Итоговый отчет
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ HTTP API")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Пройдено тестов: {passed}/{total}")
    print(f"Успешность: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ВСЕ HTTP API ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ LLM PII Proxy готов к использованию с включенной PII защитой")
    else:
        print("⚠️ НЕКОТОРЫЕ HTTP API ТЕСТЫ ПРОВАЛЕНЫ")
        print("❌ Требуется дополнительная настройка")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 