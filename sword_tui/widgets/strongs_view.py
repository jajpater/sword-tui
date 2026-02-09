"""Strong's dictionary view widget for displaying stacked dictionary entries."""

from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from sword_tui.backend.dictionary import DictionaryEntry


class DictionaryEntryWidget(Static):
    """Widget displaying a single dictionary entry."""

    DEFAULT_CSS = """
    DictionaryEntryWidget {
        width: 100%;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self, entry: DictionaryEntry, **kwargs):
        super().__init__("", **kwargs)
        self._entry = entry
        self._render_entry()

    def _render_entry(self) -> None:
        """Render the dictionary entry with formatting."""
        text = Text()

        # Title line (e.g., "G25 - ἀγαπάω (agapaō)")
        text.append(self._entry.title, style="bold cyan")
        text.append("\n")

        # Pronunciation if available
        if self._entry.pronunciation:
            text.append("Pronunciation: ", style="dim")
            text.append(self._entry.pronunciation, style="italic")
            text.append("\n")

        text.append("\n")

        # Definition
        if self._entry.definition:
            text.append(self._entry.definition)
        elif self._entry.raw_text:
            # Fallback to raw text
            text.append(self._entry.raw_text, style="dim")

        self.update(text)

    def update_entry(self, entry: DictionaryEntry) -> None:
        """Update the displayed entry."""
        self._entry = entry
        self._render_entry()


class ModuleHeader(Static):
    """Header widget showing module name."""

    DEFAULT_CSS = """
    ModuleHeader {
        width: 100%;
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    def __init__(self, module_name: str, **kwargs):
        super().__init__("", **kwargs)
        self._module_name = module_name
        self._render_header()

    def _render_header(self) -> None:
        """Render the header."""
        text = Text()
        text.append("═══ ", style="dim")
        text.append(self._module_name, style="bold")
        text.append(" ═══", style="dim")
        self.update(text)


class StrongsView(Widget):
    """Widget showing stacked dictionary entries for a Strong's number."""

    DEFAULT_CSS = """
    StrongsView {
        width: 100%;
        height: 100%;
        background: $surface;
    }

    StrongsView > #strongs-scroll {
        height: 100%;
    }

    StrongsView > #strongs-header {
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        padding: 0 1;
    }

    StrongsView .entry-container {
        width: 100%;
        padding: 0 0 1 0;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_number: str = ""
        self._entries: List[DictionaryEntry] = []

    def compose(self) -> ComposeResult:
        yield Static("Strong's Lookup", id="strongs-header")
        with VerticalScroll(id="strongs-scroll"):
            yield Vertical(id="strongs-content")

    def update_entries(
        self,
        strongs_number: str,
        entries: List[DictionaryEntry],
    ) -> None:
        """Update the displayed dictionary entries.

        Args:
            strongs_number: The Strong's number being displayed
            entries: List of dictionary entries to show
        """
        self._current_number = strongs_number
        self._entries = entries

        # Update header
        header = self.query_one("#strongs-header", Static)
        if strongs_number:
            header.update(f"Strong's: {strongs_number}")
        else:
            header.update("Strong's Lookup")

        # Clear and rebuild content
        content = self.query_one("#strongs-content", Vertical)
        content.remove_children()

        if not entries:
            if strongs_number:
                content.mount(Static(f"No entries found for {strongs_number}", classes="dim"))
            return

        # Add entries grouped by module
        for entry in entries:
            content.mount(ModuleHeader(entry.module))
            content.mount(DictionaryEntryWidget(entry))

    def clear(self) -> None:
        """Clear the view."""
        self._current_number = ""
        self._entries = []
        self.query_one("#strongs-header", Static).update("Strong's Lookup")
        self.query_one("#strongs-content", Vertical).remove_children()

    @property
    def current_number(self) -> str:
        """Get the currently displayed Strong's number."""
        return self._current_number

    @property
    def entries(self) -> List[DictionaryEntry]:
        """Get the currently displayed entries."""
        return self._entries
