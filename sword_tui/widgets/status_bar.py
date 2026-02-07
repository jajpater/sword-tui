"""Status bar widget."""

from typing import Optional

from rich.text import Text
from textual.widgets import Static


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
        super().__init__(**kwargs)
        self._mode = "browse"
        self._reference = ""
        self._module = ""
        self._message: Optional[str] = None

    def set_mode(self, mode: str) -> None:
        """Set the current mode.

        Args:
            mode: Mode name ("browse", "search", "parallel", "command")
        """
        self._mode = mode
        self._message = None
        self._update()

    def set_reference(self, reference: str) -> None:
        """Set the current Bible reference.

        Args:
            reference: Reference string (e.g., "Genesis 1")
        """
        self._reference = reference
        self._update()

    def set_module(self, module: str) -> None:
        """Set the current module name.

        Args:
            module: Module name (e.g., "DutSVV")
        """
        self._module = module
        self._update()

    def show_message(self, message: str) -> None:
        """Show a temporary message.

        Args:
            message: Message to display
        """
        self._message = message
        self._update()

    def clear_message(self) -> None:
        """Clear the temporary message."""
        self._message = None
        self._update()

    def _update(self) -> None:
        """Update the status bar display."""
        text = Text()

        # Left side: reference and module
        if self._reference:
            text.append(self._reference, style="bold")
        if self._module:
            if self._reference:
                text.append(" | ")
            text.append(f"[{self._module}]", style="cyan")

        # Message or hints
        if self._message:
            text.append(" ")
            text.append(self._message, style="yellow")
        else:
            # Add hints on the right
            hints = self._get_hints()
            if hints:
                # Calculate padding
                hint_text = " | ".join(f"{k} {v}" for k, v in hints)
                # We can't easily right-align in Textual Static, so just add space
                text.append("  ")
                for i, (key, desc) in enumerate(hints):
                    if i > 0:
                        text.append(" | ", style="dim")
                    text.append(key, style="bold yellow")
                    text.append(f" {desc}", style="")

        self.update(text)

    def _get_hints(self) -> list[tuple[str, str]]:
        """Get keybinding hints for the current mode.

        Returns:
            List of (key, description) tuples
        """
        if self._mode == "browse":
            return [
                ("j/k", "scroll"),
                ("]/[", "hfdst"),
                ("g", "ga naar"),
                ("/", "zoek"),
                ("P", "parallel"),
                ("m", "module"),
                ("q", "quit"),
            ]
        elif self._mode == "search":
            return [
                ("j/k", "nav"),
                ("Enter", "ga naar"),
                ("v", "visual"),
                ("y", "copy"),
                ("Esc", "sluit"),
            ]
        elif self._mode == "parallel":
            return [
                ("j/k", "scroll"),
                ("Tab", "wissel"),
                ("]/[", "hfdst"),
                ("P", "sluit"),
                ("m", "module"),
            ]
        elif self._mode == "command":
            return [
                ("Enter", "uitvoeren"),
                ("Esc", "annuleer"),
                ("Tab", "complete"),
            ]
        else:
            return []
