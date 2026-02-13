"""Command handlers for sword-tui."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional
import json

from sword_tui.commands.parser import ParsedCommand, parse_reference
from sword_tui.data.types import Bookmark
from sword_tui.data.aliases import resolve_alias

VALID_COLORS = {"red", "green", "blue", "yellow", "magenta", "cyan"}

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
        self._tag_colors: Dict[str, str] = {}
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
        help_text = """NAVIGATIE
  j/k         Vorige/volgende vers
  gg          Eerste vers
  G           Laatste vers
  ]/[         Volgende/vorige hoofdstuk
  }/{         Volgende/vorig boek
  Ctrl+D/U    Pagina omlaag/omhoog
  r           Ga naar referentie (boek picker)
  :<nummer>   Ga naar vers nummer

NAVIGATIE GESCHIEDENIS
  Ctrl+O      Terug (vorige locatie)
  Ctrl+I      Vooruit (volgende locatie)
  Ctrl+J      Jumplist paneel tonen
  e           Export jumplist (alleen referenties)
  E           Export jumplist (referenties + tekst)

ZOEKEN
  /           KWIC zoeken in hele bijbel
  Ctrl+F      Zoeken in huidig hoofdstuk
  n/N         Volgende/vorige match

IN ZOEKRESULTATEN
  j/k         Navigeer resultaten
  Ctrl+D/U    Pagina omlaag/omhoog
  m           Preview module wisselen
  S           Toggle zoekmodus
  Enter       Ga naar resultaat
  Esc         Sluiten

ZOEKMODI (S of :searchmode)
  1           KWIC alleen (één pane)
  2           Referenties + preview
  3           KWIC + preview

PARALLEL VIEW
  P           Toggle parallel view
  h/l         Focus links/rechts pane
  Tab         Wissel pane focus
  L           Koppel/ontkoppel panes
  m           Module picker (actieve pane)
  M           Module picker (rechter pane)

SELECTIE & KOPIËREN
  v           Visual mode (selecteer verzen)
  y           Kopieer selectie/vers
  Y           Kopieer heel hoofdstuk
  b           Bookmark huidige positie

BOOKMARKS
  '           Toon bookmarks
  :bm add <t> Bookmark met tags (spatie-gescheiden)
  :bm list    Alle bookmarks tonen
  :bm list <t> Filter op tag
  :bm del <n> Bookmark verwijderen
  :bm color <tag> <kleur>  Kleur toewijzen aan tag
  :bm export [pad]         Export bookmarks
  :bm export --text [pad]  Export met verstekst

VERSELISTS
  V           Voeg vers toe aan actieve verselist
  :vl new <n> Nieuwe verselist
  :vl add <n> Voeg vers toe aan verselist
  :vl list    Toon alle verselists
  :vl del <n> Verwijder verselist
  :vl load <n> Open verselist view
  :vl export <n> [pad]  Export verselist

STRONG'S & CROSS-REFS
  s           Toggle Strong's modus
  x           Toggle cross-references
  h/l         Strong's: vorig/volgend woord
  j/k         Crossref: navigeer lijst (in crossref pane)
  Tab         Wissel focus (bijbel/crossref of Strong's)
  Enter       Ga naar cross-reference

STUDY MODE (3-pane)
  T           Toggle study mode
  Tab         Wissel pane (bijbel/commentaar/xrefs)
  j/k         Navigeer in actieve pane
  m           Volgende commentaar module
  M           Kies commentaar module
  Enter       Ga naar cross-reference (in xref pane)

TABS
  gt          Volgende tab
  gT          Vorige tab
  1gt..9gt    Ga naar tab N
  :tabnew     Nieuwe tab
  :tabnew <r> Nieuwe tab bij referentie
  :tabclose   Sluit huidige tab
  :tabname    Hernoem tab

COMMANDO'S
  :quit :q    Afsluiten
  :module     Module picker / wissel module
  :export     Exporteer tekst naar klembord
  :goto <ref> Ga naar referentie
  :jumps      Jumplist paneel tonen
  :jumps export [pad]           Export referenties naar bestand
  :jumps export --text [pad]    Export referenties + verstekst
  :jumps save [naam]            Jumplist opslaan
  :jumps load [naam]            Jumplist laden
  :jumps list                   Opgeslagen jumplists tonen
  :jumps tovl [naam]            Jumplist → verselist
  :help       Deze hulp tonen
"""
        return CommandResult(success=True, message=help_text)

    def _cmd_jumps(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :jumps command.

        Subcommands:
            :jumps              Toggle jumplist panel
            :jumps export [pad] Export refs to file (default: jumplist.txt)
            :jumps export --text [--module=X] [pad]  Export refs + verse text
        """
        if not cmd.args:
            return CommandResult(success=True, action="toggle_jumplist")

        subcommand = cmd.args[0].lower()

        if subcommand == "export":
            with_text = "text" in cmd.flags
            module = cmd.flags.get("module")
            # Remaining args after "export" are the file path
            path_parts = cmd.args[1:]
            path = " ".join(path_parts) if path_parts else "jumplist.txt"
            data = {"path": path, "with_text": with_text}
            if module:
                data["module"] = module
            return CommandResult(
                success=True,
                action="export_jumplist",
                data=data,
            )
        elif subcommand == "save":
            name = cmd.args[1] if len(cmd.args) > 1 else ""
            return CommandResult(
                success=True,
                action="save_jumplist",
                data={"name": name},
            )
        elif subcommand == "list":
            return CommandResult(
                success=True,
                action="list_jumplists",
            )
        elif subcommand == "load":
            name = cmd.args[1] if len(cmd.args) > 1 else ""
            return CommandResult(
                success=True,
                action="load_jumplist",
                data={"name": name},
            )
        elif subcommand == "tovl":
            name = cmd.args[1] if len(cmd.args) > 1 else ""
            return CommandResult(
                success=True,
                action="jumps_to_verselist",
                data={"name": name},
            )

        return CommandResult(
            success=False,
            message=f"Onbekend jumps subcommando: {subcommand}",
        )

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
            filter_tag = cmd.args[1] if len(cmd.args) > 1 else ""
            return self._bookmark_list(filter_tag=filter_tag)
        elif subcommand in ("del", "delete", "rm"):
            return self._bookmark_delete(cmd.args[1:])
        elif subcommand == "export":
            with_text = "text" in cmd.flags
            module = cmd.flags.get("module")
            path_parts = cmd.args[1:]
            path = " ".join(path_parts) if path_parts else "bookmarks.txt"
            data = {"path": path, "with_text": with_text}
            if module:
                data["module"] = module
            return CommandResult(
                success=True,
                action="export_bookmarks",
                data=data,
            )
        elif subcommand == "color":
            if len(cmd.args) < 3:
                return CommandResult(
                    success=False,
                    message=f"Gebruik: :bm color <tag> <kleur> ({', '.join(sorted(VALID_COLORS))})"
                )
            tag = cmd.args[1]
            color = cmd.args[2].lower()
            if color not in VALID_COLORS:
                return CommandResult(
                    success=False,
                    message=f"Ongeldige kleur: {color}. Kies uit: {', '.join(sorted(VALID_COLORS))}"
                )
            self._tag_colors[tag] = color
            self._save_bookmarks()
            return CommandResult(
                success=True,
                action="refresh_bookmark_colors",
                message=f"Tag '{tag}' kleur: {color}",
            )
        else:
            return CommandResult(
                success=False,
                message=f"Onbekende bookmark subcommando: {subcommand}"
            )

    def _bookmark_add(self, args: List[str]) -> CommandResult:
        """Add a bookmark for current location. Args are treated as tags."""
        tags = args if args else []
        return CommandResult(
            success=True,
            action="bookmark_add",
            data={"tags": tags},
        )

    def _bookmark_list(self, filter_tag: str = "") -> CommandResult:
        """List all bookmarks, optionally filtered by tag."""
        if not self._bookmarks:
            return CommandResult(
                success=True,
                message="Geen bookmarks"
            )

        lines = ["Bookmarks:"]
        for i, bm in enumerate(self._bookmarks, 1):
            if filter_tag and filter_tag.lower() not in [t.lower() for t in bm.tags]:
                continue
            tag_str = f"[{', '.join(bm.tags)}] " if bm.tags else ""
            lines.append(f"  {i}. {tag_str}{bm.reference} [{bm.module}]")

        return CommandResult(
            success=True,
            message="\n".join(lines)
        )

    def _bookmark_delete(self, args: List[str]) -> CommandResult:
        """Delete a bookmark by tag, reference, or number."""
        if not args:
            return CommandResult(
                success=False,
                message="Geef bookmark tag, referentie of nummer"
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
                    message=f"Bookmark '{removed.display_name}' verwijderd"
                )
        except ValueError:
            pass

        # Try as tag match
        for i, bm in enumerate(self._bookmarks):
            if target.lower() in [t.lower() for t in bm.tags]:
                self._bookmarks.pop(i)
                self._save_bookmarks()
                return CommandResult(
                    success=True,
                    message=f"Bookmark '{bm.display_name}' verwijderd"
                )

        # Try as reference match
        for i, bm in enumerate(self._bookmarks):
            if bm.reference.lower() == target.lower():
                self._bookmarks.pop(i)
                self._save_bookmarks()
                return CommandResult(
                    success=True,
                    message=f"Bookmark '{bm.display_name}' verwijderd"
                )

        return CommandResult(
            success=False,
            message=f"Bookmark niet gevonden: {target}"
        )

    def _cmd_verselist(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :verselist (vl) command.

        Subcommands:
            :vl new <naam>      Create new verse list
            :vl add <naam>      Add current verse to list
            :vl list            Show all verse lists
            :vl del <naam>      Delete a verse list
            :vl load <naam>     Open verse list view
            :vl export <naam> [pad]  Export verse list
        """
        if not cmd.args:
            return CommandResult(
                success=False,
                message="Gebruik: :vl new|add|list|del|load|export <naam>"
            )

        subcommand = cmd.args[0].lower()

        if subcommand == "new":
            name = " ".join(cmd.args[1:]) if len(cmd.args) > 1 else ""
            if not name:
                return CommandResult(success=False, message="Geef een naam: :vl new <naam>")
            return CommandResult(
                success=True, action="vl_new", data={"name": name}
            )
        elif subcommand == "add":
            name = " ".join(cmd.args[1:]) if len(cmd.args) > 1 else ""
            if not name:
                return CommandResult(success=False, message="Geef een naam: :vl add <naam>")
            return CommandResult(
                success=True, action="vl_add", data={"name": name}
            )
        elif subcommand == "list":
            return CommandResult(success=True, action="vl_list")
        elif subcommand in ("del", "delete", "rm"):
            name = " ".join(cmd.args[1:]) if len(cmd.args) > 1 else ""
            if not name:
                return CommandResult(success=False, message="Geef een naam: :vl del <naam>")
            return CommandResult(
                success=True, action="vl_delete", data={"name": name}
            )
        elif subcommand == "load":
            name = " ".join(cmd.args[1:]) if len(cmd.args) > 1 else ""
            if not name:
                return CommandResult(success=False, message="Geef een naam: :vl load <naam>")
            return CommandResult(
                success=True, action="vl_load", data={"name": name}
            )
        elif subcommand == "export":
            name = cmd.args[1] if len(cmd.args) > 1 else ""
            if not name:
                return CommandResult(success=False, message="Geef een naam: :vl export <naam> [pad]")
            path = " ".join(cmd.args[2:]) if len(cmd.args) > 2 else f"{name}.txt"
            with_text = "text" in cmd.flags
            data = {"name": name, "path": path, "with_text": with_text}
            return CommandResult(success=True, action="vl_export", data=data)
        else:
            return CommandResult(
                success=False,
                message=f"Onbekend verselist subcommando: {subcommand}"
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

    def _cmd_searchmode(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :searchmode command.

        Usage:
            :searchmode [1|2|3]
            1 = KWIC only (single pane with all snippets)
            2 = Refs + preview (default)
            3 = KWIC + preview
        """
        if not cmd.args:
            # Show current mode
            current = self.app._search_display_mode
            mode_names = {
                1: "KWIC (alleen lijst)",
                2: "Referenties + preview",
                3: "KWIC + preview",
            }
            return CommandResult(
                success=True,
                message=f"Huidige zoekmodus: {current} - {mode_names[current]}"
            )

        try:
            mode = int(cmd.first_arg)
            if mode not in (1, 2, 3):
                return CommandResult(
                    success=False,
                    message="Ongeldige modus. Gebruik 1, 2 of 3."
                )
            return CommandResult(
                success=True,
                action="set_search_mode",
                data={"mode": mode}
            )
        except ValueError:
            return CommandResult(
                success=False,
                message="Gebruik: :searchmode [1|2|3]"
            )

    def _cmd_tabnew(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :tabnew command."""
        ref = cmd.rest_args if cmd.args else ""
        return CommandResult(
            success=True,
            action="tab_new",
            data={"ref": ref} if ref else None,
        )

    def _cmd_tabclose(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :tabclose command."""
        return CommandResult(success=True, action="tab_close")

    def _cmd_tabname(self, cmd: ParsedCommand) -> CommandResult:
        """Handle :tabname command."""
        name = cmd.rest_args if cmd.args else ""
        if not name:
            return CommandResult(
                success=False,
                message="Gebruik: :tabname <naam>",
            )
        return CommandResult(
            success=True,
            action="tab_name",
            data={"name": name},
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

    def get_chapter_colors(self, book: str, chapter: int) -> Dict[int, str]:
        """Get bookmark colors for verses in a given chapter.

        Returns:
            Dict mapping verse number to color name.
        """
        result: Dict[int, str] = {}
        for bm in self._bookmarks:
            if bm.book == book and bm.chapter == chapter and bm.verse:
                for tag in bm.tags:
                    if tag in self._tag_colors:
                        result[bm.verse] = self._tag_colors[tag]
                        break
        return result

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
                self._tag_colors = data.get("tag_colors", {})
        except (json.JSONDecodeError, KeyError, TypeError):
            self._bookmarks = []

    def _save_bookmarks(self) -> None:
        """Save bookmarks to config file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        bookmarks_file = self._config_dir / "bookmarks.json"

        data = {
            "bookmarks": [bm.to_dict() for bm in self._bookmarks],
            "tag_colors": self._tag_colors,
        }

        with open(bookmarks_file, "w") as f:
            json.dump(data, f, indent=2)
