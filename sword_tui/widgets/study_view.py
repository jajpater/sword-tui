"""3-pane study view widget for Bible study."""

from typing import List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message

from sword_tui.data.types import CrossReference, VerseSegment
from sword_tui.backend.commentary import CommentaryEntry


class StudyVerseChanged(Message):
    """Message sent when the study verse changes."""

    def __init__(self, book: str, chapter: int, verse: int) -> None:
        self.book = book
        self.chapter = chapter
        self.verse = verse
        super().__init__()


class StudyGotoRef(Message):
    """Message sent when user wants to navigate to a cross-reference."""

    def __init__(self, crossref: CrossReference) -> None:
        self.crossref = crossref
        super().__init__()


class BiblePane(Widget):
    """Left pane: Bible text display."""

    DEFAULT_CSS = """
    BiblePane {
        width: 1fr;
        height: 100%;
        border-right: solid $primary;
    }

    BiblePane #bible-pane-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    BiblePane.active-pane #bible-pane-header {
        background: $primary;
        color: $text;
        text-style: bold reverse;
    }

    BiblePane #bible-pane-scroll {
        height: 100%;
    }

    BiblePane .verse-row {
        padding: 0 1;
    }

    BiblePane .verse-row.current {
        background: $primary-darken-2;
    }

    BiblePane .verse-num {
        color: $text-muted;
        min-width: 4;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._module = ""
        self._book = ""
        self._chapter = 0
        self._current_verse = 1
        self._verses: List[VerseSegment] = []

    def compose(self) -> ComposeResult:
        yield Static("Bijbeltekst", id="bible-pane-header")
        yield VerticalScroll(id="bible-pane-scroll")

    def update_chapter(
        self,
        module: str,
        book: str,
        chapter: int,
        verses: List[VerseSegment],
        current_verse: int = 1,
    ) -> None:
        """Update the displayed chapter."""
        self._module = module
        self._book = book
        self._chapter = chapter
        self._verses = verses
        self._current_verse = current_verse

        # Update header
        header = self.query_one("#bible-pane-header", Static)
        header.update(f"{module} - {book} {chapter}")

        # Rebuild content directly in the scroll container
        scroll = self.query_one("#bible-pane-scroll", VerticalScroll)
        scroll.remove_children()

        for seg in verses:
            row = Static(classes="verse-row")
            text = Text()
            text.append(f"{seg.verse:3} ", style="dim")
            text.append(seg.text)
            row.update(text)
            if seg.verse == current_verse:
                row.add_class("current")
            scroll.mount(row)

        # Scroll to current verse after layout is complete
        if current_verse > 1:
            self.set_timer(0.15, self._scroll_to_current)

    def _scroll_to_current(self) -> None:
        """Scroll the bible pane to the current verse row."""
        scroll = self.query_one("#bible-pane-scroll", VerticalScroll)
        for row in self.query(".verse-row.current"):
            scroll.scroll_to_widget(row, animate=False)
            return

    def set_current_verse(self, verse: int) -> None:
        """Set the current verse (highlight it)."""
        self._current_verse = verse
        scroll = self.query_one("#bible-pane-scroll", VerticalScroll)

        # Update highlighting and scroll
        rows = list(self.query(".verse-row"))
        for i, row in enumerate(rows):
            if i < len(self._verses) and self._verses[i].verse == verse:
                row.add_class("current")
                scroll.scroll_to_widget(row, animate=False)
            else:
                row.remove_class("current")

    @property
    def current_verse(self) -> int:
        return self._current_verse


class CommentaryPane(Widget):
    """Middle pane: Commentary display."""

    DEFAULT_CSS = """
    CommentaryPane {
        width: 1fr;
        height: 100%;
        border-right: solid $primary;
    }

    CommentaryPane #commentary-pane-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    CommentaryPane.active-pane #commentary-pane-header {
        background: $primary;
        color: $text;
        text-style: bold reverse;
    }

    CommentaryPane #commentary-pane-scroll {
        height: 100%;
    }

    CommentaryPane #commentary-pane-scroll {
        padding: 1;
    }

    CommentaryPane .no-commentary {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }

    CommentaryPane .crossref-section {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $surface-lighten-1;
    }

    CommentaryPane .crossref-header {
        color: $primary;
        text-style: bold;
    }

    CommentaryPane .crossref-item {
        color: $secondary;
        padding-left: 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._module = ""
        self._entry: Optional[CommentaryEntry] = None

    def compose(self) -> ComposeResult:
        yield Static("Commentaar", id="commentary-pane-header")
        yield VerticalScroll(id="commentary-pane-scroll")

    def update_commentary(self, entry: Optional[CommentaryEntry]) -> None:
        """Update the displayed commentary."""
        self._entry = entry

        # Update header
        header = self.query_one("#commentary-pane-header", Static)
        if entry:
            header.update(f"{entry.module} - {entry.book} {entry.chapter}:{entry.verse}")
            self._module = entry.module
        else:
            header.update("Commentaar")

        # Rebuild content directly in scroll container
        scroll = self.query_one("#commentary-pane-scroll", VerticalScroll)
        scroll.remove_children()

        if not entry:
            scroll.mount(Static("Geen commentaar beschikbaar", classes="no-commentary"))
            return

        # Commentary text — for TSK with keyword groups, use Rich Text styling
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

            # Cross-references section (regular commentaries only)
            if entry.crossrefs:
                scroll.mount(Static("Verwijzingen:", classes="crossref-header"))
                for ref in entry.crossrefs:
                    scroll.mount(Static(f"→ {ref.reference}", classes="crossref-item"))

    @property
    def crossrefs(self) -> List[CrossReference]:
        """Get cross-references from current commentary."""
        if self._entry:
            return self._entry.crossrefs
        return []

    @property
    def module(self) -> str:
        return self._module


class CrossRefLookupPane(Widget):
    """Right pane: Looked-up cross-reference text."""

    DEFAULT_CSS = """
    CrossRefLookupPane {
        width: 1fr;
        height: 100%;
    }

    CrossRefLookupPane #xref-pane-header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }

    CrossRefLookupPane.active-pane #xref-pane-header {
        background: $primary;
        color: $text;
        text-style: bold reverse;
    }

    CrossRefLookupPane #xref-pane-scroll {
        height: 100%;
    }

    CrossRefLookupPane #xref-pane-status {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
        dock: bottom;
    }

    CrossRefLookupPane .xref-entry {
        padding: 0 1 1 1;
        border-bottom: solid $surface-lighten-1;
    }

    CrossRefLookupPane .xref-entry.selected {
        background: $primary-darken-2;
    }

    CrossRefLookupPane .xref-ref {
        color: $primary;
        text-style: bold;
    }

    CrossRefLookupPane .xref-text {
        padding-left: 1;
    }

    CrossRefLookupPane .no-refs {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refs: List[CrossReference] = []
        self._texts: List[str] = []  # Looked-up text for each ref
        self._selected_index = 0
        self._entries: List[Static] = []

    def compose(self) -> ComposeResult:
        yield Static("Cross-refs", id="xref-pane-header")
        yield VerticalScroll(id="xref-pane-scroll")
        yield Static("", id="xref-pane-status")

    def update_refs(
        self,
        refs: List[CrossReference],
        texts: List[str],
    ) -> None:
        """Update with looked-up cross-reference texts.

        Args:
            refs: List of cross-references
            texts: List of looked-up verse texts (same order as refs)
        """
        self._refs = refs
        self._texts = texts
        self._selected_index = 0
        self._entries = []

        # Update header
        header = self.query_one("#xref-pane-header", Static)
        header.update(f"Cross-refs ({len(refs)})")

        # Update status
        status = self.query_one("#xref-pane-status", Static)
        if refs:
            status.update("j/k: navigeer | Enter: ga naar")
        else:
            status.update("")

        # Rebuild content directly in scroll container
        scroll = self.query_one("#xref-pane-scroll", VerticalScroll)
        scroll.remove_children()

        if not refs:
            scroll.mount(Static("Geen verwijzingen", classes="no-refs"))
            return

        for i, (ref, text) in enumerate(zip(refs, texts)):
            content = Text()
            content.append(f"── {ref.reference} ──", style="bold cyan")
            display_text = text if text else "(tekst niet gevonden)"
            content.append(f"\n{display_text}", style="")

            entry = Static(content, classes="xref-entry")

            if i == 0:
                entry.add_class("selected")

            scroll.mount(entry)
            self._entries.append(entry)

    def next_ref(self) -> None:
        """Select next cross-reference."""
        if not self._entries:
            return
        self._select_index(self._selected_index + 1)

    def prev_ref(self) -> None:
        """Select previous cross-reference."""
        if not self._entries:
            return
        self._select_index(self._selected_index - 1)

    def _select_index(self, index: int) -> None:
        """Select entry at index."""
        if not self._entries:
            return

        index = index % len(self._entries)

        if 0 <= self._selected_index < len(self._entries):
            self._entries[self._selected_index].remove_class("selected")

        self._selected_index = index
        if 0 <= index < len(self._entries):
            self._entries[index].add_class("selected")
            scroll = self.query_one("#xref-pane-scroll", VerticalScroll)
            scroll.scroll_to_widget(self._entries[index])

    def get_selected_ref(self) -> Optional[CrossReference]:
        """Get the currently selected cross-reference."""
        if self._refs and 0 <= self._selected_index < len(self._refs):
            return self._refs[self._selected_index]
        return None

    def clear(self) -> None:
        """Clear the pane."""
        self._refs = []
        self._texts = []
        self._selected_index = 0
        self._entries = []
        self.query_one("#xref-pane-header", Static).update("Cross-refs")
        self.query_one("#xref-pane-status", Static).update("")
        self.query_one("#xref-pane-scroll", VerticalScroll).remove_children()

    def update_refs_grouped(
        self,
        refs: List[CrossReference],
        texts: List[str],
        keywords: list,
    ) -> None:
        """Update with keyword-grouped cross-references (TSK style).

        Args:
            refs: All cross-references (flat)
            texts: Verse texts (same order as refs)
            keywords: List of (start_index, keyword_text) tuples
        """
        self._refs = refs
        self._texts = texts
        self._selected_index = 0
        self._entries = []

        header = self.query_one("#xref-pane-header", Static)
        header.update(f"Cross-refs ({len(refs)})")

        status = self.query_one("#xref-pane-status", Static)
        status.update("j/k: navigeer | Enter: ga naar" if refs else "")

        scroll = self.query_one("#xref-pane-scroll", VerticalScroll)
        scroll.remove_children()

        if not refs:
            scroll.mount(Static("Geen verwijzingen", classes="no-refs"))
            return

        # Build a set of indices where keywords start
        kw_map = {idx: kw for idx, kw in keywords}

        for i, (ref, text) in enumerate(zip(refs, texts)):
            # Insert keyword header before its first ref
            if i in kw_map:
                kw_text = Text(kw_map[i], style="bold white")
                scroll.mount(Static(kw_text))

            content = Text()
            content.append(f"  {ref.reference}", style="bold cyan")
            display_text = text if text else "(tekst niet gevonden)"
            content.append(f"\n    {display_text}", style="")

            entry = Static(content, classes="xref-entry")

            if i == 0:
                entry.add_class("selected")

            scroll.mount(entry)
            self._entries.append(entry)


class StudyView(Widget):
    """3-pane study interface."""

    DEFAULT_CSS = """
    StudyView {
        width: 100%;
        height: 100%;
    }

    StudyView > Horizontal {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._active_pane = 0  # 0=bible, 1=commentary, 2=crossrefs

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield BiblePane(id="study-bible")
            yield CommentaryPane(id="study-commentary")
            yield CrossRefLookupPane(id="study-crossrefs")

    def on_mount(self) -> None:
        """Set initial active pane highlight."""
        self._update_active_class()

    @property
    def bible_pane(self) -> BiblePane:
        return self.query_one("#study-bible", BiblePane)

    @property
    def commentary_pane(self) -> CommentaryPane:
        return self.query_one("#study-commentary", CommentaryPane)

    @property
    def crossref_pane(self) -> CrossRefLookupPane:
        return self.query_one("#study-crossrefs", CrossRefLookupPane)

    @property
    def active_pane(self) -> int:
        return self._active_pane

    def set_active_pane(self, pane: int) -> None:
        """Set which pane is active (0, 1, or 2)."""
        self._active_pane = pane % 3
        self._update_active_class()

    def next_pane(self) -> None:
        """Move focus to next pane."""
        self._active_pane = (self._active_pane + 1) % 3
        self._update_active_class()

    def prev_pane(self) -> None:
        """Move focus to previous pane."""
        self._active_pane = (self._active_pane - 1) % 3
        self._update_active_class()

    def _update_active_class(self) -> None:
        """Toggle .active-pane class on the 3 pane widgets."""
        panes = [
            self.query_one("#study-bible", BiblePane),
            self.query_one("#study-commentary", CommentaryPane),
            self.query_one("#study-crossrefs", CrossRefLookupPane),
        ]
        for i, pane in enumerate(panes):
            if i == self._active_pane:
                pane.add_class("active-pane")
            else:
                pane.remove_class("active-pane")
