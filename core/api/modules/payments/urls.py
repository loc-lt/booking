from django.urls import path

from modules.payments import views

urlpatterns = [
    path("payments/reconciliation", views.ReconciliationView.as_view()),
    path("payments/<uuid:payment_id>", views.PaymentDetailView.as_view()),
    path("payments/<uuid:payment_id>/mark-paid", views.MarkPaidView.as_view()),
    path("refunds/<uuid:refund_id>/mark-succeeded", views.RefundSucceededView.as_view()),
    path(
        "webhooks/payments/<slug:gateway>/tenants/<uuid:tenant_id>",
        views.PaymentWebhookView.as_view(),
    ),
]
