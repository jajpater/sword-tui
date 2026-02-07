"""KWIC search view with split-screen results."""

from typing import List, Optional

from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Static

from sword_tui.data.types import SearchHit
from sword_tui.widgets.kwic_list import KWICList
from sword_tui.widgets.bible_view import BibleView


class SearchView(Vertical):
    """Split-screen search results view with multiple display modes.

    Display modes:
        1: KWIC only - single pane with all KWIC results
        2: Refs + preview - refs list on left, chapter preview on right (default)
        3: KWIC + preview - KWIC list on left, chapter preview on right
    """

    DEFAULT_CSS = """
    SearchView {
        width: 100%;
        height: 100%;
    }

    SearchView #search-container {
        width: 100%;
        height: 100%;
    }

    SearchView .search-pane {
        width: 1fr;
        height: 100%;
    }

    SearchView .search-pane-full {
        width: 100%;
        height: 100%;
    }

    SearchView .search-pane-left {
        border-right: solid $primary;
    }

    SearchView .pane-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    SearchView #kwic-scroll {
        height: 100%;
    }

    SearchView #preview-scroll {
        height: 100%;
    }

    SearchView .hidden {
        display: none;
    }
    """

    class GotoResult(Message):
        """Message to navigate to a search result."""

        def __init__(self, hit: SearchHit) -> None:
            self.hit = hit
            super().__init__()

    class SearchClosed(Message):
        """Message when search view is closed."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._query = ""
        self._results: List[SearchHit] = []
        self._current_index = 0
        self._display_mode = 2  # Default: refs + preview

    def compose(self):
        """Create the search layout."""
        with Horizontal(id="search-container"):
            # Left pane: KWIC/refs results
            with Vertical(classes="search-pane search-pane-left", id="left-pane"):
                yield Static("Zoekresultaten", classes="pane-header", id="search-header")
                with VerticalScroll(id="kwic-scroll"):
                    yield KWICList(id="kwic-list")

            # Right pane: Preview (hidden in mode 1)
            with Vertical(classes="search-pane", id="preview-pane"):
                yield Static("Preview", classes="pane-header", id="preview-header")
                with VerticalScroll(id="preview-scroll"):
                    yield BibleView(id="preview-view")

    def set_display_mode(self, mode: int) -> None:
        """Set the display mode.

        Args:
            mode: 1=KWIC only, 2=refs+preview, 3=KWIC+preview
        """
        self._display_mode = mode
        self._update_layout()

        # Re-render results with new mode settings
        if self._results:
            # Update header
            header = self.query_one("#search-header", Static)
            mode_suffix = ""
            if self._display_mode == 1:
                mode_suffix = " [KWIC]"
            elif self._display_mode == 2:
                mode_suffix = " [Ref+Preview]"
            elif self._display_mode == 3:
                mode_suffix = " [KWIC+Preview]"
            header.update(f"Zoekresultaten: {len(self._results)} voor '{self._query}'{mode_suffix}")

            # Re-render KWIC list with new snippet setting
            kwic = self.query_one("#kwic-list", KWICList)
            kwic.set_results(self._results, self._query, show_snippets=(self._display_mode != 2))

    def _update_layout(self) -> None:
        """Update the layout based on display mode."""
        try:
            preview_pane = self.query_one("#preview-pane")
            left_pane = self.query_one("#left-pane")

            if self._display_mode == 1:
                # KWIC only - hide preview, full width for KWIC
                preview_pane.add_class("hidden")
                left_pane.remove_class("search-pane-left")
                left_pane.add_class("search-pane-full")
            else:
                # Modes 2 and 3 - show both panes
                preview_pane.remove_class("hidden")
                left_pane.remove_class("search-pane-full")
                left_pane.add_class("search-pane-left")
        except Exception:
            # Widget not yet mounted
            pass

    def set_results(self, results: List[SearchHit], query: str) -> None:
        """Set the search results.

        Args:
            results: List of search hits
            query: The search query
        """
        self._results = results
        self._query = query
        self._current_index = 0

        # Update header based on mode
        header = self.query_one("#search-header", Static)
        mode_suffix = ""
        if self._display_mode == 1:
            mode_suffix = " [KWIC]"
        elif self._display_mode == 2:
            mode_suffix = " [Ref+Preview]"
        elif self._display_mode == 3:
            mode_suffix = " [KWIC+Preview]"
        header.update(f"Zoekresultaten: {len(results)} voor '{query}'{mode_suffix}")

        # Populate KWIC list
        kwic = self.query_one("#kwic-list", KWICList)
        kwic.set_results(results, query, show_snippets=(self._display_mode != 2))

        # Update layout
        self._update_layout()

        # Show first result preview (for modes 2 and 3)
        if results and self._display_mode >= 2:
            self._show_preview(results[0])

    def clear_results(self) -> None:
        """Clear search results."""
        self._results = []
        self._query = ""
        self.query_one("#kwic-list", KWICList).clear_results()
        self.query_one("#search-header", Static).update("Zoekresultaten")
        self.query_one("#preview-header", Static).update("Preview")

    def move_up(self) -> None:
        """Move to previous result."""
        kwic = self.query_one("#kwic-list", KWICList)
        hit = kwic.move_up()
        if hit:
            self._current_index = kwic.index or 0
            self._show_preview(hit)

    def move_down(self) -> None:
        """Move to next result."""
        kwic = self.query_one("#kwic-list", KWICList)
        hit = kwic.move_down()
        if hit:
            self._current_index = kwic.index or 0
            self._show_preview(hit)

    def select_current(self) -> None:
        """Go to the currently selected result."""
        kwic = self.query_one("#kwic-list", KWICList)
        hit = kwic.get_selected_result()
        if hit:
            self.post_message(self.GotoResult(hit))

    def get_current_hit(self) -> Optional[SearchHit]:
        """Get the currently selected hit."""
        kwic = self.query_one("#kwic-list", KWICList)
        return kwic.get_selected_result()

    def _show_preview(self, hit: SearchHit) -> None:
        """Show preview of a search hit.

        Args:
            hit: SearchHit to preview
        """
        # Update preview header
        header = self.query_one("#preview-header", Static)
        header.update(f"{hit.book} {hit.chapter}")

        # The preview will be populated by the app with chapter context
        # For now, just show the verse
        preview = self.query_one("#preview-view", BibleView)

        # Create a segment for preview
        from sword_tui.data.types import VerseSegment
        if hit.snippet:
            seg = VerseSegment(hit.book, hit.chapter, hit.verse, hit.snippet)
            preview.update_content([seg], f"{hit.book} {hit.chapter}")
            preview.set_search_query(self._query)

    def update_preview_context(self, segments, title: str) -> None:
        """Update preview with full chapter context.

        Args:
            segments: List of VerseSegment for the chapter
            title: Title to show
        """
        preview = self.query_one("#preview-view", BibleView)
        preview.update_content(segments, title)
        preview.set_search_query(self._query)

        # Scroll to the matching verse
        hit = self.get_current_hit()
        if hit:
            preview.move_to_verse(hit.verse)
