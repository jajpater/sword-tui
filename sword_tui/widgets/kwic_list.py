"""KWIC (Key Word In Context) search results list widget."""

from typing import List, Optional

from rich.text import Text
from textual.message import Message
from textual.widgets import ListView, ListItem, Static

from sword_tui.data.types import SearchHit


class KWICList(ListView):
    """List widget for displaying KWIC search results."""

    DEFAULT_CSS = """
    KWICList {
        width: 100%;
        height: 100%;
        background: $surface;
    }

    KWICList > ListItem {
        padding: 0 1;
        height: auto;
    }

    KWICList > ListItem.--highlight {
        background: $accent;
    }

    KWICList > ListItem.visual-selected {
        background: $secondary;
    }
    """

    class ResultSelected(Message):
        """Message sent when a search result is selected."""

        def __init__(self, hit: SearchHit) -> None:
            self.hit = hit
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._results: List[SearchHit] = []
        self._query = ""
        self._show_snippets = True
        self._visual_mode = False
        self._visual_start = 0

    def set_results(
        self, results: List[SearchHit], query: str, show_snippets: bool = True
    ) -> None:
        """Set the search results to display.

        Args:
            results: List of search hits
            query: The search query (for highlighting)
            show_snippets: Whether to show KWIC snippets or just references
        """
        self._results = results
        self._query = query
        self._show_snippets = show_snippets
        self._render_results()

    def clear_results(self) -> None:
        """Clear all results."""
        self._results = []
        self._query = ""
        self.clear()

    def get_selected_result(self) -> Optional[SearchHit]:
        """Get the currently selected result.

        Returns:
            Selected SearchHit or None
        """
        if self.index is not None and 0 <= self.index < len(self._results):
            return self._results[self.index]
        return None

    def move_up(self) -> Optional[SearchHit]:
        """Move selection up and return the new selection."""
        if self.index is not None and self.index > 0:
            self.index -= 1
            if self._visual_mode:
                self._update_visual_selection()
        return self.get_selected_result()

    def move_down(self) -> Optional[SearchHit]:
        """Move selection down and return the new selection."""
        if self.index is not None and self.index < len(self._results) - 1:
            self.index += 1
            if self._visual_mode:
                self._update_visual_selection()
        return self.get_selected_result()

    def select_current(self) -> None:
        """Select the current result and send message."""
        hit = self.get_selected_result()
        if hit:
            self.post_message(self.ResultSelected(hit))

    def set_visual_mode(self, enabled: bool) -> None:
        """Enable/disable visual selection mode.

        Args:
            enabled: Whether visual mode is active
        """
        self._visual_mode = enabled
        if enabled:
            self._visual_start = self.index or 0
            self._update_visual_selection()
        else:
            self._clear_visual_highlights()

    def get_visual_selection(self) -> List[SearchHit]:
        """Get all results in the visual selection range.

        Returns:
            List of selected SearchHit objects
        """
        if not self._visual_mode or self.index is None:
            hit = self.get_selected_result()
            return [hit] if hit else []

        start = min(self._visual_start, self.index)
        end = max(self._visual_start, self.index) + 1
        return self._results[start:end]

    def _render_results(self) -> None:
        """Render results as ListItems."""
        self.clear()

        for hit in self._results:
            text = self._format_result(hit)
            # Don't use IDs to avoid DuplicateIds error on re-render
            item = ListItem(Static(text))
            self.append(item)

        if self._results:
            self.index = 0

    def _format_result(self, hit: SearchHit) -> Text:
        """Format a search hit for display.

        Args:
            hit: SearchHit to format

        Returns:
            Rich Text object
        """
        text = Text()

        # Reference
        ref = f"{hit.book} {hit.chapter}:{hit.verse}"

        if not self._show_snippets:
            # Mode 2: Only show reference
            text.append(ref, style="bold cyan")
            return text

        # Mode 1 and 3: Show KWIC with highlighted match
        text.append(ref.ljust(20), style="bold cyan")

        # Snippet with highlighting
        if hit.snippet:
            snippet = hit.snippet
            if len(snippet) > 60:
                # Truncate long snippets, keeping match visible
                if hit.match_start > 30:
                    snippet = "..." + snippet[hit.match_start - 20:]
                    # Adjust match positions
                    offset = hit.match_start - 23
                    match_start = hit.match_start - offset
                    match_end = hit.match_end - offset
                else:
                    match_start = hit.match_start
                    match_end = hit.match_end

                if len(snippet) > 60:
                    snippet = snippet[:57] + "..."
            else:
                match_start = hit.match_start
                match_end = hit.match_end

            # Add snippet with highlighting
            if match_start > 0:
                text.append(snippet[:match_start])
            if match_end > match_start:
                text.append(
                    snippet[match_start:match_end],
                    style="bold black on yellow"
                )
            if match_end < len(snippet):
                text.append(snippet[match_end:])
        else:
            text.append("(laden...)", style="dim italic")

        return text

    def _update_visual_selection(self) -> None:
        """Update visual selection highlighting."""
        if self.index is None:
            return

        start = min(self._visual_start, self.index)
        end = max(self._visual_start, self.index)

        for i, child in enumerate(self.children):
            if isinstance(child, ListItem):
                if start <= i <= end:
                    child.add_class("visual-selected")
                else:
                    child.remove_class("visual-selected")

    def _clear_visual_highlights(self) -> None:
        """Clear all visual selection highlights."""
        for child in self.children:
            if isinstance(child, ListItem):
                child.remove_class("visual-selected")
