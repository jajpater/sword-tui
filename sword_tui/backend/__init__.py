"""Diatheke backend for SWORD module access."""

from sword_tui.backend.diatheke import DiathekeBackend
from sword_tui.backend.modules import get_installed_modules, ModuleInfo

__all__ = ["DiathekeBackend", "get_installed_modules", "ModuleInfo"]
