"""
Cache layer for hot data.
"""
from learning.code_manual.Refundbot.app.cache.redis_client import (
    get_redis_client,
    close_redis_client,
    cache_get,
    cache_set,
    cache_delete
)

__all__ = [
    'get_redis_client',
    'close_redis_client',
    'cache_get',
    'cache_set',
    'cache_delete'
]
