APP_VERSION = "0.732.0"


def short_version() -> str:
    return ".".join(APP_VERSION.split(".")[:2])
