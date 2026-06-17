import os

from utilities.functions import setup_vlc_binaries


def ensure_vlc_bootstrap() -> None:
    if os.name == "nt":
        setup_vlc_binaries()


ensure_vlc_bootstrap()
