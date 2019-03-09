# -*- coding: utf-8 -*-
import aiomysql
import sqlalchemy as sa
from datetime import datetime
from dateutil.relativedelta import relativedelta
from alita_session.base import *
from sqlalchemy.exc import ProgrammingError


class SessionManager(SessionInterface):
    _pool = None
    _pool_size = 10

    def init(self):
        self.session_model = sa.Table(
            self.session_table_name, sa.MetaData(),
            sa.Column('session_key', sa.String(40), primary_key=True),
            sa.Column('session_data', sa.Text()),
            sa.Column('expire_date', sa.DateTime(), index=True),
            sa.Column('created', sa.DateTime(), default=datetime.now),
        )

    async def get_mysql_pool(self):
        self.client_config.setdefault("poolsize", self._pool_size)
        if not self._pool:
            self._pool = await aiomysql.create_pool(loop=loop, **self.client_config)
        return self._pool

    async def delete(self, session_key):
        try:
            pool = await self.get_mysql_pool()
            async with pool.acquire() as conn:
                return await conn.execute(self.session_model.delete().where(
                    self.session_model.session_key == session_key))
        except self.session_model.DoesNotExist:
            pass

    async def exists(self, session_key):
        pool = await self.get_mysql_pool()
        async with pool.acquire() as conn:
            return await conn.execute(self.session_model.select().where(
                self.session_model.session_key == session_key)).one()

    async def get(self, request, session_key):
        try:
            pool = await self.get_mysql_pool()
            async with pool.acquire() as conn:
                return await conn.execute(self.session_model.select().where(
                    self.session_model.session_key == session_key).where(
                    self.session_model.expire_date > datetime.now())).one()
        except ProgrammingError:
            self.session_model.create(self._pool)
            val = await self.get(request, session_key)
            return val

    async def save(self, request):
        pool = await self.get_mysql_pool()
        data = self.get_session_data(request.session)
        session = await self.exists(data['session_key'])
        async with pool.acquire() as conn:
            if not session:
                await conn.execute(self.session_model.insert().values(**data))
            else:
                if self.must_save:
                    await conn.execute(self.session_model.update().values(
                        session_data=data['session_data'],
                        expire_date=data['expire_date']
                    )).where(self.session_model.session_key == data['session_key'])
                else:
                    raise UpdateError

    async def clear_expired(self, months=1):
        pool = await self.get_mysql_pool()
        _date = datetime.now() + relativedelta(months=-months)
        async with pool.acquire() as conn:
            await conn.execute(self.session_model.delete().where(
                self.session_model.expire_date < _date))
