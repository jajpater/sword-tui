"""Parallel Bible view widget for comparing translations."""

from typing import List

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from sword_tui.data.types import VerseSegment
from sword_tui.widgets.bible_view import BibleView


class ParallelView(Widget):
    """Widget that shows two Bible translations side by side."""

    DEFAULT_CSS = """
    ParallelView {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    ParallelView > .pane {
        width: 1fr;
        height: 100%;
    }

    ParallelView > .pane-left {
        border-right: solid $primary;
    }

    ParallelView .pane-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    ParallelView .pane-scroll {
        height: 100%;
    }
    """

    def __init__(
        self,
        left_module: str = "",
        right_module: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._left_module = left_module
        self._right_module = right_module
        self._search_query = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="pane pane-left", id="pane-left"):
            yield Static(self._left_module, classes="pane-header", id="left-header")
            with VerticalScroll(classes="pane-scroll", id="left-scroll"):
                yield BibleView(id="left-view")

        with Vertical(classes="pane pane-right", id="pane-right"):
            yield Static(self._right_module, classes="pane-header", id="right-header")
            with VerticalScroll(classes="pane-scroll", id="right-scroll"):
                yield BibleView(id="right-view")

    def update_left(
        self,
        segments: List[VerseSegment],
        module: str,
        title: str = "",
    ) -> None:
        """Update the left pane content.

        Args:
            segments: Verse segments to display
            module: Module name for header
            title: Chapter title
        """
        self._left_module = module
        self.query_one("#left-header", Static).update(module)
        view = self.query_one("#left-view", BibleView)
        view.update_content(segments, title)
        if self._search_query:
            view.set_search_query(self._search_query)

    def update_right(
        self,
        segments: List[VerseSegment],
        module: str,
        title: str = "",
    ) -> None:
        """Update the right pane content.

        Args:
            segments: Verse segments to display
            module: Module name for header
            title: Chapter title
        """
        self._right_module = module
        self.query_one("#right-header", Static).update(module)
        view = self.query_one("#right-view", BibleView)
        view.update_content(segments, title)
        if self._search_query:
            view.set_search_query(self._search_query)

    def set_search_query(self, query: str = "") -> None:
        """Set search query for both panes.

        Args:
            query: Search term to highlight
        """
        self._search_query = query
        self.query_one("#left-view", BibleView).set_search_query(query)
        self.query_one("#right-view", BibleView).set_search_query(query)

    def set_show_strongs(self, show: bool) -> None:
        """Set whether to show Strong's numbers on both panes.

        Args:
            show: Whether to show Strong's numbers
        """
        self.query_one("#left-view", BibleView).set_show_strongs(show)
        self.query_one("#right-view", BibleView).set_show_strongs(show)

    def sync_scroll(self, scroll_y: float) -> None:
        """Synchronize scroll position of both panes.

        Args:
            scroll_y: Y scroll position
        """
        self.query_one("#left-scroll", VerticalScroll).scroll_y = scroll_y
        self.query_one("#right-scroll", VerticalScroll).scroll_y = scroll_y

    def focus_left(self) -> None:
        """Focus the left pane."""
        self.query_one("#left-scroll").focus()

    def focus_right(self) -> None:
        """Focus the right pane."""
        self.query_one("#right-scroll").focus()
