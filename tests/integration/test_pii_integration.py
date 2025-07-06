#!/usr/bin/env python3
"""
🧪 ТЕСТ PII ИНТЕГРАЦИИ С TOOL CALLING
Проверяем что PII redaction работает корректно с tool calling
"""

import asyncio
import json
import os
from typing import Dict, Any

# Импортируем наши компоненты
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway
from llm_pii_proxy.services.llm_service import LLMService
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.config.settings import Settings
from llm_pii_proxy.core.models import ChatRequest, ChatMessage

async def test_pii_basic_functionality():
    """Тест базовой функциональности PII"""
    print("🧪 ТЕСТ 1: Базовая функциональность PII")
    print("=" * 50)
    
    gateway = AsyncPIISecurityGateway()
    session_id = "test-session-1"
    
    # Тестовый контент с PII
    test_content = """
    Мой AWS ключ: AKIA1234567890EXAMPLE
    Пароль: mySecretPassword123
    API ключ: sk-abc123def456ghi789
    IP адрес: 192.168.1.100
    """
    
    print(f"📝 Исходный контент:")
    print(test_content)
    
    # Маскируем PII
    pii_result = await gateway.mask_sensitive_data(test_content, session_id)
    
    print(f"\n🔒 Результат маскирования:")
    print(f"   Найдено PII элементов: {pii_result.pii_count}")
    print(f"   Замаскированный контент:")
    print(pii_result.content)
    
    # Показываем маппинги
    print(f"\n🗂️ Маппинги:")
    for i, mapping in enumerate(pii_result.mappings):
        print(f"   {i+1}. '{mapping.original}' → '{mapping.masked}' (тип: {mapping.type})")
    
    # Демаскируем
    unmasked = await gateway.unmask_sensitive_data(pii_result.content, session_id)
    
    print(f"\n🔓 Демаскированный контент:")
    print(unmasked)
    
    # Проверяем что все восстановилось
    success = "AKIA1234567890EXAMPLE" in unmasked and "mySecretPassword123" in unmasked
    print(f"\n✅ Тест {'ПРОЙДЕН' if success else 'ПРОВАЛЕН'}")
    
    # Очищаем сессию
    await gateway.clear_session(session_id)
    
    return success

