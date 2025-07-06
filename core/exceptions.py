# core/exceptions.py
 
class PIIProxyError(Exception):
    """Base exception for PII Proxy errors"""
    pass

class PIISessionNotFoundError(PIIProxyError):
    """Raised when PII session is not found"""
    pass

class PIIProcessingError(PIIProxyError):
    """Raised when PII processing fails"""
    pass

class LLMProviderError(PIIProxyError):
    """Raised when LLM provider fails"""
    pass

class ConfigurationError(PIIProxyError):
    """Raised when configuration is invalid"""
    pass

class ValidationError(PIIProxyError):
    """Raised when input validation fails"""
    pass 