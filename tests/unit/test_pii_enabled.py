#!/usr/bin/env python3
"""
🧪 ТЕСТ PII В ВКЛЮЧЕННОМ СОСТОЯНИИ
Проверяем что PII защита работает когда включена
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

async def test_pii_protection_enabled():
    """Тест PII защиты в включенном состоянии"""
    print("🧪 ТЕСТ: PII защита ВКЛЮЧЕНА")
    print("=" * 50)
    
    # Включаем PII защиту
    os.environ['PII_PROTECTION_ENABLED'] = 'true'
    
    try:
        # Создаем новые экземпляры с включенной PII защитой
        settings = Settings()
        azure_provider = AzureOpenAIProvider()
        pii_gateway = AsyncPIISecurityGateway()
        llm_service = LLMService(azure_provider, pii_gateway)
        
        print(f"📋 Конфигурация:")
        print(f"   PII защита в settings: {settings.pii_protection_enabled}")
        print(f"   PII защита в LLMService: {llm_service.pii_enabled}")
        print(f"   Debug режим: {settings.pii_proxy_debug}")
        
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
        
        print(f"\n📝 Исходный запрос:")
        print(f"   Сообщение: {request.messages[0].content}")
        print(f"   PII защита запрошена: {request.pii_protection}")
        
        # Тестируем только PII gateway напрямую (без реального LLM вызова)
        print(f"\n🔍 Тестируем PII gateway напрямую:")
        
        session_id = "test-session"
        pii_result = await pii_gateway.mask_sensitive_data(
            content=request.messages[0].content,
            session_id=session_id
        )
        
        print(f"   Найдено PII элементов: {pii_result.pii_count}")
        print(f"   Замаскированный контент: {pii_result.content}")
        
        if pii_result.pii_count > 0:
            print(f"   🔒 PII элементы найдены и замаскированы:")
            for i, mapping in enumerate(pii_result.mappings):
                print(f"      {i+1}. '{mapping.original}' → '{mapping.masked}' (тип: {mapping.type})")
            
            # Тестируем демаскирование
            unmasked = await pii_gateway.unmask_sensitive_data(pii_result.content, session_id)
            print(f"   🔓 Демаскированный контент: {unmasked}")
            
            # Проверяем что демаскирование работает
            if request.messages[0].content == unmasked:
                print(f"   ✅ Демаскирование работает корректно")
                success = True
            else:
                print(f"   ❌ Демаскирование не работает")
                success = False
        else:
            print(f"   ⚠️ PII элементы не найдены")
            success = False
        
        # Очищаем сессию
        await pii_gateway.clear_session(session_id)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании PII: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_pii_with_mock_llm_response():
    """Тест PII с симулированным ответом LLM"""
    print("\n🧪 ТЕСТ: PII с симулированным LLM ответом")
    print("=" * 50)
    
    # Включаем PII защиту
    os.environ['PII_PROTECTION_ENABLED'] = 'true'
    
    try:
        # Создаем компоненты
        settings = Settings()
        pii_gateway = AsyncPIISecurityGateway()
        
        session_id = "test-session-2"
        
        # Исходное сообщение с PII
        original_message = "Создай файл с моим AWS ключом AKIA1234567890EXAMPLE"
        
        print(f"📝 Исходное сообщение: {original_message}")
        
        # 1. Маскируем PII в запросе
        pii_result = await pii_gateway.mask_sensitive_data(original_message, session_id)
        masked_message = pii_result.content
        
        print(f"🔒 Замаскированное сообщение: {masked_message}")
        print(f"   Найдено PII: {pii_result.pii_count}")
        
        # 2. Симулируем ответ LLM который использует маски
        if pii_result.pii_count > 0:
            aws_mask = pii_result.mappings[0].masked
            simulated_llm_response = f"Я создам файл с вашим AWS ключом {aws_mask}. Убедитесь что {aws_mask} корректный."
            
            print(f"🤖 Симулированный ответ LLM: {simulated_llm_response}")
            
            # 3. Демаскируем ответ
            unmasked_response = await pii_gateway.unmask_sensitive_data(simulated_llm_response, session_id)
            
            print(f"🔓 Демаскированный ответ: {unmasked_response}")
            
            # Проверяем что оригинальный AWS ключ восстановился
            if "AKIA1234567890EXAMPLE" in unmasked_response:
                print(f"✅ AWS ключ корректно демаскирован в ответе")
                success = True
            else:
                print(f"❌ AWS ключ не демаскирован в ответе")
                success = False
        else:
            print(f"⚠️ PII не найдено, тест не может продолжиться")
            success = False
        
        # Очищаем сессию
        await pii_gateway.clear_session(session_id)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании PII с LLM: {e}")
        return False

async def test_pii_configuration_validation():
    """Тест валидации PII конфигурации"""
    print("\n🧪 ТЕСТ: Валидация PII конфигурации")
    print("=" * 50)
    
    try:
        # Включаем PII защиту
        os.environ['PII_PROTECTION_ENABLED'] = 'true'
        
        # Создаем settings
        settings = Settings()
        
        print(f"📋 PII конфигурация:")
        print(f"   PII включен: {settings.pii_protection_enabled}")
        print(f"   PII patterns файл: {settings.pii_patterns_config_path}")
        print(f"   PII timeout: {settings.pii_session_timeout_minutes}")
        
        # Проверяем что файл patterns существует
        if os.path.exists(settings.pii_patterns_config_path):
            print(f"   ✅ PII patterns файл найден")
            
            # Пробуем создать PII gateway
            pii_gateway = AsyncPIISecurityGateway()
            print(f"   ✅ PII gateway успешно создан")
            
            return True
        else:
            print(f"   ❌ PII patterns файл не найден")
            return False
        
    except Exception as e:
        print(f"\n❌ Ошибка валидации PII конфигурации: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ PII В ВКЛЮЧЕННОМ СОСТОЯНИИ")
    print("=" * 60)
    
    # Сохраняем оригинальную настройку
    original_pii_setting = os.getenv('PII_PROTECTION_ENABLED')
    
    try:
        # Запускаем тесты
        tests = [
            test_pii_configuration_validation,
            test_pii_protection_enabled,
            test_pii_with_mock_llm_response
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
            print("✅ PII защита работает корректно в включенном состоянии")
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