# cache/context_deduplication.py

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from ..core.models import ChatMessage, ChatRequest
from ..observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached content entry"""
    hash: str
    content: str
    first_seen: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    usage_count: int = 0
    size: int = 0
    
    def __post_init__(self):
        self.size = len(self.content)


class ContextCache:
    """
    Content deduplication cache for reducing token usage in LLM requests.
    
    This cache identifies repeated content (like file contents, system prompts, etc.)
    and replaces them with references, significantly reducing context window usage.
    """
    
    def __init__(self, max_cache_size_mb: int = 100, min_content_size: int = 500):
        """
        Initialize the context cache.
        
        Args:
            max_cache_size_mb: Maximum cache size in MB
            min_content_size: Minimum content size to cache (avoid caching small snippets)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_cache_size = max_cache_size_mb * 1024 * 1024  # Convert to bytes
        self._min_content_size = min_content_size
        self._current_cache_size = 0
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_saved_tokens": 0,
            "deduplication_ratio": 0.0
        }
        
        logger.info(f"🧠 ContextCache initialized: max_size={max_cache_size_mb}MB, min_content={min_content_size}")
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash for content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]  # Short hash
    
    def _should_cache_content(self, content: str, message_role: str = None, message_has_tool_calls: bool = False, message_has_tool_call_id: bool = False) -> bool:
        """Determine if content should be cached"""
        if not content or len(content) < self._min_content_size:
            return False
        
        # 🚫 CRITICAL: Never cache tool-related messages to preserve tool_calls -> tool sequence
        if message_role == "tool":
            logger.debug(f"🚫 Skipping cache for 'tool' message to preserve tool_call sequence")
            return False
        
        if message_role == "assistant" and message_has_tool_calls:
            logger.debug(f"🚫 Skipping cache for 'assistant' message with tool_calls to preserve tool_call sequence")
            return False
        
        # Don't cache very short messages or single-line content
        if len(content.split('\n')) < 5:
            return False
            
        # Cache file contents, system prompts, large user messages
        indicators = [
            "```",  # Code blocks
            "<project_layout>",  # Project structure
            "import ",  # Code imports
            "class ",  # Class definitions
            "function ",  # Function definitions
            "You are an AI",  # System prompts
            "def ",  # Python functions
        ]
        
        return any(indicator in content for indicator in indicators)
    
    def _evict_oldest_entries(self, required_space: int):
        """Evict oldest cache entries to make space"""
        if not self._cache:
            return
        
        # Sort by last_used timestamp
        sorted_entries = sorted(
            self._cache.items(), 
            key=lambda x: x[1].last_used
        )
        
        freed_space = 0
        entries_to_remove = []
        
        for hash_key, entry in sorted_entries:
            if freed_space >= required_space:
                break
            entries_to_remove.append(hash_key)
            freed_space += entry.size
        
        # Remove entries
        for hash_key in entries_to_remove:
            entry = self._cache.pop(hash_key)
            self._current_cache_size -= entry.size
            
        logger.debug(f"🗑️ Evicted {len(entries_to_remove)} cache entries, freed {freed_space} bytes")
    
    def _add_to_cache(self, content: str) -> str:
        """Add content to cache and return its hash"""
        content_hash = self._generate_content_hash(content)
        
        if content_hash in self._cache:
            # Update existing entry
            self._cache[content_hash].last_used = time.time()
            self._cache[content_hash].usage_count += 1
            return content_hash
        
        # Check if we need to evict entries
        content_size = len(content)
        if self._current_cache_size + content_size > self._max_cache_size:
            self._evict_oldest_entries(content_size)
        
        # Add new entry
        entry = CacheEntry(
            hash=content_hash,
            content=content,
            size=content_size
        )
        
        self._cache[content_hash] = entry
        self._current_cache_size += content_size
        
        logger.debug(f"📝 Cached content: hash={content_hash}, size={content_size}")
        return content_hash
    
    def deduplicate_request(self, request: ChatRequest) -> Tuple[ChatRequest, Dict[str, str]]:
        """
        Deduplicate request content and return modified request with deduplication map.
        
        Returns:
            Tuple of (modified_request, deduplication_map)
        """
        if not request.messages:
            return request, {}
        
        deduplication_map = {}
        modified_messages = []
        original_total_size = 0
        deduplicated_total_size = 0
        
        for message in request.messages:
            content = message.content
            if not isinstance(content, str):
                modified_messages.append(message)
                continue
            
            original_total_size += len(content)
            
            # Check if content should be cached
            message_has_tool_calls = bool(getattr(message, 'tool_calls', None))
            message_has_tool_call_id = bool(getattr(message, 'tool_call_id', None))
            
            if self._should_cache_content(content, message.role, message_has_tool_calls, message_has_tool_call_id):
                content_hash = self._generate_content_hash(content)
                
                if content_hash in self._cache:
                    # Cache hit - replace with reference
                    cache_entry = self._cache[content_hash]
                    cache_entry.last_used = time.time()
                    cache_entry.usage_count += 1
                    
                    # Create deduplicated content reference
                    deduplicated_content = f"[CACHED_CONTENT:{content_hash}]"
                    deduplication_map[content_hash] = content
                    
                    # Create new message with reference
                    modified_message = type(message)(
                        role=message.role,
                        content=deduplicated_content,
                        name=message.name,
                        tool_calls=message.tool_calls,
                        tool_call_id=message.tool_call_id
                    )
                    modified_messages.append(modified_message)
                    deduplicated_total_size += len(deduplicated_content)
                    
                    self._stats["cache_hits"] += 1
                    logger.debug(f"🎯 Cache HIT: {content_hash}, saved {len(content) - len(deduplicated_content)} chars")
                    
                else:
                    # Cache miss - add to cache and keep original
                    self._add_to_cache(content)
                    modified_messages.append(message)
                    deduplicated_total_size += len(content)
                    self._stats["cache_misses"] += 1
                    
            else:
                # Don't cache - keep original
                modified_messages.append(message)
                deduplicated_total_size += len(content)
        
        # Update stats
        if original_total_size > 0:
            saved_tokens = original_total_size - deduplicated_total_size
            self._stats["total_saved_tokens"] += saved_tokens
            self._stats["deduplication_ratio"] = (
                self._stats["total_saved_tokens"] / 
                (self._stats["total_saved_tokens"] + deduplicated_total_size)
            ) * 100
        
        # Create modified request
        modified_request = ChatRequest(
            model=request.model,
            messages=modified_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_completion_tokens=request.max_completion_tokens,
            stream=request.stream,
            session_id=request.session_id,
            pii_protection=request.pii_protection,
            tools=request.tools,
            tool_choice=request.tool_choice,
            functions=request.functions
        )
        
        if deduplication_map:
            logger.info(f"🔄 Deduplication: {original_total_size} → {deduplicated_total_size} chars "
                       f"(saved {original_total_size - deduplicated_total_size}, "
                       f"{len(deduplication_map)} references)")
        
        return modified_request, deduplication_map
    
    def restore_content(self, response_content: str, deduplication_map: Dict[str, str]) -> str:
        """
        Restore cached content references in response content.
        
        This ensures the response contains full content instead of cache references.
        """
        if not deduplication_map:
            return response_content
        
        restored_content = response_content
        
        for content_hash, original_content in deduplication_map.items():
            cache_reference = f"[CACHED_CONTENT:{content_hash}]"
            if cache_reference in restored_content:
                restored_content = restored_content.replace(cache_reference, original_content)
                logger.debug(f"🔄 Restored content reference: {content_hash}")
        
        return restored_content
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            **self._stats,
            "cache_entries": len(self._cache),
            "cache_size_mb": round(self._current_cache_size / (1024 * 1024), 2),
            "cache_utilization": round(
                (self._current_cache_size / self._max_cache_size) * 100, 2
            ) if self._max_cache_size > 0 else 0
        }
    
    def clear_cache(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._current_cache_size = 0
        logger.info("🧹 Cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information for debugging"""
        entries_info = []
        for hash_key, entry in self._cache.items():
            entries_info.append({
                "hash": hash_key,
                "size": entry.size,
                "usage_count": entry.usage_count,
                "age_seconds": round(time.time() - entry.first_seen, 2),
                "content_preview": entry.content[:100] + "..." if len(entry.content) > 100 else entry.content
            })
        
        return {
            "total_entries": len(self._cache),
            "total_size_mb": round(self._current_cache_size / (1024 * 1024), 2),
            "entries": sorted(entries_info, key=lambda x: x["usage_count"], reverse=True)
        }


# Global cache instance
_global_cache: Optional[ContextCache] = None


def get_context_cache() -> ContextCache:
    """Get the global context cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ContextCache()
    return _global_cache


def clear_global_cache():
    """Clear the global cache"""
    global _global_cache
    if _global_cache:
        _global_cache.clear_cache() 