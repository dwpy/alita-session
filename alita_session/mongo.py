# -*- coding: utf-8 -*-
import motor.motor_asyncio
from datetime import datetime
from alita_session.base import *
from dateutil.relativedelta import relativedelta


class SessionManager(SessionInterface):
    _client = None
    _db = None
    _collection = None

    async def get_session_collection(self):
        if not self._collection:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(**self.client_config)
            self._db = self._client[self.client_config['db']]
            self._collection = self._db[self.session_table_name]
        return self._collection

    async def delete(self, session_key):
        collection = await self.get_session_collection()
        await collection.remove({'session_key': session_key})

    async def exists(self, session_key):
        collection = await self.get_session_collection()
        return await collection.find_one({'session_key': session_key})

    async def get(self, request, session_key):
        collection = await self.get_session_collection()
        return await collection.find_one({
            'session_key': session_key,
            'expire_date': {'$gt': datetime.now()}
        })

    async def save(self, request):
        data = self.get_session_data(request.session)
        session = await self.exists(data['session_key'])
        collection = await self.get_session_collection()
        if not session:
            await collection.insert_one(**data)
        else:
            if self.must_save:
                await collection.update({
                    'session_key': data['session_key']
                }, {
                    '$set': {
                        'session_data': data['session_data'],
                        'expire_date': data['expire_date']
                    }
                })
            else:
                raise UpdateError

    async def clear_expired(self, months=1):
        collection = await self.get_session_collection()
        _date = datetime.now() + relativedelta(months=-months)
        await collection.remove({'expire_date': {'$lt': _date}})