async def test_pii_with_tool_calling():
    """Тест PII с tool calling"""
    print("\n🧪 ТЕСТ 2: PII с Tool Calling")
    print("=" * 50)
    
    gateway = AsyncPIISecurityGateway()
    session_id = "test-session-2"
    
    # Создаем запрос с PII и tools
    request = ChatRequest(
        model="gpt-4.1",
        messages=[
            ChatMessage(
                role="user", 
                content="Создай файл с моим AWS ключом AKIA1234567890EXAMPLE и паролем mySecretPassword123"
            )
        ],
        session_id=session_id,
        pii_protection=True,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "Create a file with content",
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
    )
    
    print(f"📝 Исходное сообщение:")
    print(request.messages[0].content)
    
    # Маскируем PII в сообщении
    pii_result = await gateway.mask_sensitive_data(request.messages[0].content, session_id)
    
    print(f"\n🔒 Замаскированное сообщение:")
    print(pii_result.content)
    print(f"   Найдено PII: {pii_result.pii_count}")
    
    # Показываем все найденные маппинги
    print(f"\n🗂️ Найденные маппинги:")
    for i, mapping in enumerate(pii_result.mappings):
        print(f"   {i+1}. '{mapping.original}' → '{mapping.masked}' (тип: {mapping.type})")
    
    if pii_result.pii_count == 0:
        print("⚠️ PII элементы не найдены - тест не может продолжиться")
        return False
    
    # Используем первый найденный маппинг для симуляции
    first_mapping = pii_result.mappings[0]
    
    # Симулируем ответ LLM с tool call, который содержит маски
    simulated_response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "gpt-4.1",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_test",
                            "type": "function",
                            "function": {
                                "name": "create_file",
                                "arguments": json.dumps({
                                    "filename": "credentials.txt",
                                    "content": f"Найденный элемент: {first_mapping.masked}"
                                })
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }
        ]
    }
    
    print(f"\n🤖 Симулированный ответ LLM (с масками):")
    print(json.dumps(simulated_response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"], indent=2))
    
    # Демаскируем tool call arguments
    tool_call = simulated_response["choices"][0]["message"]["tool_calls"][0]
    masked_args = tool_call["function"]["arguments"]
    
    unmasked_args = await gateway.unmask_sensitive_data(masked_args, session_id)
    
    print(f"\n🔓 Демаскированные аргументы:")
    print(unmasked_args)
    
    # Проверяем что найденный PII элемент восстановился
    success = first_mapping.original in unmasked_args
    print(f"\n✅ Тест {'ПРОЙДЕН' if success else 'ПРОВАЛЕН'}")
    
    # Очищаем сессию
    await gateway.clear_session(session_id)
    
    return success

async def test_pii_streaming():
    """Тест PII со streaming"""
    print("\n🧪 ТЕСТ 3: PII со Streaming")
    print("=" * 50)
    
    gateway = AsyncPIISecurityGateway()
    session_id = "test-session-3"
    
    # Симулируем streaming chunks с PII
    chunks = [
        "Ваш AWS ключ ",
        "AKIA1234567890EXAMPLE ",
        "и пароль ",
        "mySecretPassword123 ",
        "сохранены в файле"
    ]
    
    print(f"📝 Исходные chunks:")
    for i, chunk in enumerate(chunks):
        print(f"   {i+1}. '{chunk}'")
    
    # Маскируем каждый chunk
    masked_chunks = []
    for i, chunk in enumerate(chunks):
        pii_result = await gateway.mask_sensitive_data(chunk, session_id)
        masked_chunks.append(pii_result.content)
        print(f"🔒 Chunk {i+1} маскирован: '{chunk}' → '{pii_result.content}'")
    
    # Собираем полный замаскированный текст
    full_masked = "".join(masked_chunks)
    print(f"\n🔗 Полный замаскированный текст:")
    print(full_masked)
    
    # Демаскируем полный текст
    unmasked = await gateway.unmask_sensitive_data(full_masked, session_id)
    
    print(f"\n🔓 Демаскированный текст:")
    print(unmasked)
    
    # Проверяем что все восстановилось
    success = "AKIA1234567890EXAMPLE" in unmasked and "mySecretPassword123" in unmasked
    print(f"\n✅ Тест {'ПРОЙДЕН' if success else 'ПРОВАЛЕН'}")
    
    # Очищаем сессию
    await gateway.clear_session(session_id)
    
    return success

async def test_pii_edge_cases():
    """Тест edge cases для PII"""
    print("\n🧪 ТЕСТ 4: Edge Cases")
    print("=" * 50)
    
    gateway = AsyncPIISecurityGateway()
    session_id = "test-session-4"
    
    # Тестируем разные edge cases
    test_cases = [
        ("", "Пустая строка"),
        ("   ", "Только пробелы"),
        ("Нет PII данных", "Текст без PII"),
        ("AKIA1234567890EXAMPLE", "Только AWS ключ"),
        ("password: mySecret", "Только пароль"),
    ]
    
    all_passed = True
    
    for content, description in test_cases:
        print(f"\n📝 Тест: {description}")
        print(f"   Контент: '{content}'")
        
        try:
            # Маскируем
            pii_result = await gateway.mask_sensitive_data(content, session_id)
            print(f"   Маскирован: '{pii_result.content}' (PII: {pii_result.pii_count})")
            
            # Демаскируем
            unmasked = await gateway.unmask_sensitive_data(pii_result.content, session_id)
            print(f"   Демаскирован: '{unmasked}'")
            
            # Проверяем что результат корректный
            if pii_result.pii_count == 0:
                # Если PII не найдено, текст должен остаться неизменным
                success = content == pii_result.content == unmasked
            else:
                # Если PII найдено, демаскированный текст должен совпадать с исходным
                success = content == unmasked
            
            print(f"   ✅ {'ПРОЙДЕН' if success else 'ПРОВАЛЕН'}")
            all_passed = all_passed and success
            
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            all_passed = False
    
    # Очищаем сессию
    await gateway.clear_session(session_id)
    
    return all_passed

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ PII ИНТЕГРАЦИИ")
    print("=" * 60)
    
    # Проверяем что файлы конфигурации существуют
    config_files = [
        "llm_pii_proxy/config/pii_patterns.yaml",
        "azure.env"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ Найден конфигурационный файл: {config_file}")
        else:
            print(f"⚠️ Не найден конфигурационный файл: {config_file}")
    
    # Запускаем тесты
    tests = [
        test_pii_basic_functionality,
        test_pii_with_tool_calling,
        test_pii_streaming,
        test_pii_edge_cases
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
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Пройдено тестов: {passed}/{total}")
    print(f"Успешность: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 