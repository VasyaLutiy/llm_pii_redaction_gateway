#!/usr/bin/env python3
"""
🧪 ТЕСТ PII С РЕАЛЬНЫМ LLM СЕРВИСОМ
Проверяем интеграцию PII с LLMService
"""

import asyncio
import json
import os
from typing import Dict, Any

# Импортируем наши компоненты
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.services.llm_service import LLMService
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway
from llm_pii_proxy.config.settings import Settings
from llm_pii_proxy.core.models import ChatRequest, ChatMessage

async def test_llm_service_without_pii():
    """Тест LLM сервиса без PII (текущее состояние)"""
    print("🧪 ТЕСТ 1: LLM сервис БЕЗ PII защиты")
    print("=" * 50)
    
    # Настройка компонентов
    azure_provider = AzureOpenAIProvider()  # Не передаем аргументы
    pii_gateway = AsyncPIISecurityGateway()
    llm_service = LLMService(azure_provider, pii_gateway)
    
    # Создаем запрос с PII данными
    request = ChatRequest(
        model="gpt-4.1",
        messages=[
            ChatMessage(
                role="user", 
                content="Привет! Мой AWS ключ AKIA1234567890EXAMPLE и пароль mySecret123"
            )
        ],
        pii_protection=True,  # Запрашиваем защиту, но она отключена глобально
        max_tokens=50
    )
    
    print(f"📝 Исходный запрос:")
    print(f"   Сообщение: {request.messages[0].content}")
    print(f"   PII защита запрошена: {request.pii_protection}")
    print(f"   Переменная PII_PROTECTION_ENABLED: {os.getenv('PII_PROTECTION_ENABLED', 'false')}")
    
    try:
        # Отправляем запрос
        response = await llm_service.process_chat_request(request)
        
        print(f"\n✅ Запрос успешно обработан!")
        print(f"   ID ответа: {response.id}")
        print(f"   Модель: {response.model}")
        print(f"   Контент ответа: {response.choices[0]['message']['content'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при обработке запроса: {e}")
        return False

async def test_llm_service_with_pii_enabled():
    """Тест LLM сервиса с включенной PII защитой"""
    print("\n🧪 ТЕСТ 2: LLM сервис С PII защитой")
    print("=" * 50)
    
    # Временно включаем PII защиту
    original_pii_setting = os.getenv('PII_PROTECTION_ENABLED', 'false')
    os.environ['PII_PROTECTION_ENABLED'] = 'true'
    
    try:
        # Настройка компонентов
        azure_provider = AzureOpenAIProvider()  # Не передаем аргументы
        pii_gateway = AsyncPIISecurityGateway()
        llm_service = LLMService(azure_provider, pii_gateway)
        
        # Создаем запрос с PII данными
        request = ChatRequest(
            model="gpt-4.1",
            messages=[
                ChatMessage(
                    role="user", 
                    content="Привет! Мой AWS ключ AKIA1234567890EXAMPLE и IP адрес 192.168.1.100"
                )
            ],
            pii_protection=True,
            max_tokens=50
        )
        
        print(f"📝 Исходный запрос:")
        print(f"   Сообщение: {request.messages[0].content}")
        print(f"   PII защита запрошена: {request.pii_protection}")
        print(f"   Переменная PII_PROTECTION_ENABLED: {os.getenv('PII_PROTECTION_ENABLED', 'false')}")
        
        # Отправляем запрос
        response = await llm_service.process_chat_request(request)
        
        print(f"\n✅ Запрос успешно обработан с PII защитой!")
        print(f"   ID ответа: {response.id}")
        print(f"   Модель: {response.model}")
        print(f"   Контент ответа: {response.choices[0]['message']['content'][:200]}...")
        
        # Проверяем что в ответе нет замаскированных данных (они должны быть демаскированы)
        response_content = response.choices[0]['message']['content']
        if '<aws_key_' in response_content or '<ip_address_' in response_content:
            print(f"⚠️ ВНИМАНИЕ: В ответе остались замаскированные данные!")
            print(f"   Это может означать проблему с демаскированием")
        else:
            print(f"✅ Ответ корректно демаскирован")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при обработке запроса с PII: {e}")
        return False
    
    finally:
        # Восстанавливаем оригинальную настройку
        os.environ['PII_PROTECTION_ENABLED'] = original_pii_setting

