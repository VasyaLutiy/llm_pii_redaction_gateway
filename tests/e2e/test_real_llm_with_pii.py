#!/usr/bin/env python3
"""
🧪 ТЕСТ PII С РЕАЛЬНОЙ LLM
Проверяем что PII защита работает с реальными вызовами Azure OpenAI
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

async def test_pii_with_real_llm_simple():
    """Тест PII с реальным LLM - простой запрос"""
    print("🧪 ТЕСТ 1: PII с реальным LLM - простой запрос")
    print("=" * 60)
    
    # Включаем PII защиту
    os.environ['PII_PROTECTION_ENABLED'] = 'true'
    
    try:
        # Создаем компоненты с включенной PII защитой
        settings = Settings()
        azure_provider = AzureOpenAIProvider()
        pii_gateway = AsyncPIISecurityGateway()
        llm_service = LLMService(azure_provider, pii_gateway)
        
        print(f"📋 Конфигурация:")
        print(f"   PII защита: {settings.pii_protection_enabled}")
        print(f"   Debug режим: {settings.pii_proxy_debug}")
        print(f"   Azure endpoint: {settings.azure_openai_endpoint}")
        print(f"   Azure model: {settings.azure_completions_model}")
        
        # Создаем запрос с PII данными
        request = ChatRequest(
            model="gpt-4.1",
            messages=[
                ChatMessage(
                    role="user", 
                    content="Привет! Мой AWS ключ AKIA1234567890EXAMPLE и IP адрес 192.168.1.100. Можешь сказать что-то об этих данных?"
                )
            ],
            pii_protection=True,
            max_tokens=100
        )
        
        print(f"\n📝 Исходный запрос:")
        print(f"   Сообщение: {request.messages[0].content}")
        print(f"   PII защита запрошена: {request.pii_protection}")
        
        print(f"\n🚀 Отправляем запрос к реальной LLM с PII защитой...")
        
        # Отправляем запрос
        response = await llm_service.process_chat_request(request)
        
        print(f"\n✅ Ответ получен!")
        print(f"   ID ответа: {response.id}")
        print(f"   Модель: {response.model}")
        
        response_content = response.choices[0]['message']['content']
        print(f"   Контент ответа:")
        print(f"   {response_content}")
        
        # Проверяем что в ответе есть оригинальные PII данные (демаскированы)
        has_original_aws = "AKIA1234567890EXAMPLE" in response_content
        has_original_ip = "192.168.1.100" in response_content
        has_masked_data = "<aws_key_" in response_content or "<ip_address_" in response_content
        
        print(f"\n🔍 Анализ ответа:")
        print(f"   Содержит оригинальный AWS ключ: {has_original_aws}")
        print(f"   Содержит оригинальный IP: {has_original_ip}")
        print(f"   Содержит замаскированные данные: {has_masked_data}")
        
        if has_original_aws or has_original_ip:
            print(f"   ✅ PII корректно демаскирован в ответе")
            success = True
        elif has_masked_data:
            print(f"   ⚠️ В ответе остались замаскированные данные")
            success = False
        else:
            print(f"   ℹ️ LLM не упомянул PII данные в ответе")
            success = True  # Это тоже нормально
        
        return success
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании с реальной LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_pii_with_real_llm_tools():
    """Тест PII с реальным LLM и tool calls"""
    print("\n🧪 ТЕСТ 2: PII с реальным LLM и tool calls")
    print("=" * 60)
    
    # Включаем PII защиту
    os.environ['PII_PROTECTION_ENABLED'] = 'true'
    
    try:
        # Создаем компоненты
        settings = Settings()
        azure_provider = AzureOpenAIProvider()
        pii_gateway = AsyncPIISecurityGateway()
        llm_service = LLMService(azure_provider, pii_gateway)
        
        # Создаем запрос с PII данными и tools
        request = ChatRequest(
            model="gpt-4.1",
            messages=[
                ChatMessage(
                    role="user", 
                    content="Создай файл credentials.txt с моим AWS ключом AKIA1234567890EXAMPLE"
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
        print(f"   Tools: {len(request.tools)} tool(s)")
        
        print(f"\n🚀 Отправляем запрос с tools к реальной LLM...")
        
        # Отправляем запрос
        response = await llm_service.process_chat_request(request)
        
        print(f"\n✅ Ответ получен!")
        print(f"   ID ответа: {response.id}")
        print(f"   Модель: {response.model}")
        
        # Проверяем ответ
        choice = response.choices[0]
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
                
                # Проверяем что AWS ключ демаскирован в tool call
                args_str = json.dumps(args_dict)
                has_original_aws = "AKIA1234567890EXAMPLE" in args_str
                has_masked_aws = "<aws_key_" in args_str
                
                print(f"     🔍 Анализ аргументов:")
                print(f"       Содержит оригинальный AWS ключ: {has_original_aws}")
                print(f"       Содержит замаскированный AWS ключ: {has_masked_aws}")
                
                if has_original_aws:
                    print(f"       ✅ AWS ключ корректно демаскирован в tool call")
                    success = True
                elif has_masked_aws:
                    print(f"       ❌ AWS ключ остался замаскированным в tool call")
                    success = False
                else:
                    print(f"       ⚠️ AWS ключ не найден в tool call аргументах")
                    success = False
        else:
            print(f"   📝 Обычный ответ (без tool calls)")
            content = choice.get('message', {}).get('content', '')
            print(f"   Контент: {content}")
            
            # Если нет tool calls, проверяем обычный контент
            has_original_aws = "AKIA1234567890EXAMPLE" in content
            success = has_original_aws
        
        return success
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании tools с реальной LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_pii_disabled_vs_enabled():
    """Тест сравнения PII отключен vs включен"""
    print("\n🧪 ТЕСТ 3: Сравнение PII отключен vs включен")
    print("=" * 60)
    
    test_message = "Мой AWS ключ AKIA1234567890EXAMPLE"
    
    try:
        # Тест 1: PII отключен
        print(f"🔴 Тест с ОТКЛЮЧЕННОЙ PII защитой:")
        os.environ['PII_PROTECTION_ENABLED'] = 'false'
        
        settings_off = Settings()
        azure_provider_off = AzureOpenAIProvider()
        pii_gateway_off = AsyncPIISecurityGateway()
        llm_service_off = LLMService(azure_provider_off, pii_gateway_off)
        
        request_off = ChatRequest(
            model="gpt-4.1",
            messages=[ChatMessage(role="user", content=test_message)],
            pii_protection=True,
            max_tokens=50
        )
        
        print(f"   Settings PII enabled: {settings_off.pii_protection_enabled}")
        print(f"   LLMService PII enabled: {llm_service_off.pii_enabled}")
        
        # Тест 2: PII включен
        print(f"\n🟢 Тест с ВКЛЮЧЕННОЙ PII защитой:")
        os.environ['PII_PROTECTION_ENABLED'] = 'true'
        
        settings_on = Settings()
        azure_provider_on = AzureOpenAIProvider()
        pii_gateway_on = AsyncPIISecurityGateway()
        llm_service_on = LLMService(azure_provider_on, pii_gateway_on)
        
        request_on = ChatRequest(
            model="gpt-4.1",
            messages=[ChatMessage(role="user", content=test_message)],
            pii_protection=True,
            max_tokens=50
        )
        
        print(f"   Settings PII enabled: {settings_on.pii_protection_enabled}")
        print(f"   LLMService PII enabled: {llm_service_on.pii_enabled}")
        
        # Проверяем что настройки различаются
        config_different = (
            settings_off.pii_protection_enabled != settings_on.pii_protection_enabled or
            llm_service_off.pii_enabled != llm_service_on.pii_enabled
        )
        
        if config_different:
            print(f"\n✅ Конфигурации корректно различаются")
            return True
        else:
            print(f"\n❌ Конфигурации не различаются")
            return False
        
    except Exception as e:
        print(f"\n❌ Ошибка при сравнении конфигураций: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ PII С РЕАЛЬНОЙ LLM")
    print("=" * 70)
    
    # Сохраняем оригинальную настройку
    original_pii_setting = os.getenv('PII_PROTECTION_ENABLED')
    
    try:
        # Запускаем тесты
        tests = [
            test_pii_disabled_vs_enabled,
            test_pii_with_real_llm_simple,
            test_pii_with_real_llm_tools
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
        print("📊 ИТОГОВЫЙ ОТЧЕТ")
        print("=" * 70)
        
        passed = sum(results)
        total = len(results)
        
        print(f"Пройдено тестов: {passed}/{total}")
        print(f"Успешность: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
            print("✅ PII защита работает корректно с реальной LLM")
        else:
            print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
            print("❌ PII защита требует доработки")
        
        return passed == total
        
    finally:
        # Восстанавливаем оригинальную настройку
        if original_pii_setting is not None:
            os.environ['PII_PROTECTION_ENABLED'] = original_pii_setting
        else:
            os.environ.pop('PII_PROTECTION_ENABLED', None)

if __name__ == "__main__":
    asyncio.run(main()) 