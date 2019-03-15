# -*- coding: utf-8 -*-
import copy
import asyncio
import aioredis
from alita_session.redis import RedisSessionManager


class SessionManager(RedisSessionManager):
    async def get_redis_pool(self):
        if not self._pool:
            self.client_config.setdefault("maxsize", self._pool_size)
            _config = copy.copy(self.client_config)
            address = _config.pop("host"), _config.pop("port", 6379)
            loop = asyncio.get_event_loop()
            self._pool = await aioredis.create_redis_pool(address, loop=loop, **_config)
        return self._pool
