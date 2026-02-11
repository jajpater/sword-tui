"""Commentary module picker widget for study mode."""

from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Static


class CommentaryPicker(Widget):
    """Widget for selecting a commentary module."""

    DEFAULT_CSS = """
    CommentaryPicker {
        width: 50;
        height: 12;
        background: $surface;
        border: solid $primary;
        padding: 1;
        align: center middle;
        layer: modal;
    }

    CommentaryPicker > .picker-title {
        height: 1;
        text-style: bold;
        color: $primary;
    }

    CommentaryPicker > .picker-list {
        height: 1fr;
    }

    CommentaryPicker > .picker-hint {
        height: 1;
        color: $text-muted;
    }
    """

    class CommentarySelected(Message):
        """Message sent when a commentary module is selected."""

        def __init__(self, module: str) -> None:
            self.module = module
            super().__init__()

    class Cancelled(Message):
        """Message sent when picker is cancelled."""

        pass

    def __init__(
        self, modules: List[str], current_module: str = "", **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._modules = modules
        self._current_module = current_module

    def compose(self) -> ComposeResult:
        yield Static("Kies commentaar module", classes="picker-title")
        yield ListView(classes="picker-list", id="picker-list")
        yield Static("j/k nav, Enter=selecteer, Esc=annuleer", classes="picker-hint")

    def on_mount(self) -> None:
        lst = self.query_one("#picker-list", ListView)
        for mod in self._modules:
            txt = Text()
            if mod == self._current_module:
                txt.append("* ", style="bold green")
                txt.append(mod, style="bold green")
            else:
                txt.append("  ")
                txt.append(mod, style="cyan")
            lst.append(ListItem(Static(txt)))

        # Pre-select current module
        for i, mod in enumerate(self._modules):
            if mod == self._current_module:
                lst.index = i
                break

    def on_key(self, event) -> None:
        key = event.key
        if key == "escape":
            event.stop()
            self.post_message(self.Cancelled())
        elif key == "down" or event.character == "j":
            event.stop()
            lst = self.query_one("#picker-list", ListView)
            if lst.index is not None and lst.index < len(self._modules) - 1:
                lst.index += 1
        elif key == "up" or event.character == "k":
            event.stop()
            lst = self.query_one("#picker-list", ListView)
            if lst.index is not None and lst.index > 0:
                lst.index -= 1
        elif key == "enter":
            event.stop()
            self._select_current()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        event.stop()
        self._select_current()

    def _select_current(self) -> None:
        lst = self.query_one("#picker-list", ListView)
        if lst.index is not None and lst.index < len(self._modules):
            self.post_message(self.CommentarySelected(self._modules[lst.index]))
