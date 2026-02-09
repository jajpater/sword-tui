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
_DEF = re.compile(r'<def>([^<]+)</def>')
_HTML_TAG = re.compile(r'<[^>]+>')


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
            proc = subprocess.run(
                ["diatheke", "-b", module, "-k", number],
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

            if trans_matches:
                transliteration = trans_matches[0].strip()

            # Extract pronunciation
            pron_match = _PRON.search(entry_content)
            if pron_match:
                pronunciation = pron_match.group(1).strip()

            # Extract definition
            def_match = _DEF.search(entry_content)
            if def_match:
                definition = def_match.group(1).strip()

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
