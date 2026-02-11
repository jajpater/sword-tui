"""Tab state management for multiple workspaces."""

from dataclasses import dataclass, field
from typing import List, Optional

from sword_tui.jumplist import JumpList


@dataclass
class TabState:
    """Snapshot of all per-tab state."""

    name: str = ""
    # Navigation
    book: str = "Genesis"
    chapter: int = 1
    verse: int = 1
    module: str = "DutSVV"
    # Main modes (mutually exclusive)
    in_parallel_mode: bool = False
    in_study_mode: bool = False
    # Side panels (combinable)
    in_strongs_mode: bool = False
    in_crossref_mode: bool = False
    in_jumplist_mode: bool = False
    # Parallel state
    secondary_module: str = ""
    right_book: str = "Genesis"
    right_chapter: int = 1
    panes_linked: bool = True
    active_pane: str = "left"
    # Study state
    study_commentary_module: str = "DutKant"
    study_active_pane: int = 0
    study_include_bible_xrefs: bool = False
    # Filters
    strongs_filter: bool = False
    footnotes_filter: bool = False
    # Focus
    crossref_pane_focused: bool = False
    strongs_pane_focused: bool = False
    # Jumplist (not serialized, session-only)
    _jumplist_ref: JumpList = field(default_factory=JumpList, repr=False)

    def to_dict(self) -> dict:
        """Serialize for config.json (without jumplist)."""
        return {
            "name": self.name,
            "book": self.book,
            "chapter": self.chapter,
            "verse": self.verse,
            "module": self.module,
            "in_parallel_mode": self.in_parallel_mode,
            "in_study_mode": self.in_study_mode,
            "in_strongs_mode": self.in_strongs_mode,
            "in_crossref_mode": self.in_crossref_mode,
            "in_jumplist_mode": self.in_jumplist_mode,
            "secondary_module": self.secondary_module,
            "right_book": self.right_book,
            "right_chapter": self.right_chapter,
            "panes_linked": self.panes_linked,
            "active_pane": self.active_pane,
            "study_commentary_module": self.study_commentary_module,
            "study_active_pane": self.study_active_pane,
            "study_include_bible_xrefs": self.study_include_bible_xrefs,
            "strongs_filter": self.strongs_filter,
            "footnotes_filter": self.footnotes_filter,
            "crossref_pane_focused": self.crossref_pane_focused,
            "strongs_pane_focused": self.strongs_pane_focused,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TabState":
        """Deserialize from config.json."""
        return cls(
            name=data.get("name", ""),
            book=data.get("book", "Genesis"),
            chapter=data.get("chapter", 1),
            verse=data.get("verse", 1),
            module=data.get("module", "DutSVV"),
            in_parallel_mode=data.get("in_parallel_mode", False),
            in_study_mode=data.get("in_study_mode", False),
            in_strongs_mode=data.get("in_strongs_mode", False),
            in_crossref_mode=data.get("in_crossref_mode", False),
            in_jumplist_mode=data.get("in_jumplist_mode", False),
            secondary_module=data.get("secondary_module", ""),
            right_book=data.get("right_book", "Genesis"),
            right_chapter=data.get("right_chapter", 1),
            panes_linked=data.get("panes_linked", True),
            active_pane=data.get("active_pane", "left"),
            study_commentary_module=data.get("study_commentary_module", "DutKant"),
            study_active_pane=data.get("study_active_pane", 0),
            study_include_bible_xrefs=data.get("study_include_bible_xrefs", False),
            strongs_filter=data.get("strongs_filter", False),
            footnotes_filter=data.get("footnotes_filter", False),
            crossref_pane_focused=data.get("crossref_pane_focused", False),
            strongs_pane_focused=data.get("strongs_pane_focused", False),
        )


class TabManager:
    """Manages the tab list."""

    MAX_TABS = 9

    def __init__(self) -> None:
        self._tabs: List[TabState] = [TabState()]
        self._active_index: int = 0

    @property
    def active(self) -> TabState:
        """Get the active tab state."""
        return self._tabs[self._active_index]

    @property
    def active_index(self) -> int:
        return self._active_index

    @property
    def count(self) -> int:
        return len(self._tabs)

    @property
    def tabs(self) -> List[TabState]:
        return self._tabs

    def new_tab(self, state: Optional[TabState] = None) -> int:
        """Add a new tab after the current one. Returns index of the new tab."""
        if len(self._tabs) >= self.MAX_TABS:
            return -1
        if state is None:
            state = TabState()
        insert_at = self._active_index + 1
        self._tabs.insert(insert_at, state)
        self._active_index = insert_at
        return insert_at

    def close_tab(self, index: Optional[int] = None) -> bool:
        """Close a tab. Returns False if it's the last tab."""
        if len(self._tabs) <= 1:
            return False
        if index is None:
            index = self._active_index
        if index < 0 or index >= len(self._tabs):
            return False
        self._tabs.pop(index)
        if self._active_index >= len(self._tabs):
            self._active_index = len(self._tabs) - 1
        elif self._active_index > index:
            self._active_index -= 1
        return True

    def switch_to(self, index: int) -> bool:
        """Switch to tab at index. Returns True on success."""
        if index < 0 or index >= len(self._tabs):
            return False
        self._active_index = index
        return True

    def next_tab(self) -> int:
        """Switch to next tab (cyclic). Returns new index."""
        self._active_index = (self._active_index + 1) % len(self._tabs)
        return self._active_index

    def prev_tab(self) -> int:
        """Switch to previous tab (cyclic). Returns new index."""
        self._active_index = (self._active_index - 1) % len(self._tabs)
        return self._active_index

    def to_list(self) -> List[dict]:
        """Serialize all tabs for config."""
        return [tab.to_dict() for tab in self._tabs]

    @classmethod
    def from_list(cls, data: List[dict], active: int = 0) -> "TabManager":
        """Deserialize from config."""
        mgr = cls()
        if data:
            mgr._tabs = [TabState.from_dict(d) for d in data]
            mgr._active_index = max(0, min(active, len(mgr._tabs) - 1))
        return mgr
