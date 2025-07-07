# config/settings.py
 
import os
from typing import Optional
from llm_pii_proxy.core.exceptions import ConfigurationError

class Settings:
    """Application settings without Pydantic dependency"""
    
    def __init__(self):
        # Загружаем azure.env файл если есть
        self._load_env_file()
        
        # Azure OpenAI settings
        self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        self.azure_completions_model = os.getenv("AZURE_COMPLETIONS_MODEL", "gpt-4.1")
        
        # PII Proxy settings
        self.pii_proxy_debug = os.getenv("PII_PROXY_DEBUG", "false").lower() == "true"
        self.pii_session_timeout_minutes = int(os.getenv("PII_SESSION_TIMEOUT_MINUTES", "60"))
        
        # PII Protection settings
        self.pii_protection_enabled = os.getenv("PII_PROTECTION_ENABLED", "false").lower() == "true"
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        default_pii_patterns_path = os.path.join(base_dir, 'llm_pii_proxy', 'config', 'pii_patterns.yaml')
        self.pii_patterns_config_path = os.getenv("PII_PATTERNS_CONFIG_PATH", default_pii_patterns_path)
        
        # API settings
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        
        # Security settings
        self.enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
        self.api_key = os.getenv("API_KEY")
        
        # OpenRouter settings
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL")
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        # Выбор провайдера (для валидации)
        self.use_openrouter = os.getenv("USE_OPENROUTER", "false").lower() == "true"
        self.use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
        
        # Валидация критических настроек
        self.validate_settings()
    
    def _load_env_file(self):
        """Загружаем переменные из azure.env файла (относительно корня проекта)"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        env_file = os.path.join(base_dir, 'azure.env')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")  # Убираем кавычки
                        os.environ[key] = value

    def validate_settings(self) -> None:
        """Validate critical settings"""
        required_vars = []
        
        if not self.use_openrouter and not self.use_ollama:
            # Требуем Azure переменные только если используем Azure напрямую
            required_vars.extend([
                ("AZURE_OPENAI_API_KEY", self.azure_openai_api_key),
                ("AZURE_OPENAI_ENDPOINT", self.azure_openai_endpoint),
                ("AZURE_COMPLETIONS_MODEL", self.azure_completions_model)
            ])
        else:
            # Для OpenRouter требуем только ключ
            if self.use_openrouter:
                required_vars.append(("OPENROUTER_API_KEY", self.openrouter_api_key))
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        if missing_vars:
            raise ConfigurationError(f"Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
        
        if self.enable_auth and not self.api_key:
            raise ConfigurationError("API_KEY is required when ENABLE_AUTH is True")
        
        if self.pii_session_timeout_minutes < 1:
            raise ConfigurationError("PII_SESSION_TIMEOUT_MINUTES must be at least 1")
        
        # Проверяем PII конфигурацию
        if self.pii_protection_enabled and not os.path.exists(self.pii_patterns_config_path):
            raise ConfigurationError(f"PII patterns config file not found: {self.pii_patterns_config_path}")

    def get_display_config(self) -> dict:
        """Получить конфигурацию для отображения (с скрытием чувствительных данных)"""
        return {
            "azure_openai_endpoint": self.azure_openai_endpoint,
            "azure_openai_api_key": f"{self.azure_openai_api_key[:10]}..." if self.azure_openai_api_key else None,
            "azure_openai_api_version": self.azure_openai_api_version,
            "azure_completions_model": self.azure_completions_model,
            "pii_proxy_debug": self.pii_proxy_debug,
            "pii_protection_enabled": self.pii_protection_enabled,
            "pii_patterns_config_path": self.pii_patterns_config_path,
            "pii_session_timeout_minutes": self.pii_session_timeout_minutes,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "enable_auth": self.enable_auth,
            "api_key": f"{self.api_key[:10]}..." if self.api_key else None,
        }

# Global settings instance
settings = Settings() 