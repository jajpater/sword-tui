"""Bible text view widget."""

import re
from typing import List, Optional

from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Static

from sword_tui.data.types import VerseSegment


class VerseRow(Static):
    """Single verse display widget."""

    DEFAULT_CSS = """
    VerseRow {
        width: 100%;
        padding: 0 2;
        background: $surface;
    }
    VerseRow.current {
        background: $surface-lighten-1;
    }
    VerseRow.selected {
        background: #333300;
    }
    """

    def __init__(self, segment: VerseSegment, **kwargs):
        super().__init__("", **kwargs)
        self.segment = segment
        self._is_current = False
        self._is_selected = False
        self._search_query = ""

    def set_state(
        self,
        is_current: bool = False,
        is_selected: bool = False,
        search_query: str = "",
    ) -> None:
        """Update the verse state and re-render."""
        self._is_current = is_current
        self._is_selected = is_selected
        self._search_query = search_query
        self._render_verse()

        # Update CSS classes
        self.remove_class("current", "selected")
        if is_current:
            self.add_class("current")
        elif is_selected:
            self.add_class("selected")

    def _render_verse(self) -> None:
        """Render the verse with formatting."""
        text = Text()

        # Current verse indicator
        if self._is_current:
            text.append("▶ ", style="bold cyan")
        else:
            text.append("  ")

        # Verse number
        if self._is_current:
            verse_style = "bold black on cyan"
        elif self._is_selected:
            verse_style = "bold black on yellow"
        else:
            verse_style = "bold yellow"
        text.append(f"{self.segment.verse}", style=verse_style)
        text.append(". ", style="dim")

        # Verse text with optional search highlighting
        base_style = ""
        if self._is_selected and not self._is_current:
            base_style = "on #333300"

        self._append_with_highlight(text, self.segment.text, base_style)
        self.update(text)

    def _append_with_highlight(
        self, text: Text, content: str, base_style: str = ""
    ) -> None:
        """Append text with search term highlighting."""
        if not self._search_query:
            text.append(content, style=base_style)
            return

        pattern = re.compile(re.escape(self._search_query), re.IGNORECASE)
        last_end = 0

        for match in pattern.finditer(content):
            if match.start() > last_end:
                text.append(content[last_end : match.start()], style=base_style)
            text.append(match.group(), style="bold black on yellow")
            last_end = match.end()

        if last_end < len(content):
            text.append(content[last_end:], style=base_style)


