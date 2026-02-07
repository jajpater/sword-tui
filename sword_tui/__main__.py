"""Entry point for sword-tui."""

from sword_tui.app import SwordApp


def main() -> None:
    """Run the sword-tui application."""
    app = SwordApp()
    app.run()


if __name__ == "__main__":
    main()
