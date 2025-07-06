#!/usr/bin/env python3
"""
🧪 ТЕСТ ИСПРАВЛЕННЫХ PII ПАТТЕРНОВ
Проверяем что исправленные паттерны корректно детектируют PII
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway

async def test_fixed_patterns():
    """Тест исправленных PII паттернов"""
    print("🧪 ТЕСТ ИСПРАВЛЕННЫХ PII ПАТТЕРНОВ")
    print("=" * 60)
    
    pii_gateway = AsyncPIISecurityGateway()
    
    # Тестовые данные
    test_cases = [
        {
            "name": "AWS ключ полный",
            "content": "Мой AWS ключ AKIA1234567890EXAMPLE",
            "expected_count": 1,
            "expected_type": "aws_key"
        },
        {
            "name": "Пароль с русским словом",
            "content": "паролем MySecretPassword123",
            "expected_count": 1,
            "expected_type": "password"
        },
        {
            "name": "Комбинированный тест",
            "content": "Создай файл config.json с моим AWS ключом AKIA1234567890EXAMPLE и паролем MySecretPassword123",
            "expected_count": 2,
            "expected_types": ["aws_key", "password"]
        },
        {
            "name": "Пароль английский",
            "content": "password is SecretPass123",
            "expected_count": 1,
            "expected_type": "password"
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Тест {i}: {test_case['name']}")
        print(f"   Контент: {test_case['content']}")
        
        try:
            # Маскируем PII
            session_id = f"test_session_{i}"
            result = await pii_gateway.mask_sensitive_data(
                content=test_case['content'],
                session_id=session_id
            )
            
            print(f"   Найдено PII: {result.pii_count}")
            print(f"   Ожидалось: {test_case['expected_count']}")
            print(f"   Замаскированный контент: {result.content}")
            
            # Проверяем количество найденных PII
            if result.pii_count == test_case['expected_count']:
                print(f"   ✅ Количество PII корректно")
                test_passed = True
            else:
                print(f"   ❌ Неверное количество PII")
                test_passed = False
                all_passed = False
            
            # Проверяем что контент изменился (если ожидаем PII)
            if test_case['expected_count'] > 0:
                if result.content != test_case['content']:
                    print(f"   ✅ Контент корректно замаскирован")
                else:
                    print(f"   ❌ Контент не изменился")
                    test_passed = False
                    all_passed = False
            
            # Очищаем сессию
            await pii_gateway.clear_session(session_id)
            
        except Exception as e:
            print(f"   ❌ Ошибка при тестировании: {e}")
            test_passed = False
            all_passed = False
    
    # Итоговый результат
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ PII ПАТТЕРНОВ ПРОЙДЕНЫ!")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ PII ПАТТЕРНОВ ПРОВАЛЕНЫ")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(test_fixed_patterns()) 