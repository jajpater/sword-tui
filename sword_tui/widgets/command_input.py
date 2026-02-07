"""Vim-style command input widget."""

from typing import List, Optional

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static


class CommandInput(Widget):
    """Vim-like command input with history and completion."""

    DEFAULT_CSS = """
    CommandInput {
        dock: bottom;
        height: 1;
        layout: horizontal;
        background: $surface;
    }

    CommandInput > .command-prefix {
        width: 1;
        height: 1;
        color: $text;
    }

    CommandInput > .command-text {
        width: 1fr;
        height: 1;
        border: none;
        padding: 0;
        background: $surface;
    }

    CommandInput > .command-text:focus {
        border: none;
    }
    """

    class CommandSubmitted(Message):
        """Message sent when a command is submitted."""

        def __init__(self, command: str, prefix: str) -> None:
            self.command = command
            self.prefix = prefix
            super().__init__()

    class CommandCancelled(Message):
        """Message sent when command input is cancelled."""

        pass

    def __init__(
        self,
        commands: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._commands = commands or []
        self._history: List[str] = []
        self._history_index = -1
        self._prefix = ":"
        self._saved_input = ""

    def compose(self) -> ComposeResult:
        yield Static(":", classes="command-prefix", id="cmd-prefix")
        yield Input(placeholder="", classes="command-text", id="cmd-input")

    @property
    def prefix_widget(self) -> Static:
        """Get the prefix widget."""
        return self.query_one("#cmd-prefix", Static)

    @property
    def input_widget(self) -> Input:
        """Get the input widget."""
        return self.query_one("#cmd-input", Input)

    def reset(self, prefix: str = ":") -> None:
        """Reset the input with given prefix.

        Args:
            prefix: Command prefix (: for commands, / for search)
        """
        self._prefix = prefix
        self.prefix_widget.update(prefix)
        self.input_widget.value = ""
        self._history_index = -1
        self._saved_input = ""

    def set_value(self, value: str) -> None:
        """Set the input value.

        Args:
            value: Text to set
        """
        self.input_widget.value = value

    def focus(self, scroll_visible: bool = True) -> None:
        """Focus the input widget."""
        self.input_widget.focus(scroll_visible=scroll_visible)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key."""
        event.stop()
        command = self.input_widget.value.strip()

        if command:
            self._add_to_history(command)

        self.post_message(self.CommandSubmitted(command, self._prefix))

    def on_key(self, event) -> None:
        """Handle special keys."""
        key = event.key

        if key == "escape":
            event.prevent_default()
            event.stop()
            self.post_message(self.CommandCancelled())
        elif key == "up":
            event.prevent_default()
            event.stop()
            self._history_previous()
        elif key == "down":
            event.prevent_default()
            event.stop()
            self._history_next()
        elif key == "tab":
            event.prevent_default()
            event.stop()
            self._complete()

    def _add_to_history(self, command: str) -> None:
        """Add command to history.

        Args:
            command: Command to add
        """
        # Don't add duplicates of the last command
        if self._history and self._history[-1] == command:
            return
        self._history.append(command)
        # Limit history size
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def _history_previous(self) -> None:
        """Navigate to previous history entry."""
        if not self._history:
            return

        if self._history_index == -1:
            # Save current input before navigating
            self._saved_input = self.input_widget.value
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1

        self.input_widget.value = self._history[self._history_index]

    def _history_next(self) -> None:
        """Navigate to next history entry."""
        if self._history_index == -1:
            return

        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.input_widget.value = self._history[self._history_index]
        else:
            # Return to saved input
            self._history_index = -1
            self.input_widget.value = self._saved_input

    def _complete(self) -> None:
        """Tab completion for commands."""
        if self._prefix != ":" or not self._commands:
            return

        current = self.input_widget.value.lstrip()
        if not current:
            return

        # Get the command part (first word)
        parts = current.split(maxsplit=1)
        cmd_part = parts[0]

        # Find matching commands
        matches = [c for c in self._commands if c.startswith(cmd_part)]

        if len(matches) == 1:
            # Unique match - complete with space
            rest = parts[1] if len(parts) > 1 else ""
            self.input_widget.value = matches[0] + " " + rest
        elif len(matches) > 1:
            # Multiple matches - complete common prefix
            common = matches[0]
            for match in matches[1:]:
                while not match.startswith(common):
                    common = common[:-1]

            if len(common) > len(cmd_part):
                rest = parts[1] if len(parts) > 1 else ""
                self.input_widget.value = common + (" " + rest if rest else "")
