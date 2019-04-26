# -*- coding: utf-8 -*-
import asyncio
import asyncio_redis
from alita_session.base import *


class RedisSessionManager(SessionInterface):
    _pool = None
    _pool_size = 10

    async def get_redis_pool(self):
        raise NotImplementedError

    async def delete(self, session_key):
        pool = await self.get_redis_pool()
        await pool.delete(session_key)

    async def exists(self, session_key):
        pool = await self.get_redis_pool()
        return await pool.get(session_key)

    def get_session_data(self, session, expire=None):
        return dict(
            key=self.get_session_key(session),
            value=self.encode(session),
            expire=expire or self.get_expiry_age(session)
        )

    async def get(self, request, session_key):
        pool = await self.get_redis_pool()
        return await pool.get(session_key)

    async def save(self, request):
        pool = await self.get_redis_pool()
        session_key = self.get_session_key(request.session)
        if not await self.exists(session_key):
            session_data = self.get_session_data(request.session)
        else:
            expire = await pool.ttl(session_key)
            session_data = self.get_session_data(request.session, expire)
        await pool.setex(**session_data)


class SessionManager(RedisSessionManager):
    async def get_redis_pool(self):
        self.client_config.setdefault("poolsize", self._pool_size)
        if not self._pool:
            loop = asyncio.get_event_loop()
            self._pool = await asyncio_redis.Pool.create(
                loop=loop, **self.client_config)
        return self._pool
