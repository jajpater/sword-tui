"""Main Textual application for sword-tui."""

from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Header

from sword_tui.backend import DiathekeBackend, get_installed_modules, DiathekeFilters, DictionaryBackend, CrossRefBackend, CommentaryBackend
from sword_tui.config import get_config
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
    CrossRefView,
    CrossRefSelected,
    DictModulePicker,
    ModulePicker,
    ParallelView,
    SearchView,
    StatusBar,
    StrongsView,
    StudyView,
    StudyGotoRef,
)


class SwordApp(App):
    """Bible TUI application using SWORD/diatheke backend."""

    TITLE = "Sword-TUI"
    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("j", "next_verse", "Next verse", show=False),
        Binding("k", "prev_verse", "Prev verse", show=False),
        Binding("r", "goto", "Reference", show=False),
        Binding("G", "last_verse", "Last verse", show=False),
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
        Binding("ctrl+u", "page_up", "Page_up", show=False),
        Binding("ctrl+f", "search_chapter", "Search in chapter", show=False),
        Binding("n", "search_next", "Next match", show=False),
        Binding("N", "search_prev", "Previous match", show=False),
        Binding("P", "toggle_parallel", "Parallel view", show=False),
        Binding("h", "focus_left_pane", "Left pane", show=False),
        Binding("l", "focus_right_pane", "Right pane", show=False),
        Binding("tab", "toggle_pane_focus", "Switch pane", show=False),
        Binding("M", "secondary_module_picker", "Secondary module", show=False),
        Binding("L", "toggle_pane_link", "Link/unlink panes", show=False),
        Binding("S", "toggle_search_mode", "Toggle search display mode", show=False),
        Binding("question_mark", "show_help", "Show help", show=False),
        Binding("s", "toggle_strongs", "Toggle Strong's", show=False),
        Binding("F", "toggle_footnotes", "Toggle footnotes", show=False),
        Binding("x", "toggle_crossrefs", "Toggle cross-references", show=False),
        Binding("T", "toggle_study", "Toggle study mode", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()

        # Load config
        self._config = get_config()

        # State
        self._current_book = "Genesis"
        self._current_chapter = 1
        self._current_module = self._config.default_module or "DutSVV"

        # Mode flags
        self._in_command_mode = False
        self._in_visual_mode = False
        self._in_picker_mode = False
        self._in_parallel_mode = False
        self._in_search_mode = False  # KWIC search mode
        self._picking_secondary_module = False
        self._picking_search_preview_module = False
        self._panes_linked = True  # Whether parallel panes show same passage
        self._active_pane = "left"  # Which pane is active: "left" or "right"

        # Search display mode: 1=KWIC only, 2=refs+preview (default), 3=KWIC+preview
        self._search_display_mode = 2

        # Diatheke filter flags (named _diatheke_filters to avoid conflict with Textual's _filters)
        self._diatheke_filters = DiathekeFilters()

        # Strong's lookup mode state
        self._in_strongs_mode = False  # Whether Strong's lookup mode is active
        self._strongs_pane_focused = False  # Whether the strongs dictionary pane has focus
        self._strongs_word_index = 0  # Index of currently selected word with Strong's
        self._strongs_words_in_verse: list[int] = []  # Indices of words with Strong's in current verse
        self._dictionary_backend = DictionaryBackend()
        self._active_greek_modules: list[str] = self._config.strongs_greek_modules.copy()
        self._active_hebrew_modules: list[str] = self._config.strongs_hebrew_modules.copy()
        self._picking_dict_modules = False

        # Cross-reference mode state
        self._in_crossref_mode = False
        self._crossref_backend = CrossRefBackend()

        # Study mode state (3-pane view)
        self._in_study_mode = False
        self._commentary_backend = CommentaryBackend()
        self._study_commentary_module = "DutKant"  # Default commentary
        self._study_active_pane = 0  # 0=bible, 1=commentary, 2=crossrefs

        # Right pane state (when unlinked)
        self._right_book = "Genesis"
        self._right_chapter = 1

        # Search state
        self._chapter_search_query = ""
        self._search_matches: list[int] = []  # Verse numbers with matches
        self._search_match_index = 0
        self._search_preview_module = ""  # Module for search preview pane
        self._search_preview_backend: Optional[DiathekeBackend] = None

        # Key sequence buffer (for gg)
        self._key_buffer = ""

        # Secondary module for parallel view
        self._secondary_module = ""
        self._secondary_backend: Optional[DiathekeBackend] = None

        # Backend
        self._backend = DiathekeBackend(self._current_module)
        self._backend.set_filters(self._diatheke_filters)

        # Command handler (initialized after mount)
        self._command_handler: Optional[CommandHandler] = None

        # Detect available modules and validate configured module
        modules = get_installed_modules()
        if modules:
            module_names = [m.name for m in modules]
            # Use configured module if valid, otherwise fall back to first available
            if self._current_module not in module_names:
                self._current_module = modules[0].name
            self._backend.set_module(self._current_module)

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        # Normal single-pane view
        with VerticalScroll(id="bible-scroll"):
            yield BibleView(id="bible-view")
        # Parallel view (two panes, initially hidden)
        yield ParallelView(id="parallel-view")
        # Search view (KWIC, initially hidden)
        yield SearchView(id="search-view")
        # Strong's dictionary view (initially hidden)
        yield StrongsView(id="strongs-view")
        # Cross-references view (initially hidden)
        yield CrossRefView(id="crossref-view")
        # Study view - 3-pane interface (initially hidden)
        yield StudyView(id="study-view")
        yield CommandInput(
            commands=["quit", "help", "module", "export", "goto"],
            id="command-input",
        )
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        self._command_handler = CommandHandler(self)

        # Hide command input, parallel view, search view, strongs view, crossref view and study view initially
        self.query_one("#command-input").display = False
        self.query_one("#parallel-view").display = False
        self.query_one("#search-view").display = False
        self.query_one("#strongs-view").display = False
        self.query_one("#crossref-view").display = False
        self.query_one("#study-view").display = False

        # Initialize status bar with filters
        self.query_one("#status-bar", StatusBar).set_filters(self._diatheke_filters)

        # Load initial content
        self._load_chapter()

        # Focus the main scroll area
        self.query_one("#bible-scroll").focus()

    def on_key(self, event) -> None:
        """Handle key events centrally."""
        if self._in_command_mode or self._in_picker_mode:
            return

        char = event.character
        key = event.key

        # Handle Strong's mode keys
        if self._in_strongs_mode:
            if key == "escape":
                event.stop()
                self.action_toggle_strongs()  # Exit strongs mode
                return
            # Tab, Ctrl+h, Ctrl+l for pane switching
            elif key == "tab" or key == "ctrl+h" or key == "ctrl+l":
                event.stop()
                self._toggle_strongs_pane_focus()
                return
            # h/l for word navigation (vim-style)
            elif char == "l" or char == "]":
                event.stop()
                self._strongs_next_word()
                return
            elif char == "h" or char == "[":
                event.stop()
                self._strongs_prev_word()
                return
            elif char == "y" and self._strongs_pane_focused:
                event.stop()
                self._yank_strongs_entry()
                return
            elif (char == "j" or key == "down") and self._strongs_pane_focused:
                event.stop()
                self._scroll_strongs_down()
                return
            elif (char == "k" or key == "up") and self._strongs_pane_focused:
                event.stop()
                self._scroll_strongs_up()
                return

        # Handle cross-reference mode keys
        if self._in_crossref_mode:
            if key == "escape":
                event.stop()
                self.action_toggle_crossrefs()  # Exit crossref mode
                return
            elif char == "j" or key == "down":
                event.stop()
                crossref_view = self.query_one("#crossref-view", CrossRefView)
                crossref_view.action_next_item()
                return
            elif char == "k" or key == "up":
                event.stop()
                crossref_view = self.query_one("#crossref-view", CrossRefView)
                crossref_view.action_prev_item()
                return
            elif key == "enter":
                event.stop()
                crossref_view = self.query_one("#crossref-view", CrossRefView)
                crossref_view.action_select_item()
                return

        # Handle study mode keys
        if self._in_study_mode:
            study = self.query_one("#study-view", StudyView)
            if key == "escape":
                event.stop()
                self.action_toggle_study()  # Exit study mode
                return
            elif key == "tab":
                event.stop()
                study.next_pane()
                self._study_active_pane = study.active_pane
                pane_names = ["bijbel", "commentaar", "crossrefs"]
                self.query_one("#status-bar", StatusBar).show_message(
                    f"Actief: {pane_names[self._study_active_pane]}"
                )
                return
            elif char == "j" or key == "down":
                event.stop()
                if self._study_active_pane == 0:
                    # Bible pane: next verse
                    bp = study.bible_pane
                    new_verse = bp.current_verse + 1
                    bp.set_current_verse(new_verse)
                    self._load_study_commentary(new_verse)
                elif self._study_active_pane == 2:
                    # Crossref pane: next ref
                    study.crossref_pane.next_ref()
                return
            elif char == "k" or key == "up":
                event.stop()
                if self._study_active_pane == 0:
                    # Bible pane: prev verse
                    bp = study.bible_pane
                    new_verse = max(1, bp.current_verse - 1)
                    bp.set_current_verse(new_verse)
                    self._load_study_commentary(new_verse)
                elif self._study_active_pane == 2:
                    # Crossref pane: prev ref
                    study.crossref_pane.prev_ref()
                return
            elif key == "enter" and self._study_active_pane == 2:
                event.stop()
                ref = study.crossref_pane.get_selected_ref()
                if ref:
                    self.post_message(StudyGotoRef(ref))
                return
            elif char == "m":
                event.stop()
                # Cycle through commentary modules
                mods = self._commentary_backend.available_modules
                if mods:
                    idx = mods.index(self._study_commentary_module) if self._study_commentary_module in mods else -1
                    self._study_commentary_module = mods[(idx + 1) % len(mods)]
                    self._load_study_commentary(study.bible_pane.current_verse)
                    self.query_one("#status-bar", StatusBar).show_message(
                        f"Commentaar: {self._study_commentary_module}"
                    )
                return

        # Handle search mode keys
        if self._in_search_mode:
            if key == "escape":
                event.stop()
                self._close_search_mode()
            elif char == "j" or key == "down":
                event.stop()
                self._search_move_down()
            elif char == "k" or key == "up":
                event.stop()
                self._search_move_up()
            elif key == "pagedown" or key == "ctrl+d":
                event.stop()
                self._search_page_down()
            elif key == "pageup" or key == "ctrl+u":
                event.stop()
                self._search_page_up()
            elif key == "enter":
                event.stop()
                self._search_goto_result()
            elif char == "S":
                event.stop()
                self.action_toggle_search_mode()
            elif char == "m":
                event.stop()
                self._search_preview_module_picker()
            return

        # Handle gg sequence (go to first verse)
        if char == "g":
            if self._key_buffer == "g":
                self._key_buffer = ""
                self.action_first_verse()
                event.stop()
                return
            else:
                self._key_buffer = "g"
                return
        else:
            # Clear key buffer on other keys
            self._key_buffer = ""

        # Handle colon for command/verse mode
        if char == ":":
            event.stop()
            self._enter_command_mode()
        elif char == "/":
            # KWIC search
            event.stop()
            self._enter_kwic_search_mode()

    # ==================== Actions ====================

    def action_next_verse(self) -> None:
        """Move to next verse (j key) - in Strong's mode with dict pane: scroll down."""
        # In Strong's mode with dictionary pane focused, scroll dictionary
        if self._in_strongs_mode and self._strongs_pane_focused:
            self._scroll_strongs_down()
            return

        view = self._get_active_view()
        if not view.next_verse():
            self.action_next_chapter()
        elif self._in_parallel_mode and self._panes_linked:
            # Sync other pane
            parallel = self.query_one("#parallel-view", ParallelView)
            other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
            other.set_current_verse(view.current_verse)

        # Update Strong's words for new verse
        if self._in_strongs_mode:
            self._update_strongs_words_in_verse()
            self._lookup_current_strongs()

        # Update cross-references for new verse
        if self._in_crossref_mode:
            self._load_crossrefs_for_current_verse()

        self._update_status()

    def action_prev_verse(self) -> None:
        """Move to previous verse (k key) - in Strong's mode with dict pane: scroll up."""
        # In Strong's mode with dictionary pane focused, scroll dictionary
        if self._in_strongs_mode and self._strongs_pane_focused:
            self._scroll_strongs_up()
            return

        view = self._get_active_view()
        if not view.prev_verse():
            # Go to previous chapter
            book = self._get_active_book()
            chapter = self._get_active_chapter()
            if chapter > 1:
                self._set_active_chapter(chapter - 1)
                if self._panes_linked:
                    self._load_chapter()
                else:
                    self._load_active_pane_chapter()
                view.last_verse()
                if self._in_parallel_mode and self._panes_linked:
                    parallel = self.query_one("#parallel-view", ParallelView)
                    other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
                    other.last_verse()
            elif book_index(book) > 0:
                new_book = BOOK_ORDER[book_index(book) - 1]
                self._set_active_book(new_book)
                self._set_active_chapter(book_chapters(new_book))
                if self._panes_linked:
                    self._load_chapter()
                else:
                    self._load_active_pane_chapter()
                view.last_verse()
                if self._in_parallel_mode and self._panes_linked:
                    parallel = self.query_one("#parallel-view", ParallelView)
                    other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
                    other.last_verse()
        elif self._in_parallel_mode and self._panes_linked:
            parallel = self.query_one("#parallel-view", ParallelView)
            other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
            other.set_current_verse(view.current_verse)

        # Update Strong's words for new verse
        if self._in_strongs_mode:
            self._update_strongs_words_in_verse()
            self._lookup_current_strongs()

        # Update cross-references for new verse
        if self._in_crossref_mode:
            self._load_crossrefs_for_current_verse()

        self._update_status()

    def action_next_chapter(self) -> None:
        """Go to next chapter, verse 1."""
        book = self._get_active_book()
        chapter = self._get_active_chapter()
        max_chapters = book_chapters(book)
        if chapter < max_chapters:
            self._set_active_chapter(chapter + 1)
            if self._panes_linked or not self._in_parallel_mode:
                self._load_chapter()
            else:
                self._load_active_pane_chapter()
        else:
            self.action_next_book()

    def action_prev_chapter(self) -> None:
        """Go to previous chapter, verse 1."""
        book = self._get_active_book()
        chapter = self._get_active_chapter()
        if chapter > 1:
            self._set_active_chapter(chapter - 1)
            if self._panes_linked or not self._in_parallel_mode:
                self._load_chapter()
            else:
                self._load_active_pane_chapter()
        else:
            # Go to previous book, last chapter
            idx = book_index(book)
            if idx > 0:
                new_book = BOOK_ORDER[idx - 1]
                self._set_active_book(new_book)
                self._set_active_chapter(book_chapters(new_book))
                if self._panes_linked or not self._in_parallel_mode:
                    self._load_chapter()
                else:
                    self._load_active_pane_chapter()

    def action_next_book(self) -> None:
        """Go to next book, chapter 1, verse 1."""
        book = self._get_active_book()
        idx = book_index(book)
        if idx < len(BOOK_ORDER) - 1:
            self._set_active_book(BOOK_ORDER[idx + 1])
            self._set_active_chapter(1)
            if self._panes_linked or not self._in_parallel_mode:
                self._load_chapter()
            else:
                self._load_active_pane_chapter()

    def action_prev_book(self) -> None:
        """Go to previous book, chapter 1, verse 1."""
        book = self._get_active_book()
        idx = book_index(book)
        if idx > 0:
            self._set_active_book(BOOK_ORDER[idx - 1])
            self._set_active_chapter(1)
            if self._panes_linked or not self._in_parallel_mode:
                self._load_chapter()
            else:
                self._load_active_pane_chapter()

    def action_goto(self) -> None:
        """Open goto dialog."""
        self._in_picker_mode = True
        picker = BookPicker()
        self.mount(picker)
        picker.focus()

    def action_first_verse(self) -> None:
        """Go to first verse (gg)."""
        view = self._get_active_view()
        view.first_verse()
        if self._in_parallel_mode and self._panes_linked:
            parallel = self.query_one("#parallel-view", ParallelView)
            other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
            other.first_verse()
        self._update_status()

    def action_last_verse(self) -> None:
        """Go to last verse (G)."""
        view = self._get_active_view()
        view.last_verse()
        if self._in_parallel_mode and self._panes_linked:
            parallel = self.query_one("#parallel-view", ParallelView)
            other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
            other.last_verse()
        self._update_status()

    def _goto_verse(self, verse: int) -> None:
        """Go to specific verse number."""
        view = self._get_active_view()
        view.move_to_verse(verse)
        if self._in_parallel_mode and self._panes_linked:
            parallel = self.query_one("#parallel-view", ParallelView)
            other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
            other.move_to_verse(verse)
        self._update_status()

    def action_visual_mode(self) -> None:
        """Toggle visual selection mode."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            right = parallel.query_one("#right-view", BibleView)
            if self._in_visual_mode:
                left.end_visual_mode()
                right.end_visual_mode()
                self._in_visual_mode = False
                status.set_mode("parallel")
            else:
                left.start_visual_mode()
                right.start_visual_mode()
                self._in_visual_mode = True
                status.set_mode("visual")
        else:
            view = self.query_one("#bible-view", BibleView)
            if self._in_visual_mode:
                view.end_visual_mode()
                self._in_visual_mode = False
                status.set_mode("normal")
            else:
                view.start_visual_mode()
                self._in_visual_mode = True
                status.set_mode("visual")
        self._update_status()

    def action_escape(self) -> None:
        """Handle escape key."""
        if self._in_visual_mode:
            if self._in_parallel_mode:
                parallel = self.query_one("#parallel-view", ParallelView)
                parallel.query_one("#left-view", BibleView).end_visual_mode()
                parallel.query_one("#right-view", BibleView).end_visual_mode()
                self._in_visual_mode = False
                self.query_one("#status-bar", StatusBar).set_mode("parallel")
            else:
                view = self.query_one("#bible-view", BibleView)
                view.end_visual_mode()
                self._in_visual_mode = False
                self.query_one("#status-bar", StatusBar).set_mode("normal")
            self._update_status()

    def action_yank(self) -> None:
        """Copy current verse or visual selection."""
        # In Strong's mode with dictionary pane focused, copy dictionary entry
        if self._in_strongs_mode and self._strongs_pane_focused:
            self._yank_strongs_entry()
            return

        status = self.query_one("#status-bar", StatusBar)

        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            right = parallel.query_one("#right-view", BibleView)

            # Get text from both panes
            left_text = left.get_selected_text()
            right_text = right.get_selected_text()

            # Format: both translations
            text = f"[{self._current_module}]\n{left_text}\n\n[{self._secondary_module}]\n{right_text}"

            try:
                import pyperclip
                pyperclip.copy(text)

                start, end = left.get_visual_range()
                if start == end:
                    msg = f"Gekopieerd: {self._current_book} {self._current_chapter}:{start} (2 vertalingen)"
                else:
                    msg = f"Gekopieerd: {self._current_book} {self._current_chapter}:{start}-{end} (2 vertalingen)"
                status.show_message(msg)
            except ImportError:
                status.show_message("pyperclip niet beschikbaar")
        else:
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
                status.show_message(msg)
            except ImportError:
                status.show_message("pyperclip niet beschikbaar")

        # Exit visual mode after yank
        if self._in_visual_mode:
            if self._in_parallel_mode:
                parallel = self.query_one("#parallel-view", ParallelView)
                parallel.query_one("#left-view", BibleView).end_visual_mode()
                parallel.query_one("#right-view", BibleView).end_visual_mode()
                self._in_visual_mode = False
                status.set_mode("parallel")
            else:
                view = self.query_one("#bible-view", BibleView)
                view.end_visual_mode()
                self._in_visual_mode = False
                status.set_mode("normal")

    def action_yank_chapter(self) -> None:
        """Copy entire chapter."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            right = parallel.query_one("#right-view", BibleView)

            text = f"[{self._current_module}]\n{left.get_all_text()}\n\n[{self._secondary_module}]\n{right.get_all_text()}"

            try:
                import pyperclip
                pyperclip.copy(text)
                status.show_message(
                    f"Gekopieerd: {self._current_book} {self._current_chapter} (2 vertalingen)"
                )
            except ImportError:
                status.show_message("pyperclip niet beschikbaar")
        else:
            view = self.query_one("#bible-view", BibleView)
            text = view.get_all_text()

            try:
                import pyperclip
                pyperclip.copy(text)
                status.show_message(
                    f"Gekopieerd: {self._current_book} {self._current_chapter} (heel hoofdstuk)"
                )
            except ImportError:
                status.show_message("pyperclip niet beschikbaar")

    def action_bookmark(self) -> None:
        """Bookmark current verse or visual selection."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            start, end = left.get_visual_range()
        else:
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
            status.show_message(f"Bookmark: {ref}")

        # Exit visual mode after bookmark
        if self._in_visual_mode:
            if self._in_parallel_mode:
                parallel = self.query_one("#parallel-view", ParallelView)
                parallel.query_one("#left-view", BibleView).end_visual_mode()
                parallel.query_one("#right-view", BibleView).end_visual_mode()
                self._in_visual_mode = False
                status.set_mode("parallel")
            else:
                view = self.query_one("#bible-view", BibleView)
                view.end_visual_mode()
                self._in_visual_mode = False
                status.set_mode("normal")

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
        """Open module picker for primary module."""
        self._in_picker_mode = True
        self._picking_secondary_module = False
        picker = ModulePicker(current_module=self._current_module, )
        self.mount(picker)
        picker.focus()

    def action_secondary_module_picker(self) -> None:
        """Open module picker for secondary module or dictionary modules."""
        if self._in_strongs_mode:
            # In Strong's mode, M opens dictionary module picker
            self._in_picker_mode = True
            self._picking_dict_modules = True

            # Determine which modules based on current Strong's number
            strongs_view = self.query_one("#strongs-view", StrongsView)
            current_num = strongs_view.current_number
            if current_num.startswith("H"):
                current_modules = self._active_hebrew_modules
                title = "Selecteer Hebreeuwse Woordenboeken"
            else:
                current_modules = self._active_greek_modules
                title = "Selecteer Griekse Woordenboeken"

            picker = DictModulePicker(
                title=title,
                current_modules=current_modules,
            )
            self.mount(picker)
            picker.focus()
            return

        if not self._in_parallel_mode:
            self.query_one("#status-bar", StatusBar).show_message(
                "M werkt alleen in parallel view of Strong's mode"
            )
            return
        self._in_picker_mode = True
        self._picking_secondary_module = True
        picker = ModulePicker(current_module=self._secondary_module, )
        self.mount(picker)
        picker.focus()

    def action_toggle_parallel(self) -> None:
        """Toggle parallel view mode."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_parallel_mode:
            # Switch back to single view
            self._in_parallel_mode = False
            self.query_one("#bible-scroll").display = True
            self.query_one("#parallel-view").display = False
            self.query_one("#bible-scroll").focus()
            status.set_mode("normal")
        else:
            # Switch to parallel view - need to pick secondary module
            modules = get_installed_modules()
            if len(modules) < 2:
                status.show_message("Minimaal 2 modules nodig voor parallel view")
                return

            # Find a different module for secondary
            for mod in modules:
                if mod.name != self._current_module:
                    self._secondary_module = mod.name
                    break

            self._secondary_backend = DiathekeBackend(self._secondary_module)
            self._secondary_backend.set_filters(self._diatheke_filters)
            self._in_parallel_mode = True

            # Hide single view, show parallel view
            self.query_one("#bible-scroll").display = False
            self.query_one("#parallel-view").display = True

            # Load content into both panes
            self._load_parallel_chapter()
            self.query_one("#parallel-view", ParallelView).focus_left()
            status.set_mode("parallel")

    def action_focus_left_pane(self) -> None:
        """Focus the left pane (h key) - in Strong's mode: previous word."""
        # In Strong's mode, h navigates to previous word
        if self._in_strongs_mode:
            self._strongs_prev_word()
            return

        if self._in_parallel_mode:
            self._active_pane = "left"
            self.query_one("#parallel-view", ParallelView).focus_left()
            self._update_status()

    def action_focus_right_pane(self) -> None:
        """Focus the right pane (l key) - in Strong's mode: next word."""
        # In Strong's mode, l navigates to next word
        if self._in_strongs_mode:
            self._strongs_next_word()
            return

        if self._in_parallel_mode:
            self._active_pane = "right"
            self.query_one("#parallel-view", ParallelView).focus_right()
            self._update_status()

    def action_toggle_pane_focus(self) -> None:
        """Toggle focus between panes (Tab)."""
        # In Strong's mode, toggle between bible and dictionary pane
        if self._in_strongs_mode:
            self._toggle_strongs_pane_focus()
            return

        # In parallel mode, toggle between left and right pane
        if self._in_parallel_mode:
            if self._active_pane == "left":
                self.action_focus_right_pane()
            else:
                self.action_focus_left_pane()

    def action_search_chapter(self) -> None:
        """Search within current chapter (Ctrl+F)."""
        self._in_command_mode = True
        self.query_one("#status-bar", StatusBar).display = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = True
        cmd_input.reset("?")  # Use ? prefix for chapter search
        cmd_input.focus()

    def action_search_next(self) -> None:
        """Go to next search match (n)."""
        if not self._search_matches:
            self.query_one("#status-bar", StatusBar).show_message("Geen zoekopdracht")
            return

        self._search_match_index = (self._search_match_index + 1) % len(self._search_matches)
        verse = self._search_matches[self._search_match_index]
        self._goto_verse(verse)
        self.query_one("#status-bar", StatusBar).show_message(
            f"Match {self._search_match_index + 1}/{len(self._search_matches)}"
        )

    def action_search_prev(self) -> None:
        """Go to previous search match (N)."""
        if not self._search_matches:
            self.query_one("#status-bar", StatusBar).show_message("Geen zoekopdracht")
            return

        self._search_match_index = (self._search_match_index - 1) % len(self._search_matches)
        verse = self._search_matches[self._search_match_index]
        self._goto_verse(verse)
        self.query_one("#status-bar", StatusBar).show_message(
            f"Match {self._search_match_index + 1}/{len(self._search_matches)}"
        )

    def action_toggle_pane_link(self) -> None:
        """Toggle linking between parallel panes (L)."""
        if not self._in_parallel_mode:
            self.query_one("#status-bar", StatusBar).show_message(
                "L werkt alleen in parallel view"
            )
            return

        self._panes_linked = not self._panes_linked
        status = self.query_one("#status-bar", StatusBar)
        if self._panes_linked:
            status.show_message("Panes gekoppeld")
            # Sync right pane to left pane
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            right = parallel.query_one("#right-view", BibleView)
            right.set_current_verse(left.current_verse)
        else:
            status.show_message("Panes ontkoppeld - navigeer onafhankelijk")

    def action_toggle_search_mode(self) -> None:
        """Toggle search display mode (S)."""
        # Cycle through modes: 1 -> 2 -> 3 -> 1
        self._search_display_mode = (self._search_display_mode % 3) + 1

        mode_names = {
            1: "KWIC (alleen lijst)",
            2: "Referenties + preview",
            3: "KWIC + preview",
        }
        status = self.query_one("#status-bar", StatusBar)
        status.show_message(f"Zoekmodus: {mode_names[self._search_display_mode]}")

        # Update search view if currently in search mode
        if self._in_search_mode:
            search_view = self.query_one("#search-view", SearchView)
            search_view.set_display_mode(self._search_display_mode)

    def action_show_help(self) -> None:
        """Show help (?)."""
        # Execute the :help command
        if self._command_handler:
            from sword_tui.commands.parser import ParsedCommand
            result = self._command_handler._cmd_help(ParsedCommand(name="help"))
            if result.message:
                # Show help in a notification
                self.notify(result.message, title="Help", timeout=30)

    def action_toggle_strongs(self) -> None:
        """Toggle Strong's numbers filter and lookup mode (s)."""
        self._diatheke_filters.toggle_strongs()
        status = self.query_one("#status-bar", StatusBar)
        status.set_filters(self._diatheke_filters)

        if self._diatheke_filters.strongs:
            # Enter Strong's lookup mode
            self._in_strongs_mode = True
            status.show_message("Strong's modus aan - h/l voor navigatie, Tab voor pane")
            status.set_mode("strongs")

            # Show the strongs view panel
            self.query_one("#strongs-view").display = True

            # Initialize Strong's word navigation
            self._strongs_word_index = 0
            self._update_strongs_words_in_verse()

            # Look up first Strong's word if available
            self._lookup_current_strongs()
        else:
            # Exit Strong's lookup mode
            self._in_strongs_mode = False
            status.show_message("Strong's modus uit")

            # Hide strongs view
            self.query_one("#strongs-view").display = False
            self.query_one("#strongs-view", StrongsView).clear()

            # Restore mode
            if self._in_parallel_mode:
                status.set_mode("parallel")
            else:
                status.set_mode("normal")

        # Reload current chapter to reflect filter change
        self._load_chapter()

    def action_toggle_footnotes(self) -> None:
        """Toggle footnotes filter (F)."""
        self._diatheke_filters.toggle_footnotes()
        status = self.query_one("#status-bar", StatusBar)
        if self._diatheke_filters.footnotes:
            status.show_message("Voetnoten aan")
        else:
            status.show_message("Voetnoten uit")
        status.set_filters(self._diatheke_filters)
        # Reload current chapter to reflect filter change
        self._load_chapter()

    def action_toggle_crossrefs(self) -> None:
        """Toggle cross-references mode (x)."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_crossref_mode:
            # Exit cross-reference mode
            self._in_crossref_mode = False
            status.show_message("Cross-references uit")

            # Hide crossref view
            self.query_one("#crossref-view").display = False
            self.query_one("#crossref-view", CrossRefView).clear()

            # Restore mode
            if self._in_parallel_mode:
                status.set_mode("parallel")
            else:
                status.set_mode("normal")
        else:
            # Enter cross-reference mode
            if not self._crossref_backend.available:
                status.show_message("Geen cross-ref bronnen (TSK/commentaren) beschikbaar")
                return

            self._in_crossref_mode = True
            sources = self._crossref_backend.sources
            source_names = ", ".join(s.module for s in sources[:3])
            if len(sources) > 3:
                source_names += f" (+{len(sources) - 3})"
            status.show_message(f"Cross-refs: {source_names} | j/k nav, Enter ga naar")
            status.set_mode("crossref")

            # Show the crossref view panel
            self.query_one("#crossref-view").display = True

            # Load cross-references for current verse
            self._load_crossrefs_for_current_verse()

    def _load_crossrefs_for_current_verse(self) -> None:
        """Load cross-references for the current verse."""
        view = self._get_active_view()
        segment = view.get_current_segment()

        if not segment:
            return

        # Get cross-references with preview text
        crossrefs = self._crossref_backend.lookup_with_previews(
            segment.book,
            segment.chapter,
            segment.verse,
            self._backend,
        )

        # Update the crossref view
        crossref_view = self.query_one("#crossref-view", CrossRefView)
        crossref_view.update_crossrefs(segment.reference, crossrefs)

    def on_cross_ref_selected(self, message: CrossRefSelected) -> None:
        """Handle cross-reference selection for navigation."""
        xref = message.crossref

        # Navigate to the selected reference
        self._current_book = xref.book
        self._current_chapter = xref.chapter
        self._load_chapter()

        # Go to the specific verse
        view = self._get_active_view()
        view.move_to_verse(xref.verse)

        self._update_status()

        # Reload cross-references for the new verse
        if self._in_crossref_mode:
            self._load_crossrefs_for_current_verse()

    # ==================== Study Mode ====================

    def action_toggle_study(self) -> None:
        """Toggle 3-pane study mode (T)."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_study_mode:
            # Exit study mode
            self._in_study_mode = False
            self.query_one("#study-view").display = False
            self.query_one("#bible-scroll").display = True
            status.show_message("Study mode uit")
            status.set_mode("normal")
        else:
            # Enter study mode
            if not self._commentary_backend.available:
                status.show_message("Geen commentaar modules beschikbaar")
                return

            # Disable other modes
            if self._in_parallel_mode:
                self.action_toggle_parallel()
            if self._in_search_mode:
                self._close_search_mode()
            if self._in_strongs_mode:
                self.action_toggle_strongs()
            if self._in_crossref_mode:
                self.action_toggle_crossrefs()

            self._in_study_mode = True
            self.query_one("#bible-scroll").display = False
            self.query_one("#study-view").display = True

            # Load current chapter into study view
            self._load_study_view()

            mods = self._commentary_backend.available_modules
            status.show_message(f"Study mode: {self._study_commentary_module} | Tab: panes | m: wissel commentaar")
            status.set_mode("study")

    def _load_study_view(self) -> None:
        """Load content into all study view panes."""
        study = self.query_one("#study-view", StudyView)

        # Load bible text (pane 1)
        verses = self._backend.lookup_chapter(self._current_book, self._current_chapter)
        view = self._get_active_view()
        current_verse = view.current_verse if hasattr(view, 'current_verse') else 1

        study.bible_pane.update_chapter(
            self._current_module,
            self._current_book,
            self._current_chapter,
            verses,
            current_verse,
        )

        # Load commentary (pane 2)
        self._load_study_commentary(current_verse)

    def _load_study_commentary(self, verse: int) -> None:
        """Load commentary for the current verse in study mode."""
        study = self.query_one("#study-view", StudyView)

        entry = self._commentary_backend.lookup(
            self._current_book,
            self._current_chapter,
            verse,
            self._study_commentary_module,
        )

        study.commentary_pane.update_commentary(entry)

        # Load cross-reference texts (pane 3)
        if entry and entry.crossrefs:
            self._load_study_crossrefs(entry.crossrefs)
        else:
            study.crossref_pane.clear()

    def _load_study_crossrefs(self, refs: list) -> None:
        """Load cross-reference texts into pane 3."""
        study = self.query_one("#study-view", StudyView)

        texts = []
        for ref in refs:
            seg = self._backend.lookup_verse(ref.book, ref.chapter, ref.verse)
            if seg:
                texts.append(seg.text)
            else:
                texts.append("")

        study.crossref_pane.update_refs(refs, texts)

    def on_study_goto_ref(self, message: StudyGotoRef) -> None:
        """Handle navigation to a cross-reference from study mode."""
        xref = message.crossref

        self._current_book = xref.book
        self._current_chapter = xref.chapter
        self._load_study_view()

        # Set verse
        study = self.query_one("#study-view", StudyView)
        study.bible_pane.set_current_verse(xref.verse)
        self._load_study_commentary(xref.verse)

        self._update_status()

    def _strongs_next_word(self) -> None:
        """Navigate to next word with Strong's number (l key)."""
        if not self._in_strongs_mode:
            return

        if not self._strongs_words_in_verse:
            self._update_strongs_words_in_verse()

        if not self._strongs_words_in_verse:
            self.query_one("#status-bar", StatusBar).show_message(
                "Geen Strong's nummers in dit vers"
            )
            return

        # Move to next word
        self._strongs_word_index = (self._strongs_word_index + 1) % len(self._strongs_words_in_verse)
        self._lookup_current_strongs()

    def _strongs_prev_word(self) -> None:
        """Navigate to previous word with Strong's number (h key)."""
        if not self._in_strongs_mode:
            return

        if not self._strongs_words_in_verse:
            self._update_strongs_words_in_verse()

        if not self._strongs_words_in_verse:
            self.query_one("#status-bar", StatusBar).show_message(
                "Geen Strong's nummers in dit vers"
            )
            return

        # Move to previous word
        self._strongs_word_index = (self._strongs_word_index - 1) % len(self._strongs_words_in_verse)
        self._lookup_current_strongs()

    def _update_strongs_words_in_verse(self) -> None:
        """Update the list of words with Strong's numbers in current verse."""
        view = self._get_active_view()
        segment = view.get_current_segment()

        self._strongs_words_in_verse = []
        self._strongs_word_index = 0

        if segment and segment.words:
            for i, word in enumerate(segment.words):
                if word.strongs:
                    self._strongs_words_in_verse.append(i)

    def _lookup_current_strongs(self) -> None:
        """Look up the Strong's number for the currently selected word."""
        view = self._get_active_view()
        segment = view.get_current_segment()

        if not segment or not segment.words or not self._strongs_words_in_verse:
            return

        if self._strongs_word_index >= len(self._strongs_words_in_verse):
            self._strongs_word_index = 0

        word_idx = self._strongs_words_in_verse[self._strongs_word_index]
        if word_idx >= len(segment.words):
            return

        word = segment.words[word_idx]
        if not word.strongs:
            return

        # Get the first Strong's number (could be multiple)
        strongs_num = word.strongs[0]

        # Determine which dictionary modules to use based on G or H prefix
        if strongs_num.startswith("G"):
            modules = self._active_greek_modules
        elif strongs_num.startswith("H"):
            modules = self._active_hebrew_modules
        else:
            modules = self._active_greek_modules + self._active_hebrew_modules

        # Look up in dictionary
        entries = self._dictionary_backend.lookup_strongs(strongs_num, modules)

        # Update the strongs view
        strongs_view = self.query_one("#strongs-view", StrongsView)
        strongs_view.update_entries(strongs_num, entries)

        # Show status with current word
        status = self.query_one("#status-bar", StatusBar)
        word_count = len(self._strongs_words_in_verse)
        status.show_message(
            f"{word.text}[{strongs_num}] ({self._strongs_word_index + 1}/{word_count})"
        )

    def _toggle_strongs_pane_focus(self) -> None:
        """Toggle logical focus between bible view and strongs dictionary pane.

        Note: We don't actually change widget focus - we just track which pane
        is logically active for key handling. This ensures all keys go through
        the App's on_key handler.
        """
        self._strongs_pane_focused = not self._strongs_pane_focused
        status = self.query_one("#status-bar", StatusBar)

        if self._strongs_pane_focused:
            status.show_message("Woordenboek pane - j/k scroll, y kopieer")
        else:
            status.show_message("Bijbel pane - h/l Strong's navigatie")

    def _scroll_strongs_down(self) -> None:
        """Scroll the strongs view down."""
        scroll = self.query_one("#strongs-view", StrongsView).query_one("#strongs-scroll")
        scroll.scroll_down()

    def _scroll_strongs_up(self) -> None:
        """Scroll the strongs view up."""
        scroll = self.query_one("#strongs-view", StrongsView).query_one("#strongs-scroll")
        scroll.scroll_up()

    def _yank_strongs_entry(self) -> None:
        """Copy the current Strong's entry to clipboard."""
        strongs_view = self.query_one("#strongs-view", StrongsView)
        entries = strongs_view.entries
        status = self.query_one("#status-bar", StatusBar)

        if not entries:
            status.show_message("Geen entry om te kopiëren")
            return

        # Format entries for copying
        lines = []
        for entry in entries:
            lines.append(f"=== {entry.module} ===")
            lines.append(entry.title)
            if entry.pronunciation:
                lines.append(f"Pronunciation: {entry.pronunciation}")
            lines.append("")
            if entry.definition:
                lines.append(entry.definition)
            lines.append("")

        text = "\n".join(lines)

        try:
            import pyperclip
            pyperclip.copy(text)
            status.show_message(f"Gekopieerd: {strongs_view.current_number}")
        except ImportError:
            status.show_message("pyperclip niet beschikbaar")

    def _load_parallel_chapter(self) -> None:
        """Load current chapter into both parallel panes."""
        parallel = self.query_one("#parallel-view", ParallelView)

        # Set Strong's display flag
        parallel.set_show_strongs(self._diatheke_filters.strongs)

        # Left pane: primary module with current book/chapter
        left_title = f"{self._current_book} {self._current_chapter}"
        left_segments = self._backend.lookup_chapter(
            self._current_book, self._current_chapter
        )
        parallel.update_left(left_segments, self._current_module, left_title)

        # Right pane: secondary module
        if self._secondary_backend:
            # Use right pane's own book/chapter when unlinked
            if self._panes_linked:
                right_book = self._current_book
                right_chapter = self._current_chapter
            else:
                right_book = self._right_book
                right_chapter = self._right_chapter

            right_title = f"{right_book} {right_chapter}"
            right_segments = self._secondary_backend.lookup_chapter(right_book, right_chapter)
            parallel.update_right(right_segments, self._secondary_module, right_title)

    def action_page_down(self) -> None:
        """Page down (move multiple verses)."""
        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            for _ in range(10):
                if not left.next_verse():
                    break
            if self._panes_linked:
                parallel.query_one("#right-view", BibleView).set_current_verse(left.current_verse)
        else:
            view = self.query_one("#bible-view", BibleView)
            for _ in range(10):
                if not view.next_verse():
                    break
        self._update_status()

    def action_page_up(self) -> None:
        """Page up (move multiple verses)."""
        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            left = parallel.query_one("#left-view", BibleView)
            for _ in range(10):
                if not left.prev_verse():
                    break
            if self._panes_linked:
                parallel.query_one("#right-view", BibleView).set_current_verse(left.current_verse)
        else:
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

    def _close_command_mode(self) -> None:
        """Close command mode."""
        self._in_command_mode = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = False
        self.query_one("#status-bar", StatusBar).display = True
        if self._in_search_mode:
            self.query_one("#search-view", SearchView).focus()
        elif self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            if self._active_pane == "right":
                parallel.focus_right()
            else:
                parallel.focus_left()
        else:
            self.query_one("#bible-scroll").focus()

    # ==================== KWIC Search Mode ====================

    def _enter_kwic_search_mode(self) -> None:
        """Enter KWIC search mode - show search input."""
        self._in_command_mode = True
        self.query_one("#status-bar", StatusBar).display = False
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.display = True
        cmd_input.reset("/")
        cmd_input.focus()

    def _open_search_view(self, query: str) -> None:
        """Open the search view with results."""
        status = self.query_one("#status-bar", StatusBar)
        status.show_message(f"Zoeken naar '{query}'...")

        # Always fetch snippets so user can switch between modes freely
        results = self._backend.search(query, fetch_snippets=True)

        if not results:
            status.show_message(f"Geen resultaten voor '{query}'")
            return

        # Hide other views, show search view
        self.query_one("#bible-scroll").display = False
        self.query_one("#parallel-view").display = False
        self.query_one("#search-view").display = True

        # Populate search view with current display mode
        search_view = self.query_one("#search-view", SearchView)
        search_view.set_display_mode(self._search_display_mode)
        search_view.set_results(results, query)

        # Load preview context for first result (for modes 2 and 3)
        if results and self._search_display_mode >= 2:
            self._update_search_preview(results[0])

        self._in_search_mode = True
        status.set_mode("search")
        status.show_message(f"{len(results)} resultaten voor '{query}'")

    def _close_search_mode(self) -> None:
        """Close search mode and return to normal view."""
        self._in_search_mode = False

        # Hide search view
        self.query_one("#search-view").display = False
        self.query_one("#search-view", SearchView).clear_results()

        # Restore appropriate view
        if self._in_parallel_mode:
            self.query_one("#parallel-view").display = True
            self.query_one("#parallel-view", ParallelView).focus_left()
            self.query_one("#status-bar", StatusBar).set_mode("parallel")
        else:
            self.query_one("#bible-scroll").display = True
            self.query_one("#bible-scroll").focus()
            self.query_one("#status-bar", StatusBar).set_mode("normal")

    def _search_move_up(self) -> None:
        """Move to previous search result."""
        search_view = self.query_one("#search-view", SearchView)
        search_view.move_up()
        hit = search_view.get_current_hit()
        if hit:
            self._update_search_preview(hit)

    def _search_move_down(self) -> None:
        """Move to next search result."""
        search_view = self.query_one("#search-view", SearchView)
        search_view.move_down()
        hit = search_view.get_current_hit()
        if hit:
            self._update_search_preview(hit)

    def _search_page_down(self) -> None:
        """Move down 10 search results."""
        search_view = self.query_one("#search-view", SearchView)
        for _ in range(10):
            search_view.move_down()
        hit = search_view.get_current_hit()
        if hit:
            self._update_search_preview(hit)

    def _search_page_up(self) -> None:
        """Move up 10 search results."""
        search_view = self.query_one("#search-view", SearchView)
        for _ in range(10):
            search_view.move_up()
        hit = search_view.get_current_hit()
        if hit:
            self._update_search_preview(hit)

    def _search_goto_result(self) -> None:
        """Go to the selected search result."""
        search_view = self.query_one("#search-view", SearchView)
        hit = search_view.get_current_hit()
        if hit:
            self._close_search_mode()
            self._current_book = hit.book
            self._current_chapter = hit.chapter
            self._load_chapter()
            self._get_active_view().move_to_verse(hit.verse)
            self._get_active_view().set_search_query(self._chapter_search_query)
            self._update_status()

    def _search_preview_module_picker(self) -> None:
        """Open module picker for search preview pane."""
        self._in_picker_mode = True
        self._picking_search_preview_module = True
        current = self._search_preview_module or self._current_module
        picker = ModulePicker(current_module=current, )
        self.mount(picker)
        picker.focus()

    def _update_search_preview(self, hit) -> None:
        """Update the search preview pane with chapter context."""
        # Use search preview backend if available, otherwise use main backend
        backend = self._search_preview_backend or self._backend
        module = self._search_preview_module or self._current_module

        # Load the chapter for preview
        segments = backend.lookup_chapter(hit.book, hit.chapter)
        search_view = self.query_one("#search-view", SearchView)
        title = f"{hit.book} {hit.chapter} [{module}]"
        search_view.update_preview_context(segments, title)

    # ==================== Event Handlers ====================

    def on_command_input_command_submitted(
        self, event: CommandInput.CommandSubmitted
    ) -> None:
        """Handle submitted command."""
        self._close_command_mode()

        command = event.command
        prefix = event.prefix

        if prefix == "/":
            # KWIC search
            if command.strip():
                self._chapter_search_query = command  # Save for highlighting
                self._open_search_view(command)
        elif prefix == "?":
            # Chapter search (Ctrl+F)
            self._do_chapter_search(command)
        elif prefix == ":":
            # Check if command is just a number (go to verse)
            if command.isdigit():
                self._goto_verse(int(command))
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
        self._set_active_book(event.book)
        self._set_active_chapter(event.chapter)

        if self._panes_linked or not self._in_parallel_mode:
            self._load_chapter()
        else:
            self._load_active_pane_chapter()

        if event.verse:
            view = self._get_active_view()
            view.move_to_verse(event.verse)
            if self._in_parallel_mode and self._panes_linked:
                parallel = self.query_one("#parallel-view", ParallelView)
                other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
                other.move_to_verse(event.verse)
        self._update_status()

    def on_book_picker_cancelled(self, event: BookPicker.Cancelled) -> None:
        """Handle picker cancellation."""
        self._close_picker()

    def on_module_picker_module_selected(
        self, event: ModulePicker.ModuleSelected
    ) -> None:
        """Handle module selection from picker."""
        self._close_picker()

        if self._picking_search_preview_module:
            # Update search preview module
            self._search_preview_module = event.module.name
            self._search_preview_backend = DiathekeBackend(self._search_preview_module)
            # Refresh preview with new module
            search_view = self.query_one("#search-view", SearchView)
            hit = search_view.get_current_hit()
            if hit:
                self._update_search_preview(hit)
            self.query_one("#status-bar", StatusBar).show_message(
                f"Preview module: {self._search_preview_module}"
            )
        elif self._picking_secondary_module:
            # Update secondary module for parallel view
            self._secondary_module = event.module.name
            self._secondary_backend = DiathekeBackend(self._secondary_module)
            self._secondary_backend.set_filters(self._diatheke_filters)
            if self._in_parallel_mode:
                self._load_parallel_chapter()
            self._update_status()
        else:
            # Update primary module
            self._current_module = event.module.name
            self._backend.set_module(self._current_module)
            self._load_chapter()

    def on_module_picker_cancelled(self, event: ModulePicker.Cancelled) -> None:
        """Handle picker cancellation."""
        self._close_picker()

    def on_dict_module_picker_modules_selected(
        self, event: DictModulePicker.ModulesSelected
    ) -> None:
        """Handle dictionary module selection."""
        self._close_picker()

        # Update the appropriate module list based on current Strong's number
        strongs_view = self.query_one("#strongs-view", StrongsView)
        current_num = strongs_view.current_number
        if current_num.startswith("H"):
            self._active_hebrew_modules = event.modules
        else:
            self._active_greek_modules = event.modules

        # Re-lookup current Strong's with new modules
        self._lookup_current_strongs()

        status = self.query_one("#status-bar", StatusBar)
        status.show_message(f"{len(event.modules)} woordenboeken geselecteerd")

    def on_dict_module_picker_cancelled(
        self, event: DictModulePicker.Cancelled
    ) -> None:
        """Handle dictionary module picker cancellation."""
        self._close_picker()

    def _close_picker(self) -> None:
        """Close any open picker."""
        self._in_picker_mode = False
        self._picking_search_preview_module = False
        self._picking_secondary_module = False
        self._picking_dict_modules = False
        for picker in self.query("BookPicker, ModulePicker, DictModulePicker"):
            picker.remove()
        if self._in_search_mode:
            self.query_one("#search-view", SearchView).focus()
        elif self._in_strongs_mode:
            self.query_one("#bible-scroll").focus()
        elif self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            if self._active_pane == "right":
                parallel.focus_right()
            else:
                parallel.focus_left()
        else:
            self.query_one("#bible-scroll").focus()

    # ==================== Helper Methods ====================

    def _get_active_book(self) -> str:
        """Get the book for the active pane."""
        if self._in_parallel_mode and not self._panes_linked and self._active_pane == "right":
            return self._right_book
        return self._current_book

    def _set_active_book(self, book: str) -> None:
        """Set the book for the active pane."""
        if self._in_parallel_mode and not self._panes_linked and self._active_pane == "right":
            self._right_book = book
        else:
            self._current_book = book
            if self._panes_linked:
                self._right_book = book

    def _get_active_chapter(self) -> int:
        """Get the chapter for the active pane."""
        if self._in_parallel_mode and not self._panes_linked and self._active_pane == "right":
            return self._right_chapter
        return self._current_chapter

    def _set_active_chapter(self, chapter: int) -> None:
        """Set the chapter for the active pane."""
        if self._in_parallel_mode and not self._panes_linked and self._active_pane == "right":
            self._right_chapter = chapter
        else:
            self._current_chapter = chapter
            if self._panes_linked:
                self._right_chapter = chapter

    def _get_active_view(self) -> BibleView:
        """Get the active BibleView widget."""
        if self._in_parallel_mode:
            parallel = self.query_one("#parallel-view", ParallelView)
            if self._active_pane == "right":
                return parallel.query_one("#right-view", BibleView)
            return parallel.query_one("#left-view", BibleView)
        return self.query_one("#bible-view", BibleView)

    def _get_active_backend(self) -> DiathekeBackend:
        """Get the backend for the active pane."""
        if self._in_parallel_mode and self._active_pane == "right" and self._secondary_backend:
            return self._secondary_backend
        return self._backend

    def _load_chapter(self) -> None:
        """Load the current chapter (for single view or linked parallel)."""
        segments = self._backend.lookup_chapter(
            self._current_book, self._current_chapter
        )

        view = self.query_one("#bible-view", BibleView)
        view.set_show_strongs(self._diatheke_filters.strongs)
        view.update_content(segments, f"{self._current_book} {self._current_chapter}")

        scroll = self.query_one("#bible-scroll", VerticalScroll)
        scroll.scroll_home()

        # Also update parallel view if active
        if self._in_parallel_mode:
            self._load_parallel_chapter()

        # Exit visual mode on chapter change
        if self._in_visual_mode:
            self._in_visual_mode = False
            self.query_one("#status-bar", StatusBar).set_mode("normal")

        self._update_status()

    def _load_active_pane_chapter(self) -> None:
        """Load chapter for only the active pane (when unlinked)."""
        if not self._in_parallel_mode:
            self._load_chapter()
            return

        parallel = self.query_one("#parallel-view", ParallelView)
        book = self._get_active_book()
        chapter = self._get_active_chapter()
        backend = self._get_active_backend()

        segments = backend.lookup_chapter(book, chapter)
        title = f"{book} {chapter}"

        if self._active_pane == "right":
            right = parallel.query_one("#right-view", BibleView)
            right.update_content(segments, title)
        else:
            left = parallel.query_one("#left-view", BibleView)
            left.update_content(segments, title)
            # Update header
            parallel.update_left(segments, self._current_module, title)

        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar with current position."""
        status = self.query_one("#status-bar", StatusBar)

        if self._in_parallel_mode:
            # Show position for active pane
            view = self._get_active_view()
            book = self._get_active_book()
            chapter = self._get_active_chapter()

            if self._in_visual_mode:
                start, end = view.get_visual_range()
                status.set_position(book, chapter, start, end if end != start else None)
            else:
                status.set_position(book, chapter, view.current_verse)

            # Show modules with active indicator
            if self._panes_linked:
                status.set_module(f"{self._current_module} | {self._secondary_module}")
            else:
                left_mod = f"[{self._current_module}]" if self._active_pane == "left" else self._current_module
                right_mod = f"[{self._secondary_module}]" if self._active_pane == "right" else self._secondary_module
                status.set_module(f"{left_mod} | {right_mod}")
        else:
            view = self.query_one("#bible-view", BibleView)
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

    def _do_chapter_search(self, query: str) -> None:
        """Search within current chapter (Ctrl+F)."""
        if not query:
            return

        self._chapter_search_query = query
        self._search_matches = []
        self._search_match_index = 0

        # Get segments from active view
        view = self._get_active_view()
        segments = view._segments

        # Find verses containing the query
        query_lower = query.lower()
        for seg in segments:
            if query_lower in seg.text.lower():
                self._search_matches.append(seg.verse)

        status = self.query_one("#status-bar", StatusBar)

        if self._search_matches:
            # Set search query for highlighting on active view
            view.set_search_query(query)
            # Also highlight on other pane if linked
            if self._in_parallel_mode and self._panes_linked:
                parallel = self.query_one("#parallel-view", ParallelView)
                other = parallel.query_one("#right-view" if self._active_pane == "left" else "#left-view", BibleView)
                other.set_search_query(query)

            # Go to first match
            first_verse = self._search_matches[0]
            self._goto_verse(first_verse)
            status.show_message(
                f"Gevonden: {len(self._search_matches)} matches - n/N voor volgende/vorige"
            )
        else:
            status.show_message(f"Niet gevonden: '{query}'")

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
                if self._in_parallel_mode:
                    parallel = self.query_one("#parallel-view", ParallelView)
                    parallel.query_one("#left-view", BibleView).move_to_verse(data["verse"])
                    parallel.query_one("#right-view", BibleView).move_to_verse(data["verse"])
                else:
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
        elif action == "set_search_mode":
            data = result.data or {}
            mode = data.get("mode", 2)
            self._search_display_mode = mode
            mode_names = {
                1: "KWIC (alleen lijst)",
                2: "Referenties + preview",
                3: "KWIC + preview",
            }
            self.query_one("#status-bar", StatusBar).show_message(
                f"Zoekmodus: {mode_names[mode]}"
            )
            # Update search view if currently in search mode
            if self._in_search_mode:
                search_view = self.query_one("#search-view", SearchView)
                search_view.set_display_mode(mode)
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
