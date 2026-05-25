from .dev import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
MIDDLEWARE = tuple(
    item for item in MIDDLEWARE if not item.startswith("blueapps.account.middlewares.")
)
