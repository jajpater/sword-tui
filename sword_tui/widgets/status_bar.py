"""Status bar widget."""

from typing import Optional, TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

if TYPE_CHECKING:
    from sword_tui.backend import DiathekeFilters


class StatusBar(Static):
    """Status bar showing current location and keybinding hints."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._mode = "normal"
        self._book = ""
        self._chapter = 1
        self._verse = 1
        self._verse_end: Optional[int] = None  # For visual selection range
        self._module = ""
        self._message: Optional[str] = None
        self._filters: Optional["DiathekeFilters"] = None

    def set_mode(self, mode: str) -> None:
        """Set the current mode: normal, visual, command."""
        self._mode = mode
        self._message = None
        self._update()

    def set_position(
        self,
        book: str,
        chapter: int,
        verse: int,
        verse_end: Optional[int] = None,
    ) -> None:
        """Set the current Bible position."""
        self._book = book
        self._chapter = chapter
        self._verse = verse
        self._verse_end = verse_end
        self._update()

    def set_module(self, module: str) -> None:
        """Set the current module name."""
        self._module = module
        self._update()

    def show_message(self, message: str) -> None:
        """Show a temporary message."""
        self._message = message
        self._update()

    def clear_message(self) -> None:
        """Clear the temporary message."""
        self._message = None
        self._update()

    def set_filters(self, filters: Optional["DiathekeFilters"]) -> None:
        """Set the diatheke filters for display."""
        self._filters = filters
        self._update()

    def _update(self) -> None:
        """Update the status bar display."""
        text = Text()

        # Reference
        if self._book:
            if self._verse_end and self._verse_end != self._verse:
                # Range selection
                ref = f"{self._book} {self._chapter}:{self._verse}-{self._verse_end}"
                count = self._verse_end - self._verse + 1
                text.append(ref, style="bold")
                text.append(f" ({count} vs)", style="dim")
            else:
                ref = f"{self._book} {self._chapter}:{self._verse}"
                text.append(ref, style="bold")

        # Module
        if self._module:
            text.append(" | ")
            text.append(f"[{self._module}]", style="cyan")

        # Filter indicators
        if self._filters:
            if self._filters.strongs or self._filters.footnotes:
                text.append(" ")
            if self._filters.strongs:
                text.append("[s]", style="bold green")
            if self._filters.footnotes:
                text.append("[F]", style="bold green")

        # Mode indicator
        if self._mode == "visual":
            text.append(" | ")
            text.append("VISUAL", style="bold black on yellow")
        elif self._mode == "parallel":
            text.append(" | ")
            text.append("PARALLEL", style="bold black on cyan")
        elif self._mode == "strongs":
            text.append(" | ")
            text.append("STRONG'S", style="bold black on green")

        # Message or hints
        if self._message:
            text.append("  ")
            text.append(self._message, style="yellow")
        else:
            hints = self._get_hints()
            if hints:
                text.append("  ")
                for i, (key, desc) in enumerate(hints):
                    if i > 0:
                        text.append(" ", style="dim")
                    text.append(key, style="bold yellow")
                    text.append(f" {desc}", style="dim")

        self.update(text)

    def _get_hints(self) -> list[tuple[str, str]]:
        """Get keybinding hints for the current mode."""
        if self._mode == "normal":
            return [
                ("j/k", "vers"),
                ("]/[", "hfdst"),
                ("r", "ref"),
                ("/", "zoek"),
                ("?", "help"),
            ]
        elif self._mode == "visual":
            return [
                ("j/k", "select"),
                ("y", "copy"),
                ("b", "mark"),
                ("Esc", "stop"),
            ]
        elif self._mode == "parallel":
            return [
                ("Tab", "pane"),
                ("m/M", "module"),
                ("L", "link"),
                ("P", "sluiten"),
            ]
        elif self._mode == "command":
            return [
                ("Enter", "run"),
                ("Esc", "stop"),
            ]
        elif self._mode == "search":
            return [
                ("j/k", "navigeer"),
                ("^D/^U", "pagina"),
                ("m", "module"),
                ("S", "modus"),
                ("Enter", "ga naar"),
            ]
        elif self._mode == "strongs":
            return [
                ("^h/^l", "woord"),
                ("j/k", "vers"),
                ("M", "modules"),
                ("s", "sluiten"),
            ]
        else:
            return []
