"""Tests for command parsing and handling."""

import pytest

from sword_tui.commands.parser import (
    parse_command,
    parse_reference,
    get_command_names,
    COMMAND_ALIASES,
)


class TestParseCommand:
    """Test command parsing."""

    def test_simple_command(self):
        """Simple command should parse."""
        cmd = parse_command("quit")
        assert cmd.name == "quit"
        assert cmd.args == []
        assert cmd.flags == {}

    def test_command_with_args(self):
        """Command with arguments should parse."""
        cmd = parse_command("module DutSVV")
        assert cmd.name == "module"
        assert cmd.args == ["DutSVV"]

    def test_command_alias(self):
        """Command aliases should resolve."""
        cmd = parse_command("q")
        assert cmd.name == "quit"

        cmd = parse_command("m DutSVV")
        assert cmd.name == "module"
        assert cmd.args == ["DutSVV"]

    def test_command_with_flags(self):
        """Command with flags should parse."""
        cmd = parse_command("export --fmt=html Gen 1:1")
        assert cmd.name == "export"
        assert cmd.flags == {"fmt": "html"}
        assert "Gen" in cmd.args
        assert "1:1" in cmd.args

    def test_quoted_args(self):
        """Quoted arguments should be preserved."""
        cmd = parse_command('bookmark add "My Favorite Verse"')
        assert cmd.name == "bookmark"
        assert cmd.args == ["add", "My Favorite Verse"]

    def test_empty_command(self):
        """Empty command should return empty name."""
        cmd = parse_command("")
        assert cmd.name == ""

    def test_first_arg_property(self):
        """first_arg property should work."""
        cmd = parse_command("module DutSVV")
        assert cmd.first_arg == "DutSVV"

        cmd = parse_command("quit")
        assert cmd.first_arg == ""

    def test_rest_args_property(self):
        """rest_args property should work."""
        cmd = parse_command("goto Gen 1:5")
        assert cmd.rest_args == "Gen 1:5"


class TestParseReference:
    """Test Bible reference parsing."""

    def test_book_chapter(self):
        """Book and chapter should parse."""
        result = parse_reference("Gen 1")
        assert result == ("Gen", 1, None, None)

    def test_book_chapter_verse(self):
        """Book, chapter, and verse should parse."""
        result = parse_reference("Gen 1:5")
        assert result == ("Gen", 1, 5, None)

    def test_book_chapter_verse_range(self):
        """Verse range should parse."""
        result = parse_reference("Gen 1:5-10")
        assert result == ("Gen", 1, 5, 10)

    def test_multi_word_book(self):
        """Multi-word book names should parse."""
        result = parse_reference("1 Kings 3:16")
        assert result == ("1 Kings", 3, 16, None)

    def test_invalid_reference(self):
        """Invalid reference should return None."""
        assert parse_reference("invalid") is None
        assert parse_reference("") is None

    def test_whitespace(self):
        """Whitespace should be handled."""
        result = parse_reference("  Gen  1:5  ")
        assert result == ("Gen", 1, 5, None)


class TestCommandAliases:
    """Test command aliases."""

    def test_common_aliases(self):
        """Common aliases should be defined."""
        assert "q" in COMMAND_ALIASES
        assert COMMAND_ALIASES["q"] == "quit"
        assert "m" in COMMAND_ALIASES
        assert COMMAND_ALIASES["m"] == "module"

    def test_get_command_names(self):
        """Command names list should be available."""
        names = get_command_names()
        assert "quit" in names
        assert "module" in names
        assert "bookmark" in names
