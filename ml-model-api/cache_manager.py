"""
Intelligent caching system for FlavorSnap API responses.

Features:
- Hash-based image deduplication
- Redis-backed caching with TTL
- Cache hit/miss analytics
- Automatic cache invalidation
"""

import hashlib
import json
import time
import redis
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Intelligent caching manager with hash-based deduplication"""

    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        """
        Initialize cache manager

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379')
        self.default_ttl = default_ttl
        self.redis_client = None
        self._connect_redis()

    def _connect_redis(self):
        """Establish Redis connection with error handling"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connection established")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback")
            self.redis_client = None

    def _get_fallback_cache(self) -> Dict[str, Any]:
        """In-memory fallback cache when Redis is unavailable"""
        if not hasattr(self, '_fallback_cache'):
            self._fallback_cache = {}
        return self._fallback_cache

    def compute_image_hash(self, image_data: bytes) -> str:
        """
        Compute SHA-256 hash of image data for deduplication

        Args:
            image_data: Raw image bytes

        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(image_data).hexdigest()

    def get_cache_key(self, image_hash: str, model_version: str = "v1") -> str:
        """
        Generate cache key for image hash and model version

        Args:
            image_hash: SHA-256 hash of image
            model_version: Model version identifier

        Returns:
            Cache key string
        """
        return f"prediction:{model_version}:{image_hash}"

    def get_cached_prediction(self, image_hash: str, model_version: str = "v1") -> Optional[Dict[str, Any]]:
        """
        Retrieve cached prediction result

        Args:
            image_hash: SHA-256 hash of image
            model_version: Model version identifier

        Returns:
            Cached prediction data or None if not found
        """
        cache_key = self.get_cache_key(image_hash, model_version)

        try:
            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    # Check if cache entry is still valid
                    if self._is_cache_valid(data):
                        logger.info(f"Cache hit for image hash: {image_hash[:8]}...")
                        self._increment_cache_hit()
                        return data
                    else:
                        # Remove expired entry
                        self.redis_client.delete(cache_key)
            else:
                # Fallback to in-memory cache
                fallback_cache = self._get_fallback_cache()
                if cache_key in fallback_cache:
                    data = fallback_cache[cache_key]
                    if self._is_cache_valid(data):
                        logger.info(f"Fallback cache hit for image hash: {image_hash[:8]}...")
                        return data
                    else:
                        del fallback_cache[cache_key]
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")

        self._increment_cache_miss()
        return None

    def cache_prediction(self, image_hash: str, prediction_data: Dict[str, Any],
                        model_version: str = "v1", custom_ttl: int = None) -> bool:
        """
        Cache prediction result

        Args:
            image_hash: SHA-256 hash of image
            prediction_data: Prediction result data
            model_version: Model version identifier
            custom_ttl: Custom TTL in seconds (optional)

        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = self.get_cache_key(image_hash, model_version)
        ttl = custom_ttl or self.default_ttl

        # Add cache metadata
        cache_entry = {
            **prediction_data,
            'cached_at': datetime.now().isoformat(),
            'ttl': ttl,
            'model_version': model_version,
            'image_hash': image_hash
        }

        try:
            if self.redis_client:
                success = self.redis_client.setex(cache_key, ttl, json.dumps(cache_entry))
                if success:
                    logger.info(f"Cached prediction for image hash: {image_hash[:8]}...")
                    return True
            else:
                # Fallback to in-memory cache
                fallback_cache = self._get_fallback_cache()
                fallback_cache[cache_key] = cache_entry
                logger.info(f"Fallback cached prediction for image hash: {image_hash[:8]}...")
                return True
        except Exception as e:
            logger.error(f"Cache storage error: {e}")

        return False

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """
        Check if cache entry is still valid

        Args:
            cache_entry: Cache entry data

        Returns:
            True if valid, False if expired
        """
        if 'cached_at' not in cache_entry or 'ttl' not in cache_entry:
            return False

        try:
            cached_at = datetime.fromisoformat(cache_entry['cached_at'])
            ttl = cache_entry['ttl']
            expires_at = cached_at + timedelta(seconds=ttl)
            return datetime.now() < expires_at
        except (ValueError, KeyError):
            return False

    def invalidate_cache(self, image_hash: str = None, model_version: str = "v1") -> int:
        """
        Invalidate cache entries

        Args:
            image_hash: Specific image hash to invalidate (optional)
            model_version: Model version (used with image_hash)

        Returns:
            Number of entries invalidated
        """
        try:
            if self.redis_client:
                if image_hash:
                    cache_key = self.get_cache_key(image_hash, model_version)
                    result = self.redis_client.delete(cache_key)
                    logger.info(f"Invalidated cache for image hash: {image_hash[:8]}...")
                    return result
                else:
                    # Invalidate all prediction cache entries
                    pattern = f"prediction:{model_version}:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        result = self.redis_client.delete(*keys)
                        logger.info(f"Invalidated {result} cache entries for model {model_version}")
                        return result
            else:
                # Fallback cache invalidation
                fallback_cache = self._get_fallback_cache()
                if image_hash:
                    cache_key = self.get_cache_key(image_hash, model_version)
                    if cache_key in fallback_cache:
                        del fallback_cache[cache_key]
                        return 1
                else:
                    # Clear all entries
                    keys_to_delete = [k for k in fallback_cache.keys()
                                    if k.startswith(f"prediction:{model_version}:")]
                    for key in keys_to_delete:
                        del fallback_cache[key]
                    return len(keys_to_delete)
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

        return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics

        Returns:
            Dictionary with cache stats
        """
        try:
            if self.redis_client:
                # Get Redis info
                info = self.redis_client.info()
                return {
                    'cache_type': 'redis',
                    'connected': True,
                    'used_memory': info.get('used_memory_human', 'unknown'),
                    'total_connections_received': info.get('total_connections_received', 0),
                    'cache_hit_rate': self._calculate_hit_rate()
                }
            else:
                fallback_cache = self._get_fallback_cache()
                return {
                    'cache_type': 'in_memory_fallback',
                    'connected': False,
                    'cached_entries': len(fallback_cache),
                    'cache_hit_rate': self._calculate_hit_rate()
                }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {
                'cache_type': 'error',
                'connected': False,
                'error': str(e)
            }

    def _increment_cache_hit(self):
        """Increment cache hit counter"""
        try:
            if self.redis_client:
                self.redis_client.incr('cache:hits')
            else:
                if not hasattr(self, '_fallback_stats'):
                    self._fallback_stats = {'hits': 0, 'misses': 0}
                self._fallback_stats['hits'] += 1
        except Exception:
            pass

    def _increment_cache_miss(self):
        """Increment cache miss counter"""
        try:
            if self.redis_client:
                self.redis_client.incr('cache:misses')
            else:
                if not hasattr(self, '_fallback_stats'):
                    self._fallback_stats = {'hits': 0, 'misses': 0}
                self._fallback_stats['misses'] += 1
        except Exception:
            pass

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        try:
            if self.redis_client:
                hits = int(self.redis_client.get('cache:hits') or 0)
                misses = int(self.redis_client.get('cache:misses') or 0)
            else:
                if hasattr(self, '_fallback_stats'):
                    hits = self._fallback_stats['hits']
                    misses = self._fallback_stats['misses']
                else:
                    return 0.0

            total = hits + misses
            return (hits / total * 100) if total > 0 else 0.0
        except Exception:
            return 0.0

    def cleanup_expired_entries(self) -> int:
        """
        Clean up expired cache entries (for fallback cache)

        Returns:
            Number of entries cleaned up
        """
        if self.redis_client:
            # Redis handles TTL automatically
            return 0

        fallback_cache = self._get_fallback_cache()
        keys_to_delete = []
        current_time = datetime.now()

        for key, entry in fallback_cache.items():
            if not self._is_cache_valid(entry):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del fallback_cache[key]

        if keys_to_delete:
            logger.info(f"Cleaned up {len(keys_to_delete)} expired fallback cache entries")

        return len(keys_to_delete)


# Global cache manager instance
cache_manager = CacheManager()