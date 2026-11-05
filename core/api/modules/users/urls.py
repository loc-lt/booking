from django.urls import path

from modules.users import views

urlpatterns = [
    path("me", views.MeView.as_view()),
    path("me/accept-invitation", views.AcceptInvitationView.as_view()),
    path("permissions", views.PermissionListView.as_view()),
    path("roles", views.RoleListView.as_view()),
    path("roles/<uuid:role_id>/permissions", views.RolePermissionsView.as_view()),
    path("members", views.MemberListView.as_view()),
    path("members/invite", views.MemberInviteView.as_view()),
    path("members/<uuid:membership_id>", views.MemberDetailView.as_view()),
    path("members/<uuid:membership_id>/roles", views.MemberRolesView.as_view()),
    path("members/<uuid:membership_id>/disable", views.MemberDisableView.as_view()),
    path("members/<uuid:membership_id>/enable", views.MemberEnableView.as_view()),
]
