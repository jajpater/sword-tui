"""Command parser for ex-style commands."""

import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParsedCommand:
    """A parsed command with name and arguments."""

    name: str
    args: List[str] = field(default_factory=list)
    flags: Dict[str, str] = field(default_factory=dict)
    raw: str = ""

    @property
    def first_arg(self) -> str:
        """Get the first argument or empty string."""
        return self.args[0] if self.args else ""

    @property
    def rest_args(self) -> str:
        """Get all arguments as a single string."""
        return " ".join(self.args)


# Command aliases
COMMAND_ALIASES: Dict[str, str] = {
    "q": "quit",
    "q!": "quit!",
    "w": "write",
    "e": "edit",
    "h": "help",
    "mod": "module",
    "m": "module",
    "bm": "bookmark",
    "exp": "export",
    "p": "parallel",
}


def parse_command(command_str: str) -> ParsedCommand:
    """Parse a command string into a ParsedCommand.

    Supports:
    - Simple commands: :quit, :help
    - Commands with args: :module DutSVV
    - Flags: :export --fmt=html Gen 1:1-5
    - Quoted args: :bookmark add "My Bookmark"

    Args:
        command_str: Raw command string (without leading :)

    Returns:
        ParsedCommand instance
    """
    command_str = command_str.strip()
    if not command_str:
        return ParsedCommand(name="", raw=command_str)

    try:
        # Use shlex for proper quote handling
        tokens = shlex.split(command_str)
    except ValueError:
        # Fallback for unbalanced quotes
        tokens = command_str.split()

    if not tokens:
        return ParsedCommand(name="", raw=command_str)

    # First token is the command name
    name = tokens[0].lower()

    # Resolve aliases
    name = COMMAND_ALIASES.get(name, name)

    # Parse remaining tokens into args and flags
    args: List[str] = []
    flags: Dict[str, str] = {}

    for token in tokens[1:]:
        if token.startswith("--"):
            # Long flag: --fmt=html or --verbose
            if "=" in token:
                key, value = token[2:].split("=", 1)
                flags[key] = value
            else:
                flags[token[2:]] = "true"
        elif token.startswith("-") and len(token) > 1:
            # Short flag: -f html or -v
            # For simplicity, treat as boolean flag
            flags[token[1:]] = "true"
        else:
            args.append(token)

    return ParsedCommand(
        name=name,
        args=args,
        flags=flags,
        raw=command_str,
    )


def get_command_names() -> List[str]:
    """Get list of available command names.

    Returns:
        List of command names for completion
    """
    return [
        "quit",
        "help",
        "module",
        "export",
        "bookmark",
        "parallel",
        "goto",
        "search",
        "yank",
    ]


def parse_reference(ref_str: str) -> Optional[tuple[str, int, Optional[int], Optional[int]]]:
    """Parse a Bible reference string.

    Supports:
    - "Gen 1" -> ("Gen", 1, None, None)
    - "Gen 1:5" -> ("Gen", 1, 5, None)
    - "Gen 1:5-10" -> ("Gen", 1, 5, 10)
    - "Genesis 3:16" -> ("Genesis", 3, 16, None)

    Args:
        ref_str: Reference string

    Returns:
        Tuple of (book, chapter, verse_start, verse_end) or None if invalid
    """
    # Pattern: Book Chapter[:Verse[-EndVerse]]
    pattern = re.compile(
        r"^(?P<book>[\w\s]+?)\s+(?P<chapter>\d+)"
        r"(?::(?P<verse>\d+)(?:-(?P<end>\d+))?)?$"
    )

    match = pattern.match(ref_str.strip())
    if not match:
        return None

    book = match.group("book").strip()
    chapter = int(match.group("chapter"))
    verse = int(match.group("verse")) if match.group("verse") else None
    end_verse = int(match.group("end")) if match.group("end") else None

    return (book, chapter, verse, end_verse)
