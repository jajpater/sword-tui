"""VerseList manager for CRUD and JSON persistence."""

import json
from pathlib import Path
from typing import List, Optional

from sword_tui.data.types import VerseList, VerseRef


class VerseListManager:
    """Manages verse lists with JSON persistence."""

    def __init__(self) -> None:
        self._lists: List[VerseList] = []
        self._config_path = Path.home() / ".config" / "sword-tui" / "verselists.json"
        self._load()

    def _load(self) -> None:
        """Load verse lists from disk."""
        if not self._config_path.exists():
            return
        try:
            with open(self._config_path) as f:
                data = json.load(f)
            self._lists = [VerseList.from_dict(vl) for vl in data.get("verselists", [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._lists = []

    def _save(self) -> None:
        """Save verse lists to disk."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"verselists": [vl.to_dict() for vl in self._lists]}
        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)

    def create(self, name: str) -> VerseList:
        """Create a new verse list."""
        vl = VerseList(name=name)
        self._lists.append(vl)
        self._save()
        return vl

    def delete(self, name: str) -> bool:
        """Delete a verse list by name. Returns True if found."""
        for i, vl in enumerate(self._lists):
            if vl.name.lower() == name.lower():
                self._lists.pop(i)
                self._save()
                return True
        return False

    def get(self, name: str) -> Optional[VerseList]:
        """Get a verse list by name."""
        for vl in self._lists:
            if vl.name.lower() == name.lower():
                return vl
        return None

    def list_all(self) -> List[VerseList]:
        """Get all verse lists."""
        return self._lists.copy()

    def add_ref(self, name: str, ref: VerseRef) -> bool:
        """Add a verse reference to a list. Returns True if found."""
        vl = self.get(name)
        if not vl:
            return False
        # Avoid duplicates
        for existing in vl.refs:
            if existing.book == ref.book and existing.chapter == ref.chapter and existing.verse == ref.verse:
                return True
        vl.refs.append(ref)
        self._save()
        return True

    def remove_ref(self, name: str, index: int) -> bool:
        """Remove a verse reference by index. Returns True if found."""
        vl = self.get(name)
        if not vl or index < 0 or index >= len(vl.refs):
            return False
        vl.refs.pop(index)
        self._save()
        return True
