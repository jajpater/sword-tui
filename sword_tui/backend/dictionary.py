"""Dictionary lookup via diatheke for Strong's numbers."""

import html
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DictionaryEntry:
    """A parsed dictionary entry."""

    module: str
    key: str  # e.g., "G25" or "H430"
    title: str  # e.g., "G25 - ἀγαπάω (agapaō)"
    greek_word: str  # Original Greek/Hebrew word
    transliteration: str  # Romanized form
    pronunciation: str  # Pronunciation guide
    definition: str  # Full definition text
    raw_text: str  # Raw text for fallback display


# Regex patterns for parsing dictionary XML output
_ENTRY_FREE = re.compile(r'<entryFree[^>]*>(.*?)</entryFree>', re.DOTALL)
_TITLE = re.compile(r'<title>([^<]+)</title>')
_ORTH = re.compile(r'<orth[^>]*>([^<]+)</orth>')
_ORTH_TRANS = re.compile(r'<orth[^>]*type="trans"[^>]*>([^<]+)</orth>')
_PRON = re.compile(r'<pron[^>]*>([^<]+)</pron>')
_DEF = re.compile(r'<def>(.*?)</def>', re.DOTALL)  # Match content with nested tags
_HTML_TAG = re.compile(r'<[^>]+>')
# Pattern for foreign language tags (Hebrew/Greek words in BDB)
_FOREIGN = re.compile(r'<foreign[^>]*>([^<]+)</foreign>')
# Patterns for cleaning definition content
_REF_TAG = re.compile(r'<ref[^>]*>([^<]*)</ref>')
_HI_TAG = re.compile(r'<hi[^>]*>([^<]*)</hi>')
_FOREIGN_TAG = re.compile(r'<foreign[^>]*>([^<]*)</foreign>')
_SENSE_TAG = re.compile(r'<sense[^>]*>(.*?)</sense>', re.DOTALL)
_NOTE_TAG = re.compile(r'<note[^>]*>(.*?)</note>', re.DOTALL)
_LB_TAG = re.compile(r'<lb\s*/?>')
_WHITESPACE = re.compile(r'\s+')


def _clean_definition(raw_def: str, remove_leading_word: str = "") -> str:
    """Clean XML tags from definition text for human-readable output.

    Args:
        raw_def: Raw definition text with XML tags
        remove_leading_word: Optional word to remove from start of definition

    Returns:
        Cleaned plain text definition
    """
    text = raw_def

    # Replace <ref target="...">H433</ref> with just the reference text
    text = _REF_TAG.sub(r'\1', text)

    # Replace <hi rend="italic">word</hi> with just the word
    text = _HI_TAG.sub(r'\1', text)

    # Replace <foreign>word</foreign> with just the word
    text = _FOREIGN_TAG.sub(r'\1', text)

    # Format <sense n="X"> tags for better readability
    # Numbers (1, 2, 3) get their own line, letters (a, b, c) are indented
    def format_sense_open(match: re.Match) -> str:
        n = match.group(1) if match.group(1) else ""
        if n.isdigit():
            return f"\n{n}. "
        elif n.isalpha() and len(n) == 1:
            return f"\n   {n}. "
        return "\n• "

    text = re.sub(r'<sense[^>]*n="([^"]*)"[^>]*>', format_sense_open, text)
    text = re.sub(r'<sense[^>]*>', '\n• ', text)  # Sense without n attribute
    text = re.sub(r'</sense>', '', text)

    # Remove <note> tags and their content (footnotes within definitions)
    text = _NOTE_TAG.sub('', text)

    # Replace <lb/> line breaks with actual newlines
    text = _LB_TAG.sub('\n', text)

    # Strip any remaining HTML/XML tags
    text = _HTML_TAG.sub(' ', text)

    # Unescape HTML entities
    text = html.unescape(text)

    # Remove leading ". " artifacts from sense content
    text = re.sub(r'\n(\d+\.) \. ', r'\n\1 ', text)
    text = re.sub(r'\n(   [a-z]\.) \. ', r'\n\1 ', text)
    text = re.sub(r'\n• \. ', '\n• ', text)

    # Normalize whitespace (but preserve intentional newlines)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned = _WHITESPACE.sub(' ', line).strip()
        if cleaned:
            # Remove leading word if specified (already in title)
            if remove_leading_word and cleaned.startswith(remove_leading_word):
                cleaned = cleaned[len(remove_leading_word):].strip()
            if cleaned:
                cleaned_lines.append(cleaned)

    return '\n'.join(cleaned_lines)


