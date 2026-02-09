"""Diatheke backend for SWORD module access."""

from sword_tui.backend.diatheke import DiathekeBackend, DiathekeFilters
from sword_tui.backend.modules import get_installed_modules, ModuleInfo
from sword_tui.backend.dictionary import DictionaryBackend, DictionaryEntry

__all__ = [
    "DiathekeBackend",
    "DiathekeFilters",
    "DictionaryBackend",
    "DictionaryEntry",
    "get_installed_modules",
    "ModuleInfo",
]
