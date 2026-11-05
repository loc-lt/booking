from django.urls import path

from modules.booking import views

urlpatterns = [
    path("bookings", views.BookingListView.as_view()),
    path("bookings/preview", views.BookingPreviewView.as_view()),
    path("bookings/<uuid:booking_id>", views.BookingDetailView.as_view()),
    path("bookings/<uuid:booking_id>/approve", views.BookingApproveView.as_view()),
    path("bookings/<uuid:booking_id>/reject", views.BookingRejectView.as_view()),
    path("bookings/<uuid:booking_id>/check-in", views.BookingCheckInView.as_view()),
    path("bookings/<uuid:booking_id>/cancel", views.BookingCancelView.as_view()),
    path("bookings/<uuid:booking_id>/check-out", views.BookingCheckOutView.as_view()),
]
