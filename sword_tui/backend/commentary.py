"""Commentary lookup via SWORD modules."""

import html
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sword_tui.data.types import CrossReference
from sword_tui.data.canon import resolve_alias, DIATHEKE_TO_CANON, diatheke_token
from sword_tui.backend.crossref import _BOOK_ABBREVS, _SCRIPREF_PATTERN, CROSSREF_MODULES, parse_osis_refs
from sword_tui.backend.modules import get_installed_modules


@dataclass
class KeywordGroup:
    """A TSK keyword with its associated cross-references."""
    keyword: str
    refs: List[CrossReference]


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
    keyword_groups: List[KeywordGroup] = None  # TSK: refs grouped by keyword


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
        """Detect available commentary modules via diatheke modulelist."""
        self._checked = True

        modules = get_installed_modules()
        self._available_modules = [
            m.name for m in modules if m.module_type == "Commentaries"
        ]

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
            # Use OSIS format for crossref modules (TSK etc.) for reliable parsing
            cmd = ["diatheke", "-b", mod, "-k", ref]
            if mod in CROSSREF_MODULES:
                cmd = ["diatheke", "-b", mod, "-f", "OSIS", "-k", ref]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return None

            # Decode with error handling - some modules use Latin-1
            try:
                raw_text = proc.stdout.decode("utf-8")
            except UnicodeDecodeError:
                raw_text = proc.stdout.decode("latin-1", errors="replace")
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
        crossrefs = self._extract_crossrefs(raw_text, module)

        # Clean the text for display
        keyword_groups = None
        if module in CROSSREF_MODULES:
            clean_text = self._clean_text_osis_tsk(raw_text)
            keyword_groups = self._extract_keyword_groups(raw_text)
        else:
            clean_text = self._clean_text(raw_text)

        return CommentaryEntry(
            module=module,
            book=book,
            chapter=chapter,
            verse=verse,
            text=clean_text,
            raw_text=raw_text,
            crossrefs=crossrefs,
            keyword_groups=keyword_groups,
        )

    def _extract_crossrefs(self, text: str, module: str = "") -> List[CrossReference]:
        """Extract cross-references from commentary text."""
        # For crossref modules (TSK etc.) with OSIS output, use osisRef parser
        if module in CROSSREF_MODULES:
            return parse_osis_refs(text)

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

    def _extract_keyword_groups(self, text: str) -> List[KeywordGroup]:
        """Extract keyword→refs groups from TSK OSIS output.

        Walks through the OSIS body, tracking text gaps between <reference>
        tags.  A gap with ≥3 letters is a new keyword; punctuation-only gaps
        (like "; " or ",") are ignored.
        """
        from sword_tui.backend.crossref import _OSIS_TO_CANON

        verse_matches = re.findall(
            r'<verse[^>]*>(.*?)</verse>', text, re.DOTALL,
        )
        body = max(verse_matches, key=len) if verse_matches else ""
        if not body:
            return []

        # Match complete <reference osisRef="...">display</reference> tags
        full_ref = re.compile(
            r'<reference\s+osisRef="(?P<ref>[^"]+)"[^>]*>[^<]*</reference>'
        )

        groups: list[KeywordGroup] = []
        current_kw: Optional[str] = None
        current_refs: list[CrossReference] = []
        last_end = 0

        for m in full_ref.finditer(body):
            # Text gap between previous ref (or start) and this ref
            gap = body[last_end:m.start()]
            gap_clean = re.sub(r'<[^>]+>', '', gap).strip()

            # A gap with ≥3 letters and at least one period signals
            # a new keyword (TSK keywords end with ".").  This excludes
            # chapter-outline entries that end with ";" and punctuation
            # gaps like "; " or ",".
            if len(re.findall(r'[A-Za-z]', gap_clean)) >= 3 and '.' in gap_clean:
                if current_kw is not None and current_refs:
                    groups.append(KeywordGroup(keyword=current_kw, refs=current_refs))
                kw = gap_clean
                if kw.endswith('.'):
                    kw = kw[:-1]
                current_kw = kw
                current_refs = []

            # Parse osisRef
            raw = m.group('ref')
            parts = raw.split("-")
            t = parts[0].split(".")
            if len(t) < 3:
                last_end = m.end()
                continue
            try:
                ch, vs = int(t[1]), int(t[2])
            except (ValueError, IndexError):
                last_end = m.end()
                continue
            book = _OSIS_TO_CANON.get(t[0]) or resolve_alias(t[0]) or t[0]
            ve = None
            if len(parts) == 2:
                et = parts[1].split(".")
                if len(et) >= 3:
                    try:
                        if int(et[1]) == ch:
                            ve = int(et[2])
                    except (ValueError, IndexError):
                        pass

            if current_kw is not None:
                current_refs.append(CrossReference(
                    book=book, chapter=ch, verse=vs, verse_end=ve,
                ))

            last_end = m.end()

        if current_kw is not None and current_refs:
            groups.append(KeywordGroup(keyword=current_kw, refs=current_refs))

        return groups

    def _clean_text_osis_tsk(self, text: str) -> str:
        """Clean TSK OSIS output for display in the commentary pane.

        Shows keywords with full Dutch book name references:
            without
              Job 26:7
              Jesaja 45:18
            Spirit
              Job 26:14
        """
        groups = self._extract_keyword_groups(text)
        if not groups:
            return ""

        lines: list[str] = []
        for g in groups:
            lines.append(g.keyword)
            for r in g.refs:
                lines.append(f"  {r.reference}")
            lines.append("")

        return '\n'.join(lines).strip()

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
