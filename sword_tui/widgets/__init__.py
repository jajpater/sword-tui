"""Textual widgets for sword-tui."""

from sword_tui.widgets.bible_view import BibleView
from sword_tui.widgets.parallel_view import ParallelView
from sword_tui.widgets.kwic_list import KWICList
from sword_tui.widgets.book_picker import BookPicker
from sword_tui.widgets.command_input import CommandInput
from sword_tui.widgets.module_picker import ModulePicker
from sword_tui.widgets.status_bar import StatusBar

__all__ = [
    "BibleView",
    "ParallelView",
    "KWICList",
    "BookPicker",
    "CommandInput",
    "ModulePicker",
    "StatusBar",
]
