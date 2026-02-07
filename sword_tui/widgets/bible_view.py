"""Bible text view widget."""

import re
from typing import List, Optional

from rich.text import Text
from textual.widgets import Static

from sword_tui.data.types import VerseSegment


class BibleView(Static):
    """Widget that displays Bible text with verse numbers."""

    DEFAULT_CSS = """
    BibleView {
        width: 100%;
        padding: 1 2;
        background: $surface;
    }
    """

    def __init__(
        self,
        segments: Optional[List[VerseSegment]] = None,
        title: str = "",
        **kwargs,
    ):
        super().__init__("", **kwargs)  # Initialize with empty string
        self._segments: List[VerseSegment] = segments or []
        self._title = title
        self._search_query = ""
        self._highlight_verse: Optional[int] = None

    def update_content(
        self,
        segments: List[VerseSegment],
        title: str = "",
    ) -> None:
        """Update the displayed content.

        Args:
            segments: List of verse segments to display
            title: Optional title (e.g., "Genesis 1")
        """
        self._segments = segments
        self._title = title
        self._refresh_content()

    def set_search_query(self, query: str = "") -> None:
        """Set the search term for highlighting.

        Args:
            query: Search term to highlight
        """
        self._search_query = query
        self._refresh_content()

    def highlight_verse(self, verse: Optional[int]) -> None:
        """Highlight a specific verse.

        Args:
            verse: Verse number to highlight, or None to clear
        """
        self._highlight_verse = verse
        self._refresh_content()

    def get_verse_text(self, verse: int) -> str:
        """Get the text of a specific verse.

        Args:
            verse: Verse number

        Returns:
            Verse text or empty string if not found
        """
        for seg in self._segments:
            if seg.verse == verse:
                return seg.text
        return ""

    def get_all_text(self) -> str:
        """Get all displayed text.

        Returns:
            Concatenated verse text
        """
        return "\n".join(
            f"{seg.verse}. {seg.text}" for seg in self._segments
        )

    def _refresh_content(self) -> None:
        """Render the Bible text with Rich formatting."""
        text = Text()

        # Title
        if self._title:
            text.append(self._title, style="bold cyan")
            text.append("\n")
            text.append("─" * len(self._title), style="dim")
            text.append("\n\n")

        # Verses
        for seg in self._segments:
            is_highlighted = self._highlight_verse == seg.verse

            # Verse number
            verse_style = "bold yellow"
            if is_highlighted:
                verse_style = "bold black on yellow"
            text.append(f"{seg.verse}", style=verse_style)
            text.append(". ", style="dim")

            # Verse text
            base_style = "reverse" if is_highlighted else ""
            self._append_with_highlight(text, seg.text, base_style)
            text.append("\n")

        self.update(text)

    def _append_with_highlight(
        self, text: Text, content: str, base_style: str = ""
    ) -> None:
        """Append text with search term highlighting.

        Args:
            text: Rich Text object to append to
            content: Text content to add
            base_style: Base style to apply
        """
        if not self._search_query:
            text.append(content, style=base_style)
            return

        # Case-insensitive search highlighting
        pattern = re.compile(re.escape(self._search_query), re.IGNORECASE)
        last_end = 0

        for match in pattern.finditer(content):
            # Text before match
            if match.start() > last_end:
                text.append(content[last_end:match.start()], style=base_style)

            # Highlighted match
            text.append(match.group(), style="bold black on yellow")
            last_end = match.end()

        # Remaining text after last match
        if last_end < len(content):
            text.append(content[last_end:], style=base_style)