class BibleView(Vertical):
    """Widget that displays Bible text with verse navigation."""

    DEFAULT_CSS = """
    BibleView {
        width: 100%;
        background: $surface;
    }
    """

    def __init__(
        self,
        segments: Optional[List[VerseSegment]] = None,
        title: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._segments: List[VerseSegment] = segments or []
        self._title = title
        self._search_query = ""
        self._current_verse: int = 1
        self._visual_start: Optional[int] = None
        self._visual_mode = False
        self._verse_widgets: dict[int, VerseRow] = {}

    @property
    def current_verse(self) -> int:
        """Get current verse number."""
        return self._current_verse

    @property
    def verse_count(self) -> int:
        """Get total number of verses."""
        return len(self._segments)

    @property
    def visual_mode(self) -> bool:
        """Check if in visual mode."""
        return self._visual_mode

    def get_visual_range(self) -> tuple[int, int]:
        """Get the visual selection range (start, end) inclusive."""
        if not self._visual_mode or self._visual_start is None:
            return (self._current_verse, self._current_verse)
        start = min(self._visual_start, self._current_verse)
        end = max(self._visual_start, self._current_verse)
        return (start, end)

    def update_content(
        self,
        segments: List[VerseSegment],
        title: str = "",
    ) -> None:
        """Update the displayed content."""
        self._segments = segments
        self._title = title
        self._current_verse = segments[0].verse if segments else 1
        self._visual_mode = False
        self._visual_start = None
        self._rebuild_widgets()

    def _rebuild_widgets(self) -> None:
        """Rebuild all verse widgets."""
        # Remove existing widgets
        self._verse_widgets.clear()
        self.remove_children()

        # Create new widgets
        vis_start, vis_end = self.get_visual_range() if self._visual_mode else (0, 0)

        for seg in self._segments:
            widget = VerseRow(seg, id=f"verse-{seg.verse}")
            is_current = seg.verse == self._current_verse
            is_selected = self._visual_mode and vis_start <= seg.verse <= vis_end
            widget.set_state(is_current, is_selected, self._search_query)
            self._verse_widgets[seg.verse] = widget
            self.mount(widget)

    def _update_verse_states(self) -> None:
        """Update all verse widget states without rebuilding."""
        vis_start, vis_end = self.get_visual_range() if self._visual_mode else (0, 0)

        for verse_num, widget in self._verse_widgets.items():
            is_current = verse_num == self._current_verse
            is_selected = self._visual_mode and vis_start <= verse_num <= vis_end
            widget.set_state(is_current, is_selected, self._search_query)

    def _scroll_to_current(self) -> None:
        """Scroll to make current verse visible."""
        if self._current_verse in self._verse_widgets:
            widget = self._verse_widgets[self._current_verse]
            widget.scroll_visible(top=True)

    def set_search_query(self, query: str = "") -> None:
        """Set the search term for highlighting."""
        self._search_query = query
        self._update_verse_states()

    def set_current_verse(self, verse: int) -> None:
        """Set the current verse (cursor position)."""
        if self._segments:
            max_verse = max(s.verse for s in self._segments)
            min_verse = min(s.verse for s in self._segments)
            self._current_verse = max(min_verse, min(verse, max_verse))
            self._update_verse_states()
            self._scroll_to_current()

    def move_to_verse(self, verse: int) -> None:
        """Move cursor to specific verse."""
        self.set_current_verse(verse)

    def next_verse(self) -> bool:
        """Move to next verse. Returns True if moved, False if at end."""
        if self._segments:
            verses = sorted(s.verse for s in self._segments)
            try:
                idx = verses.index(self._current_verse)
                if idx < len(verses) - 1:
                    self._current_verse = verses[idx + 1]
                    self._update_verse_states()
                    self._scroll_to_current()
                    return True
            except ValueError:
                pass
        return False

    def prev_verse(self) -> bool:
        """Move to previous verse. Returns True if moved, False if at start."""
        if self._segments:
            verses = sorted(s.verse for s in self._segments)
            try:
                idx = verses.index(self._current_verse)
                if idx > 0:
                    self._current_verse = verses[idx - 1]
                    self._update_verse_states()
                    self._scroll_to_current()
                    return True
            except ValueError:
                pass
        return False

    def first_verse(self) -> None:
        """Go to first verse."""
        if self._segments:
            self._current_verse = min(s.verse for s in self._segments)
            self._update_verse_states()
            self._scroll_to_current()

    def last_verse(self) -> None:
        """Go to last verse."""
        if self._segments:
            self._current_verse = max(s.verse for s in self._segments)
            self._update_verse_states()
            self._scroll_to_current()

    def start_visual_mode(self) -> None:
        """Start visual selection at current verse."""
        self._visual_mode = True
        self._visual_start = self._current_verse
        self._update_verse_states()

    def end_visual_mode(self) -> None:
        """End visual selection mode."""
        self._visual_mode = False
        self._visual_start = None
        self._update_verse_states()

    def get_current_segment(self) -> Optional[VerseSegment]:
        """Get the current verse segment."""
        for seg in self._segments:
            if seg.verse == self._current_verse:
                return seg
        return None

    def get_selected_segments(self) -> List[VerseSegment]:
        """Get segments in visual selection (or just current verse)."""
        start, end = self.get_visual_range()
        return [s for s in self._segments if start <= s.verse <= end]

    def get_verse_text(self, verse: int) -> str:
        """Get the text of a specific verse."""
        for seg in self._segments:
            if seg.verse == verse:
                return seg.text
        return ""

    def get_selected_text(self) -> str:
        """Get text of selected verses."""
        segments = self.get_selected_segments()
        return "\n".join(f"{s.verse}. {s.text}" for s in segments)

    def get_all_text(self) -> str:
        """Get all displayed text."""
        return "\n".join(f"{seg.verse}. {seg.text}" for seg in self._segments)
