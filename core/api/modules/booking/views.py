"""Thin views: request serializer -> one service call -> response. Permission checks that
depend on the booking (own booking, its site) happen in the service."""

from typing import Any
from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from kernel.access import TenantAPIView
from kernel.idempotency import HEADER, run_idempotent
from kernel.pagination import paginate
from modules.booking import serializers as s
from modules.booking import service


def _one(booking: Any) -> dict[str, Any]:
    return s.booking_json(service.describe([booking])[0])


def _many(rows: list[Any]) -> list[dict[str, Any]]:
    return [s.booking_json(v) for v in service.describe(rows)]


class BookingListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        query = s.BookingListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        q = query.validated_data
        qs = service.list_bookings(
            access=request.access,
            filters={
                "resource_id": q.get("resourceId"),
                "resource_type_id": q.get("resourceTypeId"),
                "site_id": q.get("siteId"),
                "member_id": q.get("memberId"),
                "status": q.get("status"),
                "from": q.get("from"),
                "to": q.get("to"),
            },
        )
        return Response(paginate(qs, request.query_params, _many))

    def post(self, request: Request) -> Response:
        def handle() -> Response:
            body = s.CreateBookingRequest(data=request.data)
            body.is_valid(raise_exception=True)
            d = body.validated_data
            booking = service.create_booking(
                access=request.access,
                req=service.BookingRequest(
                    resource_id=d["resourceId"],
                    member_id=d.get("memberId"),
                    start=d["start"],
                    end=d["end"],
                    custom_field_values=d["customFieldValues"],
                ),
            )
            return Response(_one(booking), status=status.HTTP_201_CREATED)

        return run_idempotent(
            tenant_id=request.access.tenant_id,
            membership_id=request.access.membership_id,
            key=request.headers.get(HEADER),
            endpoint="POST /bookings",
            body=request.data,
            handler=handle,
        )


class BookingPreviewView(TenantAPIView):
    """POST /bookings/preview: pipeline steps 1-6 as a dry run. Saves nothing."""

    def post(self, request: Request) -> Response:
        body = s.PreviewBookingRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        return Response(
            service.preview_booking(
                access=request.access,
                req=service.BookingRequest(
                    resource_id=d["resourceId"],
                    member_id=d.get("memberId"),
                    start=d["start"],
                    end=d["end"],
                    custom_field_values=d["customFieldValues"],
                ),
            )
        )


class BookingDetailView(TenantAPIView):
    def get(self, request: Request, booking_id: UUID) -> Response:
        return Response(_one(service.get_booking(access=request.access, booking_id=booking_id)))


class BookingApproveView(TenantAPIView):
    def post(self, request: Request, booking_id: UUID) -> Response:
        return Response(_one(service.approve(access=request.access, booking_id=booking_id)))


class BookingRejectView(TenantAPIView):
    def post(self, request: Request, booking_id: UUID) -> Response:
        body = s.RejectBookingRequest(data=request.data)
        body.is_valid(raise_exception=True)
        booking = service.reject(
            access=request.access, booking_id=booking_id, reason=body.validated_data["reason"]
        )
        return Response(_one(booking))


class BookingCheckInView(TenantAPIView):
    def post(self, request: Request, booking_id: UUID) -> Response:
        return Response(_one(service.check_in(access=request.access, booking_id=booking_id)))


class BookingCancelView(TenantAPIView):
    def post(self, request: Request, booking_id: UUID) -> Response:
        return Response(_one(service.cancel(access=request.access, booking_id=booking_id)))


class BookingCheckOutView(TenantAPIView):
    def post(self, request: Request, booking_id: UUID) -> Response:
        return Response(_one(service.check_out(access=request.access, booking_id=booking_id)))
