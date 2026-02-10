"""Jumplist for navigation history (vim-style Ctrl+O / Ctrl+I)."""

from dataclasses import dataclass
from typing import Optional

MAX_ENTRIES = 100


@dataclass
class JumpEntry:
    """A single location in the jumplist."""

    book: str
    chapter: int
    verse: int


class JumpList:
    """Navigation history with back/forward support.

    Records locations before big jumps (chapter/book navigation, goto,
    cross-ref, search results). Small movements (j/k, Ctrl+D/U) are
    not recorded.
    """

    def __init__(self) -> None:
        self._entries: list[JumpEntry] = []
        self._cursor: int = -1  # -1 means "at the end" (no history yet)

    def record(self, book: str, chapter: int, verse: int) -> None:
        """Record current location before a jump.

        If cursor is not at the end, forward history is truncated.
        """
        entry = JumpEntry(book=book, chapter=chapter, verse=verse)

        # Truncate forward history if we're not at the end
        if self._entries and self._cursor < len(self._entries) - 1:
            self._entries = self._entries[: self._cursor + 1]

        self._entries.append(entry)

        # Enforce max size
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self._entries[-MAX_ENTRIES:]

        self._cursor = len(self._entries) - 1

    def back(self, current_book: str, current_chapter: int, current_verse: int) -> Optional[JumpEntry]:
        """Go back in history (Ctrl+O).

        If at the end of the list, saves current position first so
        Ctrl+I can return to it.
        """
        if not self._entries:
            return None

        # If at the end, save current position so we can come back
        if self._cursor == len(self._entries) - 1:
            current = JumpEntry(book=current_book, chapter=current_chapter, verse=current_verse)
            # Only append if different from the last entry
            last = self._entries[-1]
            if last.book != current.book or last.chapter != current.chapter or last.verse != current.verse:
                self._entries.append(current)
                self._cursor = len(self._entries) - 1

        if self._cursor <= 0:
            return None

        self._cursor -= 1
        return self._entries[self._cursor]

    def forward(self) -> Optional[JumpEntry]:
        """Go forward in history (Ctrl+I)."""
        if not self._entries:
            return None

        if self._cursor >= len(self._entries) - 1:
            return None

        self._cursor += 1
        return self._entries[self._cursor]

    @property
    def entries(self) -> list[JumpEntry]:
        """Return a copy of all entries."""
        return self._entries.copy()

    @property
    def cursor(self) -> int:
        """Return the current cursor position."""
        return self._cursor

    def jump_to(self, index: int) -> Optional[JumpEntry]:
        """Set cursor to given index and return the entry."""
        if not self._entries or index < 0 or index >= len(self._entries):
            return None
        self._cursor = index
        return self._entries[self._cursor]
