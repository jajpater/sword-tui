"""Diatheke CLI wrapper for SWORD Bible access."""

import html
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from sword_tui.data.types import VerseSegment, SearchHit, WordWithStrongs


@dataclass
class DiathekeFilters:
    """Diatheke output filter flags.

    Controls which additional data is included in diatheke output.
    Maps to diatheke -f option flags.
    """

    strongs: bool = False  # 'n' - Strong's numbers
    footnotes: bool = False  # 'f' - Footnotes

    def to_flag_string(self) -> str:
        """Convert active filters to diatheke -f flag string.

        Returns:
            String of single-char flags, e.g. 'n' for Strong's only,
            'nf' for Strong's + footnotes, '' for no filters.
        """
        flags = ""
        if self.strongs:
            flags += "n"
        if self.footnotes:
            flags += "f"
        return flags

    def toggle_strongs(self) -> None:
        """Toggle Strong's numbers filter."""
        self.strongs = not self.strongs

    def toggle_footnotes(self) -> None:
        """Toggle footnotes filter."""
        self.footnotes = not self.footnotes


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

# Pattern to extract Strong's word tags: <w savlm="strong:G1063 strong:G25">text</w>
_STRONGS_WORD = re.compile(r'<w\s+savlm="([^"]+)"[^>]*>([^<]+)</w>')
# Pattern to extract Strong's numbers from savlm attribute
_STRONGS_NUM = re.compile(r'strong:([GH]\d+)')


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
        self._filters: Optional[DiathekeFilters] = None

    def set_module(self, module: str) -> None:
        """Set the active module."""
        self.module = module

    def set_filters(self, filters: Optional[DiathekeFilters]) -> None:
        """Set the diatheke filters to use for lookups."""
        self._filters = filters

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

    def search(
        self,
        query: str,
        search_type: str = "phrase",
        fetch_snippets: bool = True,
    ) -> List[SearchHit]:
        """Search for text in the current module.

        Args:
            query: Search query
            search_type: "phrase", "regex", or "multiword"
            fetch_snippets: Whether to fetch full verse text for each hit

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
                timeout=30,
            )
            if proc.returncode != 0:
                return []

            # Decode with error handling - some modules use Latin-1
            try:
                output = proc.stdout.decode("utf-8")
            except UnicodeDecodeError:
                output = proc.stdout.decode("latin-1", errors="replace")

            return self._parse_search(output, query, fetch_snippets)
        except (subprocess.TimeoutExpired, OSError):
            return []

    def _lookup_raw(self, ref: str) -> str:
        """Perform raw diatheke lookup."""
        if not self.available:
            return self._fallback_lookup(ref)

        try:
            cmd = ["diatheke", "-b", self.module]
            # Add filter flags if any are active
            if self._filters:
                flags = self._filters.to_flag_string()
                if flags:
                    cmd.extend(["-f", flags])
            cmd.extend(["-k", ref])

            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return ""
            # Decode with error handling - some modules use Latin-1
            try:
                return proc.stdout.decode("utf-8")
            except UnicodeDecodeError:
                return proc.stdout.decode("latin-1", errors="replace")
        except (subprocess.TimeoutExpired, OSError):
            return ""

    def _parse_strongs_words(self, raw_line: str) -> tuple[str, tuple[WordWithStrongs, ...]]:
        """Parse Strong's numbers from a raw line with XML markup.

        Args:
            raw_line: Raw line containing <w savlm="strong:G1063">word</w> tags

        Returns:
            Tuple of (plain_text, words_with_strongs)
        """
        words: list[WordWithStrongs] = []
        plain_parts: list[str] = []
        last_end = 0

        for match in _STRONGS_WORD.finditer(raw_line):
            # Add any text before this match
            before = raw_line[last_end:match.start()]
            # Strip HTML from the "before" text
            before_clean = _HTML_TAG.sub(" ", before)
            before_clean = html.unescape(before_clean)
            before_clean = _WHITESPACE.sub(" ", before_clean).strip()
            if before_clean:
                plain_parts.append(before_clean)
                # Add non-strongs words
                for word in before_clean.split():
                    if word:
                        words.append(WordWithStrongs(text=word))

            # Extract Strong's numbers from savlm attribute
            savlm = match.group(1)
            word_text = match.group(2).strip()
            strongs_nums = tuple(_STRONGS_NUM.findall(savlm))

            if word_text:
                plain_parts.append(word_text)
                words.append(WordWithStrongs(text=word_text, strongs=strongs_nums))

            last_end = match.end()

        # Handle remaining text after last match
        after = raw_line[last_end:]
        after_clean = _HTML_TAG.sub(" ", after)
        after_clean = html.unescape(after_clean)
        after_clean = _WHITESPACE.sub(" ", after_clean).strip()
        if after_clean:
            plain_parts.append(after_clean)
            for word in after_clean.split():
                if word:
                    words.append(WordWithStrongs(text=word))

        plain_text = " ".join(plain_parts)
        plain_text = _WHITESPACE.sub(" ", plain_text).strip()

        return plain_text, tuple(words)

    def _parse_lookup(
        self, book: str, chapter: int, text: str
    ) -> List[VerseSegment]:
        """Parse diatheke lookup output into verse segments."""
        # Keep both raw and normalized lines for Strong's parsing
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        segments: List[VerseSegment] = []

        for raw_line in raw_lines:
            # Skip module attribution lines
            if raw_line.startswith("(") and raw_line.endswith(")"):
                continue

            # First normalize to get reference pattern
            normalized = _HTML_TAG.sub(" ", raw_line)
            normalized = html.unescape(normalized)
            normalized = _WHITESPACE.sub(" ", normalized).strip()

            if not normalized:
                continue

            # Try full reference pattern: "Book Chapter:Verse: text"
            match = _VERSE_PATTERN.match(normalized)
            if match:
                raw_book = match.group("book").strip()
                ch = int(match.group("chapter"))
                verse = int(match.group("verse"))

                # Resolve diatheke book name to canonical
                seg_book = DIATHEKE_TO_CANON.get(raw_book)
                if not seg_book:
                    seg_book = resolve_alias(raw_book) or book

                # Parse Strong's from the raw text portion
                # Find the text part after the reference in the raw line
                ref_pattern = re.compile(
                    rf"{re.escape(raw_book)}\s+{ch}:{verse}\s*[:\-]?\s*"
                )
                ref_match = ref_pattern.search(raw_line)
                if ref_match:
                    raw_text = raw_line[ref_match.end():]
                    verse_text, words = self._parse_strongs_words(raw_text)
                else:
                    verse_text = match.group("text").strip()
                    words = ()

                if verse_text:
                    segments.append(VerseSegment(
                        seg_book, ch, verse, verse_text, words
                    ))
                continue

            # Try leading verse number pattern: "1. text"
            match2 = _LEADING_VERSE.match(normalized)
            if match2:
                verse = int(match2.group("verse"))

                # Parse Strong's from raw line
                # Find text after verse number
                verse_pattern = re.compile(rf"^\s*{verse}[\.\:\s]+")
                verse_match = verse_pattern.match(raw_line)
                if verse_match:
                    raw_text = raw_line[verse_match.end():]
                    verse_text, words = self._parse_strongs_words(raw_text)
                else:
                    verse_text = match2.group("text").strip()
                    words = ()

                if verse_text:
                    segments.append(VerseSegment(
                        book, chapter, verse, verse_text, words
                    ))
                continue

        return segments

    def _parse_search(
        self, text: str, query: str, fetch_snippets: bool = True
    ) -> List[SearchHit]:
        """Parse diatheke search output.

        Args:
            text: Raw diatheke output
            query: The search query
            fetch_snippets: Whether to fetch verse text for each hit

        Returns:
            List of SearchHit results
        """
        hits: List[SearchHit] = []

        # Diatheke output format:
        # Entries containing "query"-- Book Ch:Vs
        # Book Ch:Vs ; Book Ch:Vs ; Book Ch:Vs ; ...
        # -- N matches total (Module)

        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            # Skip header and footer lines
            if line.startswith("Entries containing") or line.startswith("--"):
                # But the header line may contain the first result after "--"
                if "--" in line and not line.startswith("--"):
                    # Extract part after "--"
                    parts = line.split("--", 1)
                    if len(parts) > 1:
                        line = parts[1].strip()
                    else:
                        continue
                else:
                    continue

            # Split by " ; " to handle multiple references per line
            refs = line.split(" ; ")

            for ref in refs:
                ref = ref.strip()
                if not ref:
                    continue

                # Parse reference: "Book Chapter:Verse"
                match = _SEARCH_REF.match(ref)
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

        # Fetch verse text for each hit if requested
        if fetch_snippets:
            for i, hit in enumerate(hits):
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
