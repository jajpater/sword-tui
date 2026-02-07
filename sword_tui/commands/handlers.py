"""Command handlers for sword-tui."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
import json

from sword_tui.commands.parser import ParsedCommand, parse_reference
from sword_tui.data.types import Bookmark
from sword_tui.data.aliases import resolve_alias

if TYPE_CHECKING:
    from sword_tui.app import SwordApp


@dataclass
class CommandResult:
    """Result of command execution."""

    success: bool
    message: str = ""
    action: str = ""  # Special action to take: "quit", "goto", etc.
    data: Optional[dict] = None


class CommandHandler:
    """Handles command execution."""

    def __init__(self, app: "SwordApp") -> None:
        self.app = app
        self._bookmarks: List[Bookmark] = []
        self._config_dir = Path.home() / ".config" / "sword-tui"
        self._load_bookmarks()

    def execute(self, cmd: ParsedCommand) -> CommandResult:
        """Execute a parsed command.

        Args:
            cmd: Parsed command

        Returns:
            CommandResult with status and message
        """
        if not cmd.name:
            return CommandResult(success=False, message="Geen commando")

        # Dispatch to handler
        handler_name = f"_cmd_{cmd.name.replace('-', '_')}"
        handler = getattr(self, handler_name, None)

        if handler:
            return handler(cmd)
        else:
            return CommandResult(
                success=False,
                message=f"Onbekend commando: {cmd.name}"
            )

    def _cmd_quit(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :quit command."""
        return CommandResult(success=True, action="quit")

    def _cmd_help(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :help command."""
        help_text = """
Commando's:
  :quit, :q         - Afsluiten
  :module <name>    - Wissel module
  :export <ref>     - Exporteer tekst
  :bookmark add <n> - Bookmark toevoegen
  :bookmark list    - Bookmarks tonen
  :bookmark del <n> - Bookmark verwijderen
  :goto <ref>       - Ga naar referentie

Toetsen:
  j/k     - Scroll
  ]/[     - Volgende/vorige hoofdstuk
  }/{     - Volgende/vorig boek
  g       - Ga naar
  /       - Zoeken
  P       - Parallel view
  m       - Module picker
  y       - Kopieer
  q       - Afsluiten
"""
        return CommandResult(success=True, message=help_text)

    def _cmd_module(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :module command."""
        if not cmd.args:
            return CommandResult(
                success=True,
                action="module_picker"
            )

        module_name = cmd.first_arg
        return CommandResult(
            success=True,
            action="set_module",
            data={"module": module_name}
        )

    def _cmd_goto(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :goto command."""
        if not cmd.args:
            return CommandResult(
                success=False,
                message="Gebruik: :goto <referentie>"
            )

        ref_str = cmd.rest_args
        parsed = parse_reference(ref_str)

        if not parsed:
            return CommandResult(
                success=False,
                message=f"Ongeldige referentie: {ref_str}"
            )

        book, chapter, verse, _ = parsed
        canonical = resolve_alias(book)

        if not canonical:
            return CommandResult(
                success=False,
                message=f"Onbekend boek: {book}"
            )

        return CommandResult(
            success=True,
            action="goto",
            data={"book": canonical, "chapter": chapter, "verse": verse}
        )

    def _cmd_export(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :export command."""
        if not cmd.args:
            return CommandResult(
                success=False,
                message="Gebruik: :export [--fmt=txt|html] <referentie>"
            )

        fmt = cmd.flags.get("fmt", "txt")
        ref_str = cmd.rest_args
        parsed = parse_reference(ref_str)

        if not parsed:
            return CommandResult(
                success=False,
                message=f"Ongeldige referentie: {ref_str}"
            )

        book, chapter, verse_start, verse_end = parsed
        canonical = resolve_alias(book)

        if not canonical:
            return CommandResult(
                success=False,
                message=f"Onbekend boek: {book}"
            )

        return CommandResult(
            success=True,
            action="export",
            data={
                "book": canonical,
                "chapter": chapter,
                "verse_start": verse_start,
                "verse_end": verse_end,
                "format": fmt,
            }
        )

    def _cmd_bookmark(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :bookmark command."""
        if not cmd.args:
            return CommandResult(
                success=False,
                message="Gebruik: :bookmark add|list|del <naam>"
            )

        subcommand = cmd.args[0].lower()

        if subcommand == "add":
            return self._bookmark_add(cmd.args[1:])
        elif subcommand == "list":
            return self._bookmark_list()
        elif subcommand in ("del", "delete", "rm"):
            return self._bookmark_delete(cmd.args[1:])
        else:
            return CommandResult(
                success=False,
                message=f"Onbekende bookmark subcommando: {subcommand}"
            )

    def _bookmark_add(self, args: List[str]) -> CommandResult:
        """Add a bookmark for current location."""
        name = " ".join(args) if args else ""

        if not name:
            return CommandResult(
                success=False,
                message="Geef een naam voor de bookmark"
            )

        # Get current location from app
        book = self.app._current_book
        chapter = self.app._current_chapter
        module = self.app._current_module

        bookmark = Bookmark(
            name=name,
            book=book,
            chapter=chapter,
            module=module,
        )

        self._bookmarks.append(bookmark)
        self._save_bookmarks()

        return CommandResult(
            success=True,
            message=f"Bookmark '{name}' toegevoegd: {book} {chapter}"
        )

    def _bookmark_list(self) -> CommandResult:
        """List all bookmarks."""
        if not self._bookmarks:
            return CommandResult(
                success=True,
                message="Geen bookmarks"
            )

        lines = ["Bookmarks:"]
        for i, bm in enumerate(self._bookmarks, 1):
            lines.append(f"  {i}. {bm.name}: {bm.reference} [{bm.module}]")

        return CommandResult(
            success=True,
            message="\n".join(lines)
        )

    def _bookmark_delete(self, args: List[str]) -> CommandResult:
        """Delete a bookmark by name or number."""
        if not args:
            return CommandResult(
                success=False,
                message="Geef bookmark naam of nummer"
            )

        target = " ".join(args)

        # Try as number first
        try:
            idx = int(target) - 1
            if 0 <= idx < len(self._bookmarks):
                removed = self._bookmarks.pop(idx)
                self._save_bookmarks()
                return CommandResult(
                    success=True,
                    message=f"Bookmark '{removed.name}' verwijderd"
                )
        except ValueError:
            pass

        # Try as name
        for i, bm in enumerate(self._bookmarks):
            if bm.name.lower() == target.lower():
                self._bookmarks.pop(i)
                self._save_bookmarks()
                return CommandResult(
                    success=True,
                    message=f"Bookmark '{bm.name}' verwijderd"
                )

        return CommandResult(
            success=False,
            message=f"Bookmark niet gevonden: {target}"
        )

    def _cmd_parallel(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :parallel command."""
        return CommandResult(
            success=True,
            action="toggle_parallel"
        )

    def _cmd_yank(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :yank command."""
        return CommandResult(
            success=True,
            action="yank"
        )

    def _cmd_search(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :search command."""
        if not cmd.args:
            return CommandResult(
                success=False,
                message="Gebruik: :search <zoekterm>"
            )

        query = cmd.rest_args
        return CommandResult(
            success=True,
            action="search",
            data={"query": query}
        )

    def get_bookmarks(self) -> List[Bookmark]:
        """Get all bookmarks."""
        return self._bookmarks.copy()

    def goto_bookmark(self, bookmark: Bookmark) -> CommandResult:
        """Navigate to a bookmark."""
        return CommandResult(
            success=True,
            action="goto",
            data={
                "book": bookmark.book,
                "chapter": bookmark.chapter,
                "verse": bookmark.verse,
            }
        )

    def _load_bookmarks(self) -> None:
        """Load bookmarks from config file."""
        bookmarks_file = self._config_dir / "bookmarks.json"
        if not bookmarks_file.exists():
            return

        try:
            with open(bookmarks_file) as f:
                data = json.load(f)
                self._bookmarks = [
                    Bookmark.from_dict(bm) for bm in data.get("bookmarks", [])
                ]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._bookmarks = []

    def _save_bookmarks(self) -> None:
        """Save bookmarks to config file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        bookmarks_file = self._config_dir / "bookmarks.json"

        data = {
            "bookmarks": [bm.to_dict() for bm in self._bookmarks]
        }

        with open(bookmarks_file, "w") as f:
            json.dump(data, f, indent=2)
