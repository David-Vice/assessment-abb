from abb_rag import get_settings
from arq.connections import ArqRedis, RedisSettings, create_pool


def get_redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def create_redis_pool() -> ArqRedis:
    return await create_pool(get_redis_settings())
