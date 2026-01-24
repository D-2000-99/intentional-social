"""Storage service for centralized storage operations with caching."""
from typing import List, Optional


class StorageService:
    """Centralized storage operations with optional caching."""
    
    def __init__(self, redis_client=None):
        """
        Initialize storage service.
        
        Args:
            redis_client: Optional Redis client for caching presigned URLs
        """
        self.redis = redis_client
    
    def get_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        response_cache_control: Optional[str] = None,
    ) -> str:
        """
        Get presigned URL with optional Redis caching.
        Cache TTL = expiration - 60 seconds (safety margin).
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL string
        """
        cache_suffix = response_cache_control or "default"
        if self.redis:
            cache_key = f"presigned:{s3_key}:{cache_suffix}"
            cached_url = self.redis.get(cache_key)
            if cached_url:
                return cached_url.decode('utf-8')
        
        # Generate new URL
        from app.core.s3 import generate_presigned_url
        url = generate_presigned_url(s3_key, expiration, response_cache_control)
        
        # Cache it
        if self.redis:
            cache_ttl = expiration - 60  # Expire 1 min before URL expires
            self.redis.setex(cache_key, cache_ttl, url)
        
        return url
    
    def batch_get_presigned_urls(
        self,
        s3_keys: List[str],
        expiration: int = 3600,
        response_cache_control: Optional[str] = None,
    ) -> List[str]:
        """
        Get multiple presigned URLs efficiently.
        
        Args:
            s3_keys: List of S3 object keys
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            List of presigned URL strings
        """
        if not s3_keys:
            return []
        
        urls = []
        
        # Try to get from cache first
        cache_suffix = response_cache_control or "default"
        if self.redis:
            cache_keys = [f"presigned:{key}:{cache_suffix}" for key in s3_keys]
            cached_urls = self.redis.mget(cache_keys)
            
            uncached_indices = []
            for i, cached_url in enumerate(cached_urls):
                if cached_url:
                    urls.append(cached_url.decode('utf-8'))
                else:
                    urls.append(None)
                    uncached_indices.append(i)
            
            # Generate missing URLs
            if uncached_indices:
                from app.core.s3 import generate_presigned_url
                for i in uncached_indices:
                    url = generate_presigned_url(s3_keys[i], expiration, response_cache_control)
                    urls[i] = url
                    
                    # Cache it
                    cache_key = f"presigned:{s3_keys[i]}:{cache_suffix}"
                    cache_ttl = expiration - 60
                    self.redis.setex(cache_key, cache_ttl, url)
        else:
            # No cache, generate all
            from app.core.s3 import generate_presigned_urls
            urls = generate_presigned_urls(s3_keys, expiration, response_cache_control)
        
        return urls
