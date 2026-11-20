import contextlib
import contextvars
from typing import Optional

tenant_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "tenant_id", default=None
)


@contextlib.contextmanager
def use_tenant(tenant_id: Optional[str]):
    token = tenant_context.set(tenant_id)
    try:
        yield
    finally:
        tenant_context.reset(token)
