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


def _clean_definition(raw_def: str) -> str:
    """Clean XML tags from definition text for human-readable output.

    Args:
        raw_def: Raw definition text with XML tags

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

    # Replace <sense n="1"> with "1." for readability
    def format_sense(match: re.Match) -> str:
        content = match.group(1)
        return content

    text = _SENSE_TAG.sub(format_sense, text)

    # Remove <note> tags and their content (footnotes within definitions)
    text = _NOTE_TAG.sub('', text)

    # Replace <lb/> line breaks with actual newlines
    text = _LB_TAG.sub('\n', text)

    # Strip any remaining HTML/XML tags
    text = _HTML_TAG.sub(' ', text)

    # Unescape HTML entities
    text = html.unescape(text)

    # Normalize whitespace (but preserve intentional newlines)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned = _WHITESPACE.sub(' ', line).strip()
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
                text=True,
                timeout=5,
            )
            # Verify we got the right entry (check title matches requested number)
            lookup_key = strongs_number.upper()  # e.g., "H430" or "G25"
            if (proc.returncode != 0 or "Entry not found" in proc.stdout
                    or f"<title>{lookup_key}</title>" not in proc.stdout):
                # Try with full key (for BDBGlosses_Strongs and similar)
                proc = subprocess.run(
                    ["diatheke", "-b", module, "-k", lookup_key],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            if proc.returncode != 0:
                return None

            raw = proc.stdout.strip()
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
                definition = _clean_definition(def_match.group(1))
            else:
                # No <def> tag - use entire content minus title/foreign as definition
                # This handles BDBGlosses_Strongs format with <sense> tags
                content_for_def = entry_content
                # Remove title
                content_for_def = _TITLE.sub('', content_for_def)
                definition = _clean_definition(content_for_def)

        # If XML parsing didn't work, try to extract from plain text
        if not greek_word and not definition:
            # Strip HTML tags for fallback
            plain = _HTML_TAG.sub(' ', raw_text)
            plain = html.unescape(plain)
            plain = re.sub(r'\s+', ' ', plain).strip()
            definition = plain

        # Build title
        if greek_word and transliteration:
            title = f"{strongs_number} - {greek_word} ({transliteration})"
        elif greek_word:
            title = f"{strongs_number} - {greek_word}"
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
