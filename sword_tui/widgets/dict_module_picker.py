"""Dictionary module picker widget for selecting Strong's lookup modules."""

from typing import List, Set

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from sword_tui.backend.modules import ModuleInfo, get_installed_modules


class ModuleCheckbox(Static):
    """A single module with checkbox display."""

    DEFAULT_CSS = """
    ModuleCheckbox {
        width: 100%;
        height: 1;
        padding: 0 2;
        background: $surface;
    }
    ModuleCheckbox.selected {
        background: $surface-lighten-1;
    }
    ModuleCheckbox.cursor {
        background: $primary-darken-1;
    }
    """

    def __init__(self, module: ModuleInfo, checked: bool = False, **kwargs):
        super().__init__("", **kwargs)
        self._module = module
        self._checked = checked
        self._is_cursor = False
        self._render()

    def _render(self) -> None:
        """Render the checkbox with module name."""
        text = Text()

        # Checkbox
        if self._checked:
            text.append("[✓] ", style="bold green")
        else:
            text.append("[ ] ", style="dim")

        # Module name
        if self._is_cursor:
            text.append(self._module.name, style="bold")
        else:
            text.append(self._module.name)

        # Module description if available
        if self._module.description:
            text.append(f"  {self._module.description[:40]}", style="dim")

        self.update(text)

    @property
    def module(self) -> ModuleInfo:
        """Get the module info."""
        return self._module

    @property
    def checked(self) -> bool:
        """Get checked state."""
        return self._checked

    def toggle(self) -> None:
        """Toggle the checked state."""
        self._checked = not self._checked
        self._render()

    def set_cursor(self, is_cursor: bool) -> None:
        """Set whether this is the cursor position."""
        self._is_cursor = is_cursor
        self.remove_class("cursor")
        if is_cursor:
            self.add_class("cursor")
        self._render()


class DictModulePicker(Widget):
    """Widget for selecting dictionary modules with multi-select checkboxes."""

    class ModulesSelected(Message):
        """Message sent when user confirms module selection."""

        def __init__(self, modules: List[str]) -> None:
            super().__init__()
            self.modules = modules

    class Cancelled(Message):
        """Message sent when picker is cancelled."""
        pass

    DEFAULT_CSS = """
    DictModulePicker {
        width: 60%;
        height: 60%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        layer: dialog;
        align: center middle;
    }

    DictModulePicker > #picker-title {
        width: 100%;
        height: 1;
        background: $primary-darken-1;
        color: $text;
        text-align: center;
        text-style: bold;
    }

    DictModulePicker > #picker-scroll {
        height: 100%;
        margin: 1 0;
    }

    DictModulePicker > #picker-footer {
        width: 100%;
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        title: str = "Select Dictionary Modules",
        current_modules: List[str] = None,
        module_type: str = "Lexicons / Dictionaries",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._title = title
        self._current_modules: Set[str] = set(current_modules or [])
        self._module_type = module_type
        self._cursor_index = 0
        self._checkboxes: List[ModuleCheckbox] = []

    def compose(self) -> ComposeResult:
        yield Static(self._title, id="picker-title")
        with VerticalScroll(id="picker-scroll"):
            yield Vertical(id="picker-content")
        yield Static("j/k:navigate  Space:toggle  Enter:confirm  Esc:cancel", id="picker-footer")

    def on_mount(self) -> None:
        """Populate the picker with available dictionary modules."""
        modules = get_installed_modules()

        # Filter to dictionary/lexicon type modules
        dict_modules = [
            m for m in modules
            if m.module_type and (
                "lex" in m.module_type.lower() or
                "dict" in m.module_type.lower() or
                "strong" in m.name.lower()
            )
        ]

        # If no dict modules found, show all modules
        if not dict_modules:
            dict_modules = modules

        content = self.query_one("#picker-content", Vertical)

        for i, mod in enumerate(dict_modules):
            checked = mod.name in self._current_modules
            checkbox = ModuleCheckbox(mod, checked=checked)
            if i == 0:
                checkbox.set_cursor(True)
            self._checkboxes.append(checkbox)
            content.mount(checkbox)

        self.focus()

    def on_key(self, event) -> None:
        """Handle key events."""
        key = event.key
        char = event.character

        if key == "escape":
            event.stop()
            self.post_message(self.Cancelled())
            self.remove()
        elif key == "enter":
            event.stop()
            self._confirm_selection()
        elif key == "space":
            event.stop()
            self._toggle_current()
        elif char == "j" or key == "down":
            event.stop()
            self._move_cursor(1)
        elif char == "k" or key == "up":
            event.stop()
            self._move_cursor(-1)

    def _move_cursor(self, delta: int) -> None:
        """Move the cursor up or down."""
        if not self._checkboxes:
            return

        # Clear old cursor
        if 0 <= self._cursor_index < len(self._checkboxes):
            self._checkboxes[self._cursor_index].set_cursor(False)

        # Update index
        self._cursor_index = max(0, min(len(self._checkboxes) - 1, self._cursor_index + delta))

        # Set new cursor
        self._checkboxes[self._cursor_index].set_cursor(True)
        self._checkboxes[self._cursor_index].scroll_visible()

    def _toggle_current(self) -> None:
        """Toggle the checkbox at the cursor."""
        if 0 <= self._cursor_index < len(self._checkboxes):
            self._checkboxes[self._cursor_index].toggle()

    def _confirm_selection(self) -> None:
        """Confirm selection and send message."""
        selected = [cb.module.name for cb in self._checkboxes if cb.checked]
        self.post_message(self.ModulesSelected(selected))
        self.remove()
