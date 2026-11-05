from django.urls import path

from modules.rules import views

urlpatterns = [
    path("rules", views.RuleSetView.as_view()),
    path("rules/versions", views.RuleVersionListView.as_view()),
    path("rules/versions/<int:version>", views.RuleVersionDetailView.as_view()),
]
