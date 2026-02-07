"""Book/chapter/verse picker widget."""

from typing import List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, ListView, ListItem, Static

from sword_tui.data.canon import search_books, book_chapters, CanonBook


class BookPicker(Widget):
    """Widget for selecting a Bible book, chapter, and optionally verse."""

    DEFAULT_CSS = """
    BookPicker {
        width: 50;
        height: 20;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    BookPicker > .picker-title {
        height: 1;
        text-style: bold;
        color: $primary;
    }

    BookPicker > .picker-input {
        height: 3;
        margin-bottom: 1;
    }

    BookPicker > .picker-list {
        height: 1fr;
    }

    BookPicker > .picker-hint {
        height: 1;
        color: $text-muted;
    }
    """

    class BookSelected(Message):
        """Message sent when a book/chapter is selected."""

        def __init__(self, book: str, chapter: int, verse: Optional[int] = None) -> None:
            self.book = book
            self.chapter = chapter
            self.verse = verse
            super().__init__()

    class Cancelled(Message):
        """Message sent when picker is cancelled."""

        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = "book"  # "book", "chapter", "verse"
        self._selected_book: Optional[str] = None
        self._selected_chapter: Optional[int] = None
        self._books: List[CanonBook] = []

    def compose(self) -> ComposeResult:
        yield Static("Ga naar...", classes="picker-title", id="picker-title")
        yield Input(placeholder="Boek zoeken...", classes="picker-input", id="picker-input")
        yield ListView(classes="picker-list", id="picker-list")
        yield Static("Enter=selecteer, Esc=annuleer", classes="picker-hint")

    def on_mount(self) -> None:
        """Initialize the picker."""
        self._update_book_list("")
        self.query_one("#picker-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for filtering."""
        if self._mode == "book":
            self._update_book_list(event.value)
        elif self._mode == "chapter":
            self._filter_chapters(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        event.stop()
        value = event.value.strip()

        if self._mode == "book":
            # Try to parse as "Book Chapter" or "Book Chapter:Verse"
            if self._try_parse_reference(value):
                return
            # Otherwise select first matching book
            self._select_first_book()
        elif self._mode == "chapter":
            self._select_chapter(value)
        elif self._mode == "verse":
            self._select_verse(value)

    def on_key(self, event) -> None:
        """Handle key events."""
        key = event.key

        if key == "escape":
            event.stop()
            self.post_message(self.Cancelled())
        elif key == "down":
            event.stop()
            lst = self.query_one("#picker-list", ListView)
            if lst.index is not None and lst.index < len(lst.children) - 1:
                lst.index += 1
        elif key == "up":
            event.stop()
            lst = self.query_one("#picker-list", ListView)
            if lst.index is not None and lst.index > 0:
                lst.index -= 1

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection."""
        event.stop()
        if self._mode == "book":
            # Get selected book
            idx = self.query_one("#picker-list", ListView).index
            if idx is not None and idx < len(self._books):
                self._selected_book = self._books[idx].name
                self._switch_to_chapter_mode()
        elif self._mode == "chapter":
            self._select_chapter_from_list()

    def _try_parse_reference(self, value: str) -> bool:
        """Try to parse a full reference like "Gen 1" or "Gen 1:5".

        Returns:
            True if successfully parsed and selected
        """
        import re

        # Pattern: "Book Chapter" or "Book Chapter:Verse"
        match = re.match(
            r"^(.+?)\s+(\d+)(?::(\d+))?$",
            value.strip()
        )
        if not match:
            return False

        book_query = match.group(1)
        chapter = int(match.group(2))
        verse = int(match.group(3)) if match.group(3) else None

        # Find matching book
        books = search_books(book_query, limit=1)
        if not books:
            return False

        book = books[0].name
        max_chapters = book_chapters(book)

        if chapter < 1 or chapter > max_chapters:
            return False

        self.post_message(self.BookSelected(book, chapter, verse))
        return True

    def _update_book_list(self, query: str) -> None:
        """Update the book list based on search query."""
        self._books = search_books(query, limit=15)
        lst = self.query_one("#picker-list", ListView)
        lst.clear()

        for book in self._books:
            text = Text()
            text.append(book.abbr.ljust(8), style="bold yellow")
            text.append(book.name)
            text.append(f" ({book.chapters}h)", style="dim")
            lst.append(ListItem(Static(text)))

        if self._books:
            lst.index = 0

    def _select_first_book(self) -> None:
        """Select the first book in the list."""
        if self._books:
            self._selected_book = self._books[0].name
            self._switch_to_chapter_mode()

    def _switch_to_chapter_mode(self) -> None:
        """Switch to chapter selection mode."""
        if not self._selected_book:
            return

        self._mode = "chapter"
        chapters = book_chapters(self._selected_book)

        self.query_one("#picker-title", Static).update(
            f"{self._selected_book} - Hoofdstuk"
        )
        inp = self.query_one("#picker-input", Input)
        inp.value = ""
        inp.placeholder = f"Hoofdstuk (1-{chapters})..."

        lst = self.query_one("#picker-list", ListView)
        lst.clear()

        # Show chapters in grid-like format
        for i in range(1, chapters + 1, 5):
            text = Text()
            for j in range(5):
                ch = i + j
                if ch <= chapters:
                    text.append(f"{ch:4}", style="bold cyan")
            lst.append(ListItem(Static(text)))

        lst.index = 0
        inp.focus()

    def _filter_chapters(self, value: str) -> None:
        """Filter chapter list based on input."""
        # For simplicity, we keep the grid but could filter here
        pass

    def _select_chapter(self, value: str) -> None:
        """Select a chapter by number."""
        if not self._selected_book:
            return

        try:
            chapter = int(value)
            max_chapters = book_chapters(self._selected_book)
            if 1 <= chapter <= max_chapters:
                self.post_message(self.BookSelected(self._selected_book, chapter))
        except ValueError:
            pass

    def _select_chapter_from_list(self) -> None:
        """Select chapter based on list position."""
        if not self._selected_book:
            return

        lst = self.query_one("#picker-list", ListView)
        if lst.index is not None:
            # Calculate chapter from grid position
            chapter = lst.index * 5 + 1
            max_chapters = book_chapters(self._selected_book)
            if chapter <= max_chapters:
                self.post_message(self.BookSelected(self._selected_book, chapter))

    def _select_verse(self, value: str) -> None:
        """Select a verse by number."""
        if not self._selected_book or not self._selected_chapter:
            return

        try:
            verse = int(value)
            if verse >= 1:
                self.post_message(
                    self.BookSelected(
                        self._selected_book,
                        self._selected_chapter,
                        verse
                    )
                )
        except ValueError:
            pass
