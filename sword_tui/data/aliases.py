"""Alias resolution for Bible book names."""

from typing import List, Optional

from sword_tui.data.canon import (
    CanonBook,
    resolve_alias as _resolve_alias,
    search_books as _search_books,
)


def resolve_alias(alias: str, *, fuzzy: bool = True) -> Optional[str]:
    """Resolve a book alias to the canonical name.

    Args:
        alias: Book name or alias (e.g., "gen", "Genesis", "1mo")
        fuzzy: Enable fuzzy prefix matching

    Returns:
        Canonical book name or None if not found
    """
    return _resolve_alias(alias, fuzzy=fuzzy)


def suggest_books(prefix: str, limit: int = 12) -> List[CanonBook]:
    """Suggest books matching a prefix.

    Args:
        prefix: Search prefix
        limit: Maximum number of suggestions

    Returns:
        List of matching CanonBook objects
    """
    return _search_books(prefix, limit)