class DictionaryBackend:
    """Interface to diatheke for dictionary lookups."""

    def __init__(self):
        """Initialize the dictionary backend."""
        self.available = shutil.which("diatheke") is not None

    def lookup_strongs(
        self,
        strongs_number: str,
        modules: List[str],
    ) -> List[DictionaryEntry]:
        """Look up a Strong's number in multiple dictionary modules.

        Args:
            strongs_number: Strong's number like "G25" or "H430"
            modules: List of dictionary module names to search

        Returns:
            List of DictionaryEntry results from available modules
        """
        if not self.available or not strongs_number:
            return []

        # Normalize the number - extract just the digits
        # "G25" -> look up "25" in StrongsGreek
        # "H430" -> look up "430" in StrongsHebrew
        num_match = re.match(r'[GH]?(\d+)', strongs_number.upper())
        if not num_match:
            return []

        number = num_match.group(1)
        entries: List[DictionaryEntry] = []

        for module in modules:
            entry = self._lookup_single(strongs_number, number, module)
            if entry:
                entries.append(entry)

        return entries

    def _lookup_single(
        self,
        strongs_number: str,
        number: str,
        module: str,
    ) -> Optional[DictionaryEntry]:
        """Look up a single dictionary entry.

        Args:
            strongs_number: Full Strong's number like "G25"
            number: Just the numeric part like "25"
            module: Dictionary module name

        Returns:
            DictionaryEntry if found, None otherwise
        """
        try:
            # Different modules use different key formats:
            # - StrongsHebrew/StrongsGreek: use number only (e.g., "430")
            # - BDBGlosses_Strongs: use full key with prefix (e.g., "H430")
            # Try number-only first (more common), then full key with prefix
            proc = subprocess.run(
                ["diatheke", "-b", module, "-k", number],
                capture_output=True,
                timeout=5,
            )

            # Verify we got the right entry
            lookup_key = strongs_number.upper()  # e.g., "H430" or "G25"
            got_correct_entry = False

            # Decode with error handling - some modules use Latin-1
            try:
                stdout = proc.stdout.decode("utf-8")
            except UnicodeDecodeError:
                stdout = proc.stdout.decode("latin-1", errors="replace")

            if proc.returncode == 0 and "Entry not found" not in stdout:
                # Check various formats for correct entry:
                # - XML format: <title>H430</title>
                # - Plain format: starts with "00430:" or "430:"
                padded_num = number.zfill(5)  # e.g., "00430"
                if (f"<title>{lookup_key}</title>" in stdout
                        or stdout.strip().startswith(f"{padded_num}:")
                        or stdout.strip().startswith(f"{number}:")):
                    got_correct_entry = True

            if not got_correct_entry:
                # Try with full key (for BDBGlosses_Strongs and similar)
                proc = subprocess.run(
                    ["diatheke", "-b", module, "-k", lookup_key],
                    capture_output=True,
                    timeout=5,
                )
                try:
                    stdout = proc.stdout.decode("utf-8")
                except UnicodeDecodeError:
                    stdout = proc.stdout.decode("latin-1", errors="replace")

            if proc.returncode != 0:
                return None

            raw = stdout.strip()
            if not raw or "Entry not found" in raw:
                return None

            return self._parse_entry(module, strongs_number, raw)

        except (subprocess.TimeoutExpired, OSError):
            return None

    def _parse_entry(
        self,
        module: str,
        strongs_number: str,
        raw_text: str,
    ) -> DictionaryEntry:
        """Parse dictionary XML output into a DictionaryEntry.

        Args:
            module: Dictionary module name
            strongs_number: Strong's number like "G25"
            raw_text: Raw diatheke output

        Returns:
            Parsed DictionaryEntry
        """
        greek_word = ""
        transliteration = ""
        pronunciation = ""
        definition = ""

        # Try to extract from XML structure
        entry_match = _ENTRY_FREE.search(raw_text)
        if entry_match:
            entry_content = entry_match.group(1)

            # Extract Greek/Hebrew word (first <orth> without type="trans")
            orth_matches = _ORTH.findall(entry_content)
            trans_matches = _ORTH_TRANS.findall(entry_content)

            if orth_matches:
                # First match that's not a transliteration
                for orth in orth_matches:
                    if orth not in trans_matches:
                        greek_word = orth.strip()
                        break

            # If no <orth>, try <foreign> tag (used by BDBGlosses_Strongs)
            if not greek_word:
                foreign_matches = _FOREIGN.findall(entry_content)
                if foreign_matches:
                    greek_word = foreign_matches[0].strip()

            if trans_matches:
                transliteration = trans_matches[0].strip()

            # Extract pronunciation
            pron_match = _PRON.search(entry_content)
            if pron_match:
                pronunciation = pron_match.group(1).strip()

            # Extract definition and clean XML tags
            def_match = _DEF.search(entry_content)
            if def_match:
                definition = _clean_definition(def_match.group(1), greek_word)
            else:
                # No <def> tag - use entire content minus title/foreign as definition
                # This handles BDBGlosses_Strongs format with <sense> tags
                content_for_def = entry_content
                # Remove title
                content_for_def = _TITLE.sub('', content_for_def)
                definition = _clean_definition(content_for_def, greek_word)

        # If XML parsing didn't work, try other formats
        if not greek_word and not definition:
            # Try StrongsReal HTML formats:
            # Hebrew: "00430: <a name...>430</a><br /> אלהים<br /> ['ĕlôhîym] \<i>el-o-heem'</i>\<br /> Definition..."
            # Greek: "00025: <a name...>25</a>   <b>ἀγαπάω</b> [A)GAPA/W] {agapáō}   \<i>ag-ap-ah'-o</i>\<br /> Definition..."
            if '<br />' in raw_text or '<br/>' in raw_text or '<b>' in raw_text:
                # Extract Greek/Hebrew word
                # Try Hebrew format first (word after <br />, before next <br)
                word_match = re.search(r'<br\s*/?>\s*([^\[<\n]+?)\s*<br', raw_text)
                if word_match:
                    potential_word = word_match.group(1).strip()
                    # Make sure it's not just a number
                    if potential_word and not potential_word.isdigit():
                        greek_word = potential_word

                # If no Hebrew word found, try <b>word</b> (Greek format)
                # but skip if it's just a number (entry ID)
                if not greek_word:
                    for match in re.finditer(r'<b>([^<]+)</b>', raw_text):
                        potential = match.group(1).strip()
                        if potential and not potential.isdigit():
                            greek_word = potential
                            break

                # Extract transliteration
                # Hebrew format uses [...] for transliteration
                # Greek format uses [...] for betacode, {word} for transliteration
                # Try [...] first, check if it looks like transliteration (not betacode)
                trans_match = re.search(r"\[([^\]]+)\]", raw_text)
                if trans_match:
                    potential = trans_match.group(1).strip().strip("'")
                    # Betacode uses uppercase and special chars like A)GAPA/W
                    # Real transliteration uses lowercase with diacritics
                    if not re.match(r'^[A-Z/)(\\_=+|]+$', potential):
                        transliteration = potential
                    else:
                        # It's betacode, look for {word} nearby (within first 200 chars)
                        early_text = raw_text[:200]
                        curly_match = re.search(r'\{([^}]+)\}', early_text)
                        if curly_match:
                            transliteration = curly_match.group(1).strip()

                # Extract pronunciation in \<i>...</i>\ or <i>...</i>
                pron_match = re.search(r'\\?<i>([^<]+)</i>\\?', raw_text)
                if pron_match:
                    pronunciation = pron_match.group(1).strip().strip("'")

                # Extract definition (after transliteration/pronunciation, before module name)
                # Find where definition starts (after last <br /> before definition)
                def_match = re.search(r'</i>\\?\s*<br\s*/?>\s*(.+?)(?:\n?\([A-Za-z]+\))?$', raw_text, re.DOTALL)
                if def_match:
                    def_text = def_match.group(1)
                    # Clean HTML: convert <a href...>X</a> to X, <i>...</i> to text, etc.
                    def_text = re.sub(r'<a[^>]*>([^<]*)</a>', r'\1', def_text)
                    def_text = re.sub(r'</?i>', '', def_text)
                    def_text = re.sub(r'</?b>', '', def_text)
                    def_text = re.sub(r'<br\s*/?>', ' ', def_text)
                    def_text = re.sub(r'<[^>]+>', '', def_text)
                    def_text = html.unescape(def_text)
                    definition = re.sub(r'\s+', ' ', def_text).strip()

            # Try plain text Strong's format:
            # "00430:  430  'elohiym  el-o-heem'\n\n definition..."
            elif not greek_word and not definition:
                lines = raw_text.strip().split('\n')
                first_line = lines[0] if lines else ""

                # Parse first line: "NNNNN:  NNN  word  pronunciation"
                first_match = re.match(r"\d+:\s+\d+\s+'?(\S+)\s+(\S+)'?", first_line)
                if first_match:
                    transliteration = first_match.group(1).strip("'")
                    pronunciation = first_match.group(2).strip("'")

                    # Rest is definition (skip empty lines and module attribution)
                    def_lines = []
                    for line in lines[1:]:
                        line = line.strip()
                        # Skip empty lines and module attribution like "(StrongsHebrew)"
                        if line and not re.match(r'^\([A-Za-z]+\)$', line):
                            def_lines.append(line)
                    definition = ' '.join(def_lines)
                    # Normalize whitespace
                    definition = re.sub(r'\s+', ' ', definition).strip()

            # Generic fallback: strip HTML tags
            if not definition:
                plain = _HTML_TAG.sub(' ', raw_text)
                plain = html.unescape(plain)
                plain = re.sub(r'\s+', ' ', plain).strip()
                definition = plain

        # Build title
        if greek_word and transliteration:
            title = f"{strongs_number} - {greek_word} ({transliteration})"
        elif greek_word:
            title = f"{strongs_number} - {greek_word}"
        elif transliteration:
            # Plain text format without Greek/Hebrew script
            title = f"{strongs_number} - {transliteration}"
        else:
            title = strongs_number

        return DictionaryEntry(
            module=module,
            key=strongs_number,
            title=title,
            greek_word=greek_word,
            transliteration=transliteration,
            pronunciation=pronunciation,
            definition=definition,
            raw_text=raw_text,
        )

    def get_formatted_entry(self, entry: DictionaryEntry) -> str:
        """Format a dictionary entry for display.

        Args:
            entry: DictionaryEntry to format

        Returns:
            Formatted string for display
        """
        lines = [entry.title]

        if entry.pronunciation:
            lines.append(f"Pronunciation: {entry.pronunciation}")

        lines.append("")

        if entry.definition:
            lines.append(entry.definition)
        elif entry.raw_text:
            # Fallback to cleaned raw text
            plain = _HTML_TAG.sub(' ', entry.raw_text)
            plain = html.unescape(plain)
            plain = re.sub(r'\s+', ' ', plain).strip()
            lines.append(plain)

        return "\n".join(lines)
