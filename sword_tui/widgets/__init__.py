"""Textual widgets for sword-tui."""

from sword_tui.widgets.bible_view import BibleView
from sword_tui.widgets.parallel_view import ParallelView
from sword_tui.widgets.kwic_list import KWICList
from sword_tui.widgets.book_picker import BookPicker
from sword_tui.widgets.command_input import CommandInput
from sword_tui.widgets.module_picker import ModulePicker
from sword_tui.widgets.status_bar import StatusBar
from sword_tui.widgets.search_view import SearchView
from sword_tui.widgets.strongs_view import StrongsView
from sword_tui.widgets.dict_module_picker import DictModulePicker

__all__ = [
    "BibleView",
    "ParallelView",
    "KWICList",
    "BookPicker",
    "CommandInput",
    "ModulePicker",
    "StatusBar",
    "SearchView",
    "StrongsView",
    "DictModulePicker",
]
