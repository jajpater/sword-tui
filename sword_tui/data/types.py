"""Data types for sword-tui."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class VerseSegment:
    """A single verse segment from Bible text."""

    book: str
    chapter: int
    verse: int
    text: str

    @property
    def reference(self) -> str:
        """Return formatted reference string."""
        return f"{self.book} {self.chapter}:{self.verse}"


@dataclass(frozen=True)
class SearchHit:
    """A search result hit."""

    book: str
    chapter: int
    verse: int
    snippet: str
    match_start: int = 0
    match_end: int = 0

    @property
    def reference(self) -> str:
        """Return formatted reference string."""
        return f"{self.book} {self.chapter}:{self.verse}"


@dataclass
class Bookmark:
    """A saved bookmark."""

    name: str
    book: str
    chapter: int
    verse: Optional[int] = None
    module: str = ""
    created: datetime = field(default_factory=datetime.now)

    @property
    def reference(self) -> str:
        """Return formatted reference string."""
        if self.verse:
            return f"{self.book} {self.chapter}:{self.verse}"
        return f"{self.book} {self.chapter}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "book": self.book,
            "chapter": self.chapter,
            "verse": self.verse,
            "module": self.module,
            "created": self.created.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        """Create from dictionary."""
        created = data.get("created")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        else:
            created = datetime.now()
        return cls(
            name=data["name"],
            book=data["book"],
            chapter=data["chapter"],
            verse=data.get("verse"),
            module=data.get("module", ""),
            created=created,
        )
