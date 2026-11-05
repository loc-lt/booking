from django.urls import path

from modules.availability import views

urlpatterns = [
    path("availability", views.AvailabilityView.as_view()),
    path("sites/<uuid:site_id>/hours", views.SiteHoursView.as_view()),
    path("resources/<uuid:resource_id>/hours", views.ResourceHoursView.as_view()),
    path("availability-exceptions", views.ExceptionListView.as_view()),
    path("availability-exceptions/<uuid:exception_id>", views.ExceptionDetailView.as_view()),
]
