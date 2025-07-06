# 🧪 Тесты LLM PII Proxy

Эта папка содержит все тесты для LLM PII Proxy, организованные по типам.

## 📁 Структура тестов

```
tests/
├── unit/           # Unit тесты (тестирование отдельных компонентов)
├── integration/    # Integration тесты (тестирование взаимодействия компонентов)
├── e2e/           # End-to-end тесты (тестирование полного цикла)
└── run_all_tests.py  # Скрипт для запуска всех тестов
```

### 🔧 Unit тесты (`unit/`)
- `test_centralized_config.py` - Тестирование централизованной конфигурации
- `test_pii_patterns_fixed.py` - Тестирование PII паттернов
- `test_pii_enabled.py` - Тестирование включения PII защиты
- `test_pii_with_llm_service.py` - Тестирование LLM сервиса с PII

### 🔗 Integration тесты (`integration/`)
- `test_pii_integration.py` - Интеграционное тестирование PII
- `test_cursor_tools.py` - Тестирование инструментов Cursor
- `test_cursor_simulation.py` - Симуляция поведения Cursor
- `test_cursor_exact.py` - Точное воспроизведение запросов Cursor
- `test_full_tool_cycle.py` - Полный цикл tool calling

### 🌐 E2E тесты (`e2e/`)
- `test_real_llm_with_pii.py` - Тестирование с реальной LLM и PII
- `test_http_api_with_pii.py` - Тестирование HTTP API с PII

## 🚀 Запуск тестов

### Запуск всех тестов
```bash
cd llm_pii_proxy/tests
python run_all_tests.py
```

### Запуск отдельных тестов
```bash
cd llm_pii_proxy/tests

# Unit тесты
python unit/test_pii_patterns_fixed.py
python unit/test_centralized_config.py

# Integration тесты
python integration/test_cursor_tools.py
python integration/test_pii_integration.py

# E2E тесты (требуют запущенный сервер)
python e2e/test_http_api_with_pii.py
```

### Запуск тестов по типам
```bash
cd llm_pii_proxy/tests

# Только unit тесты
python unit/test_*.py

# Только integration тесты
python integration/test_*.py

# Только e2e тесты
python e2e/test_*.py
```

## ⚙️ Требования для запуска

### Для Unit и Integration тестов:
- Python 3.8+
- Установленные зависимости из `requirements_llm_proxy.txt`
- Настроенные переменные окружения Azure OpenAI

### Для E2E тестов:
- Запущенный LLM PII Proxy сервер на `http://192.168.0.182:8000`
- Доступ к Azure OpenAI API

## 🔧 Конфигурация тестов

Тесты используют следующие переменные окружения:
- `AZURE_OPENAI_ENDPOINT` - Endpoint Azure OpenAI
- `AZURE_OPENAI_API_KEY` - API ключ Azure OpenAI
- `AZURE_COMPLETIONS_MODEL` - Модель для completions
- `PII_PROTECTION_ENABLED` - Включение PII защиты (устанавливается тестами)

## 📊 Интерпретация результатов

### ✅ Успешные тесты
- Все assertions прошли
- Код возврата 0
- Выводится "✅ ТЕСТ ПРОЙДЕН"

### ❌ Провалившиеся тесты
- Есть failed assertions
- Код возврата != 0
- Выводится "❌ ТЕСТ ПРОВАЛЕН"

### ⚠️ Предупреждения
- Тест прошел, но есть предупреждения
- Обычно связано с неполным тестированием функций

## 🐛 Отладка тестов

### Включение подробного логирования
```bash
export PII_PROXY_DEBUG=true
python unit/test_pii_patterns_fixed.py
```

### Проверка конфигурации
```bash
python unit/test_centralized_config.py
```

### Проверка подключения к Azure
```bash
python integration/test_cursor_tools.py
```

## 📝 Добавление новых тестов

1. Создайте новый файл в соответствующей папке (`unit/`, `integration/`, `e2e/`)
2. Начните имя файла с `test_`
3. Добавьте путь к корню проекта в импорты:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
   ```
4. Импортируйте нужные компоненты
5. Создайте async функции тестов
6. Добавьте `if __name__ == "__main__":` блок для запуска

## 🔍 Мониторинг качества

Тесты покрывают:
- ✅ Конфигурацию системы
- ✅ PII паттерны и маскирование
- ✅ Tool calling функциональность
- ✅ HTTP API endpoints
- ✅ Интеграцию с Azure OpenAI
- ✅ End-to-end сценарии

Цель: поддерживать покрытие тестами >80% для критической функциональности. 