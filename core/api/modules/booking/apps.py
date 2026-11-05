from django.apps import AppConfig


class BookingConfig(AppConfig):
    name = "modules.booking"
    label = "booking"

    def ready(self) -> None:
        from modules.booking import jobs  # noqa: F401  (registers the timers)
