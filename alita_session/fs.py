# -*- coding: utf-8 -*-
import os
import re
import tempfile
from datetime import datetime
from alita_session.base import *
from aiofiles import open as open_async
from pickle import dump, loads, HIGHEST_PROTOCOL
from dateutil.relativedelta import relativedelta


class SessionManager(SessionInterface):
    _fs_transaction_suffix = '.sess'

    def __init__(self, app, key_prefix=None, use_signer=False, permanent=False,
                 path=None, filename_template='fs_%s.sess', mode=0o644):
        super(SessionManager, self).__init__(app, key_prefix, use_signer, permanent)
        if path is None:
            sd = self.app.config.get('SESSION_DIRECTORY') or \
                 self.client_config.get('SESSION_DIRECTORY')
            if sd:
                path = os.path.abspath(os.path.expanduser(sd))
                if not os.path.exists(path):
                    os.makedirs(path)
            else:
                path = tempfile.gettempdir()
        self.path = path
        self.filename_template = filename_template
        self.mode = mode

    def get_session_filename(self, session_key):
        return os.path.join(self.path, self.filename_template % session_key)

    async def delete(self, session_key):
        fn = self.get_session_filename(session_key)
        try:
            os.unlink(fn)
        except OSError:
            pass

    async def exists(self, session_key):
        return await self.get(session_key)

    async def get(self, session_key):
        try:
            f = await open_async(self.get_session_filename(session_key), 'rb')
        except IOError:
            data = None
        else:
            try:
                data = loads(await f.read())
                if data['expire_date'] <= datetime.now():
                    return None
            except Exception as ex:
                data = None
            finally:
                await f.close()
        return data

    async def save(self, request):
        data = self.get_session_data(request.session)
        fn = self.get_session_filename(data['session_key'])
        fd, tmp = tempfile.mkstemp(dir=self.path)
        f = os.fdopen(fd, 'wb')
        try:
            dump(data, f, HIGHEST_PROTOCOL)
        finally:
            f.close()
        try:
            os.rename(tmp, fn)
            os.chmod(fn, self.mode)
        except (IOError, OSError):
            pass

    async def clear_expired(self, months=1):
        _date = datetime.now() + relativedelta(months=-months)
        before, after = self.filename_template.split('%s', 1)
        filename_re = re.compile(r'%s(.{5,})%s$' % (re.escape(before),
                                                    re.escape(after)))
        for filename in os.listdir(self.path):
            #: this is a session that is still being saved.
            if not filename.endswith(self._fs_transaction_suffix):
                continue
            match = filename_re.match(filename)
            if match is None:
                continue
            session_key = match.group(1)
            data = self.get(session_key)
            if data and data['expire_date'] < _date:
                self.delete(session_key)
