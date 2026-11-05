"""Permission codes. Tenants assign them to roles (role_permissions); a role assignment can
be limited to one location (membership_roles.location_id). Views check them with
kernel.access.require_perm. The default roles live in modules/users/constants.py.

Tenants combine these codes into their own roles; they never invent new codes
(docs/database/API_KICH_BAN.md 5.2). DESCRIPTIONS feeds GET /permissions.
"""

RESOURCE_TYPE_READ = "resource_type.read"
RESOURCE_TYPE_MANAGE = "resource_type.manage"
RESOURCE_READ = "resource.read"
RESOURCE_MANAGE = "resource.manage"
SITE_READ = "site.read"
SITE_MANAGE = "site.manage"
AVAILABILITY_READ = "availability.read"
AVAILABILITY_MANAGE = "availability.manage"
BOOKING_CREATE = "booking.create"  # for oneself
BOOKING_CREATE_FOR_OTHERS = "booking.create_for_others"
BOOKING_READ_OWN = "booking.read_own"
BOOKING_READ_ALL = "booking.read_all"  # within the role's location scope
BOOKING_CANCEL_OWN = "booking.cancel_own"
BOOKING_CANCEL_ANY = "booking.cancel_any"
BOOKING_CHECK_IN_OWN = "booking.check_in_own"
BOOKING_CHECK_IN_ANY = "booking.check_in_any"
BOOKING_APPROVE = "booking.approve"
PAYMENT_READ = "payment.read"
PAYMENT_MARK_PAID = "payment.mark_paid"
PAYMENT_REFUND = "payment.refund"
POLICY_PUBLISH = "policy.publish"
RULE_READ = "rule.read"
RULE_PUBLISH = "rule.publish"
MEMBER_READ = "member.read"
MEMBER_MANAGE = "member.manage"
ROLE_MANAGE = "role.manage"
AUDIT_READ = "audit.read"

DESCRIPTIONS: dict[str, str] = {
    RESOURCE_TYPE_READ: "See resource types and their settings",
    RESOURCE_TYPE_MANAGE: "Create resource types, add fields, publish flow config",
    RESOURCE_READ: "See resources",
    RESOURCE_MANAGE: "Create and edit resources, put them in maintenance",
    SITE_READ: "See sites and their opening hours",
    SITE_MANAGE: "Create sites, set opening hours",
    AVAILABILITY_READ: "Search free slots",
    AVAILABILITY_MANAGE: "Block or open extra time (holidays, maintenance)",
    BOOKING_CREATE: "Book for oneself",
    BOOKING_CREATE_FOR_OTHERS: "Book on behalf of another member",
    BOOKING_READ_OWN: "See one's own bookings",
    BOOKING_READ_ALL: "See every booking at the role's sites",
    BOOKING_CANCEL_OWN: "Cancel one's own bookings before the deadline",
    BOOKING_CANCEL_ANY: "Cancel any booking at the role's sites, also after the deadline",
    BOOKING_CHECK_IN_OWN: "Check in and out of one's own bookings",
    BOOKING_CHECK_IN_ANY: "Check anyone in or out at the role's sites",
    BOOKING_APPROVE: "Approve or reject bookings at the role's sites",
    PAYMENT_READ: "See payments and refunds",
    PAYMENT_MARK_PAID: "Record a payment taken at the desk",
    PAYMENT_REFUND: "Record a refund paid out",
    POLICY_PUBLISH: "Publish or restore policy versions",
    RULE_READ: "See booking rules",
    RULE_PUBLISH: "Publish booking rules",
    MEMBER_READ: "See members",
    MEMBER_MANAGE: "Invite members, change their roles, disable them",
    ROLE_MANAGE: "Create roles and choose their permissions",
    AUDIT_READ: "See the event log",
}

ALL_PERMISSIONS = frozenset(DESCRIPTIONS)
