from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from django.db import transaction

_current_tenant: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)


def current_tenant_id() -> UUID | None:
    return _current_tenant.get()


@contextmanager
def fresh_tenant_context() -> Iterator[None]:
    """No tenant at the start of a request, and none left behind after it. Without this a
    worker thread keeps the previous request's tenant in the context variable: logs of the
    next request name the wrong tenant, and tenant_scope() "restores" it into the database
    session (app.tenant_id) of a request that has no tenant."""
    token = _current_tenant.set(None)
    try:
        yield
    finally:
        _current_tenant.reset(token)


def activate_tenant(tenant_id: UUID | str | None) -> None:
    """SET LOCAL app.tenant_id until the current transaction ends. RLS policies read it.

    None clears it, and then every tenant table looks empty.
    """
    conn = transaction.get_connection()
    if not conn.in_atomic_block:
        raise RuntimeError(
            "activate_tenant() must run inside transaction.atomic(): "
            "SET LOCAL only lasts until the transaction ends."
        )
    tenant = UUID(str(tenant_id)) if tenant_id is not None else None
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.tenant_id', %s, true)", [str(tenant) if tenant else ""]
        )
    _current_tenant.set(tenant)


def activate_user(user_id: UUID) -> None:
    """SET LOCAL app.user_id: lets the caller read their own memberships across tenants
    (GET /me/tenants), and only while no tenant is active (users migration 0003)."""
    conn = transaction.get_connection()
    if not conn.in_atomic_block:
        return
    with conn.cursor() as cursor:
        cursor.execute("SELECT set_config('app.user_id', %s, true)", [str(user_id)])


@contextmanager
def tenant_scope(tenant_id: UUID | str) -> Iterator[None]:
    """Run a block as one tenant, in its own transaction (or savepoint).

    For the worker, management commands and tests. API views don't need it: the base view
    activates the tenant inside the request transaction.
    """
    previous = _current_tenant.get()
    try:
        with transaction.atomic():
            activate_tenant(tenant_id)
            yield
    finally:
        conn = transaction.get_connection()
        if conn.in_atomic_block and not conn.needs_rollback:
            activate_tenant(previous)
        else:
            _current_tenant.set(previous)