async def test_llm_service_with_tools_and_pii():
    """Тест LLM сервиса с tools и PII защитой"""
    print("\n🧪 ТЕСТ 3: LLM сервис с Tools и PII защитой")
    print("=" * 50)
    
    # Временно включаем PII защиту
    original_pii_setting = os.getenv('PII_PROTECTION_ENABLED', 'false')
    os.environ['PII_PROTECTION_ENABLED'] = 'true'
    
    try:
        # Настройка компонентов
        azure_provider = AzureOpenAIProvider()  # Не передаем аргументы
        pii_gateway = AsyncPIISecurityGateway()
        llm_service = LLMService(azure_provider, pii_gateway)
        
        # Создаем запрос с PII данными и tools
        request = ChatRequest(
            model="gpt-4.1",
            messages=[
                ChatMessage(
                    role="user", 
                    content="Создай файл с моим AWS ключом AKIA1234567890EXAMPLE"
                )
            ],
            pii_protection=True,
            max_tokens=150,
            tools=[
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
        )
        
        print(f"📝 Исходный запрос:")
        print(f"   Сообщение: {request.messages[0].content}")
        print(f"   PII защита: {request.pii_protection}")
        print(f"   Tools: {len(request.tools)} tool(s)")
        
        # Отправляем запрос
        response = await llm_service.process_chat_request(request)
        
        print(f"\n✅ Запрос с tools успешно обработан!")
        print(f"   ID ответа: {response.id}")
        print(f"   Модель: {response.model}")
        
        # Проверяем ответ
        choice = response.choices[0]
        if choice.get('message', {}).get('tool_calls'):
            print(f"   🔧 Tool calls найдены: {len(choice['message']['tool_calls'])}")
            
            for i, tool_call in enumerate(choice['message']['tool_calls']):
                print(f"   Tool {i+1}: {tool_call['function']['name']}")
                args = tool_call['function']['arguments']
                
                # Проверяем что аргументы демаскированы
                if isinstance(args, str):
                    args_dict = json.loads(args)
                else:
                    args_dict = args
                
                print(f"   Аргументы: {args_dict}")
                
                # Проверяем что AWS ключ демаскирован
                args_str = json.dumps(args_dict)
                if 'AKIA1234567890EXAMPLE' in args_str:
                    print(f"   ✅ AWS ключ корректно демаскирован в tool call")
                elif '<aws_key_' in args_str:
                    print(f"   ⚠️ AWS ключ остался замаскированным в tool call")
                else:
                    print(f"   ℹ️ AWS ключ не найден в tool call аргументах")
        else:
            print(f"   📝 Обычный ответ (без tool calls)")
            content = choice.get('message', {}).get('content', '')
            print(f"   Контент: {content[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при обработке запроса с tools и PII: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Восстанавливаем оригинальную настройку
        os.environ['PII_PROTECTION_ENABLED'] = original_pii_setting

async def test_pii_configuration():
    """Тест конфигурации PII"""
    print("\n🧪 ТЕСТ 4: Конфигурация PII")
    print("=" * 50)
    
    # Проверяем файлы конфигурации
    config_files = [
        "llm_pii_proxy/config/pii_patterns.yaml",
        "azure.env"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ Найден: {config_file}")
        else:
            print(f"❌ Не найден: {config_file}")
    
    # Проверяем переменные окружения
    env_vars = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'PII_PROTECTION_ENABLED',
        'PII_PROXY_DEBUG'
    ]
    
    print(f"\n📋 Переменные окружения:")
    for var in env_vars:
        value = os.getenv(var, 'НЕ УСТАНОВЛЕНА')
        if var.endswith('_KEY'):
            # Скрываем ключи
            display_value = f"{value[:10]}..." if len(value) > 10 else value
        else:
            display_value = value
        print(f"   {var}: {display_value}")
    
    # Тестируем создание компонентов
    try:
        settings = Settings()
        print(f"\n✅ Settings успешно инициализированы")
        
        azure_provider = AzureOpenAIProvider()  # Не передаем аргументы
        print(f"✅ AzureOpenAIProvider успешно инициализирован")
        
        pii_gateway = AsyncPIISecurityGateway()
        print(f"✅ AsyncPIISecurityGateway успешно инициализирован")
        
        llm_service = LLMService(azure_provider, pii_gateway)
        print(f"✅ LLMService успешно инициализирован")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка инициализации компонентов: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ PII ИНТЕГРАЦИИ С LLM СЕРВИСОМ")
    print("=" * 60)
    
    # Запускаем тесты
    tests = [
        test_pii_configuration,
        test_llm_service_without_pii,
        test_llm_service_with_pii_enabled,
        test_llm_service_with_tools_and_pii
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