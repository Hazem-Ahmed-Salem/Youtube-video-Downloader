"""
MainMenuScreen

Main menu screen for the YouTube Video Downloader TUI.
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Button
from textual.screen import Screen
from textual.binding import Binding

from TUI.utils import has_ffmpeg


class MainMenuScreen(Screen):
    """Main menu screen"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "simple_download", "Simple Download"),
        Binding("2", "advanced_download", "Advanced Download"),
        Binding("3", "video_info", "Video Info"),
        Binding("4", "check_ffmpeg", "Check FFmpeg"),
    ]
    
    DEFAULT_CSS = """
    MainMenuScreen {
        align: center middle;
    }
    
    .menu-container {
        width: 70;
        height: auto;
        padding: 2;
        border: double $primary;
        background: $surface;
    }
    
    .menu-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .menu-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }
    
    .menu-button {
        width: 100%;
        margin: 1 0;
    }
    
    .ffmpeg-status {
        text-align: center;
        margin-top: 1;
        padding: 1;
        border: solid $accent;
    }
    
    .ffmpeg-available {
        color: $success;
    }
    
    .ffmpeg-unavailable {
        color: $error;
    }
    """
    
    def compose(self) -> ComposeResult:
        ffmpeg_available = has_ffmpeg()
        
        with Container(classes="menu-container"):
            yield Static("🎬 YOUTUBE VIDEO DOWNLOADER", classes="menu-title")
            yield Static("Built with Textual & pytubefix", classes="menu-subtitle")
            
            if ffmpeg_available:
                yield Static(
                    "✅ FFmpeg: Available (All resolutions supported)",
                    classes="ffmpeg-status ffmpeg-available"
                )
            else:
                yield Static(
                    "❌ FFmpeg: Not available (720p max with audio)",
                    classes="ffmpeg-status ffmpeg-unavailable"
                )
            
            yield Button("📥 Simple Download (Best Quality)", id="btn-simple", classes="menu-button", variant="primary")
            yield Button("🎯 Advanced Download (Choose Resolution)", id="btn-advanced", classes="menu-button", variant="success")
            yield Button("📊 Show Video Information", id="btn-info", classes="menu-button", variant="default")
            yield Button("🔧 Check FFmpeg Installation", id="btn-ffmpeg", classes="menu-button", variant="warning")
            yield Button("🚪 Exit", id="btn-exit", classes="menu-button", variant="error")
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Import here to avoid circular imports
        from TUI.screens.simple_download import SimpleDownloadScreen
        from TUI.screens.advanced_download import AdvancedDownloadScreen
        from TUI.screens.video_info import VideoInfoScreen
        from TUI.screens.ffmpeg_check import FFmpegCheckScreen
        
        if event.button.id == "btn-simple":
            self.app.push_screen(SimpleDownloadScreen())
        elif event.button.id == "btn-advanced":
            self.app.push_screen(AdvancedDownloadScreen())
        elif event.button.id == "btn-info":
            self.app.push_screen(VideoInfoScreen())
        elif event.button.id == "btn-ffmpeg":
            self.app.push_screen(FFmpegCheckScreen())
        elif event.button.id == "btn-exit":
            self.app.exit()
            
    def action_simple_download(self) -> None:
        from TUI.screens.simple_download import SimpleDownloadScreen
        self.app.push_screen(SimpleDownloadScreen())
        
    def action_advanced_download(self) -> None:
        from TUI.screens.advanced_download import AdvancedDownloadScreen
        self.app.push_screen(AdvancedDownloadScreen())
        
    def action_video_info(self) -> None:
        from TUI.screens.video_info import VideoInfoScreen
        self.app.push_screen(VideoInfoScreen())
        
    def action_check_ffmpeg(self) -> None:
        from TUI.screens.ffmpeg_check import FFmpegCheckScreen
        self.app.push_screen(FFmpegCheckScreen())
