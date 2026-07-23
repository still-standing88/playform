import os

from utilities.functions import setup_mpv_binaries


def ensure_mpv_bootstrap() -> None:
    if os.name == "nt":
        setup_mpv_binaries()


ensure_mpv_bootstrap()
