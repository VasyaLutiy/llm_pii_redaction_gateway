#!/usr/bin/env python3
"""
🧪 ЗАПУСК ВСЕХ ТЕСТОВ LLM PII PROXY
Скрипт для запуска всех тестов из правильной директории
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def run_test_file(test_file_path: str) -> bool:
    """Запускает один тестовый файл"""
    print(f"\n{'='*60}")
    print(f"🧪 ЗАПУСК: {test_file_path}")
    print(f"{'='*60}")
    
    try:
        # Запускаем тест
        result = subprocess.run(
            [sys.executable, test_file_path],
            cwd=os.path.dirname(os.path.abspath(__file__)) + "/../../..",  # Корень проекта
            capture_output=True,
            text=True,
            timeout=120  # 2 минуты таймаут
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ ТЕСТ ПРОЙДЕН: {test_file_path}")
            return True
        else:
            print(f"❌ ТЕСТ ПРОВАЛЕН: {test_file_path} (код: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ ТЕСТ ПРЕВЫСИЛ ТАЙМАУТ: {test_file_path}")
        return False
    except Exception as e:
        print(f"💥 ОШИБКА ПРИ ЗАПУСКЕ: {test_file_path} - {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ LLM PII PROXY")
    print("=" * 80)
    
    # Получаем путь к директории tests
    tests_dir = Path(__file__).parent
    
    # Собираем все тестовые файлы
    test_files = []
    
    # Unit tests
    unit_dir = tests_dir / "unit"
    if unit_dir.exists():
        for test_file in unit_dir.glob("test_*.py"):
            test_files.append(("Unit", str(test_file)))
    
    # Integration tests
    integration_dir = tests_dir / "integration"
    if integration_dir.exists():
        for test_file in integration_dir.glob("test_*.py"):
            test_files.append(("Integration", str(test_file)))
    
    # E2E tests
    e2e_dir = tests_dir / "e2e"
    if e2e_dir.exists():
        for test_file in e2e_dir.glob("test_*.py"):
            test_files.append(("E2E", str(test_file)))
    
    print(f"📋 Найдено тестов: {len(test_files)}")
    for test_type, test_file in test_files:
        print(f"   [{test_type}] {os.path.basename(test_file)}")
    
    # Запускаем тесты
    passed = 0
    failed = 0
    
    for test_type, test_file in test_files:
        print(f"\n🔄 [{test_type}] {os.path.basename(test_file)}")
        
        if run_test_file(test_file):
            passed += 1
        else:
            failed += 1
    
    # Итоговый отчет
    print(f"\n{'='*80}")
    print(f"📊 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*80}")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📊 Всего: {passed + failed}")
    
    if failed == 0:
        print(f"🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        sys.exit(0)
    else:
        print(f"💥 ЕСТЬ ПРОВАЛИВШИЕСЯ ТЕСТЫ!")
        sys.exit(1)

if __name__ == "__main__":
    main() 