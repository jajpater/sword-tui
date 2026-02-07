"""Main Textual application for sword-tui."""

from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Static

from sword_tui.backend import DiathekeBackend, get_installed_modules
from sword_tui.commands import CommandHandler, parse_command
from sword_tui.data import (
    BOOK_ORDER,
    book_chapters,
    book_index,
    resolve_alias,
    VerseSegment,
)
from sword_tui.widgets import (
    BibleView,
    BookPicker,
    CommandInput,
    KWICList,
    ModulePicker,
    ParallelView,
    StatusBar,
)


class SwordApp(App):
    """Bible TUI application using SWORD/diatheke backend."""

    TITLE = "Sword-TUI"
    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("ctrl+d", "page_down", "Page Down", show=False),
        Binding("ctrl+u", "page_up", "Page Up", show=False),
        Binding("g", "goto", "Goto", show=False),
        Binding("m", "module_picker", "Module", show=False),
        Binding("shift+p", "toggle_parallel", "Parallel", show=False),
        Binding("y", "yank", "Copy", show=False),
        Binding("bracketright", "next_chapter", "Next", show=False),
        Binding("bracketleft", "prev_chapter", "Prev", show=False),
        Binding("braceright", "next_book", "Next Book", show=False),
        Binding("braceleft", "prev_book", "Prev Book", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()

        # State
        self._current_book = "Genesis"
        self._current_chapter = 1
        self._current_module = "DutSVV"
        self._parallel_module = "KJV"

        # Mode flags
        self._in_command_mode = False
        self._in_search_mode = False
        self._in_parallel_mode = False
        self._in_picker_mode = False

        # Digit buffer for numeric input
        self._digit_buffer = ""

        # Backend
        self._backend = DiathekeBackend(self._current_module)
        self._parallel_backend = DiathekeBackend(self._parallel_module)

        # Command handler (initialized after mount)
        self._command_handler: Optional[CommandHandler] = None

        # Detect available modules
        modules = get_installed_modules()
        if modules:
            self._current_module = modules[0].name
            self._backend.set_module(self._current_module)
            if len(modules) > 1:
                self._parallel_module = modules[1].name
                self._parallel_backend.set_module(self._parallel_module)

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        yield VerticalScroll(BibleView(id="bible-view"), id="bible-scroll")
        yield CommandInput(
            commands=["quit", "help", "module", "export", "bookmark", "goto", "search"],
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

        # Update status bar
        self._update_status()

        # Focus the main scroll area
        self.query_one("#bible-scroll").focus()

    def on_key(self, event) -> None:
        """Handle key events centrally."""
        if self._in_command_mode or self._in_picker_mode:
            return

        key = event.key
        char = event.character

        # Handle digits for numeric input
        if char and char.isdigit():
            self._digit_buffer += char
            return

        # Process digit buffer on non-digit key
        if self._digit_buffer:
            self._process_digit_buffer()

        # Mode-specific handling
        if self._in_search_mode:
            self._handle_search_key(event)
            return

        # Global keys
        if char == ":":
            event.stop()
            self.action_command_mode()
        elif char == "/":
            event.stop()
            self.action_search_mode()

    def _process_digit_buffer(self) -> None:
        """Process accumulated digit input as chapter number."""
        if not self._digit_buffer:
            return

        try:
            chapter = int(self._digit_buffer)
            max_chapters = book_chapters(self._current_book)
            if 1 <= chapter <= max_chapters:
                self._current_chapter = chapter
                self._load_chapter()
        except ValueError:
            pass

        self._digit_buffer = ""

    def _handle_search_key(self, event) -> None:
        """Handle keys in search mode."""
        key = event.key
        char = event.character

        if key == "escape":
            event.stop()
            self._close_search_mode()
        elif key == "enter":
            event.stop()
            self._goto_search_result()
        elif char == "j" or key == "down":
            event.stop()
            self._search_move_down()
        elif char == "k" or key == "up":
            event.stop()
            self._search_move_up()

    # ==================== Actions ====================

    def action_scroll_down(self) -> None:
        """Scroll down."""
        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_down()

    def action_scroll_up(self) -> None:
        """Scroll up."""
        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_up()

    def action_page_down(self) -> None:
        """Page down."""
        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_page_down()

    def action_page_up(self) -> None:
        """Page up."""
        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_page_up()

    def action_next_chapter(self) -> None:
        """Go to next chapter."""
        max_chapters = book_chapters(self._current_book)
        if self._current_chapter < max_chapters:
            self._current_chapter += 1
            self._load_chapter()
        else:
            self.action_next_book()

    def action_prev_chapter(self) -> None:
        """Go to previous chapter."""
        if self._current_chapter > 1:
            self._current_chapter -= 1
            self._load_chapter()
        else:
            self.action_prev_book(last_chapter=True)

    def action_next_book(self) -> None:
        """Go to next book."""
        idx = book_index(self._current_book)
        if idx < len(BOOK_ORDER) - 1:
            self._current_book = BOOK_ORDER[idx + 1]
            self._current_chapter = 1
            self._load_chapter()

    def action_prev_book(self, last_chapter: bool = False) -> None:
        """Go to previous book."""
        idx = book_index(self._current_book)
        if idx > 0:
            self._current_book = BOOK_ORDER[idx - 1]
            if last_chapter:
                self._current_chapter = book_chapters(self._current_book)
            else:
                self._current_chapter = 1
            self._load_chapter()

    def action_goto(self) -> None:
        """Open goto dialog."""
        self._in_picker_mode = True
        picker = BookPicker(id="book-picker")
        self.mount(picker)
        picker.focus()

    def action_command_mode(self) -> None:
        """Enter command mode."""
        if self._in_command_mode:
            return

        self._in_command_mode = True
        self.query_one("#status-bar", StatusBar).display = False

        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = True
        cmd_input.reset(":")
        cmd_input.focus()

    def action_search_mode(self) -> None:
        """Enter search mode with / prefix."""
        if self._in_command_mode:
            return

        self._in_command_mode = True
        self.query_one("#status-bar", StatusBar).display = False

        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = True
        cmd_input.reset("/")
        cmd_input.focus()

    def action_module_picker(self) -> None:
        """Open module picker."""
        self._in_picker_mode = True
        picker = ModulePicker(current_module=self._current_module, id="module-picker")
        self.mount(picker)
        picker.focus()

    def action_toggle_parallel(self) -> None:
        """Toggle parallel view (not yet implemented in simplified version)."""
        self.query_one("#status-bar", StatusBar).show_message(
            "Parallel view: gebruik 'nix run .' voor volledige versie"
        )

    def action_yank(self) -> None:
        """Copy current chapter text to clipboard."""
        try:
            import pyperclip

            view = self.query_one("#bible-view", BibleView)
            text = view.get_all_text()
            pyperclip.copy(text)

            self.query_one("#status-bar", StatusBar).show_message(
                f"Gekopieerd: {self._current_book} {self._current_chapter}"
            )
        except ImportError:
            self.query_one("#status-bar", StatusBar).show_message(
                "pyperclip niet beschikbaar"
            )

    # ==================== Event Handlers ====================

    def on_command_input_command_submitted(
        self, event: CommandInput.CommandSubmitted
    ) -> None:
        """Handle submitted command."""
        self._close_command_mode()

        command = event.command
        prefix = event.prefix

        if prefix == "/":
            self._enter_search_mode(command)
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
            self.query_one("#bible-view", BibleView).highlight_verse(event.verse)

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

    # ==================== Helper Methods ====================

    def _close_command_mode(self) -> None:
        """Close command mode."""
        self._in_command_mode = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = False

        self.query_one("#status-bar", StatusBar).display = True
        self.query_one("#bible-scroll").focus()

    def _close_picker(self) -> None:
        """Close any open picker."""
        self._in_picker_mode = False

        for picker in self.query("BookPicker, ModulePicker"):
            picker.remove()

        self.query_one("#bible-scroll").focus()

    def _load_chapter(self) -> None:
        """Load the current chapter."""
        segments = self._backend.lookup_chapter(
            self._current_book, self._current_chapter
        )
        title = f"{self._current_book} {self._current_chapter}"

        view = self.query_one("#bible-view", BibleView)
        view.update_content(segments, title)

        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_home()

        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar."""
        status = self.query_one("#status-bar", StatusBar)
        status.set_reference(f"{self._current_book} {self._current_chapter}")
        status.set_module(self._current_module)

    def _enter_search_mode(self, query: str) -> None:
        """Enter search mode with results."""
        if not query:
            return

        self._in_search_mode = True

        # Perform search
        results = self._backend.search(query)

        # Show results in status bar for now (simplified)
        if results:
            first = results[0]
            self.query_one("#status-bar", StatusBar).show_message(
                f"Gevonden: {len(results)} resultaten, eerste: {first.reference}"
            )
            # Navigate to first result
            self._current_book = first.book
            self._current_chapter = first.chapter
            self._load_chapter()
            self.query_one("#bible-view", BibleView).set_search_query(query)
            self.query_one("#bible-view", BibleView).highlight_verse(first.verse)
        else:
            self.query_one("#status-bar", StatusBar).show_message(
                f"Geen resultaten voor '{query}'"
            )

        self._in_search_mode = False

    def _close_search_mode(self) -> None:
        """Close search mode."""
        self._in_search_mode = False
        self.query_one("#status-bar", StatusBar).set_mode("browse")
        self.query_one("#bible-scroll").focus()

    def _goto_search_result(self) -> None:
        """Navigate to selected search result."""
        pass

    def _search_move_down(self) -> None:
        """Move selection down in search results."""
        pass

    def _search_move_up(self) -> None:
        """Move selection up in search results."""
        pass

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
                self.query_one("#bible-view", BibleView).highlight_verse(data["verse"])
        elif action == "set_module":
            data = result.data or {}
            module = data.get("module", "")
            if module:
                self._current_module = module
                self._backend.set_module(module)
                self._load_chapter()
        elif action == "module_picker":
            self.action_module_picker()
        elif action == "toggle_parallel":
            self.action_toggle_parallel()
        elif action == "search":
            data = result.data or {}
            query = data.get("query", "")
            if query:
                self._enter_search_mode(query)
        elif action == "yank":
            self.action_yank()
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

    def _format_html(self, segments: List[VerseSegment], book: str, chapter: int) -> str:
        """Format verses as HTML."""
        lines = [f"<h2>{book} {chapter}</h2>", "<p>"]
        for s in segments:
            lines.append(f'<sup>{s.verse}</sup> {s.text} ')
        lines.append("</p>")
        return "\n".join(lines)
