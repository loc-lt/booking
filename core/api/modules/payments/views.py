"""Payments: read, take money at the desk, settle refunds, gateway webhooks
(API_KICH_BAN.md section 7)."""

import json
from typing import Any
from uuid import UUID

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from kernel import permissions as perms
from kernel.access import TenantAPIView, require_perm
from kernel.errors import NotFound, ValidationFailed
from kernel.history import history_of
from kernel.tenant_context import activate_tenant
from modules.booking import service as booking
from modules.payments import service
from modules.payments.models import Payment, PaymentEvent, Refund
from modules.tenancy import service as tenancy


def refund_json(r: Refund) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "paymentId": str(r.payment_id),
        "amountMinor": r.amount_minor,
        "status": r.status.lower(),
        "reasonCode": r.reason_code,
        "appliedRule": r.applied_rule,
        "requestedAt": r.requested_at.isoformat(),
        "completedAt": r.completed_at.isoformat() if r.completed_at else None,
    }


def event_json(e: PaymentEvent) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "paymentId": str(e.payment_id) if e.payment_id else None,
        "gateway": e.gateway,
        "gatewayEventId": e.gateway_event_id,
        "type": e.type,
        "signatureVerified": e.signature_verified,
        "outcome": e.outcome.lower(),
        "receivedAt": e.received_at.isoformat(),
    }


def payment_json(p: Payment) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "bookingId": str(p.booking_id),
        "status": p.status.lower(),
        "amountMinor": p.amount_minor,
        "refundedMinor": p.refunded_minor,
        "currency": p.currency,
        "gateway": p.gateway,
        "method": p.method,
        "sessionId": p.gateway_session_id,
        "expiresAt": p.expires_at.isoformat() if p.expires_at else None,
        "paidAt": p.paid_at.isoformat() if p.paid_at else None,
        "refunds": [refund_json(r) for r in service.refunds_of(p.id)],
        "events": [event_json(e) for e in service.events_of(p.id)],
        "history": [
            {
                "fromStatus": h.from_status.lower() if h.from_status else None,
                "toStatus": h.to_status.lower(),
                "action": h.action.lower(),
                "actorKind": h.actor_kind.lower(),
                "occurredAt": h.at.isoformat(),
            }
            for h in history_of("payment", p.id)
        ],
    }


def _visible_payment(request: Request, payment_id: UUID) -> Payment:
    payment = service.get_payment(payment_id)
    b = booking.get_booking(access=request.access, booking_id=payment.booking_id)
    if b.booker_membership_id != request.access.membership_id:
        require_perm(request.access, perms.PAYMENT_READ, b.location_id)
    return payment


class PaymentDetailView(TenantAPIView):
    def get(self, request: Request, payment_id: UUID) -> Response:
        return Response(payment_json(_visible_payment(request, payment_id)))


class MarkPaidRequest(serializers.Serializer):
    method = serializers.ChoiceField(choices=["cash", "card", "bank_transfer", "other"])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class MarkPaidView(TenantAPIView):
    def post(self, request: Request, payment_id: UUID) -> Response:
        body = MarkPaidRequest(data=request.data)
        body.is_valid(raise_exception=True)
        booking.mark_paid(
            access=request.access,
            payment_id=payment_id,
            method=body.validated_data["method"],
            note=body.validated_data.get("note") or None,
        )
        return Response(payment_json(service.get_payment(payment_id)))


class RefundSucceededView(TenantAPIView):
    def post(self, request: Request, refund_id: UUID) -> Response:
        refund = booking.mark_refunded(access=request.access, refund_id=refund_id)
        return Response(payment_json(service.get_payment(refund.payment_id)))


class ReconciliationView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_perm(request.access, perms.PAYMENT_READ)
        return Response({"data": [event_json(e) for e in service.reconciliation_queue()]})


class PaymentWebhookView(APIView):
    """POST /webhooks/payments/{gateway}/tenants/{tenantId}. No JWT, no X-Tenant-Id: the gateway
    signs the raw body (X-Signature: HMAC-SHA256 hex). The tenant comes from the callback URL
    registered with the gateway, because payments sit behind RLS (API_KICH_BAN.md 7.1).
    Every stored message gets 200, duplicates and bad signatures included, so the gateway
    stops resending; the outcome is in the body and in payment_events."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def post(self, request: Request, gateway: str, tenant_id: UUID) -> Response:
        raw = request.body
        try:
            tenancy.get_tenant(tenant_id)
        except Exception:
            raise NotFound("Unknown tenant.") from None
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise ValidationFailed.one("_", "Body must be JSON.") from None
        if not isinstance(body, dict):
            raise ValidationFailed.one("_", "Body must be a JSON object.")
        activate_tenant(tenant_id)
        result = booking.apply_payment_webhook(
            gateway=gateway,
            raw_body=raw,
            signature=request.headers.get("X-Signature", ""),
            body=body,
            tenant_id=tenant_id,
        )
        return Response({"received": True, "outcome": result.outcome.lower()})
