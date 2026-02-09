# Plan: 3-Pane Studie Interface

## Concept

Een drievoudige studie-interface voor diepgaande bijbelstudie:

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ 1. BIJBELTEKST      │ 2. COMMENTAAR/TSK   │ 3. CROSS-REFS       │
│                     │                     │    (opgezocht)      │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Genesis 10:1        │ ── DutKant ──       │ ── 1 Kron 1:4 ──    │
│                     │                     │                     │
│ DIT nu zijn de      │ "geboorten" = Of:   │ Dit zijn de         │
│ geboorten van       │ geslachten.         │ nakomelingen van    │
│ Noachs zonen, Sem,  │                     │ Sem, Cham en Jafet  │
│ Cham en Jafeth...   │ Verwijzingen:       │                     │
│                     │ → 1 Kron 1:4        │                     │
│                     │                     │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

## Pane Functies

### Pane 1: Bijbeltekst (links)
- De primaire bijbelmodule (GBS2, DutSVV, KJV, etc.)
- Navigatie met j/k, ]/[, etc.
- Bij vers-wissel: update pane 2 en 3

### Pane 2: Commentaar/TSK (midden)
- Toont commentaar voor het HUIDIGE vers
- Kan wisselen tussen modules: DutKant, TSK, MHC, Geneva, Catena
- Bevat inline referenties (scripRef, crossReference notes)
- `m` om commentaar module te wisselen

### Pane 3: Cross-refs Opgezocht (rechts)
- Toont de TEKST van referenties uit pane 2
- Als DutKant zegt "1 Kron 1:4" → hier zie je die tekst
- Navigeerbaar: j/k door de refs, Enter om erheen te gaan

## Keybindings

```
Navigatie (pane 1 actief):
  j/k         Vorig/volgend vers
  ]/[         Vorig/volgend hoofdstuk
  h/l         Focus naar links/rechts pane
  Tab         Cycle door panes

Pane 2 (commentaar):
  m           Wissel commentaar module
  j/k         Scroll in commentaar

Pane 3 (cross-refs):
  j/k         Navigeer door refs
  Enter       Ga naar geselecteerde ref
  y           Kopieer ref tekst

Modes:
  T           Toggle study mode (3-pane) aan/uit
  P           Parallel view (2 bijbels naast elkaar) - bestaand
```

## Implementatie

### Fase 1: StudyView Widget

Nieuwe widget: `widgets/study_view.py`

```python
class StudyView(Widget):
    """3-pane study interface."""

    def compose(self):
        with Horizontal():
            # Pane 1: Bible text
            yield BiblePane(id="study-bible")
            # Pane 2: Commentary
            yield CommentaryPane(id="study-commentary")
            # Pane 3: Cross-refs lookup
            yield CrossRefPane(id="study-crossrefs")
```

### Fase 2: CommentaryPane

Nieuwe widget voor commentaar weergave:

```python
class CommentaryPane(Widget):
    """Shows commentary for current verse."""

    def update_verse(self, book, chapter, verse):
        # Haal commentaar op voor dit vers
        # Parse scripRef tags
        # Emit event met gevonden referenties
```

### Fase 3: CrossRefPane (aangepast)

Uitbreiding van huidige CrossRefView:

```python
class CrossRefPane(Widget):
    """Shows looked-up text of cross-references."""

    def update_refs(self, refs: List[CrossReference]):
        # Zoek tekst op voor elke ref
        # Toon in scrollable lijst
```

### Fase 4: App Integratie

- Nieuwe mode: `_in_study_mode`
- Keybinding `T` voor toggle
- State sync tussen panes

## Data Flow

```
User navigeert naar Gen 10:1
         │
         ▼
┌─────────────────┐
│ Pane 1: Bible   │ ──► Laad Gen 10:1 tekst
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Pane 2: Comment │ ──► diatheke -b DutKant -k "Gen 10:1"
└─────────────────┘     Parse <scripRef> tags
         │              Vind: 1 Kron 1:4
         ▼
┌─────────────────┐
│ Pane 3: Xrefs   │ ──► diatheke -b DutSVV -k "1 Kron 1:4"
└─────────────────┘     Toon opgezochte tekst
```

## Modules Config

In `~/.config/sword-tui/config.json`:

```json
{
  "study_mode": {
    "bible_module": "GBS2",
    "commentary_modules": ["DutKant", "TSK", "MHC"],
    "default_commentary": "DutKant",
    "crossref_bible": "DutSVV"
  }
}
```

## Bookmarks (later)

Na de study mode:
- `b` bookmark huidig vers
- `'` open bookmark lijst
- Opslag in `~/.config/sword-tui/bookmarks.json`
