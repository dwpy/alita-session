# -*- coding: utf-8 -*-
import aioredis
from alita_session.base import *
from alita_session.redis import RedisPoolMixin


class AioSessionManager(SessionInterface, RedisPoolMixin):
    async def get_redis_pool(self):
        self.client_config.setdefault("poolsize", self._pool_size)
        host = self.client_config.pop("host")
        port = self.client_config.pop("port")
        if not self._pool:
            self._pool = await aioredis.create_redis_pool(
                (host, port), loop=loop, **self.client_config)
        return self._pool
