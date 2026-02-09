"""Cross-reference view widget for displaying related verses."""

from typing import List, Optional, Tuple

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message

from sword_tui.data.types import CrossReference


class CrossRefSelected(Message):
    """Message sent when a cross-reference is selected for navigation."""

    def __init__(self, crossref: CrossReference) -> None:
        self.crossref = crossref
        super().__init__()


class SourceHeader(Static):
    """Header widget showing source module name."""

    DEFAULT_CSS = """
    SourceHeader {
        width: 100%;
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
        margin-top: 1;
    }
    """

    def __init__(self, source: str, **kwargs):
        super().__init__("", **kwargs)
        self._source = source
        self._render_header()

    def _render_header(self) -> None:
        text = Text()
        text.append("── ", style="dim")
        text.append(self._source, style="bold")
        text.append(" ──", style="dim")
        self.update(text)


class CrossRefItem(Static):
    """Widget displaying a single cross-reference entry."""

    DEFAULT_CSS = """
    CrossRefItem {
        width: 100%;
        padding: 0 1;
        background: $surface;
    }

    CrossRefItem:hover {
        background: $surface-lighten-1;
    }

    CrossRefItem.selected {
        background: $primary-darken-1;
    }
    """

    def __init__(self, crossref: CrossReference, index: int, source: str = "", **kwargs):
        super().__init__("", **kwargs)
        self._crossref = crossref
        self._index = index
        self._source = source
        self._render_item()

    def _render_item(self) -> None:
        """Render the cross-reference item."""
        text = Text()

        # Reference
        text.append(self._crossref.reference, style="bold cyan")

        # Preview if available
        if self._crossref.preview:
            text.append("\n")
            text.append(self._crossref.preview, style="dim")

        self.update(text)

    @property
    def crossref(self) -> CrossReference:
        """Get the cross-reference."""
        return self._crossref

    @property
    def index(self) -> int:
        """Get the index of this item."""
        return self._index

    @property
    def source(self) -> str:
        """Get the source module."""
        return self._source

    def select(self) -> None:
        """Mark this item as selected."""
        self.add_class("selected")

    def deselect(self) -> None:
        """Remove selection from this item."""
        self.remove_class("selected")


class CrossRefView(Widget):
    """Widget showing cross-references for the current verse."""

    DEFAULT_CSS = """
    CrossRefView {
        width: 100%;
        height: 100%;
        background: $surface;
    }

    CrossRefView > #crossref-scroll {
        height: 100%;
    }

    CrossRefView > #crossref-header {
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        padding: 0 1;
    }

    CrossRefView #crossref-status {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
        text-style: italic;
    }

    CrossRefView .entry-container {
        width: 100%;
        padding: 0 0 1 0;
    }

    CrossRefView .no-refs {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        ("j", "next_item", "Next"),
        ("k", "prev_item", "Previous"),
        ("enter", "select_item", "Go to"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_ref: str = ""
        self._crossrefs: List[Tuple[CrossReference, str]] = []  # (ref, source) tuples
        self._selected_index: int = 0
        self._items: List[CrossRefItem] = []  # Cache of CrossRefItem widgets

    def compose(self) -> ComposeResult:
        yield Static("Cross-References", id="crossref-header")
        with VerticalScroll(id="crossref-scroll"):
            yield Vertical(id="crossref-content")
        yield Static("", id="crossref-status")

    def update_crossrefs(
        self,
        source_ref: str,
        crossrefs: List[Tuple[CrossReference, str]],
    ) -> None:
        """Update the displayed cross-references.

        Args:
            source_ref: The source verse reference
            crossrefs: List of (CrossReference, source_module) tuples
        """
        self._current_ref = source_ref
        self._crossrefs = crossrefs
        self._selected_index = 0

        # Update header
        header = self.query_one("#crossref-header", Static)
        if source_ref:
            header.update(f"Cross-refs: {source_ref}")
        else:
            header.update("Cross-References")

        # Update status
        status = self.query_one("#crossref-status", Static)
        if crossrefs:
            # Count unique sources
            sources = set(src for _, src in crossrefs)
            source_info = f" uit {len(sources)} bron(nen)" if len(sources) > 1 else ""
            status.update(f"{len(crossrefs)} refs{source_info} | j/k nav | Enter ga naar")
        else:
            status.update("")

        # Clear and rebuild content
        content = self.query_one("#crossref-content", Vertical)
        content.remove_children()

        if not crossrefs:
            if source_ref:
                content.mount(Static("Geen cross-references gevonden", classes="no-refs"))
            self._items = []
            return

        # Group by source and add items
        self._items = []
        current_source = None
        item_index = 0
        for xref, source in crossrefs:
            # Add source header when source changes
            if source != current_source:
                content.mount(SourceHeader(source))
                current_source = source

            item = CrossRefItem(xref, item_index, source)
            if item_index == 0:
                item.select()
            content.mount(item)
            self._items.append(item)
            item_index += 1

    def clear(self) -> None:
        """Clear the view."""
        self._current_ref = ""
        self._crossrefs = []
        self._selected_index = 0
        self._items = []
        self.query_one("#crossref-header", Static).update("Cross-References")
        self.query_one("#crossref-status", Static).update("")
        self.query_one("#crossref-content", Vertical).remove_children()

    def action_next_item(self) -> None:
        """Move to next cross-reference."""
        if not self._crossrefs:
            return
        self._select_index(self._selected_index + 1)

    def action_prev_item(self) -> None:
        """Move to previous cross-reference."""
        if not self._crossrefs:
            return
        self._select_index(self._selected_index - 1)

    def action_select_item(self) -> None:
        """Select the current cross-reference for navigation."""
        if not self._crossrefs:
            return
        if 0 <= self._selected_index < len(self._crossrefs):
            xref, _ = self._crossrefs[self._selected_index]
            self.post_message(CrossRefSelected(xref))

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
            # Scroll into view
            self._items[index].scroll_visible()

    @property
    def current_ref(self) -> str:
        """Get the current source reference."""
        return self._current_ref

    @property
    def crossrefs(self) -> List[Tuple[CrossReference, str]]:
        """Get the current cross-references."""
        return self._crossrefs

    @property
    def selected_crossref(self) -> Optional[CrossReference]:
        """Get the currently selected cross-reference."""
        if self._crossrefs and 0 <= self._selected_index < len(self._crossrefs):
            return self._crossrefs[self._selected_index][0]
        return None
