"""Jumplist view widget for displaying navigation history."""

from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message

from sword_tui.jumplist import JumpEntry


class JumpListSelected(Message):
    """Message sent when a jumplist entry is selected for navigation."""

    def __init__(self, entry: JumpEntry, index: int) -> None:
        self.entry = entry
        self.index = index
        super().__init__()


class JumpListItem(Static):
    """Widget displaying a single jumplist entry."""

    DEFAULT_CSS = """
    JumpListItem {
        width: 100%;
        padding: 0 1;
        background: $surface;
    }

    JumpListItem:hover {
        background: $surface-lighten-1;
    }

    JumpListItem.selected {
        background: $primary-darken-1;
    }
    """

    def __init__(self, entry: JumpEntry, index: int, is_cursor: bool = False, **kwargs):
        super().__init__("", **kwargs)
        self._entry = entry
        self._index = index
        self._is_cursor = is_cursor
        self._render_item()

    def _render_item(self) -> None:
        """Render the jumplist item."""
        text = Text()
        prefix = "> " if self._is_cursor else "  "
        text.append(prefix, style="bold yellow" if self._is_cursor else "")
        text.append(
            f"{self._entry.book} {self._entry.chapter}:{self._entry.verse}",
            style="bold cyan" if self._is_cursor else "",
        )
        self.update(text)

    @property
    def entry(self) -> JumpEntry:
        """Get the jump entry."""
        return self._entry

    @property
    def index(self) -> int:
        """Get the index of this item."""
        return self._index

    def select(self) -> None:
        """Mark this item as selected."""
        self.add_class("selected")

    def deselect(self) -> None:
        """Remove selection from this item."""
        self.remove_class("selected")


class JumpListView(Widget):
    """Widget showing the jumplist navigation history."""

    DEFAULT_CSS = """
    JumpListView {
        width: 100%;
        height: 100%;
        background: $surface;
    }

    JumpListView > #jumplist-scroll {
        height: 100%;
    }

    JumpListView > #jumplist-header {
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        padding: 0 1;
    }

    JumpListView #jumplist-status {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
        text-style: italic;
    }

    JumpListView .no-entries {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_index: int = 0
        self._items: List[JumpListItem] = []

    def compose(self) -> ComposeResult:
        yield Static("Jumplist", id="jumplist-header")
        with VerticalScroll(id="jumplist-scroll"):
            yield Vertical(id="jumplist-content")
        yield Static("", id="jumplist-status")

    def update_entries(self, entries: List[JumpEntry], cursor_pos: int) -> None:
        """Fill the list with jumplist entries, marking the cursor position.

        Args:
            entries: List of JumpEntry items
            cursor_pos: Current jumplist cursor position
        """
        self._selected_index = max(0, cursor_pos) if entries else 0

        # Update header
        header = self.query_one("#jumplist-header", Static)
        header.update("Jumplist")

        # Update status
        status = self.query_one("#jumplist-status", Static)
        if entries:
            status.update(f"{len(entries)} locaties | j/k nav | Enter ga naar")
        else:
            status.update("")

        # Clear and rebuild content
        content = self.query_one("#jumplist-content", Vertical)
        content.remove_children()

        if not entries:
            content.mount(Static("Geen navigatiegeschiedenis", classes="no-entries"))
            self._items = []
            return

        self._items = []
        for i, entry in enumerate(entries):
            is_cursor = i == cursor_pos
            item = JumpListItem(entry, i, is_cursor=is_cursor)
            if i == self._selected_index:
                item.select()
            content.mount(item)
            self._items.append(item)

        # Scroll selected item into view
        if self._items and 0 <= self._selected_index < len(self._items):
            self._items[self._selected_index].scroll_visible()

    def clear(self) -> None:
        """Clear the view."""
        self._selected_index = 0
        self._items = []
        self.query_one("#jumplist-header", Static).update("Jumplist")
        self.query_one("#jumplist-status", Static).update("")
        self.query_one("#jumplist-content", Vertical).remove_children()

    def action_next_item(self) -> None:
        """Move to next item."""
        if not self._items:
            return
        self._select_index(self._selected_index + 1)

    def action_prev_item(self) -> None:
        """Move to previous item."""
        if not self._items:
            return
        self._select_index(self._selected_index - 1)

    def action_select_item(self) -> None:
        """Select the current item for navigation."""
        if not self._items:
            return
        if 0 <= self._selected_index < len(self._items):
            item = self._items[self._selected_index]
            self.post_message(JumpListSelected(item.entry, item.index))

    def _select_index(self, index: int) -> None:
        """Select item at index, wrapping around."""
        if not self._items:
            return

        # Wrap around
        index = index % len(self._items)

        # Deselect old
        if 0 <= self._selected_index < len(self._items):
            self._items[self._selected_index].deselect()

        # Select new
        self._selected_index = index
        if 0 <= index < len(self._items):
            self._items[index].select()
            self._items[index].scroll_visible()
