"""
app_info.py — Centralised application metadata.

All constants are also available as environment variables after calling
setup_env() (done automatically by app_init.setup_environment).
"""

import os

# ---------------------------------------------------------------------------
# App identity
# ---------------------------------------------------------------------------
APP_NAME        = "PlayForm"
APP_DESCRIPTION = "A modern, accessible media player for audio and video files."
APP_VERSION     = "1.0.0"
APP_PUBLISHER   = "Still Standing"
APP_AUTHOR      = "Still Standing"
APP_LICENSE     = "MIT"
APP_COPYRIGHT   = "Copyright © 2024 Still Standing"

# ---------------------------------------------------------------------------
# Online resources
# ---------------------------------------------------------------------------
APP_WEBSITE     = "https://github.com/still-standing88/playform"
APP_GITHUB_REPO = "still-standing88/playform"          # owner/repo
APP_SUPPORT_EMAIL = ""

# ---------------------------------------------------------------------------
# Environment variable names (keys for os.environ)
# ---------------------------------------------------------------------------
ENV_APP_NAME         = "APP_NAME"
ENV_APP_DESCRIPTION  = "APP_DESCRIPTION"
ENV_APP_VERSION      = "APP_VERSION"
ENV_APP_PUBLISHER    = "APP_PUBLISHER"
ENV_APP_AUTHOR       = "APP_AUTHOR"
ENV_APP_LICENSE      = "APP_LICENSE"
ENV_APP_COPYRIGHT    = "APP_COPYRIGHT"
ENV_APP_WEBSITE      = "APP_WEBSITE"
ENV_APP_GITHUB_REPO  = "APP_GITHUB_REPO"
ENV_APP_SUPPORT_EMAIL = "APP_SUPPORT_EMAIL"


def setup_env() -> None:
    """Export all app metadata to environment variables."""
    os.environ[ENV_APP_NAME]          = APP_NAME
    os.environ[ENV_APP_DESCRIPTION]   = APP_DESCRIPTION
    os.environ[ENV_APP_VERSION]       = APP_VERSION
    os.environ[ENV_APP_PUBLISHER]     = APP_PUBLISHER
    os.environ[ENV_APP_AUTHOR]        = APP_AUTHOR
    os.environ[ENV_APP_LICENSE]       = APP_LICENSE
    os.environ[ENV_APP_COPYRIGHT]     = APP_COPYRIGHT
    os.environ[ENV_APP_WEBSITE]       = APP_WEBSITE
    os.environ[ENV_APP_GITHUB_REPO]   = APP_GITHUB_REPO
    os.environ[ENV_APP_SUPPORT_EMAIL] = APP_SUPPORT_EMAIL
