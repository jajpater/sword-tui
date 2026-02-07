"""Bible canon metadata - book names, chapters, verses."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class CanonBook:
    """Metadata for a Bible book."""

    name: str
    abbr: str
    aliases: tuple[str, ...]
    chapters: int


# Complete canon with Dutch names and common aliases
_CANON_TABLE: Sequence[CanonBook] = (
    # Old Testament
    CanonBook("Genesis", "Gen", ("gen", "ge", "gn", "genesis", "1mo", "1mos"), 50),
    CanonBook("Exodus", "Ex", ("exo", "ex", "exodus", "2mo", "2mos"), 40),
    CanonBook("Leviticus", "Lev", ("lev", "le", "leviticus", "3mo", "3mos"), 27),
    CanonBook("Numeri", "Num", ("num", "nu", "numeri", "numbers", "4mo", "4mos"), 36),
    CanonBook("Deuteronomium", "Deut", ("deut", "de", "dt", "deuteronomium", "deuteronomy", "5mo", "5mos"), 34),
    CanonBook("Jozua", "Joz", ("joz", "jos", "joshua", "jozua"), 24),
    CanonBook("Richteren", "Richt", ("richt", "ri", "richteren", "judges", "judg"), 21),
    CanonBook("Ruth", "Ruth", ("ruth", "ru", "rth"), 4),
    CanonBook("1 Samuël", "1Sam", ("1sam", "1sa", "1samuel", "1 samuel"), 31),
    CanonBook("2 Samuël", "2Sam", ("2sam", "2sa", "2samuel", "2 samuel"), 24),
    CanonBook("1 Koningen", "1Kon", ("1kon", "1ki", "1kings", "1 koningen", "1koningen"), 22),
    CanonBook("2 Koningen", "2Kon", ("2kon", "2ki", "2kings", "2 koningen", "2koningen"), 25),
    CanonBook("1 Kronieken", "1Kron", ("1kron", "1chr", "1chronicles", "1 kronieken", "1kronieken"), 29),
    CanonBook("2 Kronieken", "2Kron", ("2kron", "2chr", "2chronicles", "2 kronieken", "2kronieken"), 36),
    CanonBook("Ezra", "Ezra", ("ezra", "ezr"), 10),
    CanonBook("Nehemia", "Neh", ("neh", "ne", "nehemia", "nehemiah"), 13),
    CanonBook("Esther", "Est", ("est", "esther"), 10),
    CanonBook("Job", "Job", ("job", "jb"), 42),
    CanonBook("Psalmen", "Ps", ("ps", "psa", "psalm", "psalmen", "psalms"), 150),
    CanonBook("Spreuken", "Spr", ("spr", "pr", "prov", "spreuken", "proverbs"), 31),
    CanonBook("Prediker", "Pred", ("pred", "ec", "ecc", "prediker", "ecclesiastes"), 12),
    CanonBook("Hooglied", "Hoogl", ("hoogl", "hl", "song", "hooglied", "songofsolomon", "canticles"), 8),
    CanonBook("Jesaja", "Jes", ("jes", "isa", "jesaja", "isaiah"), 66),
    CanonBook("Jeremia", "Jer", ("jer", "je", "jeremia", "jeremiah"), 52),
    CanonBook("Klaagliederen", "Klaagl", ("klaagl", "lam", "klaagliederen", "lamentations"), 5),
    CanonBook("Ezechiël", "Ez", ("ez", "ezek", "ezechiel", "ezekiel"), 48),
    CanonBook("Daniël", "Dan", ("dan", "da", "daniel"), 12),
    CanonBook("Hosea", "Hos", ("hos", "ho", "hosea"), 14),
    CanonBook("Joël", "Joël", ("joel", "joe", "jl"), 3),
    CanonBook("Amos", "Am", ("am", "amos"), 9),
    CanonBook("Obadja", "Ob", ("ob", "obad", "obadja", "obadiah"), 1),
    CanonBook("Jona", "Jona", ("jona", "jon", "jonah"), 4),
    CanonBook("Micha", "Mi", ("mi", "mic", "micha", "micah"), 7),
    CanonBook("Nahum", "Nah", ("nah", "na", "nahum"), 3),
    CanonBook("Habakuk", "Hab", ("hab", "habakuk", "habakkuk"), 3),
    CanonBook("Zefanja", "Zef", ("zef", "zeph", "zefanja", "zephaniah"), 3),
    CanonBook("Haggaï", "Hag", ("hag", "haggai"), 2),
    CanonBook("Zacharia", "Zach", ("zach", "zec", "zacharia", "zechariah"), 14),
    CanonBook("Maleachi", "Mal", ("mal", "maleachi", "malachi"), 4),
    # New Testament
    CanonBook("Mattheüs", "Matt", ("matt", "mt", "mattheus", "matthew"), 28),
    CanonBook("Markus", "Mark", ("mark", "mk", "marcus", "markus"), 16),
    CanonBook("Lukas", "Luk", ("luk", "lk", "lukas", "luke"), 24),
    CanonBook("Johannes", "Joh", ("joh", "jn", "johannes", "john"), 21),
    CanonBook("Handelingen", "Hand", ("hand", "acts", "handelingen", "actsoftheapostles"), 28),
    CanonBook("Romeinen", "Rom", ("rom", "ro", "romeinen", "romans"), 16),
    CanonBook("1 Korinthe", "1Kor", ("1kor", "1co", "1cor", "1 korinthe", "1korinthe", "1corinthians"), 16),
    CanonBook("2 Korinthe", "2Kor", ("2kor", "2co", "2cor", "2 korinthe", "2korinthe", "2corinthians"), 13),
    CanonBook("Galaten", "Gal", ("gal", "ga", "galaten", "galatians"), 6),
    CanonBook("Efeze", "Ef", ("ef", "eph", "efeze", "ephesians"), 6),
    CanonBook("Filippenzen", "Fil", ("fil", "php", "filippenzen", "philippians"), 4),
    CanonBook("Kolossenzen", "Kol", ("kol", "col", "kolossenzen", "colossians"), 4),
    CanonBook("1 Thessalonicenzen", "1Thess", ("1thess", "1th", "1 thessalonicenzen", "1thessalonicenzen", "1thessalonians"), 5),
    CanonBook("2 Thessalonicenzen", "2Thess", ("2thess", "2th", "2 thessalonicenzen", "2thessalonicenzen", "2thessalonians"), 3),
    CanonBook("1 Timotheüs", "1Tim", ("1tim", "1ti", "1 timotheus", "1timotheus", "1timothy"), 6),
    CanonBook("2 Timotheüs", "2Tim", ("2tim", "2ti", "2 timotheus", "2timotheus", "2timothy"), 4),
    CanonBook("Titus", "Tit", ("tit", "titus"), 3),
    CanonBook("Filemon", "Filem", ("filem", "phm", "filemon", "philemon"), 1),
    CanonBook("Hebreeën", "Heb", ("heb", "hebreeen", "hebrews"), 13),
    CanonBook("Jakobus", "Jak", ("jak", "jas", "jakobus", "james"), 5),
    CanonBook("1 Petrus", "1Pet", ("1pet", "1pe", "1 petrus", "1petrus", "1peter"), 5),
    CanonBook("2 Petrus", "2Pet", ("2pet", "2pe", "2 petrus", "2petrus", "2peter"), 3),
    CanonBook("1 Johannes", "1Joh", ("1joh", "1jn", "1 johannes", "1johannes", "1john"), 5),
    CanonBook("2 Johannes", "2Joh", ("2joh", "2jn", "2 johannes", "2johannes", "2john"), 1),
    CanonBook("3 Johannes", "3Joh", ("3joh", "3jn", "3 johannes", "3johannes", "3john"), 1),
    CanonBook("Judas", "Jud", ("jud", "jude", "judas"), 1),
    CanonBook("Openbaring", "Openb", ("openb", "rev", "openbaring", "revelation", "apocalypse"), 22),
)

# Book order list
BOOK_ORDER: List[str] = [book.name for book in _CANON_TABLE]

# Lookup tables
_BOOK_BY_NAME: Dict[str, CanonBook] = {book.name: book for book in _CANON_TABLE}

# Build alias map
_ALIAS_MAP: Dict[str, str] = {}
for book in _CANON_TABLE:
    _ALIAS_MAP[book.name.lower()] = book.name
    _ALIAS_MAP[book.abbr.lower()] = book.name
    for alias in book.aliases:
        _ALIAS_MAP[alias.lower()] = book.name

# Diatheke uses English book names
DIATHEKE_TOKENS: Dict[str, str] = {
    "Genesis": "Genesis",
    "Exodus": "Exodus",
    "Leviticus": "Leviticus",
    "Numeri": "Numbers",
    "Deuteronomium": "Deuteronomy",
    "Jozua": "Joshua",
    "Richteren": "Judges",
    "Ruth": "Ruth",
    "1 Samuël": "1Samuel",
    "2 Samuël": "2Samuel",
    "1 Koningen": "1Kings",
    "2 Koningen": "2Kings",
    "1 Kronieken": "1Chronicles",
    "2 Kronieken": "2Chronicles",
    "Ezra": "Ezra",
    "Nehemia": "Nehemiah",
    "Esther": "Esther",
    "Job": "Job",
    "Psalmen": "Psalms",
    "Spreuken": "Proverbs",
    "Prediker": "Ecclesiastes",
    "Hooglied": "Song of Solomon",
    "Jesaja": "Isaiah",
    "Jeremia": "Jeremiah",
    "Klaagliederen": "Lamentations",
    "Ezechiël": "Ezekiel",
    "Daniël": "Daniel",
    "Hosea": "Hosea",
    "Joël": "Joel",
    "Amos": "Amos",
    "Obadja": "Obadiah",
    "Jona": "Jonah",
    "Micha": "Micah",
    "Nahum": "Nahum",
    "Habakuk": "Habakkuk",
    "Zefanja": "Zephaniah",
    "Haggaï": "Haggai",
    "Zacharia": "Zechariah",
    "Maleachi": "Malachi",
    "Mattheüs": "Matthew",
    "Markus": "Mark",
    "Lukas": "Luke",
    "Johannes": "John",
    "Handelingen": "Acts",
    "Romeinen": "Romans",
    "1 Korinthe": "1Corinthians",
    "2 Korinthe": "2Corinthians",
    "Galaten": "Galatians",
    "Efeze": "Ephesians",
    "Filippenzen": "Philippians",
    "Kolossenzen": "Colossians",
    "1 Thessalonicenzen": "1Thessalonians",
    "2 Thessalonicenzen": "2Thessalonians",
    "1 Timotheüs": "1Timothy",
    "2 Timotheüs": "2Timothy",
    "Titus": "Titus",
    "Filemon": "Philemon",
    "Hebreeën": "Hebrews",
    "Jakobus": "James",
    "1 Petrus": "1Peter",
    "2 Petrus": "2Peter",
    "1 Johannes": "1John",
    "2 Johannes": "2John",
    "3 Johannes": "3John",
    "Judas": "Jude",
    "Openbaring": "Revelation",
}

# Reverse mapping for parsing diatheke output
DIATHEKE_TO_CANON: Dict[str, str] = {v: k for k, v in DIATHEKE_TOKENS.items()}

# Verse count overrides (where default assumptions are wrong)
VERSE_COUNT_OVERRIDES: Dict[tuple[str, int], int] = {
    ("Genesis", 1): 31,
    ("Genesis", 10): 32,
    ("Psalmen", 23): 6,
    ("Psalmen", 119): 176,
    ("Johannes", 3): 36,
    ("Romeinen", 8): 39,
}


def book_chapters(name: str) -> int:
    """Return the number of chapters in a book."""
    book = _BOOK_BY_NAME.get(name)
    return book.chapters if book else 0


def book_index(name: str) -> int:
    """Return the index of a book in the canon (0-based)."""
    try:
        return BOOK_ORDER.index(name)
    except ValueError:
        return -1


def get_book(name: str) -> Optional[CanonBook]:
    """Get a CanonBook by name."""
    return _BOOK_BY_NAME.get(name)


def diatheke_token(name: str) -> str:
    """Return the diatheke-compatible book name."""
    token = DIATHEKE_TOKENS.get(name)
    if token:
        return token
    # Fallback: try abbreviation
    book = _BOOK_BY_NAME.get(name)
    if book:
        return book.abbr
    return name


def chapter_verses(book: str, chapter: int) -> int:
    """Return estimated verse count for a chapter."""
    override = VERSE_COUNT_OVERRIDES.get((book, chapter))
    if override:
        return override
    # Default estimate based on typical chapter lengths
    return 30


def resolve_alias(alias: str, fuzzy: bool = True) -> Optional[str]:
    """Resolve a book alias to the canonical name."""
    if not alias:
        return None
    token = alias.strip().lower()
    normalized = token.replace(".", "").replace(" ", "")

    # Exact match
    if token in _ALIAS_MAP:
        return _ALIAS_MAP[token]
    if normalized in _ALIAS_MAP:
        return _ALIAS_MAP[normalized]

    # Exact name match (case-insensitive)
    for name in BOOK_ORDER:
        if name.lower() == token:
            return name

    # Fuzzy prefix matching
    if fuzzy:
        candidates: List[tuple[int, str]] = []
        for key, name in _ALIAS_MAP.items():
            if key.startswith(normalized):
                idx = book_index(name)
                if idx >= 0 and (idx, name) not in candidates:
                    candidates.append((idx, name))
        candidates.sort()
        if candidates:
            return candidates[0][1]

    return None


def search_books(query: str, limit: int = 10) -> List[CanonBook]:
    """Search books by name/alias with scoring."""
    needle = query.strip().lower()
    if not needle:
        return list(_CANON_TABLE[:limit])

    matches: List[tuple[int, CanonBook]] = []

    for book in _CANON_TABLE:
        haystack = {book.name.lower(), book.abbr.lower()}
        haystack.update(alias.lower() for alias in book.aliases)

        # Prefix match = higher priority
        if any(h.startswith(needle) for h in haystack):
            matches.append((0, book))
            continue

        # Substring match = lower priority
        if any(needle in h for h in haystack):
            matches.append((1, book))

    matches.sort(key=lambda item: (item[0], book_index(item[1].name)))
    return [book for _, book in matches][:limit]


def next_book(name: str) -> Optional[str]:
    """Return the next book in the canon."""
    idx = book_index(name)
    if 0 <= idx < len(BOOK_ORDER) - 1:
        return BOOK_ORDER[idx + 1]
    return None


def prev_book(name: str) -> Optional[str]:
    """Return the previous book in the canon."""
    idx = book_index(name)
    if idx > 0:
        return BOOK_ORDER[idx - 1]
    return None
