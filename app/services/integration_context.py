from contextvars import ContextVar
from app.core.config import settings

credentials: ContextVar[dict | None] = ContextVar("integration_credentials", default=None)


def integration_value(name: str):
    current = credentials.get()
    if current is not None:
        return current.get(name) or ""
    return getattr(settings, name)
