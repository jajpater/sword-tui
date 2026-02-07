"""Diatheke CLI wrapper for SWORD Bible access."""

import html
import re
import shutil
import subprocess
from typing import List, Optional

from sword_tui.data.types import VerseSegment, SearchHit
from sword_tui.data.canon import (
    diatheke_token,
    resolve_alias,
    DIATHEKE_TO_CANON,
)

# Regex patterns for parsing diatheke output
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

# Pattern: "Book Chapter:Verse: text" or "Book Chapter:Verse text"
_VERSE_PATTERN = re.compile(
    r"^(?P<book>[\w\s]+?)\s+(?P<chapter>\d+):(?P<verse>\d+)\s*[:\-]?\s*(?P<text>.*)$"
)

# Pattern for leading verse number: "1. text" or "1 text"
_LEADING_VERSE = re.compile(r"^(?P<verse>\d+)[\.\:\s]+(?P<text>.*)$")

# Search result pattern: "Book Chapter:Verse"
_SEARCH_REF = re.compile(r"^([\w\s]+)\s+(\d+):(\d+)\s*$")


class DiathekeBackend:
    """Interface to the diatheke CLI with fallback demo data."""

    def __init__(self, module: str = "DutSVV", *, force_fallback: bool = False):
        """Initialize the backend.

        Args:
            module: SWORD module name to use
            force_fallback: Force use of fallback data (for testing)
        """
        self.module = module
        self.available = not force_fallback and shutil.which("diatheke") is not None

    def set_module(self, module: str) -> None:
        """Set the active module."""
        self.module = module

    def lookup_chapter(self, book: str, chapter: int) -> List[VerseSegment]:
        """Look up an entire chapter.

        Args:
            book: Book name (canonical or alias)
            chapter: Chapter number

        Returns:
            List of VerseSegment for each verse
        """
        # Resolve book alias to canonical name
        canonical = resolve_alias(book) or book
        diatheke_book = diatheke_token(canonical)
        ref = f"{diatheke_book} {chapter}"

        raw = self._lookup_raw(ref)
        return self._parse_lookup(canonical, chapter, raw)

    def lookup_verse(self, book: str, chapter: int, verse: int) -> Optional[VerseSegment]:
        """Look up a single verse.

        Args:
            book: Book name
            chapter: Chapter number
            verse: Verse number

        Returns:
            VerseSegment or None if not found
        """
        canonical = resolve_alias(book) or book
        diatheke_book = diatheke_token(canonical)
        ref = f"{diatheke_book} {chapter}:{verse}"

        raw = self._lookup_raw(ref)
        segments = self._parse_lookup(canonical, chapter, raw)
        for seg in segments:
            if seg.verse == verse:
                return seg
        return None

    def lookup_range(
        self, book: str, chapter: int, verse_start: int, verse_end: int
    ) -> List[VerseSegment]:
        """Look up a range of verses.

        Args:
            book: Book name
            chapter: Chapter number
            verse_start: Starting verse
            verse_end: Ending verse

        Returns:
            List of VerseSegment
        """
        canonical = resolve_alias(book) or book
        diatheke_book = diatheke_token(canonical)
        ref = f"{diatheke_book} {chapter}:{verse_start}-{verse_end}"

        raw = self._lookup_raw(ref)
        return self._parse_lookup(canonical, chapter, raw)

    def search(self, query: str, search_type: str = "phrase") -> List[SearchHit]:
        """Search for text in the current module.

        Args:
            query: Search query
            search_type: "phrase", "regex", or "multiword"

        Returns:
            List of SearchHit results
        """
        if not query.strip():
            return []

        if not self.available:
            return self._fallback_search(query)

        try:
            proc = subprocess.run(
                ["diatheke", "-b", self.module, "-s", search_type, "-k", query],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                return []

            return self._parse_search(proc.stdout, query)
        except (subprocess.TimeoutExpired, OSError):
            return []

    def _lookup_raw(self, ref: str) -> str:
        """Perform raw diatheke lookup."""
        if not self.available:
            return self._fallback_lookup(ref)

        try:
            proc = subprocess.run(
                ["diatheke", "-b", self.module, "-k", ref],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return ""
            return proc.stdout
        except (subprocess.TimeoutExpired, OSError):
            return ""

    def _parse_lookup(
        self, book: str, chapter: int, text: str
    ) -> List[VerseSegment]:
        """Parse diatheke lookup output into verse segments."""
        lines = self._normalize_lines(text)
        segments: List[VerseSegment] = []

        for line in lines:
            # Try full reference pattern: "Book Chapter:Verse: text"
            match = _VERSE_PATTERN.match(line)
            if match:
                raw_book = match.group("book").strip()
                ch = int(match.group("chapter"))
                verse = int(match.group("verse"))
                verse_text = match.group("text").strip()

                # Resolve diatheke book name to canonical
                seg_book = DIATHEKE_TO_CANON.get(raw_book)
                if not seg_book:
                    seg_book = resolve_alias(raw_book) or book

                if verse_text:
                    segments.append(VerseSegment(seg_book, ch, verse, verse_text))
                continue

            # Try leading verse number pattern: "1. text"
            match2 = _LEADING_VERSE.match(line)
            if match2:
                verse = int(match2.group("verse"))
                verse_text = match2.group("text").strip()
                if verse_text:
                    segments.append(VerseSegment(book, chapter, verse, verse_text))
                continue

        return segments

    def _parse_search(self, text: str, query: str) -> List[SearchHit]:
        """Parse diatheke search output."""
        hits: List[SearchHit] = []
        lines = text.strip().splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("--"):
                continue

            # Parse reference
            match = _SEARCH_REF.match(line)
            if match:
                raw_book = match.group(1).strip()
                chapter = int(match.group(2))
                verse = int(match.group(3))

                # Resolve book name
                book = DIATHEKE_TO_CANON.get(raw_book)
                if not book:
                    book = resolve_alias(raw_book) or raw_book

                hits.append(SearchHit(
                    book=book,
                    chapter=chapter,
                    verse=verse,
                    snippet="",
                    match_start=0,
                    match_end=0,
                ))

        # Fetch verse text for each hit (limited to avoid slowdown)
        for i, hit in enumerate(hits[:50]):
            seg = self.lookup_verse(hit.book, hit.chapter, hit.verse)
            if seg:
                # Find query match position
                text_lower = seg.text.lower()
                query_lower = query.lower()
                pos = text_lower.find(query_lower)
                if pos >= 0:
                    hits[i] = SearchHit(
                        book=hit.book,
                        chapter=hit.chapter,
                        verse=hit.verse,
                        snippet=seg.text,
                        match_start=pos,
                        match_end=pos + len(query),
                    )
                else:
                    hits[i] = SearchHit(
                        book=hit.book,
                        chapter=hit.chapter,
                        verse=hit.verse,
                        snippet=seg.text,
                        match_start=0,
                        match_end=0,
                    )

        return hits

    def _normalize_lines(self, text: str) -> List[str]:
        """Normalize diatheke output: strip HTML, clean whitespace."""
        normalized: List[str] = []

        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            # Skip module attribution lines
            if line.startswith("(") and line.endswith(")"):
                continue

            # Strip HTML tags
            if "<" in line:
                line = _HTML_TAG.sub(" ", line)

            # Unescape HTML entities
            if "&" in line:
                line = html.unescape(line)

            # Normalize whitespace
            line = _WHITESPACE.sub(" ", line).strip()

            if line:
                normalized.append(line)

        return normalized

    def _fallback_lookup(self, ref: str) -> str:
        """Return demo data when diatheke is unavailable."""
        # Basic demo data for common references
        demo = {
            "Genesis 1": self._demo_genesis_1(),
            "Psalms 23": self._demo_psalm_23(),
            "John 3": self._demo_john_3(),
        }
        for key, value in demo.items():
            if ref.lower().startswith(key.lower()):
                return value
        return self._demo_genesis_1()

    def _fallback_search(self, query: str) -> List[SearchHit]:
        """Return demo search results."""
        return [
            SearchHit("Genesis", 1, 1, "In den beginne schiep God...", 0, 0),
            SearchHit("Johannes", 3, 16, "Want alzo lief heeft God...", 0, 0),
        ]

    def _demo_genesis_1(self) -> str:
        return """Genesis 1:1: In den beginne schiep God den hemel en de aarde.
Genesis 1:2: De aarde nu was woest en ledig, en duisternis was op den afgrond.
Genesis 1:3: En God zeide: Daar zij licht! en daar werd licht.
Genesis 1:4: En God zag het licht, dat het goed was.
Genesis 1:5: En God noemde het licht dag, en de duisternis noemde Hij nacht.
"""

    def _demo_psalm_23(self) -> str:
        return """Psalms 23:1: De HEERE is mijn Herder, mij zal niets ontbreken.
Psalms 23:2: Hij doet mij nederliggen in grazige weiden.
Psalms 23:3: Hij verkwikt mijn ziel.
Psalms 23:4: Al ging ik ook in een dal der schaduw des doods.
Psalms 23:5: Gij richt de tafel toe voor mijn aangezicht.
Psalms 23:6: Ik zal in het huis des HEEREN blijven in lengte van dagen.
"""

    def _demo_john_3(self) -> str:
        return """John 3:1: En er was een mens uit de Farizeen, wiens naam was Nicodemus.
John 3:2: Deze kwam des nachts tot Jezus.
John 3:3: Jezus antwoordde: Voorwaar, voorwaar zeg Ik u.
John 3:16: Want alzo lief heeft God de wereld gehad, dat Hij Zijn eniggeboren Zoon gegeven heeft.
John 3:17: Want God heeft Zijn Zoon niet gezonden in de wereld.
"""
