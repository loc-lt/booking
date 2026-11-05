from django.db import transaction
from django.urls import path

from modules.identity import views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view()),
    # Counting failures and revoking leaked refresh tokens must commit even when the answer
    # is 401, so these two run outside ATOMIC_REQUESTS (the service opens its own).
    path("auth/login", transaction.non_atomic_requests(views.LoginView.as_view())),
    path("auth/refresh", transaction.non_atomic_requests(views.RefreshView.as_view())),
    path("auth/logout", views.LogoutView.as_view()),
    path("auth/password/forgot", views.ForgotView.as_view()),
    path("auth/password/reset", views.ResetView.as_view()),
    path("auth/password/change", views.ChangePasswordView.as_view()),
    path("auth/invitations/accept", views.AcceptInvitationLinkView.as_view()),
    path("auth/guest", views.GuestView.as_view()),
    path("me/tenants", views.MyTenantsView.as_view()),
]
