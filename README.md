# Sword-TUI

A Bible TUI (Text User Interface) application using the SWORD/diatheke backend.

## Features

- **Bible Viewer** - Browse chapters with vim-style keybindings
- **Module Picker** - Choose from installed SWORD modules
- **KWIC Search** - Keyword-in-context search with split-screen preview
- **Parallel View** - Compare two translations side by side
- **Bookmarks** - Save and load bookmarks
- **Export** - Export passages to text or HTML

## Installation

### NixOS (recommended)

```bash
nix run github:jajpater/sword-tui
```

Or add to your flake inputs:

```nix
{
  inputs.sword-tui.url = "github:jajpater/sword-tui";
}
```

### Development

```bash
# Enter development shell
nix develop

# Run the application
python -m sword_tui

# Run tests
pytest
```

## Keybindings

| Key | Action |
|-----|--------|
| `j`/`k` | Scroll up/down |
| `Ctrl+d`/`Ctrl+u` | Page down/up |
| `]`/`[` | Next/previous chapter |
| `}`/`{` | Next/previous book |
| `g` | Go to reference |
| `/` | KWIC search |
| `P` | Toggle parallel view |
| `m` | Module picker |
| `:` | Command mode |
| `y` | Yank (copy) current chapter |
| `q` | Quit |

## Commands

| Command | Description |
|---------|-------------|
| `:quit`, `:q` | Exit application |
| `:module <name>` | Switch to module |
| `:goto <ref>` | Go to reference (e.g., `:goto Gen 1:5`) |
| `:export [--fmt=txt\|html] <ref>` | Export passage |
| `:bookmark add <name>` | Add bookmark |
| `:bookmark list` | List bookmarks |
| `:bookmark del <name>` | Delete bookmark |
| `:help` | Show help |

## Requirements

- Python 3.11+
- [diatheke](https://wiki.crosswire.org/Frontends:Diatheke) - SWORD CLI frontend
- SWORD modules installed (e.g., DutSVV, KJV)

## Configuration

Configuration files are stored in `~/.config/sword-tui/`:

- `bookmarks.json` - Saved bookmarks

## License

MIT
