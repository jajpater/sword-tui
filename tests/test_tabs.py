"""Tests for tab state management and tab commands."""

import pytest

from sword_tui.tab_state import TabState, TabManager
from sword_tui.commands.parser import parse_command, get_command_names, COMMAND_ALIASES


class TestTabState:
    """Test TabState dataclass."""

    def test_defaults(self):
        """Default values should be set."""
        tab = TabState()
        assert tab.book == "Genesis"
        assert tab.chapter == 1
        assert tab.verse == 1
        assert tab.in_parallel_mode is False
        assert tab.in_study_mode is False

    def test_to_dict_roundtrip(self):
        """to_dict -> from_dict should preserve all fields."""
        tab = TabState(
            name="Test Tab",
            book="Exodus",
            chapter=3,
            verse=14,
            module="KJV",
            in_parallel_mode=True,
            in_study_mode=False,
            in_strongs_mode=True,
            in_crossref_mode=False,
            in_jumplist_mode=True,
            secondary_module="ESV",
            right_book="Romans",
            right_chapter=8,
            panes_linked=False,
            active_pane="right",
            study_commentary_module="DutKant",
            study_active_pane=2,
            study_include_bible_xrefs=True,
            strongs_filter=True,
            footnotes_filter=True,
            crossref_pane_focused=True,
            strongs_pane_focused=False,
        )

        d = tab.to_dict()
        restored = TabState.from_dict(d)

        assert restored.name == "Test Tab"
        assert restored.book == "Exodus"
        assert restored.chapter == 3
        assert restored.verse == 14
        assert restored.module == "KJV"
        assert restored.in_parallel_mode is True
        assert restored.in_strongs_mode is True
        assert restored.in_jumplist_mode is True
        assert restored.secondary_module == "ESV"
        assert restored.right_book == "Romans"
        assert restored.right_chapter == 8
        assert restored.panes_linked is False
        assert restored.active_pane == "right"
        assert restored.study_active_pane == 2
        assert restored.study_include_bible_xrefs is True
        assert restored.strongs_filter is True
        assert restored.footnotes_filter is True
        assert restored.crossref_pane_focused is True

    def test_to_dict_no_jumplist(self):
        """Jumplist should not be serialized."""
        tab = TabState()
        d = tab.to_dict()
        assert "_jumplist_ref" not in d

    def test_from_dict_missing_keys(self):
        """from_dict should handle missing keys gracefully."""
        tab = TabState.from_dict({})
        assert tab.book == "Genesis"
        assert tab.chapter == 1
        assert tab.module == "DutSVV"


class TestTabManager:
    """Test TabManager."""

    def test_initial_state(self):
        """Should start with one tab."""
        mgr = TabManager()
        assert mgr.count == 1
        assert mgr.active_index == 0

    def test_new_tab(self):
        """new_tab should add after current."""
        mgr = TabManager()
        idx = mgr.new_tab(TabState(book="Romans"))
        assert idx == 1
        assert mgr.count == 2
        assert mgr.active_index == 1
        assert mgr.active.book == "Romans"

    def test_new_tab_max(self):
        """Should refuse when MAX_TABS reached."""
        mgr = TabManager()
        for i in range(TabManager.MAX_TABS - 1):
            mgr.new_tab()
        assert mgr.count == TabManager.MAX_TABS
        result = mgr.new_tab()
        assert result == -1
        assert mgr.count == TabManager.MAX_TABS

    def test_close_tab(self):
        """close_tab should remove and adjust index."""
        mgr = TabManager()
        mgr.new_tab(TabState(book="Exodus"))
        mgr.new_tab(TabState(book="Romans"))
        assert mgr.count == 3

        # Close middle tab (active is 2, close 1)
        mgr.switch_to(1)
        result = mgr.close_tab()
        assert result is True
        assert mgr.count == 2
        assert mgr.active.book == "Romans"

    def test_close_last_tab_refused(self):
        """Cannot close the last remaining tab."""
        mgr = TabManager()
        result = mgr.close_tab()
        assert result is False
        assert mgr.count == 1

    def test_switch_to(self):
        """switch_to should change active index."""
        mgr = TabManager()
        mgr.new_tab(TabState(book="Exodus"))
        mgr.switch_to(0)
        assert mgr.active_index == 0
        assert mgr.active.book == "Genesis"

    def test_switch_to_invalid(self):
        """switch_to with invalid index should return False."""
        mgr = TabManager()
        assert mgr.switch_to(-1) is False
        assert mgr.switch_to(5) is False

    def test_next_tab_cyclic(self):
        """next_tab should wrap around."""
        mgr = TabManager()
        mgr.new_tab(TabState(book="Exodus"))
        mgr.new_tab(TabState(book="Romans"))
        # Active is 2 (Romans)
        idx = mgr.next_tab()
        assert idx == 0  # Wraps to first

    def test_prev_tab_cyclic(self):
        """prev_tab should wrap around."""
        mgr = TabManager()
        mgr.new_tab(TabState(book="Exodus"))
        mgr.switch_to(0)
        idx = mgr.prev_tab()
        assert idx == 1  # Wraps to last

    def test_to_list_from_list_roundtrip(self):
        """Serialization roundtrip should preserve tabs."""
        mgr = TabManager()
        mgr.new_tab(TabState(book="Exodus", chapter=3))
        mgr.new_tab(TabState(book="Romans", chapter=8))
        mgr.switch_to(1)

        data = mgr.to_list()
        active = mgr.active_index

        restored = TabManager.from_list(data, active)
        assert restored.count == 3
        assert restored.active_index == 1
        assert restored.tabs[0].book == "Genesis"
        assert restored.tabs[1].book == "Exodus"
        assert restored.tabs[2].book == "Romans"

    def test_from_list_empty(self):
        """from_list with empty data should return default."""
        mgr = TabManager.from_list([], 0)
        assert mgr.count == 1

    def test_close_tab_adjusts_active_index(self):
        """Closing a tab before active should adjust active_index."""
        mgr = TabManager()
        mgr.new_tab(TabState(book="Exodus"))
        mgr.new_tab(TabState(book="Romans"))
        # Active is 2 (Romans), close tab 0 (Genesis)
        result = mgr.close_tab(0)
        assert result is True
        assert mgr.active_index == 1  # Shifted down
        assert mgr.active.book == "Romans"


class TestTabCommands:
    """Test tab command parsing."""

    def test_tabnew_alias(self):
        """tn should resolve to tabnew."""
        cmd = parse_command("tn")
        assert cmd.name == "tabnew"

    def test_tabclose_alias(self):
        """tc should resolve to tabclose."""
        cmd = parse_command("tc")
        assert cmd.name == "tabclose"

    def test_tabnew_in_command_names(self):
        """Tab commands should be in command names list."""
        names = get_command_names()
        assert "tabnew" in names
        assert "tabclose" in names
        assert "tabname" in names

    def test_tabnew_with_ref(self):
        """tabnew with reference args should be parsed."""
        cmd = parse_command("tabnew Gen 1:5")
        assert cmd.name == "tabnew"
        assert cmd.rest_args == "Gen 1:5"

    def test_tabname_with_name(self):
        """tabname with name args should be parsed."""
        cmd = parse_command("tabname My Study")
        assert cmd.name == "tabname"
        assert cmd.rest_args == "My Study"
