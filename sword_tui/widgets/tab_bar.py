"""Tab bar widget showing open tabs."""

from typing import List

from rich.text import Text
from textual.widgets import Static


class TabBar(Static):
    """Horizontal bar showing open tabs, 1 line, docked under Header."""

    DEFAULT_CSS = """
    TabBar {
        dock: top;
        height: 1;
        background: $surface-darken-1;
    }
    """

    def update_tabs(self, names: List[str], active: int) -> None:
        """Update the tab bar display.

        Args:
            names: List of tab display names.
            active: Index of the active tab.
        """
        parts = Text()
        for i, name in enumerate(names):
            label = f" {i + 1}:{name} "
            if i == active:
                parts.append(label, style="reverse")
            else:
                parts.append(label)
            if i < len(names) - 1:
                parts.append("|", style="dim")
        self.update(parts)
