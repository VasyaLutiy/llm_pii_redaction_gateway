import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from unittest.mock import AsyncMock, MagicMock
from llm_pii_proxy.services.llm_service import LLMService
from llm_pii_proxy.core.models import ChatRequest, ChatMessage, ChatResponse
from llm_pii_proxy.security.pii_gateway import AsyncPIISecurityGateway

@pytest.mark.asyncio
async def test_llm_service_process_chat_request_with_real_pii():
    pii_gateway = AsyncPIISecurityGateway()
    session_id = "test-session"
    test_content = "My AWS key is AKIA1234567890EXAMPLE and password is secret123."
    # Получаем реальные маски
    pii_result = await pii_gateway.mask_sensitive_data(test_content, session_id)
    masked_content = pii_result.content

    # Используем эти маски в мок-ответе LLM
    mock_llm_provider = MagicMock()
    mock_llm_provider.create_chat_completion = AsyncMock(return_value=ChatResponse(
        id="test-id",
        model="test-model",
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": masked_content.replace("My", "Your")},
            "finish_reason": "stop"
        }],
        usage=None
    ))

    service = LLMService(mock_llm_provider, pii_gateway)
    request = ChatRequest(
        model="test-model",
        messages=[ChatMessage(role="user", content=test_content)],
        session_id=session_id
    )
    response = await service.process_chat_request(request)
    # Проверяем, что в запросе к LLM нет оригинальных PII
    args, kwargs = mock_llm_provider.create_chat_completion.call_args
    masked_request = args[0]
    print("RAW masked request sent to Azure:", masked_request.messages[0].content)
    assert "AKIA" not in masked_request.messages[0].content
    assert "secret123" not in masked_request.messages[0].content
    # Проверяем, что в ответе восстановлены оригинальные значения
    assert "AKIA1234567890EXAMPLE" in response.choices[0]["message"]["content"]
    assert "secret123" in response.choices[0]["message"]["content"]

@pytest.mark.asyncio
async def test_llm_service_full_demask_cycle():
    """Тест полного цикла: маскирование → LLM с масками в ответе → демаскирование"""
    print("\n" + "="*80)
    print("🎯 ДЕМОНСТРАЦИЯ ПОЛНОГО ЦИКЛА PII PROXY")
    print("="*80)
    
    pii_gateway = AsyncPIISecurityGateway()
    session_id = "demo-session"
    test_content = "My AWS key is AKIA1234567890EXAMPLE and password is secret123."
    
    print(f"\n📖 ШАГ 1: ИСХОДНЫЙ ТЕКСТ ПОЛЬЗОВАТЕЛЯ")
    print(f"   {test_content}")
    
    # Шаг 1: Получаем реальные маски
    pii_result = await pii_gateway.mask_sensitive_data(test_content, session_id)
    masked_content = pii_result.content
    
    print(f"\n🔒 ШАГ 2: МАСКИРОВАНИЕ PII ДАННЫХ")
    print(f"   Найдено PII элементов: {pii_result.pii_count}")
    for i, mapping in enumerate(pii_result.mappings):
        print(f"   {i+1}. '{mapping.original}' → '{mapping.masked}' (тип: {mapping.type})")
    print(f"   ЗАМАСКИРОВАННЫЙ ТЕКСТ: {masked_content}")
    
    # Извлекаем маски из замаскированного контента
    aws_mask = None
    password_mask = None
    for mapping in pii_result.mappings:
        if mapping.type == 'aws_key':
            aws_mask = mapping.masked
        elif mapping.type == 'password':
            password_mask = mapping.masked
    
    # Шаг 2: Мокируем LLM, который использует маски в своем ответе
    llm_response_with_masks = f"I found your AWS key {aws_mask} and password {password_mask}. Here's what to do: First, immediately revoke {aws_mask} from your AWS console. Then change {password_mask} to something more secure!"
    
    print(f"\n🌐 ШАГ 3: ОТПРАВКА В LLM")
    print(f"   Отправляем замаскированный текст в LLM...")
    
    print(f"\n📨 ШАГ 4: ОТВЕТ LLM (С МАСКАМИ)")
    print(f"   {llm_response_with_masks}")
    
    mock_llm_provider = MagicMock()
    mock_llm_provider.create_chat_completion = AsyncMock(return_value=ChatResponse(
        id="demo-id",
        model="gpt-4",
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": llm_response_with_masks},
            "finish_reason": "stop"
        }],
        usage={"prompt_tokens": 20, "completion_tokens": 50, "total_tokens": 70}
    ))

    # Шаг 3: Обрабатываем запрос через LLM Service
    service = LLMService(mock_llm_provider, pii_gateway)
    request = ChatRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content=test_content)],
        session_id=session_id
    )
    
    response = await service.process_chat_request(request)
    
    # Шаг 4: Проверяем результат
    final_response = response.choices[0]["message"]["content"]
    
    print(f"\n🔓 ШАГ 5: ДЕМАСКИРОВАНИЕ")
    print(f"   Восстанавливаем оригинальные PII данные...")
    for i, mapping in enumerate(pii_result.mappings):
        print(f"   {i+1}. '{mapping.masked}' → '{mapping.original}' (тип: {mapping.type})")
    
    print(f"\n🎉 ШАГ 6: ФИНАЛЬНЫЙ ОТВЕТ ПОЛЬЗОВАТЕЛЮ")
    print(f"   {final_response}")
    
    print(f"\n✅ ПРОВЕРКИ:")
    
    # Проверяем, что LLM получил замаскированные данные
    args, kwargs = mock_llm_provider.create_chat_completion.call_args
    masked_request = args[0]
    
    llm_received_original = "AKIA1234567890EXAMPLE" in masked_request.messages[0].content or "secret123" in masked_request.messages[0].content
    print(f"   LLM получил оригинальные PII данные: {'❌ НЕТ' if not llm_received_original else '🔴 ДА - ОШИБКА!'}")
    
    # Проверяем, что в финальном ответе данные демаскированы
    demask_worked = "AKIA1234567890EXAMPL" in final_response and "password is secret123." in final_response
    print(f"   Демаскирование сработало: {'✅ ДА' if demask_worked else '❌ НЕТ'}")
    
    masks_removed = aws_mask not in final_response and password_mask not in final_response
    print(f"   Маски удалены из финального ответа: {'✅ ДА' if masks_removed else '❌ НЕТ'}")
    
    print("\n" + "="*80)
    print("🚀 PII PROXY РАБОТАЕТ ИДЕАЛЬНО!")
    print("="*80)
    
    # Проверки для теста
    assert not llm_received_original
    assert demask_worked
    assert masks_removed 