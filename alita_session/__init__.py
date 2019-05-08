import time
from importlib import import_module
from alita_session.utils import http_date

__version__ = '0.1.1'


class Session:
    def __init__(self, app=None):
        self.app = app
        self.engine = None
        self.session_manager = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        if "session" in self.app.extensions:
            raise RuntimeError("Extensions session is not allow register repeated!")
        self.app.extensions.session = self
        for config_name in ['SESSION_ENGINE', 'SESSION_ENGINE_CONFIG']:
            if not self.app.config.get(config_name):
                raise RuntimeError(f"App config {config_name} not existed, "
                                   "please config it again!")
        self.engine = import_module(self.app.config['SESSION_ENGINE'])
        self.session_manager = self.engine.SessionManager(app)

        @self.app.request_middleware
        async def process_request(request):
            request.session = await self.session_manager.get_session(request)
            request.session_manager = self.session_manager

        @self.app.response_middleware
        async def process_response(request, response):
            try:
                modified = request.session.modified
                empty = request.session.is_empty()
            except AttributeError:
                pass
            else:
                if self.app.session_cookie_name in request.cookies and empty and modified:
                    response.delete_cookie(
                        self.app.session_cookie_name,
                        path=self.app.session_cookie_path,
                        domain=self.app.session_cookie_domain,
                    )
                else:
                    if (modified or self.app.session_save_every_request) and not empty:
                        if self.app.config.get("SESSION_EXPIRE_AT_BROWSER_CLOSE", False):
                            max_age = None
                            expires = None
                        else:
                            max_age = self.session_manager.get_expiry_age(request.session)
                            expires_time = time.time() + max_age
                            expires = http_date(expires_time)
                        if isinstance(response, self.app.response_class) \
                                and response.status != 500:
                            await self.session_manager.save_session(request)
                            response.set_cookie(
                                self.app.session_cookie_name,
                                self.session_manager.get_session_id(request),
                                max_age=max_age, expires=expires,
                                path=self.app.session_cookie_path,
                                domain=self.app.session_cookie_domain,
                                secure=self.app.config.get('SESSION_COOKIE_SECURE'),
                                httponly=self.app.config.get('SESSION_COOKIE_HTTPONLY'),
                                samesite=self.app.config.get('SESSION_COOKIE_SAMESITE'),
                            )
            return response
