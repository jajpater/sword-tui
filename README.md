# sword-tui

Een terminal-based Bible reader voor SWORD modules, gebouwd met [Textual](https://textual.textualize.io/).

## Features

- **Vim-style navigatie** - j/k voor verzen, ]/[ voor hoofdstukken, }/{ voor boeken
- **KWIC zoeken** - Zoek door de hele bijbel met keyword-in-context resultaten
- **Parallel view** - Twee vertalingen naast elkaar vergelijken
- **Meerdere zoekmodi** - KWIC alleen, referenties+preview, of KWIC+preview
- **Bookmarks** - Sla favoriete passages op
- **Export** - Kopieer tekst naar klembord (plain text of HTML)
- **Module support** - Werkt met alle geïnstalleerde SWORD modules

## Installatie

### NixOS / Home Manager

Voeg toe aan je `flake.nix` inputs:

```nix
{
  inputs = {
    sword-tui.url = "github:jajpater/sword-tui";
  };
}
```

En in je home-manager configuratie:

```nix
{ inputs, pkgs, ... }:
{
  home.packages = [
    inputs.sword-tui.packages.${pkgs.system}.default
  ];
}
```

Of draai direct:

```bash
nix run github:jajpater/sword-tui
```

### Vereisten

- `diatheke` (onderdeel van SWORD project)
- Minimaal één SWORD module geïnstalleerd

Op NixOS:
```nix
environment.systemPackages = [ pkgs.sword pkgs.diatheke ];
```

## Gebruik

Start de applicatie:

```bash
sword-tui
```

### Sneltoetsen

Druk `?` voor volledige help. Belangrijkste toetsen:

| Toets | Actie |
|-------|-------|
| `j`/`k` | Vorige/volgende vers |
| `]`/`[` | Volgende/vorige hoofdstuk |
| `}`/`{` | Volgende/vorig boek |
| `gg` | Eerste vers |
| `G` | Laatste vers |
| `r` | Ga naar referentie |
| `:<num>` | Ga naar vers nummer |
| `/` | KWIC zoeken |
| `Ctrl+F` | Zoeken in hoofdstuk |
| `P` | Toggle parallel view |
| `m` | Module picker |
| `v` | Visual mode (selecteren) |
| `y` | Kopieer selectie |
| `b` | Bookmark |
| `?` | Help |
| `q` | Afsluiten |

### Parallel View

| Toets | Actie |
|-------|-------|
| `P` | Toggle parallel view |
| `h`/`l` | Focus links/rechts pane |
| `Tab` | Wissel pane focus |
| `L` | Koppel/ontkoppel panes |
| `m` | Module picker (actieve pane) |
| `M` | Module picker (rechter pane) |

### Zoekmodi

In zoekresultaten, druk `S` om te wisselen tussen:

1. **KWIC alleen** - Één pane met alle resultaten en context
2. **Refs + preview** - Referentielijst links, hoofdstuk preview rechts
3. **KWIC + preview** - KWIC lijst links, hoofdstuk preview rechts

Met `m` kun je de preview module wisselen om resultaten in een andere vertaling te bekijken.

### Commando's

| Commando | Beschrijving |
|----------|--------------|
| `:quit` `:q` | Afsluiten |
| `:module <naam>` | Wissel module |
| `:goto <ref>` | Ga naar referentie |
| `:export <ref>` | Exporteer naar klembord |
| `:bm add <naam>` | Bookmark toevoegen |
| `:bm list` | Bookmarks tonen |
| `:bm del <naam>` | Bookmark verwijderen |
| `:searchmode [1-3]` | Zoekmodus instellen |
| `:help` | Help tonen |

## Configuratie

Bookmarks worden opgeslagen in `~/.config/sword-tui/bookmarks.json`.

## SWORD Modules

Installeer SWORD modules met je package manager of download ze van [CrossWire](https://crosswire.org/sword/modules/).

Op NixOS kun je modules installeren met:

```nix
environment.systemPackages = [
  (pkgs.sword.withModules (m: [ m.KJV m.DutSVV ]))
];
```

## Development

```bash
# Enter development shell
nix develop

# Run the application
python -m sword_tui

# Run tests
pytest
```

## Licentie

MIT
