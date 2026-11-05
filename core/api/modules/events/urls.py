from django.urls import path

from modules.events import views

urlpatterns = [
    path("events", views.EventListView.as_view()),
]
