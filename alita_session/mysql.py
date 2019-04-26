# -*- coding: utf-8 -*-
import asyncio
import aiomysql
import sqlalchemy as sa
from datetime import datetime
from dateutil.relativedelta import relativedelta
from alita_session.base import *
from sqlalchemy.dialects import mysql
from collections import OrderedDict


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

    def get_session_data(self, session):
        return OrderedDict([
            ('session_key', self.get_session_key(session)),
            ('session_data', self.encode(session)),
            ('expire_date', self.get_expiry_date(session)),
            ('created', datetime.now())
        ])

    async def execute(self, query, args=None):
        if not isinstance(query, str):
            query = str(query.compile(dialect=mysql.dialect()))
        pool = await self.get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)

    async def fetchall(self, query, args=None):
        if not isinstance(query, str):
            query = str(query.compile(dialect=mysql.dialect()))
        pool = await self.get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                result = await cur.fetchall()
                if cur.description is not None:
                    columns = [i[0] for i in cur.description]
                    return [dict(zip((c for c in columns), row)) for row in result]
                else:
                    return []

    async def fetchone(self, query, args=None):
        ret = await self.fetchall(query, args)
        return ret[0] if ret else None

    async def get_mysql_pool(self):
        self.client_config.setdefault("maxsize", self._pool_size)
        if not self._pool:
            loop = asyncio.get_event_loop()
            self._pool = await aiomysql.create_pool(
                loop=loop, **self.client_config)
        return self._pool

    async def delete(self, session_key):
        try:
            await self.execute(
                self.session_model
                    .delete()
                    .where(
                        self.session_model.columns.session_key == session_key),
                (session_key, ))
        except self.session_model.DoesNotExist:
            pass

    async def exists(self, session_key):
        return await self.fetchone(
            self.session_model
                .select()
                .where(
                    self.session_model.columns.session_key == session_key),
            (session_key, ))

    async def get(self, request, session_key):
        return await self.fetchone(
            self.session_model
                .select()
                .where(
                    self.session_model.columns.session_key == session_key).where(
                    self.session_model.columns.expire_date > datetime.now()),
            (session_key, datetime.now()))

    async def save(self, request):
        data = self.get_session_data(request.session)
        session = await self.exists(data['session_key'])
        if not session:
            await self.execute(
                self.session_model
                .insert()
                .values(**data),
                tuple(data.values()))
        else:
            if self.must_save:
                await self.execute(
                    self.session_model
                        .update()
                        .values(
                            session_data=data['session_data']
                        ).where(
                            self.session_model.columns.session_key == data['session_key']),
                    (
                        data['session_data'],
                        data['expire_date'],
                        data['session_key'], ))
            else:
                raise UpdateError

    async def clear_expired(self, months=1):
        _date = datetime.now() + relativedelta(months=-months)
        await self.execute(
            self.session_model
                .delete()
                .where(
                    self.session_model.columns.expire_date < _date),
            (_date, ))
