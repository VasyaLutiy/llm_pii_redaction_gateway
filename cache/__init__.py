# cache/__init__.py

"""
Context caching module for LLM PII Proxy.
Provides content deduplication to reduce token usage.
"""

from .context_deduplication import ContextCache

__all__ = ["ContextCache"] 