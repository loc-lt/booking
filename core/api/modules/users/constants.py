"""The system roles every tenant starts with (docs/backend.md: owner, admin, staff, member,
guest). Permission codes live in kernel/permissions.py.

System roles take their permissions from this file, not from role_permissions, so a new
permission code reaches every tenant with the next deploy. Tenants who want a different mix
create their own role (POST /roles).
"""

from kernel.permissions import (
    ALL_PERMISSIONS,
    AVAILABILITY_READ,
    BOOKING_APPROVE,
    BOOKING_CANCEL_ANY,
    BOOKING_CANCEL_OWN,
    BOOKING_CHECK_IN_ANY,
    BOOKING_CHECK_IN_OWN,
    BOOKING_CREATE,
    BOOKING_CREATE_FOR_OTHERS,
    BOOKING_READ_ALL,
    BOOKING_READ_OWN,
    MEMBER_READ,
    PAYMENT_MARK_PAID,
    PAYMENT_READ,
    RESOURCE_READ,
    RESOURCE_TYPE_READ,
    SITE_READ,
)

_MEMBER = {
    RESOURCE_TYPE_READ,
    RESOURCE_READ,
    SITE_READ,
    AVAILABILITY_READ,
    BOOKING_CREATE,
    BOOKING_READ_OWN,
    BOOKING_CANCEL_OWN,
    BOOKING_CHECK_IN_OWN,
}
_STAFF = _MEMBER | {
    BOOKING_CREATE_FOR_OTHERS,
    BOOKING_READ_ALL,
    BOOKING_CANCEL_ANY,
    BOOKING_CHECK_IN_ANY,
    BOOKING_APPROVE,
    PAYMENT_READ,
    PAYMENT_MARK_PAID,
    MEMBER_READ,
}

# code -> (name, permissions). Roles from docs/backend.md: owner, admin, staff, member, guest.
SYSTEM_ROLES: dict[str, tuple[str, frozenset[str]]] = {
    "owner": ("Owner", ALL_PERMISSIONS),
    "admin": ("Admin", ALL_PERMISSIONS),
    "staff": ("Staff", frozenset(_STAFF)),
    "member": ("Member", frozenset(_MEMBER)),
    "guest": ("Guest", frozenset(_MEMBER)),
}
