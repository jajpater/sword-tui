"""Cross-reference lookup via SWORD modules (TSK, commentaries, etc.)."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sword_tui.data.types import CrossReference
from sword_tui.data.canon import resolve_alias, DIATHEKE_TO_CANON, diatheke_token

# Pattern to parse references like "John 3:16" or "1 John 2:3-5"
_REF_PATTERN = re.compile(
    r"(?P<book>(?:\d\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)?)\s*"
    r"(?P<chapter>\d+)\s*[:.]\s*(?P<verse>\d+)"
    r"(?:\s*[-–]\s*(?P<verse_end>\d+))?"
)

# Pattern for scripRef tags in commentaries: <scripRef passage="...">...</scripRef>
_SCRIPREF_PATTERN = re.compile(
    r'<scripRef[^>]*passage="([^"]+)"[^>]*>',
    re.IGNORECASE
)

# Pattern for <note type="crossReference"> tags in OSIS output from Bible modules
_OSIS_XREF_NOTE = re.compile(
    r'<note[^>]*type="crossReference"[^>]*>(.*?)</note>',
    re.IGNORECASE | re.DOTALL
)

# Pattern for verse reference like "1 Kron. 1:4" or "Gen 3:15"
_SIMPLE_REF = re.compile(
    r'(\d?\s*[A-Za-z]+\.?)\s*(\d+):(\d+)(?:-(\d+))?'
)

# Pattern for references in scripRef passage attribute
# e.g., "Joh 11:51,52, 1Jo 2:2, Ro 5:6,8, 8:32" or "John.3.16"
_PASSAGE_REF = re.compile(
    r"(?P<book>[A-Za-z]+(?:\s+[A-Za-z]+)?)\s*"
    r"(?P<chapter>\d+)\s*[:.]\s*(?P<verse>\d+)"
    r"(?:\s*,\s*(?P<extra_verses>\d+(?:\s*,\s*\d+)*))?"
)

# Pattern for semicolon/comma-separated references
_REF_SEPARATOR = re.compile(r"\s*[;]\s*")

# Abbreviation mappings for common book abbreviations in references
_BOOK_ABBREVS = {
    "Joh": "John", "Jo": "John", "Jn": "John",
    "1Jo": "1 John", "1Jn": "1 John", "1 Jo": "1 John",
    "2Jo": "2 John", "2Jn": "2 John", "2 Jo": "2 John",
    "3Jo": "3 John", "3Jn": "3 John", "3 Jo": "3 John",
    "Ro": "Romans", "Rom": "Romans",
    "1Co": "1 Corinthians", "1Cor": "1 Corinthians",
    "2Co": "2 Corinthians", "2Cor": "2 Corinthians",
    "Ga": "Galatians", "Gal": "Galatians",
    "Eph": "Ephesians", "Ep": "Ephesians",
    "Php": "Philippians", "Phil": "Philippians",
    "Col": "Colossians",
    "1Th": "1 Thessalonians", "1Thes": "1 Thessalonians",
    "2Th": "2 Thessalonians", "2Thes": "2 Thessalonians",
    "1Ti": "1 Timothy", "1Tim": "1 Timothy",
    "2Ti": "2 Timothy", "2Tim": "2 Timothy",
    "Tit": "Titus",
    "Phm": "Philemon", "Phlm": "Philemon",
    "Heb": "Hebrews", "Hebr": "Hebrews",
    "Jas": "James", "Jam": "James",
    "1Pe": "1 Peter", "1Pet": "1 Peter", "1Pt": "1 Peter",
    "2Pe": "2 Peter", "2Pet": "2 Peter", "2Pt": "2 Peter",
    "Jude": "Jude", "Jud": "Jude",
    "Re": "Revelation", "Rev": "Revelation",
    "Mt": "Matthew", "Matt": "Matthew", "Mat": "Matthew",
    "Mk": "Mark", "Mar": "Mark",
    "Lk": "Luke", "Luk": "Luke", "Lu": "Luke",
    "Ac": "Acts", "Act": "Acts",
    "Ge": "Genesis", "Gen": "Genesis",
    "Ex": "Exodus", "Exo": "Exodus",
    "Le": "Leviticus", "Lev": "Leviticus",
    "Nu": "Numbers", "Num": "Numbers",
    "De": "Deuteronomy", "Deu": "Deuteronomy", "Dt": "Deuteronomy",
    "Jos": "Joshua", "Josh": "Joshua",
    "Jdg": "Judges", "Judg": "Judges",
    "Ru": "Ruth",
    "1Sa": "1 Samuel", "1Sam": "1 Samuel",
    "2Sa": "2 Samuel", "2Sam": "2 Samuel",
    "1Ki": "1 Kings", "1Kg": "1 Kings",
    "2Ki": "2 Kings", "2Kg": "2 Kings",
    "1Ch": "1 Chronicles", "1Chr": "1 Chronicles",
    "2Ch": "2 Chronicles", "2Chr": "2 Chronicles",
    "Ezr": "Ezra",
    "Ne": "Nehemiah", "Neh": "Nehemiah",
    "Es": "Esther", "Est": "Esther",
    "Job": "Job",
    "Ps": "Psalms", "Psa": "Psalms", "Psalm": "Psalms",
    "Pr": "Proverbs", "Pro": "Proverbs", "Prov": "Proverbs",
    "Ec": "Ecclesiastes", "Ecc": "Ecclesiastes",
    "So": "Song of Solomon", "Song": "Song of Solomon", "SoS": "Song of Solomon",
    "Isa": "Isaiah", "Is": "Isaiah",
    "Jer": "Jeremiah", "Je": "Jeremiah",
    "La": "Lamentations", "Lam": "Lamentations",
    "Eze": "Ezekiel", "Ezk": "Ezekiel", "Ez": "Ezekiel",
    "Da": "Daniel", "Dan": "Daniel",
    "Ho": "Hosea", "Hos": "Hosea",
    "Joe": "Joel",
    "Am": "Amos", "Amo": "Amos",
    "Ob": "Obadiah", "Oba": "Obadiah",
    "Jon": "Jonah",
    "Mic": "Micah", "Mi": "Micah",
    "Na": "Nahum", "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zep": "Zephaniah", "Zeph": "Zephaniah",
    "Hag": "Haggai",
    "Zec": "Zechariah", "Zech": "Zechariah",
    "Mal": "Malachi",
}


@dataclass
class CrossRefSource:
    """Information about a cross-reference source."""
    module: str
    module_type: str  # "crossref", "commentary", "bible"
    description: str


class CrossRefBackend:
    """Interface to cross-reference sources: TSK, commentaries, etc."""

    # Known dedicated cross-reference modules
    CROSSREF_MODULES = ["TSK", "Cross", "CrossRef"]

    # Known commentary modules that contain cross-references
    COMMENTARY_MODULES = ["DutKant", "MHC", "Geneva", "Catena"]

    def __init__(
        self,
        crossref_module: Optional[str] = None,
        commentary_modules: Optional[List[str]] = None,
    ):
        """Initialize the cross-reference backend.

        Args:
            crossref_module: Specific cross-ref module (TSK), or None for auto-detect
            commentary_modules: List of commentary modules to use for cross-refs
        """
        self._crossref_module = crossref_module
        self._commentary_modules = commentary_modules or []
        self._available_crossref: Optional[str] = None
        self._available_commentaries: List[str] = []
        self._checked = False

    @property
    def available(self) -> bool:
        """Check if any cross-reference source is available."""
        if not self._checked:
            self._detect_modules()
        return bool(self._available_crossref or self._available_commentaries)

    @property
    def sources(self) -> List[CrossRefSource]:
        """Get list of available cross-reference sources."""
        if not self._checked:
            self._detect_modules()

        sources = []
        if self._available_crossref:
            sources.append(CrossRefSource(
                module=self._available_crossref,
                module_type="crossref",
                description="Treasury of Scripture Knowledge",
            ))
        for mod in self._available_commentaries:
            sources.append(CrossRefSource(
                module=mod,
                module_type="commentary",
                description=f"Commentaar: {mod}",
            ))
        return sources

    def _detect_modules(self) -> None:
        """Detect available cross-reference modules."""
        self._checked = True

        if not shutil.which("diatheke"):
            return

        # Detect dedicated cross-ref module
        if self._crossref_module:
            if self._module_exists(self._crossref_module):
                self._available_crossref = self._crossref_module
        else:
            for mod in self.CROSSREF_MODULES:
                if self._module_exists(mod):
                    self._available_crossref = mod
                    break

        # Detect commentary modules
        if self._commentary_modules:
            for mod in self._commentary_modules:
                if self._module_exists(mod):
                    self._available_commentaries.append(mod)
        else:
            for mod in self.COMMENTARY_MODULES:
                if self._module_exists(mod):
                    self._available_commentaries.append(mod)

    def _module_exists(self, module: str) -> bool:
        """Check if a module is installed."""
        try:
            proc = subprocess.run(
                ["diatheke", "-b", module, "-k", "John 3:16"],
                capture_output=True,
                timeout=5,
            )
            stderr = proc.stderr.decode("utf-8", errors="replace")
            return proc.returncode == 0 and "not be found" not in stderr
        except (subprocess.TimeoutExpired, OSError):
            return False

    def lookup(
        self,
        book: str,
        chapter: int,
        verse: int,
        sources: Optional[List[str]] = None,
    ) -> List[Tuple[CrossReference, str]]:
        """Look up cross-references for a verse from all sources.

        Args:
            book: Book name (canonical or alias)
            chapter: Chapter number
            verse: Verse number
            sources: Optional list of specific modules to use

        Returns:
            List of (CrossReference, source_module) tuples
        """
        if not self._checked:
            self._detect_modules()

        all_refs: List[Tuple[CrossReference, str]] = []
        seen: set = set()

        # Resolve book name
        canonical = resolve_alias(book) or book
        diatheke_book = diatheke_token(canonical)
        ref = f"{diatheke_book} {chapter}:{verse}"

        # Determine which sources to query
        modules_to_query = []
        if sources:
            modules_to_query = sources
        else:
            if self._available_crossref:
                modules_to_query.append(self._available_crossref)
            modules_to_query.extend(self._available_commentaries)

        # Query each source
        for module in modules_to_query:
            refs = self._lookup_module(ref, module)
            for xref in refs:
                key = (xref.book, xref.chapter, xref.verse, xref.verse_end)
                if key not in seen:
                    seen.add(key)
                    all_refs.append((xref, module))

        return all_refs

    def _lookup_module(self, ref: str, module: str) -> List[CrossReference]:
        """Look up cross-references from a specific module."""
        try:
            proc = subprocess.run(
                ["diatheke", "-b", module, "-k", ref],
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return []

            # Decode with error handling - some modules use Latin-1
            try:
                output = proc.stdout.decode("utf-8")
            except UnicodeDecodeError:
                output = proc.stdout.decode("latin-1", errors="replace")

            # Try scripRef tags first (common in commentaries)
            refs = self._parse_scripref_tags(output)
            if refs:
                return refs

            # Fall back to plain reference parsing (for TSK-style output)
            return self._parse_plain_refs(output)

        except (subprocess.TimeoutExpired, OSError):
            return []

    def _parse_scripref_tags(self, output: str) -> List[CrossReference]:
        """Parse <scripRef> tags from commentary output."""
        refs: List[CrossReference] = []

        for match in _SCRIPREF_PATTERN.finditer(output):
            passage = match.group(1)
            # Parse the passage attribute which may contain multiple refs
            parsed = self._parse_passage_string(passage)
            refs.extend(parsed)

        return refs

    def _parse_passage_string(self, passage: str) -> List[CrossReference]:
        """Parse a passage string like 'Joh 11:51,52, 1Jo 2:2, Ro 5:6,8'."""
        refs: List[CrossReference] = []

        # Split by comma but be careful with book names like "1 John"
        # First normalize spaces
        passage = passage.replace(".", " ").replace(":", " ")
        passage = re.sub(r"\s+", " ", passage).strip()

        # Split by spaces and reconstruct
        parts = passage.split()
        current_book = None
        current_chapter = None

        i = 0
        while i < len(parts):
            part = parts[i]

            # Check if this is a book name
            if part in _BOOK_ABBREVS or resolve_alias(part):
                current_book = _BOOK_ABBREVS.get(part, part)
                i += 1
                continue

            # Check for numbered book prefix (1, 2, 3)
            if part in ("1", "2", "3") and i + 1 < len(parts):
                next_part = parts[i + 1]
                combined = f"{part} {next_part}"
                combined_abbrev = f"{part}{next_part}"
                if combined_abbrev in _BOOK_ABBREVS:
                    current_book = _BOOK_ABBREVS[combined_abbrev]
                    i += 2
                    continue
                elif resolve_alias(combined):
                    current_book = combined
                    i += 2
                    continue

            # Try to parse as chapter:verse or just verse
            if current_book:
                # Check for chapter:verse pattern in this part
                cv_match = re.match(r"(\d+)\s*(\d+)?", part)
                if cv_match:
                    num1 = int(cv_match.group(1))
                    num2 = cv_match.group(2)

                    if num2:
                        # This is chapter verse
                        current_chapter = num1
                        verse = int(num2)
                    elif current_chapter:
                        # This is just a verse in current chapter
                        verse = num1
                    else:
                        # Assume this is chapter, next will be verse
                        current_chapter = num1
                        i += 1
                        continue

                    canonical = resolve_alias(current_book) or current_book
                    refs.append(CrossReference(
                        book=canonical,
                        chapter=current_chapter,
                        verse=verse,
                    ))

            i += 1

        return refs

    def _parse_plain_refs(self, output: str) -> List[CrossReference]:
        """Parse plain reference text (TSK-style output)."""
        refs: List[CrossReference] = []
        seen: set = set()

        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', ' ', output)

        # Find all references
        for match in _REF_PATTERN.finditer(clean):
            raw_book = match.group("book").strip()
            chapter = int(match.group("chapter"))
            verse = int(match.group("verse"))
            verse_end_str = match.group("verse_end")
            verse_end = int(verse_end_str) if verse_end_str else None

            # Resolve book name
            book = _BOOK_ABBREVS.get(raw_book)
            if not book:
                book = DIATHEKE_TO_CANON.get(raw_book)
            if not book:
                book = resolve_alias(raw_book) or raw_book

            key = (book, chapter, verse, verse_end)
            if key not in seen:
                seen.add(key)
                refs.append(CrossReference(
                    book=book,
                    chapter=chapter,
                    verse=verse,
                    verse_end=verse_end,
                ))

        return refs

    def lookup_with_previews(
        self,
        book: str,
        chapter: int,
        verse: int,
        bible_backend,
        sources: Optional[List[str]] = None,
    ) -> List[Tuple[CrossReference, str]]:
        """Look up cross-references with verse previews.

        Args:
            book: Book name
            chapter: Chapter number
            verse: Verse number
            bible_backend: DiathekeBackend for fetching verse text
            sources: Optional list of specific modules to use

        Returns:
            List of (CrossReference with preview, source_module) tuples
        """
        refs = self.lookup(book, chapter, verse, sources)

        # Fetch preview text for each reference
        refs_with_preview = []
        for ref, source in refs:
            preview = ""
            try:
                seg = bible_backend.lookup_verse(ref.book, ref.chapter, ref.verse)
                if seg:
                    preview = seg.text[:100]
                    if len(seg.text) > 100:
                        preview += "..."
            except Exception:
                pass

            refs_with_preview.append((
                CrossReference(
                    book=ref.book,
                    chapter=ref.chapter,
                    verse=ref.verse,
                    verse_end=ref.verse_end,
                    preview=preview,
                ),
                source,
            ))

        return refs_with_preview

    def lookup_bible_module(self, ref: str, module: str) -> List[CrossReference]:
        """Extract cross-references from a Bible module via OSIS output.

        Runs diatheke with OSIS format and parses <note type="crossReference"> tags.

        Args:
            ref: Reference string, e.g. "John 3:16"
            module: Bible module name, e.g. "KJV"

        Returns:
            List of CrossReference objects found in the verse's OSIS markup
        """
        try:
            proc = subprocess.run(
                ["diatheke", "-b", module, "-f", "OSIS", "-o", "nflsgxtm", "-k", ref],
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return []

            try:
                output = proc.stdout.decode("utf-8")
            except UnicodeDecodeError:
                output = proc.stdout.decode("latin-1", errors="replace")

            return self._parse_osis_crossrefs(output)

        except (subprocess.TimeoutExpired, OSError):
            return []

    def _parse_osis_crossrefs(self, output: str) -> List[CrossReference]:
        """Parse cross-references from OSIS output."""
        refs: List[CrossReference] = []
        seen: set = set()

        for match in _OSIS_XREF_NOTE.finditer(output):
            note_content = match.group(1)
            # Parse references within the note
            for ref_match in _SIMPLE_REF.finditer(note_content):
                raw_book = ref_match.group(1).strip().rstrip('.')
                chapter = int(ref_match.group(2))
                verse = int(ref_match.group(3))
                verse_end = int(ref_match.group(4)) if ref_match.group(4) else None

                # Resolve book name
                book = _BOOK_ABBREVS.get(raw_book)
                if not book:
                    book = DIATHEKE_TO_CANON.get(raw_book)
                if not book:
                    book = resolve_alias(raw_book) or raw_book

                key = (book, chapter, verse, verse_end)
                if key not in seen:
                    seen.add(key)
                    refs.append(CrossReference(
                        book=book,
                        chapter=chapter,
                        verse=verse,
                        verse_end=verse_end,
                    ))

            # Also try scripRef tags within the note
            for scripref_match in _SCRIPREF_PATTERN.finditer(note_content):
                passage = scripref_match.group(1)
                parsed = self._parse_passage_string(passage)
                for r in parsed:
                    key = (r.book, r.chapter, r.verse, r.verse_end)
                    if key not in seen:
                        seen.add(key)
                        refs.append(r)

        return refs
