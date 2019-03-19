## alita-session

alita-session is session management extension for Alita。

## Installing
```
pip install alita-session
```

## Quick Start

```
from alita import Alita
from alita_session import Session

app = Alita('dw')
app.config['SESSION_ENGINE'] = 'alita_session.redis'
app.config['SESSION_ENGINE_CONFIG'] = {
    'host': {host},
    'port': {port},
    'db': {db}
}
Session().init_app(app)

```

## Links

- Code: https://github.com/dwpy/alita-session