"""Tests for canon module."""

import pytest

from sword_tui.data.canon import (
    BOOK_ORDER,
    book_chapters,
    book_index,
    diatheke_token,
    resolve_alias,
    search_books,
    next_book,
    prev_book,
)


class TestBookOrder:
    """Test book order and indexing."""

    def test_book_order_length(self):
        """Should have 66 books."""
        assert len(BOOK_ORDER) == 66

    def test_first_book(self):
        """First book should be Genesis."""
        assert BOOK_ORDER[0] == "Genesis"

    def test_last_book(self):
        """Last book should be Openbaring (Revelation)."""
        assert BOOK_ORDER[-1] == "Openbaring"

    def test_book_index(self):
        """Test book index lookup."""
        assert book_index("Genesis") == 0
        assert book_index("Psalmen") == 18
        assert book_index("Openbaring") == 65
        assert book_index("NonExistent") == -1


class TestBookChapters:
    """Test chapter count lookup."""

    def test_genesis_chapters(self):
        """Genesis should have 50 chapters."""
        assert book_chapters("Genesis") == 50

    def test_psalms_chapters(self):
        """Psalmen should have 150 chapters."""
        assert book_chapters("Psalmen") == 150

    def test_unknown_book(self):
        """Unknown book should return 0."""
        assert book_chapters("NonExistent") == 0


class TestResolveAlias:
    """Test alias resolution."""

    def test_exact_name(self):
        """Exact name should resolve."""
        assert resolve_alias("Genesis") == "Genesis"
        assert resolve_alias("Psalmen") == "Psalmen"

    def test_abbreviation(self):
        """Abbreviations should resolve."""
        assert resolve_alias("Gen") == "Genesis"
        assert resolve_alias("Ps") == "Psalmen"
        assert resolve_alias("Joh") == "Johannes"

    def test_lowercase(self):
        """Lowercase should work."""
        assert resolve_alias("genesis") == "Genesis"
        assert resolve_alias("gen") == "Genesis"

    def test_common_aliases(self):
        """Common aliases should work."""
        assert resolve_alias("1mo") == "Genesis"
        assert resolve_alias("matt") == "Mattheüs"
        assert resolve_alias("rev") == "Openbaring"

    def test_fuzzy_prefix(self):
        """Fuzzy prefix matching should work."""
        assert resolve_alias("gene") == "Genesis"
        assert resolve_alias("psal") == "Psalmen"

    def test_unknown_alias(self):
        """Unknown alias should return None."""
        assert resolve_alias("xyz") is None
        assert resolve_alias("") is None


class TestDiathekeToken:
    """Test diatheke token conversion."""

    def test_dutch_to_english(self):
        """Dutch names should convert to English."""
        assert diatheke_token("Genesis") == "Genesis"
        assert diatheke_token("Psalmen") == "Psalms"
        assert diatheke_token("Johannes") == "John"
        assert diatheke_token("Openbaring") == "Revelation"

    def test_numbered_books(self):
        """Numbered books should convert correctly."""
        assert diatheke_token("1 Koningen") == "1Kings"
        assert diatheke_token("2 Korinthe") == "2Corinthians"


class TestSearchBooks:
    """Test book search functionality."""

    def test_empty_search(self):
        """Empty search should return first books."""
        results = search_books("")
        assert len(results) > 0
        assert results[0].name == "Genesis"

    def test_prefix_search(self):
        """Prefix search should find books."""
        results = search_books("gen")
        assert len(results) >= 1
        assert results[0].name == "Genesis"

    def test_psalm_search(self):
        """Psalm search should find Psalmen."""
        results = search_books("ps")
        assert len(results) >= 1
        assert results[0].name == "Psalmen"

    def test_limit(self):
        """Limit should be respected."""
        results = search_books("", limit=5)
        assert len(results) == 5


class TestNavigation:
    """Test book navigation."""

    def test_next_book(self):
        """Next book should work."""
        assert next_book("Genesis") == "Exodus"
        assert next_book("Maleachi") == "Mattheüs"

    def test_next_book_last(self):
        """Next book from last should return None."""
        assert next_book("Openbaring") is None

    def test_prev_book(self):
        """Previous book should work."""
        assert prev_book("Exodus") == "Genesis"
        assert prev_book("Mattheüs") == "Maleachi"

    def test_prev_book_first(self):
        """Previous book from first should return None."""
        assert prev_book("Genesis") is None
