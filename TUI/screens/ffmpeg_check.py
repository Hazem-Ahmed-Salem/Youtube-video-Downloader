"""
FFmpegCheckScreen

Screen to check FFmpeg installation status.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button
from textual.screen import Screen
from textual.binding import Binding

from TUI.utils import has_ffmpeg


class FFmpegCheckScreen(Screen):
    """Screen to check FFmpeg installation"""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]
    
    DEFAULT_CSS = """
    FFmpegCheckScreen {
        align: center middle;
    }
    
    .ffmpeg-container {
        width: 80;
        height: auto;
        padding: 2;
        border: solid $primary;
        background: $surface;
    }
    
    .screen-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 2;
    }
    
    .status-available {
        background: $success-darken-2;
        color: $success;
        padding: 1;
        margin: 1;
        text-align: center;
    }
    
    .status-unavailable {
        background: $error-darken-2;
        color: $error;
        padding: 1;
        margin: 1;
        text-align: center;
    }
    
    .install-instructions {
        padding: 1;
        margin: 1;
        border: solid $accent;
    }
    
    .action-buttons {
        margin-top: 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        ffmpeg_available = has_ffmpeg()
        
        with Container(classes="ffmpeg-container"):
            yield Static("🔧 FFMPEG INSTALLATION CHECK", classes="screen-title")
            
            if ffmpeg_available:
                yield Static(
                    "✅ FFmpeg is installed and available!\n"
                    "You can download high resolution videos with audio.",
                    classes="status-available"
                )
            else:
                yield Static(
                    "❌ FFmpeg is NOT installed or not in PATH\n"
                    "Without FFmpeg, you can only download up to 720p with audio.",
                    classes="status-unavailable"
                )
                
                yield Static(
                    "[bold yellow]📥 To install FFmpeg:[/bold yellow]\n\n"
                    "[bold]Windows:[/bold]\n"
                    "  1. Download from: https://www.gyan.dev/ffmpeg/builds/\n"
                    "  2. Extract to C:\\ffmpeg\n"
                    "  3. Add C:\\ffmpeg\\bin to PATH\n\n"
                    "[bold]macOS:[/bold]\n"
                    "  brew install ffmpeg\n\n"
                    "[bold]Linux (Ubuntu/Debian):[/bold]\n"
                    "  sudo apt install ffmpeg",
                    classes="install-instructions"
                )
                
            with Horizontal(classes="action-buttons"):
                yield Button("⬅️ Back to Menu", id="btn-back", variant="primary")
                
    def action_go_back(self) -> None:
        self.app.pop_screen()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
