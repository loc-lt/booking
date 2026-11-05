from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "modules.events"
    label = "events"

    def ready(self) -> None:
        from modules.events import consumers  # noqa: F401  (registers subscribers)
