from django.urls import path

from modules.resources import views

urlpatterns = [
    path("sites", views.SiteListView.as_view()),
    path("sites/<uuid:site_id>", views.SiteDetailView.as_view()),
    path("resource-types", views.ResourceTypeListView.as_view()),
    path("resource-types/<uuid:resource_type_id>", views.ResourceTypeDetailView.as_view()),
    path("resource-types/<uuid:resource_type_id>/fields", views.ResourceTypeFieldsView.as_view()),
    path(
        "resource-types/<uuid:resource_type_id>/fields/<slug:key>/archive",
        views.ResourceTypeFieldArchiveView.as_view(),
    ),
    path(
        "resource-types/<uuid:resource_type_id>/versions",
        views.ResourceTypeVersionsView.as_view(),
    ),
    path(
        "resource-types/<uuid:resource_type_id>/versions/<int:version>/restore",
        views.ResourceTypeRestoreView.as_view(),
    ),
    path("resources", views.ResourceListView.as_view()),
    path("resources/<uuid:resource_id>", views.ResourceDetailView.as_view()),
    path("resources/<uuid:resource_id>/maintenance", views.ResourceMaintenanceView.as_view()),
    path("resources/<uuid:resource_id>/activate", views.ResourceActivateView.as_view()),
    path("resources/<uuid:resource_id>/deactivate", views.ResourceDeactivateView.as_view()),
]
