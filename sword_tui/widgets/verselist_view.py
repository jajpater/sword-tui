"""VerseList view widget — 2/3-pane study tool."""

from typing import TYPE_CHECKING, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message

from sword_tui.data.types import VerseList, VerseRef, VerseSegment

if TYPE_CHECKING:
    from sword_tui.backend.diatheke import DiathekeBackend


class VerseListGotoRef(Message):
    """Message sent when user wants to navigate to a verse from the list."""

    def __init__(self, ref: VerseRef) -> None:
        self.ref = ref
        super().__init__()


class VerseListDeleteRef(Message):
    """Message sent when user wants to delete a ref from the list."""

    def __init__(self, index: int) -> None:
        self.index = index
        super().__init__()


class RefListItem(Static):
    """A single verse reference in the list pane."""

    DEFAULT_CSS = """
    RefListItem {
        width: 100%;
        padding: 0 1;
        background: $surface;
    }

    RefListItem:hover {
        background: $surface-lighten-1;
    }

    RefListItem.selected {
        background: $primary-darken-1;
    }
    """

    def __init__(self, ref: VerseRef, index: int, **kwargs):
        super().__init__("", **kwargs)
        self._ref = ref
        self._index = index
        self._render()

    def _render(self) -> None:
        text = Text()
        text.append(f"{self._index + 1:3}. ", style="dim")
        text.append(self._ref.reference, style="bold cyan")
        self.update(text)

    @property
    def ref(self) -> VerseRef:
        return self._ref

    @property
    def index(self) -> int:
        return self._index

    def select(self) -> None:
        self.add_class("selected")

    def deselect(self) -> None:
        self.remove_class("selected")


