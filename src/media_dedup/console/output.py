"""A thin, typed facade over Rich for consistent, coloured and translated messages."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console

from media_dedup.constants import ColorMode
from media_dedup.i18n import _

if TYPE_CHECKING:
    from rich.console import RenderableType

_YES_ANSWERS = frozenset({"y", "yes"})


def make_console(color: ColorMode) -> Console:
    """Create the Rich console for a colour mode (`NO_COLOR` is honoured by Rich).

    Args:
        color: `auto` detects a terminal, `always`/`never` force the choice.

    Returns:
        The console.
    """
    match color:
        case ColorMode.ALWAYS:
            return Console(force_terminal=True, highlight=False)
        case ColorMode.NEVER:
            return Console(no_color=True, highlight=False)
        case ColorMode.AUTO:
            return Console(highlight=False)


@dataclass(frozen=True, slots=True)
class Output:
    """Semantic output channel: every message kind has its own style and emoji."""

    console: Console

    def title(self, text: str) -> None:
        """Print a section title.

        Args:
            text: Translated title.
        """
        self.console.rule(f"[bold blue]{text}[/]")

    def info(self, text: str) -> None:
        """Print an informational line.

        Args:
            text: Translated message.
        """
        self.console.print(text)

    def success(self, text: str) -> None:
        """Print a success line.

        Args:
            text: Translated message.
        """
        self.console.print(f"✅ [green]{text}[/]")

    def warning(self, text: str) -> None:
        """Print a warning line.

        Args:
            text: Translated message.
        """
        self.console.print(f"⚠️  [yellow]{text}[/]")

    def error(self, text: str) -> None:
        """Print an error line.

        Args:
            text: Translated message.
        """
        self.console.print(f"❌ [bold red]{text}[/]")

    def tip(self, text: str) -> None:
        """Print a 💡 tip — shown as soon as there is something useful to suggest.

        Args:
            text: Translated tip.
        """
        self.console.print(f"💡 [cyan]{text}[/]")

    def show(self, renderable: RenderableType) -> None:
        """Print any Rich renderable (tables, panels).

        Args:
            renderable: What to print.
        """
        self.console.print(renderable)

    def blank(self) -> None:
        """Print an empty line, to let the sections breathe."""
        self.console.line()

    def confirm(self, question: str) -> bool:
        """Ask a yes/no question; anything but an explicit yes means no.

        Args:
            question: Translated question.

        Returns:
            True only for an explicit yes (in English or in the active language).
        """
        if not sys.stdin.isatty():
            return False
        answer = self.console.input(f"❓ {question} [bold]{_('[y/N]')}[/] ")
        accepted = _YES_ANSWERS | {_("y"), _("yes")}
        return answer.strip().casefold() in accepted
