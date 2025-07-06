#!/usr/bin/env python3
"""
🧪 ТЕСТ ЦЕНТРАЛИЗОВАННОЙ КОНФИГУРАЦИИ
Проверяем что settings.py работает корректно
"""

import asyncio
import json
import os
from typing import Dict, Any

# Импортируем наши компоненты
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.config.settings import Settings, settings
from llm_pii_proxy.services.llm_service import LLMService
from llm_pii_proxy.providers.azure_provider import AzureOpenAIProvider
from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway
from llm_pii_proxy.core.models import ChatRequest, ChatMessage

async def test_settings_initialization():
    """Тест инициализации settings"""
    print("🧪 ТЕСТ 1: Инициализация Settings")
    print("=" * 50)
    
    try:
        # Проверяем что глобальный settings уже инициализирован
        print(f"✅ Глобальный settings инициализирован")
        
        # Показываем конфигурацию
        config = settings.get_display_config()
        print(f"\n📋 Текущая конфигурация:")
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        # Проверяем критические настройки
        required_fields = [
            'azure_openai_endpoint',
            'azure_openai_api_key', 
            'azure_completions_model'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(settings, field.replace('azure_openai_', 'azure_openai_').replace('azure_completions_', 'azure_completions_')):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n⚠️ Отсутствуют критические настройки: {missing_fields}")
            return False
        else:
            print(f"\n✅ Все критические настройки присутствуют")
        
        # Проверяем PII настройки
        print(f"\n🔒 PII настройки:")
        print(f"   PII защита включена: {settings.pii_protection_enabled}")
        print(f"   PII patterns файл: {settings.pii_patterns_config_path}")
        print(f"   PII timeout: {settings.pii_session_timeout_minutes} минут")
        print(f"   Debug режим: {settings.pii_proxy_debug}")
        
        # Проверяем что PII patterns файл существует
        if os.path.exists(settings.pii_patterns_config_path):
            print(f"   ✅ PII patterns файл найден")
        else:
            print(f"   ⚠️ PII patterns файл не найден: {settings.pii_patterns_config_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка инициализации settings: {e}")
        return False

async def test_settings_env_override():
    """Тест переопределения настроек через переменные окружения"""
    print("\n🧪 ТЕСТ 2: Переопределение через ENV")
    print("=" * 50)
    
    # Сохраняем оригинальные значения
    original_pii_enabled = os.getenv('PII_PROTECTION_ENABLED')
    original_debug = os.getenv('PII_PROXY_DEBUG')
    
    try:
        # Устанавливаем тестовые значения
        os.environ['PII_PROTECTION_ENABLED'] = 'true'
        os.environ['PII_PROXY_DEBUG'] = 'true'
        
        # Создаем новый экземпляр settings
        test_settings = Settings()
        
        print(f"📝 Тестовые переменные окружения:")
        print(f"   PII_PROTECTION_ENABLED: {os.getenv('PII_PROTECTION_ENABLED')}")
        print(f"   PII_PROXY_DEBUG: {os.getenv('PII_PROXY_DEBUG')}")
        
        print(f"\n🔍 Результат в settings:")
        print(f"   pii_protection_enabled: {test_settings.pii_protection_enabled}")
        print(f"   pii_proxy_debug: {test_settings.pii_proxy_debug}")
        
        # Проверяем что переопределение работает
        success = (
            test_settings.pii_protection_enabled == True and
            test_settings.pii_proxy_debug == True
        )
        
        if success:
            print(f"\n✅ Переопределение через ENV работает корректно")
        else:
            print(f"\n❌ Переопределение через ENV не работает")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования ENV переопределения: {e}")
        return False
    
    finally:
        # Восстанавливаем оригинальные значения
        if original_pii_enabled is not None:
            os.environ['PII_PROTECTION_ENABLED'] = original_pii_enabled
        else:
            os.environ.pop('PII_PROTECTION_ENABLED', None)
            
        if original_debug is not None:
            os.environ['PII_PROXY_DEBUG'] = original_debug
        else:
            os.environ.pop('PII_PROXY_DEBUG', None)

async def test_service_integration_with_settings():
    """Тест интеграции сервисов с централизованными настройками"""
    print("\n🧪 ТЕСТ 3: Интеграция сервисов с Settings")
    print("=" * 50)
    
    try:
        # Создаем компоненты которые используют settings
        azure_provider = AzureOpenAIProvider()
        pii_gateway = AsyncPIISecurityGateway()
        llm_service = LLMService(azure_provider, pii_gateway)
        
        print(f"✅ Все компоненты успешно инициализированы")
        
        # Проверяем что AzureProvider использует правильные настройки
        print(f"\n🔍 AzureProvider настройки:")
        print(f"   Endpoint: {azure_provider.endpoint}")
        print(f"   Deployment: {azure_provider.deployment_name}")
        print(f"   API Version: {azure_provider.api_version}")
        
        # Проверяем что LLMService использует правильные настройки
        print(f"\n🔍 LLMService настройки:")
        print(f"   Debug режим: {llm_service.debug_mode}")
        print(f"   PII включен: {llm_service.pii_enabled}")
        
        # Проверяем соответствие с глобальными settings
        settings_match = (
            azure_provider.endpoint == settings.azure_openai_endpoint and
            azure_provider.deployment_name == settings.azure_completions_model and
            llm_service.debug_mode == settings.pii_proxy_debug and
            llm_service.pii_enabled == settings.pii_protection_enabled
        )
        
        if settings_match:
            print(f"\n✅ Все компоненты используют централизованные настройки")
        else:
            print(f"\n❌ Обнаружено несоответствие в настройках")
            print(f"   Azure endpoint: {azure_provider.endpoint} vs {settings.azure_openai_endpoint}")
            print(f"   Azure deployment: {azure_provider.deployment_name} vs {settings.azure_completions_model}")
            print(f"   LLM debug: {llm_service.debug_mode} vs {settings.pii_proxy_debug}")
            print(f"   LLM PII: {llm_service.pii_enabled} vs {settings.pii_protection_enabled}")
        
        return settings_match
        
    except Exception as e:
        print(f"\n❌ Ошибка интеграции с settings: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_pii_settings_toggle():
    """Тест переключения PII настроек"""
    print("\n🧪 ТЕСТ 4: Переключение PII настроек")
    print("=" * 50)
    
    # Сохраняем оригинальное значение
    original_pii_enabled = os.getenv('PII_PROTECTION_ENABLED')
    
    try:
        # Тест 1: PII отключен
        os.environ['PII_PROTECTION_ENABLED'] = 'false'
        test_settings_off = Settings()
        
        azure_provider_off = AzureOpenAIProvider()
        pii_gateway_off = AsyncPIISecurityGateway()
        llm_service_off = LLMService(azure_provider_off, pii_gateway_off)
        
        print(f"🔴 PII ОТКЛЮЧЕН:")
        print(f"   Settings PII enabled: {test_settings_off.pii_protection_enabled}")
        print(f"   LLMService PII enabled: {llm_service_off.pii_enabled}")
        
        # Тест 2: PII включен
        os.environ['PII_PROTECTION_ENABLED'] = 'true'
        test_settings_on = Settings()
        
        azure_provider_on = AzureOpenAIProvider()
        pii_gateway_on = AsyncPIISecurityGateway()
        llm_service_on = LLMService(azure_provider_on, pii_gateway_on)
        
        print(f"\n🟢 PII ВКЛЮЧЕН:")
        print(f"   Settings PII enabled: {test_settings_on.pii_protection_enabled}")
        print(f"   LLMService PII enabled: {llm_service_on.pii_enabled}")
        
        # Проверяем что переключение работает
        success = (
            test_settings_off.pii_protection_enabled == False and
            llm_service_off.pii_enabled == False and
            test_settings_on.pii_protection_enabled == True and
            llm_service_on.pii_enabled == True
        )
        
        if success:
            print(f"\n✅ Переключение PII настроек работает корректно")
        else:
            print(f"\n❌ Переключение PII настроек не работает")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования переключения PII: {e}")
        return False
    
    finally:
        # Восстанавливаем оригинальное значение
        if original_pii_enabled is not None:
            os.environ['PII_PROTECTION_ENABLED'] = original_pii_enabled
        else:
            os.environ.pop('PII_PROTECTION_ENABLED', None)

async def test_settings_validation():
    """Тест валидации настроек"""
    print("\n🧪 ТЕСТ 5: Валидация настроек")
    print("=" * 50)
    
    # Сохраняем оригинальные значения
    original_api_key = os.getenv('AZURE_OPENAI_API_KEY')
    original_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    
    try:
        # Тест 1: Отсутствующий API ключ
        os.environ.pop('AZURE_OPENAI_API_KEY', None)
        
        try:
            invalid_settings = Settings()
            print(f"❌ Валидация не сработала - settings создан без API ключа")
            return False
        except Exception as e:
            print(f"✅ Валидация сработала для отсутствующего API ключа: {e}")
        
        # Восстанавливаем API ключ
        if original_api_key:
            os.environ['AZURE_OPENAI_API_KEY'] = original_api_key
        
        # Тест 2: Отсутствующий endpoint
        os.environ.pop('AZURE_OPENAI_ENDPOINT', None)
        
        try:
            invalid_settings = Settings()
            print(f"❌ Валидация не сработала - settings создан без endpoint")
            return False
        except Exception as e:
            print(f"✅ Валидация сработала для отсутствующего endpoint: {e}")
        
        # Восстанавливаем endpoint
        if original_endpoint:
            os.environ['AZURE_OPENAI_ENDPOINT'] = original_endpoint
        
        # Тест 3: Валидные настройки
        try:
            valid_settings = Settings()
            print(f"✅ Валидные настройки успешно созданы")
            return True
        except Exception as e:
            print(f"❌ Ошибка создания валидных настроек: {e}")
            return False
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования валидации: {e}")
        return False
    
    finally:
        # Восстанавливаем оригинальные значения
        if original_api_key:
            os.environ['AZURE_OPENAI_API_KEY'] = original_api_key
        if original_endpoint:
            os.environ['AZURE_OPENAI_ENDPOINT'] = original_endpoint

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ ЦЕНТРАЛИЗОВАННОЙ КОНФИГУРАЦИИ")
    print("=" * 60)
    
    # Запускаем тесты
    tests = [
        test_settings_initialization,
        test_settings_env_override,
        test_service_integration_with_settings,
        test_pii_settings_toggle,
        test_settings_validation
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
        print("✅ Централизованная конфигурация работает корректно")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        print("❌ Требуется доработка централизованной конфигурации")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 