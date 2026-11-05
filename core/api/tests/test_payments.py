"""Upfront payment as a lifecycle policy: hold, pay (desk or signed webhook), expire, refund
(docs/domain/booking.md "Payment is a policy"; API_KICH_BAN.md 7.1-7.3)."""

import json
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from kernel.models import ScheduledJob, TransitionLog
from kernel.tenant_context import tenant_scope
from modules.booking.models import BookingAllocation
from modules.payments import service as payments
from modules.payments.models import PaymentEvent
from tests.conftest import FLOW_INSTANT, book, create_resource, create_type, local
from worker.management.commands.run_worker import run_due_jobs

pytestmark = pytest.mark.django_db

PAID_FLOW = {
    **FLOW_INSTANT,
    "cancellation": {"allowedUntilMinutesBefore": 0},
    "payment": {
        "mode": "upfront",
        "amountMinor": 100000,
        "per": "hour",
        "holdMinutes": 10,
        "refundRules": [
            {"minutesBefore": 1440, "percent": 100},
            {"minutesBefore": 0, "percent": 50},
        ],
    },
}


@pytest.fixture
def paid_room(world):
    rt = create_type(world, key="studio", flowConfig=PAID_FLOW)
    return create_resource(world, rt["id"])


def _webhook(world, body: dict, signature: str | None = None):
    raw = json.dumps(body).encode()
    return APIClient().post(
        f"/api/v1/webhooks/payments/mock/tenants/{world.tenant_id}",
        data=raw,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature if signature is not None else payments.sign(raw),
    )


def test_upfront_payment_holds_the_slot_until_paid_at_the_desk(world, paid_room, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10, 30)).json()
    assert b["status"] == "awaiting_payment"
    assert (b["payment"]["status"], b["payment"]["amountMinor"]) == ("pending", 150000)
    with tenant_scope(world.tenant_id):
        alloc = BookingAllocation.objects.get(booking_id=b["id"])
        assert alloc.effect == "HOLD" and alloc.hold_expires_at is not None
    # The member can see the payment, not mark it paid.
    pay_url = f"/api/v1/payments/{b['payment']['id']}"
    assert world.client("member").get(pay_url).json()["status"] == "pending"
    assert (
        world.client("member")
        .post(f"{pay_url}/mark-paid", {"method": "cash"}, format="json")
        .status_code
        == 403
    )
    paid = world.client("staff").post(f"{pay_url}/mark-paid", {"method": "cash"}, format="json")
    assert paid.status_code == 200, paid.json()
    p = paid.json()
    assert (p["status"], p["method"], p["events"][0]["gateway"]) == ("paid", "cash", "manual")
    assert [h["toStatus"] for h in p["history"]] == ["pending", "paid"]
    after = world.client("member").get(f"/api/v1/bookings/{b['id']}").json()
    assert after["status"] == "confirmed"
    assert [h["toStatus"] for h in after["history"]] == ["awaiting_payment", "confirmed"]
    with tenant_scope(world.tenant_id):
        assert BookingAllocation.objects.get(booking_id=b["id"]).effect == "LOCK"
    again = world.client("staff").post(f"{pay_url}/mark-paid", {"method": "cash"}, format="json")
    assert again.status_code == 409


def test_signed_webhook_confirms_once(world, paid_room, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10)).json()
    session = (
        world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()["sessionId"]
    )
    event = {
        "eventId": "evt_1",
        "type": "payment.succeeded",
        "sessionId": session,
        "amountMinor": 100000,
    }
    first = _webhook(world, event)
    assert first.json() == {"received": True, "outcome": "applied"}
    assert world.client("member").get(f"/api/v1/bookings/{b['id']}").json()["status"] == "confirmed"
    assert _webhook(world, event).json()["outcome"] == "duplicate"
    with tenant_scope(world.tenant_id):
        log = TransitionLog.objects.filter(object_code="payment").order_by("at").last()
        assert (log.to_status, log.actor_kind) == ("PAID", "GATEWAY")


def test_bad_signature_and_wrong_amount_change_nothing(world, paid_room, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10)).json()
    session = (
        world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()["sessionId"]
    )
    forged = _webhook(
        world,
        {
            "eventId": "evt_x",
            "type": "payment.succeeded",
            "sessionId": session,
            "amountMinor": 100000,
        },
        signature="0" * 64,
    )
    assert forged.json()["outcome"] == "ignored"
    short = _webhook(
        world,
        {"eventId": "evt_y", "type": "payment.succeeded", "sessionId": session, "amountMinor": 1},
    )
    assert short.json()["outcome"] == "needs_reconciliation"
    assert (
        world.client("member").get(f"/api/v1/bookings/{b['id']}").json()["status"]
        == "awaiting_payment"
    )
    queue = world.client("owner").get("/api/v1/payments/reconciliation").json()["data"]
    assert [e["gatewayEventId"] for e in queue] == ["evt_y"]
    with tenant_scope(world.tenant_id):
        assert PaymentEvent.objects.get(gateway_event_id="evt_x").signature_verified is False
    unknown = APIClient().post(
        "/api/v1/webhooks/payments/mock/tenants/0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a",
        data=b"{}",
        content_type="application/json",
    )
    assert unknown.status_code == 404


