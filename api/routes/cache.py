# api/routes/cache.py

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...cache.context_deduplication import get_context_cache, clear_global_cache
from ...observability.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get context cache statistics"""
    try:
        cache = get_context_cache()
        stats = cache.get_stats()
        logger.debug(f"📊 Cache stats requested: {stats}")
        return {
            "status": "success",
            "cache_stats": stats
        }
    except Exception as e:
        logger.error(f"❌ Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.get("/info")
async def get_cache_info() -> Dict[str, Any]:
    """Get detailed cache information for debugging"""
    try:
        cache = get_context_cache()
        info = cache.get_cache_info()
        logger.debug(f"🔍 Cache info requested: {len(info.get('entries', []))} entries")
        return {
            "status": "success",
            "cache_info": info
        }
    except Exception as e:
        logger.error(f"❌ Error getting cache info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache info: {str(e)}")


@router.post("/clear")
async def clear_cache() -> Dict[str, str]:
    """Clear all cache entries"""
    try:
        clear_global_cache()
        logger.info("🧹 Cache cleared via API")
        return {
            "status": "success",
            "message": "Cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/health")
async def cache_health() -> Dict[str, Any]:
    """Check cache health and performance"""
    try:
        cache = get_context_cache()
        stats = cache.get_stats()
        
        # Calculate health metrics
        cache_utilization = stats.get("cache_utilization", 0)
        hit_rate = 0
        total_requests = stats.get("cache_hits", 0) + stats.get("cache_misses", 0)
        if total_requests > 0:
            hit_rate = (stats.get("cache_hits", 0) / total_requests) * 100
        
        health_status = "healthy"
        if cache_utilization > 90:
            health_status = "warning"
        elif cache_utilization > 95:
            health_status = "critical"
        
        return {
            "status": "success",
            "health": {
                "status": health_status,
                "cache_utilization_percent": cache_utilization,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "deduplication_ratio_percent": round(stats.get("deduplication_ratio", 0), 2)
            }
        }
    except Exception as e:
        logger.error(f"❌ Error checking cache health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check cache health: {str(e)}") 