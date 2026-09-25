"""Entry point of `media-dedup` (the image ENTRYPOINT) and `python -m media_dedup`."""

from __future__ import annotations

import sys

from media_dedup.cli.app import build_app
from media_dedup.constants import APP_NAME
from media_dedup.i18n import install
from media_dedup.i18n.bootstrap import resolve_locale


def main() -> None:
    """Install the interface language, then run the CLI."""
    install(resolve_locale(sys.argv[1:]))
    build_app()(prog_name=APP_NAME)


if __name__ == "__main__":
    main()