def test_failed_payment_expires_the_booking_and_frees_the_slot(world, paid_room, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10)).json()
    session = (
        world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()["sessionId"]
    )
    _webhook(
        world,
        {
            "eventId": "evt_f",
            "type": "payment.failed",
            "sessionId": session,
            "reason": "card_declined",
        },
    )
    after = world.client("member").get(f"/api/v1/bookings/{b['id']}").json()
    assert (after["status"], after["payment"]["status"]) == ("expired", "failed")
    assert (
        book(world, paid_room["id"], local(day, 9), local(day, 10), role="member2").status_code
        == 201
    )


def test_hold_expiry_timer(world, paid_room, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10)).json()
    ScheduledJob.objects.filter(record_id=b["id"], job_type="EXPIRE_HOLD").update(
        run_at=timezone.now() - timedelta(seconds=1)
    )
    run_due_jobs()
    after = world.client("member").get(f"/api/v1/bookings/{b['id']}").json()
    assert (after["status"], after["payment"]["status"]) == ("expired", "expired")
    # Money arriving now is not applied: a person reconciles it.
    session = (
        world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()["sessionId"]
    )
    late = _webhook(
        world,
        {
            "eventId": "evt_late",
            "type": "payment.succeeded",
            "sessionId": session,
            "amountMinor": 100000,
        },
    )
    assert late.json()["outcome"] == "needs_reconciliation"


def test_cancel_refunds_by_the_policy_and_the_desk_settles_it(world, paid_room, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10)).json()
    pay_url = f"/api/v1/payments/{b['payment']['id']}"
    world.client("staff").post(f"{pay_url}/mark-paid", {"method": "card"}, format="json")
    # A week ahead: more than 24 hours before the start -> 100%.
    cancelled = world.client("member").post(f"/api/v1/bookings/{b['id']}/cancel").json()
    assert (cancelled["status"], cancelled["payment"]["status"]) == ("cancelled", "refund_pending")
    refund = world.client("staff").get(pay_url).json()["refunds"][0]
    assert (refund["amountMinor"], refund["status"], refund["appliedRule"]["percent"]) == (
        100000,
        "pending",
        100,
    )
    assert (
        world.client("member").post(f"/api/v1/refunds/{refund['id']}/mark-succeeded").status_code
        == 403
    )
    settled = world.client("owner").post(f"/api/v1/refunds/{refund['id']}/mark-succeeded").json()
    assert (settled["status"], settled["refundedMinor"]) == ("refunded", 100000)


def test_late_cancel_refunds_half_through_the_gateway(world, paid_room, freeze, day):
    b = book(world, paid_room["id"], local(day, 9), local(day, 10)).json()
    session = (
        world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()["sessionId"]
    )
    _webhook(
        world,
        {
            "eventId": "evt_p",
            "type": "payment.succeeded",
            "sessionId": session,
            "amountMinor": 100000,
        },
    )
    freeze(local(day, 7))  # two hours before the start
    world.client("member").post(f"/api/v1/bookings/{b['id']}/cancel")
    refund = (
        world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()["refunds"][0]
    )
    assert refund["amountMinor"] == 50000
    done = _webhook(
        world,
        {
            "eventId": "evt_r",
            "type": "refund.succeeded",
            "refundId": refund["id"],
            "paymentRef": "rf_1",
        },
    )
    assert done.json()["outcome"] == "applied"
    p = world.client("member").get(f"/api/v1/payments/{b['payment']['id']}").json()
    assert (p["status"], p["refundedMinor"]) == ("partially_refunded", 50000)


def test_paid_then_approval_when_both_are_required(world, day):
    rt = create_type(world, key="hall", flowConfig={**PAID_FLOW, "confirmation": "approval"})
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 10)).json()
    assert b["status"] == "awaiting_payment"
    world.client("staff").post(
        f"/api/v1/payments/{b['payment']['id']}/mark-paid", {"method": "cash"}, format="json"
    )
    assert (
        world.client("member").get(f"/api/v1/bookings/{b['id']}").json()["status"]
        == "pending_approval"
    )
    rejected = world.client("staff").post(
        f"/api/v1/bookings/{b['id']}/reject", {"reason": "Private event"}, format="json"
    )
    assert (rejected.json()["status"], rejected.json()["payment"]["status"]) == (
        "rejected",
        "refund_pending",
    )
