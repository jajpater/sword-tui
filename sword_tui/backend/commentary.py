"""Commentary lookup via SWORD modules."""

import html
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sword_tui.data.types import CrossReference
from sword_tui.data.canon import resolve_alias, DIATHEKE_TO_CANON, diatheke_token
from sword_tui.backend.crossref import _BOOK_ABBREVS, _SCRIPREF_PATTERN


@dataclass
class CommentaryEntry:
    """A commentary entry for a verse."""

    module: str
    book: str
    chapter: int
    verse: int
    text: str  # The commentary text (cleaned)
    raw_text: str  # Raw text with markup
    crossrefs: List[CrossReference]  # Extracted cross-references


# Pattern for <note type="crossReference"> tags (OSIS format)
_XREF_NOTE_PATTERN = re.compile(
    r'<note[^>]*type="crossReference"[^>]*>([^<]+)</note>',
    re.IGNORECASE
)

# Pattern for cleaning HTML/XML tags
_HTML_TAG = re.compile(r'<[^>]+>')

# Pattern for verse reference in crossref notes like "1 Kron. 1:4"
_SIMPLE_REF = re.compile(
    r'(\d?\s*[A-Za-z]+\.?)\s*(\d+):(\d+)(?:-(\d+))?'
)


class CommentaryBackend:
    """Interface to commentary SWORD modules."""

    # Known commentary modules
    COMMENTARY_MODULES = ["DutKant", "TSK", "MHC", "Geneva", "Catena"]

    def __init__(self, default_module: Optional[str] = None):
        """Initialize the commentary backend.

        Args:
            default_module: Default commentary module to use
        """
        self._default_module = default_module
        self._available_modules: List[str] = []
        self._checked = False

    @property
    def available_modules(self) -> List[str]:
        """Get list of available commentary modules."""
        if not self._checked:
            self._detect_modules()
        return self._available_modules

    @property
    def available(self) -> bool:
        """Check if any commentary is available."""
        return len(self.available_modules) > 0

    def _detect_modules(self) -> None:
        """Detect available commentary modules."""
        self._checked = True

        if not shutil.which("diatheke"):
            return

        for mod in self.COMMENTARY_MODULES:
            if self._module_exists(mod):
                self._available_modules.append(mod)

    def _module_exists(self, module: str) -> bool:
        """Check if a module is installed."""
        try:
            proc = subprocess.run(
                ["diatheke", "-b", module, "-k", "John 3:16"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return proc.returncode == 0 and "not be found" not in proc.stderr
        except (subprocess.TimeoutExpired, OSError):
            return False

    def lookup(
        self,
        book: str,
        chapter: int,
        verse: int,
        module: Optional[str] = None,
    ) -> Optional[CommentaryEntry]:
        """Look up commentary for a verse.

        Args:
            book: Book name
            chapter: Chapter number
            verse: Verse number
            module: Commentary module to use (or default)

        Returns:
            CommentaryEntry or None if not found
        """
        if not self._checked:
            self._detect_modules()

        mod = module or self._default_module
        if not mod and self._available_modules:
            mod = self._available_modules[0]

        if not mod or mod not in self._available_modules:
            return None

        # Resolve book name
        canonical = resolve_alias(book) or book
        diatheke_book = diatheke_token(canonical)
        ref = f"{diatheke_book} {chapter}:{verse}"

        try:
            proc = subprocess.run(
                ["diatheke", "-b", mod, "-k", ref],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return None

            raw_text = proc.stdout
            if not raw_text.strip():
                return None

            # Parse the commentary
            return self._parse_commentary(mod, canonical, chapter, verse, raw_text)

        except (subprocess.TimeoutExpired, OSError):
            return None

    def _parse_commentary(
        self,
        module: str,
        book: str,
        chapter: int,
        verse: int,
        raw_text: str,
    ) -> CommentaryEntry:
        """Parse commentary output and extract cross-references."""
        # Extract cross-references
        crossrefs = self._extract_crossrefs(raw_text)

        # Clean the text for display
        clean_text = self._clean_text(raw_text)

        return CommentaryEntry(
            module=module,
            book=book,
            chapter=chapter,
            verse=verse,
            text=clean_text,
            raw_text=raw_text,
            crossrefs=crossrefs,
        )

    def _extract_crossrefs(self, text: str) -> List[CrossReference]:
        """Extract cross-references from commentary text."""
        refs: List[CrossReference] = []
        seen: set = set()

        # Method 1: scripRef tags (DutKant style)
        for match in _SCRIPREF_PATTERN.finditer(text):
            passage = match.group(1)
            parsed = self._parse_passage(passage)
            for ref in parsed:
                key = (ref.book, ref.chapter, ref.verse)
                if key not in seen:
                    seen.add(key)
                    refs.append(ref)

        # Method 2: <note type="crossReference"> tags (OSIS style)
        for match in _XREF_NOTE_PATTERN.finditer(text):
            ref_text = match.group(1)
            parsed = self._parse_simple_refs(ref_text)
            for ref in parsed:
                key = (ref.book, ref.chapter, ref.verse)
                if key not in seen:
                    seen.add(key)
                    refs.append(ref)

        return refs

    def _parse_passage(self, passage: str) -> List[CrossReference]:
        """Parse a passage string from scripRef tag."""
        refs: List[CrossReference] = []

        # Split by comma, but be careful with book names
        parts = re.split(r',\s*', passage)

        current_book = None
        current_chapter = None

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Try to parse as full reference
            match = _SIMPLE_REF.search(part)
            if match:
                raw_book = match.group(1).strip().rstrip('.')
                chapter = int(match.group(2))
                verse = int(match.group(3))
                verse_end = int(match.group(4)) if match.group(4) else None

                # Resolve book name
                book = self._resolve_book(raw_book)
                if book:
                    current_book = book
                    current_chapter = chapter
                    refs.append(CrossReference(
                        book=book,
                        chapter=chapter,
                        verse=verse,
                        verse_end=verse_end,
                    ))
            elif current_book and current_chapter:
                # Try as just verse number(s)
                verse_match = re.match(r'(\d+)(?:-(\d+))?', part)
                if verse_match:
                    verse = int(verse_match.group(1))
                    verse_end = int(verse_match.group(2)) if verse_match.group(2) else None
                    refs.append(CrossReference(
                        book=current_book,
                        chapter=current_chapter,
                        verse=verse,
                        verse_end=verse_end,
                    ))

        return refs

    def _parse_simple_refs(self, text: str) -> List[CrossReference]:
        """Parse simple reference text like '1 Kron. 1:4'."""
        refs: List[CrossReference] = []

        for match in _SIMPLE_REF.finditer(text):
            raw_book = match.group(1).strip().rstrip('.')
            chapter = int(match.group(2))
            verse = int(match.group(3))
            verse_end = int(match.group(4)) if match.group(4) else None

            book = self._resolve_book(raw_book)
            if book:
                refs.append(CrossReference(
                    book=book,
                    chapter=chapter,
                    verse=verse,
                    verse_end=verse_end,
                ))

        return refs

    def _resolve_book(self, raw_book: str) -> Optional[str]:
        """Resolve a book name/abbreviation to canonical form."""
        # Try direct lookup in abbreviations
        clean = raw_book.replace('.', '').replace(' ', '')
        if clean in _BOOK_ABBREVS:
            return _BOOK_ABBREVS[clean]

        # Try with space for numbered books
        if raw_book[0].isdigit():
            spaced = raw_book[0] + ' ' + raw_book[1:].lstrip()
            spaced_clean = spaced.replace('.', '')
            for abbrev, full in _BOOK_ABBREVS.items():
                if abbrev.lower() == spaced_clean.lower():
                    return full

        # Try resolve_alias
        resolved = resolve_alias(raw_book)
        if resolved:
            return resolved

        # Try DIATHEKE_TO_CANON
        if raw_book in DIATHEKE_TO_CANON:
            return DIATHEKE_TO_CANON[raw_book]

        return None

    def _clean_text(self, text: str) -> str:
        """Clean commentary text for display."""
        # Remove attribution line at end
        lines = text.strip().split('\n')
        if lines and lines[-1].startswith('(') and lines[-1].endswith(')'):
            lines = lines[:-1]

        text = '\n'.join(lines)

        # Remove HTML/XML tags but keep structure
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)

        # Remove remaining tags
        text = _HTML_TAG.sub('', text)

        # Unescape HTML entities
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()