class RefListPane(Widget):
    """Left pane: list of verse references."""

    DEFAULT_CSS = """
    RefListPane {
        width: 1fr;
        min-width: 25;
        max-width: 35;
        height: 100%;
        border-right: solid $primary;
    }

    RefListPane #reflist-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    RefListPane.active-pane #reflist-header {
        background: $primary;
        text-style: bold reverse;
    }

    RefListPane #reflist-scroll {
        height: 100%;
    }

    RefListPane .no-refs {
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._items: List[RefListItem] = []
        self._selected_index: int = 0

    def compose(self) -> ComposeResult:
        yield Static("Verselist", id="reflist-header")
        yield VerticalScroll(id="reflist-scroll")

    def load_refs(self, name: str, refs: List[VerseRef]) -> None:
        """Load the list of verse references."""
        self._selected_index = 0
        self._items = []

        header = self.query_one("#reflist-header", Static)
        header.update(f"{name} ({len(refs)})")

        scroll = self.query_one("#reflist-scroll", VerticalScroll)
        scroll.remove_children()

        if not refs:
            scroll.mount(Static("Geen verzen", classes="no-refs"))
            return

        for i, ref in enumerate(refs):
            item = RefListItem(ref, i)
            if i == 0:
                item.select()
            scroll.mount(item)
            self._items.append(item)

    def next_item(self) -> Optional[VerseRef]:
        """Select next item, return its ref."""
        if not self._items:
            return None
        return self._select_index(self._selected_index + 1)

    def prev_item(self) -> Optional[VerseRef]:
        """Select previous item, return its ref."""
        if not self._items:
            return None
        return self._select_index(self._selected_index - 1)

    def get_selected_ref(self) -> Optional[VerseRef]:
        """Get currently selected ref."""
        if self._items and 0 <= self._selected_index < len(self._items):
            return self._items[self._selected_index].ref
        return None

    @property
    def selected_index(self) -> int:
        return self._selected_index

    def _select_index(self, index: int) -> Optional[VerseRef]:
        """Select item at index (wrapping)."""
        if not self._items:
            return None
        index = index % len(self._items)
        if 0 <= self._selected_index < len(self._items):
            self._items[self._selected_index].deselect()
        self._selected_index = index
        if 0 <= index < len(self._items):
            self._items[index].select()
            self._items[index].scroll_visible()
            return self._items[index].ref
        return None


class VerseBiblePane(Widget):
    """Middle pane: Bible text for the selected verse."""

    DEFAULT_CSS = """
    VerseBiblePane {
        width: 2fr;
        height: 100%;
        border-right: solid $primary;
    }

    VerseBiblePane #verse-bible-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    VerseBiblePane.active-pane #verse-bible-header {
        background: $primary;
        text-style: bold reverse;
    }

    VerseBiblePane #verse-bible-scroll {
        height: 100%;
        padding: 1;
    }

    VerseBiblePane .verse-row {
        padding: 0 1;
    }

    VerseBiblePane .verse-row.current {
        background: $primary-darken-2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._verses: List[VerseSegment] = []
        self._current_verse = 0

    def compose(self) -> ComposeResult:
        yield Static("Bijbeltekst", id="verse-bible-header")
        yield VerticalScroll(id="verse-bible-scroll")

    def show_chapter(
        self,
        module: str,
        book: str,
        chapter: int,
        verses: List[VerseSegment],
        highlight_verse: int = 0,
    ) -> None:
        """Show a chapter with one verse highlighted."""
        self._verses = verses
        self._current_verse = highlight_verse

        header = self.query_one("#verse-bible-header", Static)
        header.update(f"{module} — {book} {chapter}")

        scroll = self.query_one("#verse-bible-scroll", VerticalScroll)
        scroll.remove_children()

        for seg in verses:
            row = Static(classes="verse-row")
            text = Text()
            text.append(f"{seg.verse:3} ", style="dim")
            text.append(seg.text)
            row.update(text)
            if seg.verse == highlight_verse:
                row.add_class("current")
            scroll.mount(row)

        if highlight_verse > 1:
            self.set_timer(0.15, self._scroll_to_current)

    def _scroll_to_current(self) -> None:
        scroll = self.query_one("#verse-bible-scroll", VerticalScroll)
        for row in self.query(".verse-row.current"):
            scroll.scroll_to_widget(row, animate=False)
            return

    def clear(self) -> None:
        self.query_one("#verse-bible-header", Static).update("Bijbeltekst")
        self.query_one("#verse-bible-scroll", VerticalScroll).remove_children()


class VerseCommentaryPane(Widget):
    """Right pane (optional): commentary for the selected verse."""

    DEFAULT_CSS = """
    VerseCommentaryPane {
        width: 1fr;
        height: 100%;
    }

    VerseCommentaryPane #verse-comm-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    VerseCommentaryPane.active-pane #verse-comm-header {
        background: $primary;
        text-style: bold reverse;
    }

    VerseCommentaryPane #verse-comm-scroll {
        height: 100%;
        padding: 1;
    }

    VerseCommentaryPane .no-commentary {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Static("Commentaar", id="verse-comm-header")
        yield VerticalScroll(id="verse-comm-scroll")

    def update_commentary(self, entry) -> None:
        """Update commentary display."""
        header = self.query_one("#verse-comm-header", Static)
        scroll = self.query_one("#verse-comm-scroll", VerticalScroll)
        scroll.remove_children()

        if not entry:
            header.update("Commentaar")
            scroll.mount(Static("Geen commentaar beschikbaar", classes="no-commentary"))
            return

        header.update(f"{entry.module} — {entry.book} {entry.chapter}:{entry.verse}")
        if entry.keyword_groups:
            for g in entry.keyword_groups:
                kw_text = Text(g.keyword, style="bold white")
                scroll.mount(Static(kw_text))
                for r in g.refs:
                    ref_text = Text(f"  {r.reference}", style="cyan")
                    scroll.mount(Static(ref_text))
                scroll.mount(Static(""))
        else:
            scroll.mount(Static(entry.text))

    def clear(self) -> None:
        self.query_one("#verse-comm-header", Static).update("Commentaar")
        self.query_one("#verse-comm-scroll", VerticalScroll).remove_children()


class VerseListView(Widget):
    """2/3-pane verse list study view."""

    DEFAULT_CSS = """
    VerseListView {
        width: 100%;
        height: 100%;
    }

    VerseListView > Horizontal {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._active_pane = 0  # 0=reflist, 1=bible, 2=commentary
        self._show_commentary = False
        self._verselist: Optional[VerseList] = None
        self._backend: Optional["DiathekeBackend"] = None
        self._commentary_backend = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield RefListPane(id="vl-reflist")
            yield VerseBiblePane(id="vl-bible")
            yield VerseCommentaryPane(id="vl-commentary")

    def on_mount(self) -> None:
        self.query_one("#vl-commentary").display = False
        self._update_active_class()

    @property
    def reflist_pane(self) -> RefListPane:
        return self.query_one("#vl-reflist", RefListPane)

    @property
    def bible_pane(self) -> VerseBiblePane:
        return self.query_one("#vl-bible", VerseBiblePane)

    @property
    def commentary_pane(self) -> VerseCommentaryPane:
        return self.query_one("#vl-commentary", VerseCommentaryPane)

    def load_verselist(self, vl: VerseList, backend: "DiathekeBackend") -> None:
        """Load a verse list and show it."""
        self._verselist = vl
        self._backend = backend
        self.reflist_pane.load_refs(vl.name, vl.refs)
        # Show first ref
        if vl.refs:
            self._show_ref(vl.refs[0])

    def _show_ref(self, ref: VerseRef) -> None:
        """Show the verse text for a given ref."""
        if not self._backend:
            return
        segments = self._backend.lookup_chapter(ref.book, ref.chapter)
        module = self._backend._module if hasattr(self._backend, '_module') else ""
        self.bible_pane.show_chapter(module, ref.book, ref.chapter, segments, ref.verse)

    def next_ref(self) -> None:
        """Navigate to next ref in list."""
        ref = self.reflist_pane.next_item()
        if ref:
            self._show_ref(ref)

    def prev_ref(self) -> None:
        """Navigate to prev ref in list."""
        ref = self.reflist_pane.prev_item()
        if ref:
            self._show_ref(ref)

    def get_selected_ref(self) -> Optional[VerseRef]:
        """Get the currently selected ref."""
        return self.reflist_pane.get_selected_ref()

    def get_selected_index(self) -> int:
        """Get index of selected ref."""
        return self.reflist_pane.selected_index

    def next_pane(self) -> None:
        """Move focus to next pane."""
        max_pane = 2 if self._show_commentary else 1
        self._active_pane = (self._active_pane + 1) % (max_pane + 1)
        self._update_active_class()

    def toggle_commentary(self) -> None:
        """Toggle commentary pane visibility."""
        self._show_commentary = not self._show_commentary
        self.query_one("#vl-commentary").display = self._show_commentary
        if not self._show_commentary and self._active_pane == 2:
            self._active_pane = 0
        self._update_active_class()

    def set_commentary_backend(self, backend) -> None:
        """Set the commentary backend for the commentary pane."""
        self._commentary_backend = backend

    def update_commentary_for_ref(self, ref: VerseRef) -> None:
        """Look up and display commentary for a ref."""
        if not self._commentary_backend or not self._show_commentary:
            return
        entry = self._commentary_backend.lookup(ref.book, ref.chapter, ref.verse)
        self.commentary_pane.update_commentary(entry)

    @property
    def active_pane(self) -> int:
        return self._active_pane

    def _update_active_class(self) -> None:
        panes = [
            self.query_one("#vl-reflist", RefListPane),
            self.query_one("#vl-bible", VerseBiblePane),
        ]
        if self._show_commentary:
            panes.append(self.query_one("#vl-commentary", VerseCommentaryPane))

        for i, pane in enumerate(panes):
            if i == self._active_pane:
                pane.add_class("active-pane")
            else:
                pane.remove_class("active-pane")
