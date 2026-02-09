"""Diatheke backend for SWORD module access."""

from sword_tui.backend.diatheke import DiathekeBackend, DiathekeFilters
from sword_tui.backend.modules import get_installed_modules, ModuleInfo
from sword_tui.backend.dictionary import DictionaryBackend, DictionaryEntry
from sword_tui.backend.crossref import CrossRefBackend
from sword_tui.backend.commentary import CommentaryBackend, CommentaryEntry

__all__ = [
    "DiathekeBackend",
    "DiathekeFilters",
    "DictionaryBackend",
    "DictionaryEntry",
    "CrossRefBackend",
    "CommentaryBackend",
    "CommentaryEntry",
    "get_installed_modules",
    "ModuleInfo",
]
