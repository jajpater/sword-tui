"""Main Textual application for sword-tui."""

from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Header

from sword_tui.backend import DiathekeBackend, get_installed_modules
from sword_tui.commands import CommandHandler, parse_command
from sword_tui.data import (
    BOOK_ORDER,
    book_chapters,
    book_index,
    VerseSegment,
)
from sword_tui.widgets import (
    BibleView,
    BookPicker,
    CommandInput,
    ModulePicker,
    StatusBar,
)


class SwordApp(App):
    """Bible TUI application using SWORD/diatheke backend."""

    TITLE = "Sword-TUI"
    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("j", "next_verse", "Next verse", show=False),
        Binding("k", "prev_verse", "Prev verse", show=False),
        Binding("g", "goto", "Goto", show=False),
        Binding("G", "goto_verse", "Goto verse", show=False),
        Binding("m", "module_picker", "Module", show=False),
        Binding("v", "visual_mode", "Visual", show=False),
        Binding("y", "yank", "Copy", show=False),
        Binding("Y", "yank_chapter", "Copy chapter", show=False),
        Binding("b", "bookmark", "Bookmark", show=False),
        Binding("'", "show_bookmarks", "Bookmarks", show=False),
        Binding("escape", "escape", "Escape", show=False),
        Binding("right_square_bracket", "next_chapter", "Next chapter", show=False),
        Binding("left_square_bracket", "prev_chapter", "Prev chapter", show=False),
        Binding("}", "next_book", "Next book", show=False),
        Binding("{", "prev_book", "Prev book", show=False),
        Binding("ctrl+d", "page_down", "Page down", show=False),
        Binding("ctrl+u", "page_up", "Page up", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()

        # State
        self._current_book = "Genesis"
        self._current_chapter = 1
        self._current_module = "DutSVV"

        # Mode flags
        self._in_command_mode = False
        self._in_visual_mode = False
        self._in_picker_mode = False

        # Digit buffer for numeric input (e.g., "5G" to go to verse 5)
        self._digit_buffer = ""

        # Backend
        self._backend = DiathekeBackend(self._current_module)

        # Command handler (initialized after mount)
        self._command_handler: Optional[CommandHandler] = None

        # Detect available modules
        modules = get_installed_modules()
        if modules:
            self._current_module = modules[0].name
            self._backend.set_module(self._current_module)

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        with VerticalScroll(id="bible-scroll"):
            yield BibleView(id="bible-view")
        yield CommandInput(
            commands=["quit", "help", "module", "export", "goto"],
            id="command-input",
        )
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        self._command_handler = CommandHandler(self)

        # Hide command input
        self.query_one("#command-input").display = False

        # Load initial content
        self._load_chapter()

        # Focus the main scroll area
        self.query_one("#bible-scroll").focus()

    def on_key(self, event) -> None:
        """Handle key events centrally."""
        if self._in_command_mode or self._in_picker_mode:
            return

        key = event.key
        char = event.character

        # Handle digits for numeric input (e.g., "12G" goes to verse 12)
        if char and char.isdigit():
            self._digit_buffer += char
            return

        # Handle special keys with digit prefix
        if self._digit_buffer and char == "G":
            verse = int(self._digit_buffer)
            self._digit_buffer = ""
            self._goto_verse(verse)
            event.stop()
            return

        # Clear digit buffer on other keys
        self._digit_buffer = ""

        # Handle colon and slash for command/search mode
        if char == ":":
            event.stop()
            self._enter_command_mode()
        elif char == "/":
            event.stop()
            self._enter_search_mode()

    # ==================== Actions ====================

    def action_next_verse(self) -> None:
        """Move to next verse."""
        view = self.query_one("#bible-view", BibleView)
        if not view.next_verse():
            # At end of chapter, go to next chapter
            self.action_next_chapter()
        self._update_status()

    def action_prev_verse(self) -> None:
        """Move to previous verse."""
        view = self.query_one("#bible-view", BibleView)
        if not view.prev_verse():
            # At start of chapter, go to previous chapter (last verse)
            if self._current_chapter > 1:
                self._current_chapter -= 1
                self._load_chapter()
                view.last_verse()
            elif book_index(self._current_book) > 0:
                self._current_book = BOOK_ORDER[book_index(self._current_book) - 1]
                self._current_chapter = book_chapters(self._current_book)
                self._load_chapter()
                view.last_verse()
        self._update_status()

    def action_next_chapter(self) -> None:
        """Go to next chapter, verse 1."""
        max_chapters = book_chapters(self._current_book)
        if self._current_chapter < max_chapters:
            self._current_chapter += 1
            self._load_chapter()
        else:
            self.action_next_book()

    def action_prev_chapter(self) -> None:
        """Go to previous chapter, verse 1."""
        if self._current_chapter > 1:
            self._current_chapter -= 1
            self._load_chapter()
        else:
            # Go to previous book, last chapter
            idx = book_index(self._current_book)
            if idx > 0:
                self._current_book = BOOK_ORDER[idx - 1]
                self._current_chapter = book_chapters(self._current_book)
                self._load_chapter()

    def action_next_book(self) -> None:
        """Go to next book, chapter 1, verse 1."""
        idx = book_index(self._current_book)
        if idx < len(BOOK_ORDER) - 1:
            self._current_book = BOOK_ORDER[idx + 1]
            self._current_chapter = 1
            self._load_chapter()

    def action_prev_book(self) -> None:
        """Go to previous book, chapter 1, verse 1."""
        idx = book_index(self._current_book)
        if idx > 0:
            self._current_book = BOOK_ORDER[idx - 1]
            self._current_chapter = 1
            self._load_chapter()

    def action_goto(self) -> None:
        """Open goto dialog."""
        self._in_picker_mode = True
        picker = BookPicker(id="book-picker")
        self.mount(picker)
        picker.focus()

    def action_goto_verse(self) -> None:
        """Go to last verse (G without number)."""
        view = self.query_one("#bible-view", BibleView)
        view.last_verse()
        self._update_status()

    def _goto_verse(self, verse: int) -> None:
        """Go to specific verse number."""
        view = self.query_one("#bible-view", BibleView)
        view.move_to_verse(verse)
        self._update_status()

    def action_visual_mode(self) -> None:
        """Toggle visual selection mode."""
        view = self.query_one("#bible-view", BibleView)
        if self._in_visual_mode:
            view.end_visual_mode()
            self._in_visual_mode = False
            self.query_one("#status-bar", StatusBar).set_mode("normal")
        else:
            view.start_visual_mode()
            self._in_visual_mode = True
            self.query_one("#status-bar", StatusBar).set_mode("visual")
        self._update_status()

    def action_escape(self) -> None:
        """Handle escape key."""
        if self._in_visual_mode:
            view = self.query_one("#bible-view", BibleView)
            view.end_visual_mode()
            self._in_visual_mode = False
            self.query_one("#status-bar", StatusBar).set_mode("normal")
            self._update_status()

    def action_yank(self) -> None:
        """Copy current verse or visual selection."""
        view = self.query_one("#bible-view", BibleView)
        text = view.get_selected_text()

        try:
            import pyperclip
            pyperclip.copy(text)

            segments = view.get_selected_segments()
            if len(segments) == 1:
                msg = f"Gekopieerd: {self._current_book} {self._current_chapter}:{segments[0].verse}"
            else:
                start, end = view.get_visual_range()
                msg = f"Gekopieerd: {self._current_book} {self._current_chapter}:{start}-{end}"
            self.query_one("#status-bar", StatusBar).show_message(msg)
        except ImportError:
            self.query_one("#status-bar", StatusBar).show_message("pyperclip niet beschikbaar")

        # Exit visual mode after yank
        if self._in_visual_mode:
            view.end_visual_mode()
            self._in_visual_mode = False
            self.query_one("#status-bar", StatusBar).set_mode("normal")

    def action_yank_chapter(self) -> None:
        """Copy entire chapter."""
        view = self.query_one("#bible-view", BibleView)
        text = view.get_all_text()

        try:
            import pyperclip
            pyperclip.copy(text)
            self.query_one("#status-bar", StatusBar).show_message(
                f"Gekopieerd: {self._current_book} {self._current_chapter} (heel hoofdstuk)"
            )
        except ImportError:
            self.query_one("#status-bar", StatusBar).show_message("pyperclip niet beschikbaar")

    def action_bookmark(self) -> None:
        """Bookmark current verse or visual selection."""
        view = self.query_one("#bible-view", BibleView)
        start, end = view.get_visual_range()

        if start == end:
            ref = f"{self._current_book} {self._current_chapter}:{start}"
        else:
            ref = f"{self._current_book} {self._current_chapter}:{start}-{end}"

        # Add bookmark via command handler
        if self._command_handler:
            from sword_tui.data.types import Bookmark
            bookmark = Bookmark(
                name=ref,
                book=self._current_book,
                chapter=self._current_chapter,
                verse=start,
                module=self._current_module,
            )
            self._command_handler._bookmarks.append(bookmark)
            self._command_handler._save_bookmarks()
            self.query_one("#status-bar", StatusBar).show_message(f"Bookmark: {ref}")

        # Exit visual mode after bookmark
        if self._in_visual_mode:
            view.end_visual_mode()
            self._in_visual_mode = False
            self.query_one("#status-bar", StatusBar).set_mode("normal")

    def action_show_bookmarks(self) -> None:
        """Show bookmarks list."""
        if self._command_handler:
            bookmarks = self._command_handler.get_bookmarks()
            if not bookmarks:
                self.query_one("#status-bar", StatusBar).show_message("Geen bookmarks")
            else:
                # Show first few bookmarks in status bar for now
                refs = [bm.reference for bm in bookmarks[:5]]
                self.query_one("#status-bar", StatusBar).show_message(
                    f"Bookmarks: {', '.join(refs)}"
                )

    def action_module_picker(self) -> None:
        """Open module picker."""
        self._in_picker_mode = True
        picker = ModulePicker(current_module=self._current_module, id="module-picker")
        self.mount(picker)
        picker.focus()

    def action_page_down(self) -> None:
        """Page down (move multiple verses)."""
        view = self.query_one("#bible-view", BibleView)
        for _ in range(10):
            if not view.next_verse():
                break
        self._update_status()

    def action_page_up(self) -> None:
        """Page up (move multiple verses)."""
        view = self.query_one("#bible-view", BibleView)
        for _ in range(10):
            if not view.prev_verse():
                break
        self._update_status()

    # ==================== Command Mode ====================

    def _enter_command_mode(self) -> None:
        """Enter command mode."""
        if self._in_command_mode:
            return
        self._in_command_mode = True
        self.query_one("#status-bar", StatusBar).display = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = True
        cmd_input.reset(":")
        cmd_input.focus()

    def _enter_search_mode(self) -> None:
        """Enter search mode."""
        if self._in_command_mode:
            return
        self._in_command_mode = True
        self.query_one("#status-bar", StatusBar).display = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = True
        cmd_input.reset("/")
        cmd_input.focus()

    def _close_command_mode(self) -> None:
        """Close command mode."""
        self._in_command_mode = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = False
        self.query_one("#status-bar", StatusBar).display = True
        self.query_one("#bible-scroll").focus()

    # ==================== Event Handlers ====================

    def on_command_input_command_submitted(
        self, event: CommandInput.CommandSubmitted
    ) -> None:
        """Handle submitted command."""
        self._close_command_mode()

        command = event.command
        prefix = event.prefix

        if prefix == "/":
            self._do_search(command)
        else:
            parsed = parse_command(command)
            result = self._command_handler.execute(parsed)
            self._handle_command_result(result)

    def on_command_input_command_cancelled(
        self, event: CommandInput.CommandCancelled
    ) -> None:
        """Handle cancelled command."""
        self._close_command_mode()

    def on_book_picker_book_selected(self, event: BookPicker.BookSelected) -> None:
        """Handle book selection from picker."""
        self._close_picker()
        self._current_book = event.book
        self._current_chapter = event.chapter
        self._load_chapter()

        if event.verse:
            view = self.query_one("#bible-view", BibleView)
            view.move_to_verse(event.verse)
        self._update_status()

    def on_book_picker_cancelled(self, event: BookPicker.Cancelled) -> None:
        """Handle picker cancellation."""
        self._close_picker()

    def on_module_picker_module_selected(
        self, event: ModulePicker.ModuleSelected
    ) -> None:
        """Handle module selection from picker."""
        self._close_picker()
        self._current_module = event.module.name
        self._backend.set_module(self._current_module)
        self._load_chapter()

    def on_module_picker_cancelled(self, event: ModulePicker.Cancelled) -> None:
        """Handle picker cancellation."""
        self._close_picker()

    def _close_picker(self) -> None:
        """Close any open picker."""
        self._in_picker_mode = False
        for picker in self.query("BookPicker, ModulePicker"):
            picker.remove()
        self.query_one("#bible-scroll").focus()

    # ==================== Helper Methods ====================

    def _load_chapter(self) -> None:
        """Load the current chapter."""
        segments = self._backend.lookup_chapter(
            self._current_book, self._current_chapter
        )

        view = self.query_one("#bible-view", BibleView)
        view.update_content(segments, f"{self._current_book} {self._current_chapter}")

        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_home()

        # Exit visual mode on chapter change
        if self._in_visual_mode:
            self._in_visual_mode = False
            self.query_one("#status-bar", StatusBar).set_mode("normal")

        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar with current position."""
        view = self.query_one("#bible-view", BibleView)
        status = self.query_one("#status-bar", StatusBar)

        if self._in_visual_mode:
            start, end = view.get_visual_range()
            status.set_position(
                self._current_book,
                self._current_chapter,
                start,
                end if end != start else None,
            )
        else:
            status.set_position(
                self._current_book,
                self._current_chapter,
                view.current_verse,
            )

        status.set_module(self._current_module)

    def _do_search(self, query: str) -> None:
        """Perform search and navigate to first result."""
        if not query:
            return

        results = self._backend.search(query)

        if results:
            first = results[0]
            self.query_one("#status-bar", StatusBar).show_message(
                f"Gevonden: {len(results)} resultaten"
            )
            self._current_book = first.book
            self._current_chapter = first.chapter
            self._load_chapter()

            view = self.query_one("#bible-view", BibleView)
            view.move_to_verse(first.verse)
            view.set_search_query(query)
            self._update_status()
        else:
            self.query_one("#status-bar", StatusBar).show_message(
                f"Geen resultaten voor '{query}'"
            )

    def _handle_command_result(self, result) -> None:
        """Handle command execution result."""
        if not result.success:
            self.query_one("#status-bar", StatusBar).show_message(result.message)
            return

        action = result.action

        if action == "quit":
            self.exit()
        elif action == "goto":
            data = result.data or {}
            self._current_book = data.get("book", self._current_book)
            self._current_chapter = data.get("chapter", self._current_chapter)
            self._load_chapter()
            if data.get("verse"):
                view = self.query_one("#bible-view", BibleView)
                view.move_to_verse(data["verse"])
            self._update_status()
        elif action == "set_module":
            data = result.data or {}
            module = data.get("module", "")
            if module:
                self._current_module = module
                self._backend.set_module(module)
                self._load_chapter()
        elif action == "module_picker":
            self.action_module_picker()
        elif action == "export":
            self._handle_export(result.data or {})
        elif result.message:
            self.query_one("#status-bar", StatusBar).show_message(result.message)

    def _handle_export(self, data: dict) -> None:
        """Handle export command."""
        book = data.get("book", self._current_book)
        chapter = data.get("chapter", self._current_chapter)
        verse_start = data.get("verse_start")
        verse_end = data.get("verse_end")
        fmt = data.get("format", "txt")

        if verse_start and verse_end:
            segments = self._backend.lookup_range(book, chapter, verse_start, verse_end)
        elif verse_start:
            seg = self._backend.lookup_verse(book, chapter, verse_start)
            segments = [seg] if seg else []
        else:
            segments = self._backend.lookup_chapter(book, chapter)

        if fmt == "html":
            output = self._format_html(segments, book, chapter)
        else:
            output = self._format_text(segments)

        try:
            import pyperclip
            pyperclip.copy(output)
            self.query_one("#status-bar", StatusBar).show_message(
                f"Geexporteerd naar klembord ({fmt})"
            )
        except ImportError:
            self.query_one("#status-bar", StatusBar).show_message(
                "pyperclip niet beschikbaar"
            )

    def _format_text(self, segments: List[VerseSegment]) -> str:
        """Format verses as plain text."""
        return "\n".join(f"{s.verse}. {s.text}" for s in segments)

    def _format_html(
        self, segments: List[VerseSegment], book: str, chapter: int
    ) -> str:
        """Format verses as HTML."""
        lines = [f"<h2>{book} {chapter}</h2>", "<p>"]
        for s in segments:
            lines.append(f"<sup>{s.verse}</sup> {s.text} ")
        lines.append("</p>")
        return "\n".join(lines)
