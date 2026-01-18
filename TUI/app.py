"""
YouTubeDownloaderApp

Main TUI Application for downloading YouTube videos.
"""

from textual.app import App
from textual.binding import Binding

from TUI.screens.main_menu import MainMenuScreen

try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None


class YouTubeDownloaderApp(App):
    """Main YouTube Downloader TUI Application"""
    
    TITLE = "YouTube Video Downloader"
    SUB_TITLE = "Built with Textual & pytubefix"
    
    CSS = """
    Screen {
        background: $background;
    }
    
    Header {
        background: $primary;
    }
    
    Footer {
        background: $surface;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]
    
    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())
        
    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"


def main():
    """Entry point for the TUI application"""
    if YouTube is None:
        print("❌ Error: pytubefix is not installed.")
        print("   Please install it with: pip install pytubefix")
        return 1
        
    app = YouTubeDownloaderApp()
    app.run()
    return 0


if __name__ == "__main__":
    exit(main())
