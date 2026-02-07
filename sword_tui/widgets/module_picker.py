"""SWORD module picker widget."""

from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, ListView, ListItem, Static

from sword_tui.backend.modules import ModuleInfo, get_bible_modules


class ModulePicker(Widget):
    """Widget for selecting a SWORD Bible module."""

    DEFAULT_CSS = """
    ModulePicker {
        width: 60;
        height: 15;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    ModulePicker > .picker-title {
        height: 1;
        text-style: bold;
        color: $primary;
    }

    ModulePicker > .picker-input {
        height: 3;
        margin-bottom: 1;
    }

    ModulePicker > .picker-list {
        height: 1fr;
    }

    ModulePicker > .picker-hint {
        height: 1;
        color: $text-muted;
    }
    """

    class ModuleSelected(Message):
        """Message sent when a module is selected."""

        def __init__(self, module: ModuleInfo) -> None:
            self.module = module
            super().__init__()

    class Cancelled(Message):
        """Message sent when picker is cancelled."""

        pass

    def __init__(self, current_module: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_module = current_module
        self._modules: List[ModuleInfo] = []
        self._filtered: List[ModuleInfo] = []

    def compose(self) -> ComposeResult:
        yield Static("Kies module", classes="picker-title")
        yield Input(
            placeholder="Zoeken...",
            classes="picker-input",
            id="picker-input"
        )
        yield ListView(classes="picker-list", id="picker-list")
        yield Static("Enter=selecteer, Esc=annuleer", classes="picker-hint")

    def on_mount(self) -> None:
        """Initialize the picker."""
        self._modules = get_bible_modules()
        self._filtered = self._modules
        self._update_list()
        self.query_one("#picker-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for filtering."""
        query = event.value.lower().strip()

        if not query:
            self._filtered = self._modules
        else:
            self._filtered = [
                m for m in self._modules
                if query in m.name.lower() or query in m.description.lower()
            ]

        self._update_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key."""
        event.stop()
        self._select_current()

    def on_key(self, event) -> None:
        """Handle key events."""
        key = event.key

        if key == "escape":
            event.stop()
            self.post_message(self.Cancelled())
        elif key == "down":
            event.stop()
            lst = self.query_one("#picker-list", ListView)
            if lst.index is not None and lst.index < len(self._filtered) - 1:
                lst.index += 1
        elif key == "up":
            event.stop()
            lst = self.query_one("#picker-list", ListView)
            if lst.index is not None and lst.index > 0:
                lst.index -= 1

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection."""
        event.stop()
        self._select_current()

    def _update_list(self) -> None:
        """Update the module list display."""
        lst = self.query_one("#picker-list", ListView)
        lst.clear()

        for module in self._filtered:
            text = Text()

            # Highlight current module
            name_style = "bold cyan"
            if module.name == self._current_module:
                name_style = "bold green"
                text.append("* ", style="bold green")
            else:
                text.append("  ")

            text.append(module.name.ljust(12), style=name_style)
            text.append(module.description, style="")

            lst.append(ListItem(Static(text)))

        if self._filtered:
            lst.index = 0

    def _select_current(self) -> None:
        """Select the current module."""
        lst = self.query_one("#picker-list", ListView)
        if lst.index is not None and lst.index < len(self._filtered):
            module = self._filtered[lst.index]
            self.post_message(self.ModuleSelected(module))
