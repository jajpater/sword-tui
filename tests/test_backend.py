"""Tests for diatheke backend."""

import pytest

from sword_tui.backend.diatheke import DiathekeBackend
from sword_tui.backend.modules import ModuleInfo, _parse_module_list


class TestDiathekeBackend:
    """Test DiathekeBackend with fallback data."""

    def test_init_fallback(self):
        """Backend should work with fallback mode."""
        backend = DiathekeBackend(force_fallback=True)
        assert not backend.available
        assert backend.module == "DutSVV"

    def test_set_module(self):
        """Should be able to change module."""
        backend = DiathekeBackend(force_fallback=True)
        backend.set_module("KJV")
        assert backend.module == "KJV"

    def test_lookup_chapter_fallback(self):
        """Lookup should return fallback data."""
        backend = DiathekeBackend(force_fallback=True)
        segments = backend.lookup_chapter("Genesis", 1)
        assert len(segments) > 0
        assert segments[0].book == "Genesis"
        assert segments[0].chapter == 1
        assert segments[0].verse == 1

    def test_lookup_verse(self):
        """Single verse lookup should work."""
        backend = DiathekeBackend(force_fallback=True)
        verse = backend.lookup_verse("Genesis", 1, 1)
        assert verse is not None
        assert verse.verse == 1

    def test_search_fallback(self):
        """Search should return fallback results."""
        backend = DiathekeBackend(force_fallback=True)
        results = backend.search("God")
        assert len(results) > 0

    def test_empty_search(self):
        """Empty search should return empty list."""
        backend = DiathekeBackend(force_fallback=True)
        results = backend.search("")
        assert results == []


class TestModuleParser:
    """Test module list parsing."""

    def test_parse_module_list(self):
        """Should parse diatheke -M output correctly."""
        output = """Biblical Texts:
  DutSVV : Dutch Staten Vertaling
  KJV : King James Version

Commentaries:
  MHC : Matthew Henry Commentary
"""
        modules = _parse_module_list(output)
        assert len(modules) == 3

        assert modules[0].name == "DutSVV"
        assert modules[0].description == "Dutch Staten Vertaling"
        assert modules[0].module_type == "Biblical Texts"

        assert modules[1].name == "KJV"
        assert modules[1].module_type == "Biblical Texts"

        assert modules[2].name == "MHC"
        assert modules[2].module_type == "Commentaries"

    def test_parse_empty(self):
        """Empty output should return empty list."""
        modules = _parse_module_list("")
        assert modules == []

    def test_parse_no_modules(self):
        """Output with only headers should return empty list."""
        output = """Biblical Texts:

Commentaries:
"""
        modules = _parse_module_list(output)
        assert modules == []


class TestVerseSegment:
    """Test VerseSegment data class."""

    def test_reference_property(self):
        """Reference property should format correctly."""
        from sword_tui.data.types import VerseSegment

        seg = VerseSegment("Genesis", 1, 1, "In the beginning...")
        assert seg.reference == "Genesis 1:1"

    def test_frozen(self):
        """VerseSegment should be immutable."""
        from sword_tui.data.types import VerseSegment

        seg = VerseSegment("Genesis", 1, 1, "In the beginning...")
        with pytest.raises(AttributeError):
            seg.verse = 2


class TestSearchHit:
    """Test SearchHit data class."""

    def test_reference_property(self):
        """Reference property should format correctly."""
        from sword_tui.data.types import SearchHit

        hit = SearchHit("Genesis", 1, 1, "In the beginning...", 0, 10)
        assert hit.reference == "Genesis 1:1"
