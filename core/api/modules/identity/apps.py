from django.apps import AppConfig


class IdentityConfig(AppConfig):
    name = "modules.identity"
    label = "identity"

    def ready(self) -> None:
        from modules.identity import consumers  # noqa: F401  (registers the invitation mailer)
