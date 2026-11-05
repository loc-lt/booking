"""Signing in (D-003). Everything here is reachable without a token, except password change
and GET /me/tenants. No X-Tenant-Id: a person signs in once and then picks a tenant."""

from typing import Any

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from modules.identity import service


class _Public(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


def _agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")


def _valid(serializer_class: type[serializers.Serializer], request: Request) -> dict[str, Any]:
    body = serializer_class(data=request.data)
    body.is_valid(raise_exception=True)
    return body.validated_data


class RegisterRequest(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=200, trim_whitespace=False)
    fullName = serializers.CharField(max_length=200)


class LoginRequest(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=200, trim_whitespace=False)


class RefreshRequest(serializers.Serializer):
    refreshToken = serializers.CharField(max_length=200)


class ForgotRequest(serializers.Serializer):
    email = serializers.EmailField()


class ResetRequest(serializers.Serializer):
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=200, trim_whitespace=False)


class ChangeRequest(serializers.Serializer):
    currentPassword = serializers.CharField(max_length=200, trim_whitespace=False)
    newPassword = serializers.CharField(max_length=200, trim_whitespace=False)


class AcceptRequest(serializers.Serializer):
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=200, trim_whitespace=False, required=False)
    fullName = serializers.CharField(max_length=200, required=False)


class GuestRequest(serializers.Serializer):
    tenantId = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField(required=False)
    phone = serializers.RegexField(r"^\+?[0-9 ()\-.]{6,20}$", required=False)


class RegisterView(_Public):
    def post(self, request: Request) -> Response:
        d = _valid(RegisterRequest, request)
        tokens = service.register(
            email=d["email"],
            password=d["password"],
            full_name=d["fullName"],
            user_agent=_agent(request),
        )
        return Response(tokens.json(), status=status.HTTP_201_CREATED)


class LoginView(_Public):
    """Runs outside the request transaction (urls.py): a failed attempt must stay counted."""

    def post(self, request: Request) -> Response:
        d = _valid(LoginRequest, request)
        tokens = service.login(email=d["email"], password=d["password"], user_agent=_agent(request))
        return Response(tokens.json())


class RefreshView(_Public):
    """Outside the request transaction too: revoking a leaked family must stick."""

    def post(self, request: Request) -> Response:
        d = _valid(RefreshRequest, request)
        tokens = service.refresh(refresh_token=d["refreshToken"], user_agent=_agent(request))
        return Response(tokens.json())


class LogoutView(_Public):
    def post(self, request: Request) -> Response:
        service.logout(refresh_token=_valid(RefreshRequest, request)["refreshToken"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ForgotView(_Public):
    def post(self, request: Request) -> Response:
        service.forgot_password(email=_valid(ForgotRequest, request)["email"])
        return Response({"sent": True}, status=status.HTTP_202_ACCEPTED)


class ResetView(_Public):
    def post(self, request: Request) -> Response:
        d = _valid(ResetRequest, request)
        tokens = service.reset_password(
            token=d["token"], password=d["password"], user_agent=_agent(request)
        )
        return Response(tokens.json())


class AcceptInvitationLinkView(_Public):
    def post(self, request: Request) -> Response:
        d = _valid(AcceptRequest, request)
        tokens, tenant_id = service.accept_invitation(
            token=d["token"],
            password=d.get("password"),
            full_name=d.get("fullName"),
            user_agent=_agent(request),
        )
        return Response({**tokens.json(), "tenantId": str(tenant_id)})


class GuestView(_Public):
    def post(self, request: Request) -> Response:
        d = _valid(GuestRequest, request)
        tokens, member_id = service.guest(
            tenant_id=d["tenantId"], name=d["name"], email=d.get("email"), phone=d.get("phone")
        )
        return Response(
            {**tokens.json(), "tenantId": str(d["tenantId"]), "memberId": str(member_id)},
            status=status.HTTP_201_CREATED,
        )


class ChangePasswordView(APIView):
    """Needs a token (any tenant or none)."""

    def post(self, request: Request) -> Response:
        d = _valid(ChangeRequest, request)
        tokens = service.change_password(
            user_id=request.user.user_id,
            current=d["currentPassword"],
            new=d["newPassword"],
            user_agent=_agent(request),
        )
        return Response(tokens.json())


class MyTenantsView(APIView):
    """GET /me/tenants: which tenants can I work in? No X-Tenant-Id."""

    def get(self, request: Request) -> Response:
        return Response({"data": service.tenants_of(request.user.user_id)})
