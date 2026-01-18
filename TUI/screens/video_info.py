"""
VideoInfoScreen

Screen to display video information and available streams.
"""

from typing import List, Tuple

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Input, Label, DataTable, RichLog
from textual.screen import Screen
from textual.binding import Binding
from textual import work

from TUI.utils import format_bytes
from TUI.widgets import VideoInfoPanel

try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None


class VideoInfoScreen(Screen):
    """Screen to display video information"""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]
    
    DEFAULT_CSS = """
    VideoInfoScreen {
        padding: 1;
    }
    
    .info-container {
        width: 100%;
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
    
    .url-input {
        width: 100%;
        margin: 1 0;
    }
    
    .action-buttons {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    
    .action-buttons Button {
        margin: 0 1;
    }
    
    .streams-table {
        height: 15;
        margin: 1 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            with Container(classes="info-container"):
                yield Static("📊 VIDEO INFORMATION", classes="screen-title")
                yield Label("Enter YouTube URL:")
                yield Input(placeholder="https://www.youtube.com/watch?v=...", id="url-input", classes="url-input")
                yield VideoInfoPanel(id="video-info")
                yield Label("Available Streams:")
                yield DataTable(id="streams-table", classes="streams-table")
                with Horizontal(classes="action-buttons"):
                    yield Button("🔍 Load Info", id="btn-load", variant="primary")
                    yield Button("⬅️ Back", id="btn-back", variant="default")
                yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()
        
    def on_mount(self):
        table = self.query_one("#streams-table", DataTable)
        table.add_columns("Type", "Resolution/Bitrate", "Format", "Size")
        
    def action_go_back(self) -> None:
        self.app.pop_screen()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-load":
            self.load_video_info()
            
    def load_video_info(self):
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            self.log_message("❌ Please enter a YouTube URL")
            return
        self._load_info_task(url)
        
    @work(thread=True)
    def _load_info_task(self, url: str):
        try:
            self.app.call_from_thread(self.log_message, "⏳ Loading video information...")
            yt = YouTube(url)
            
            self.app.call_from_thread(
                self.update_video_info,
                yt.title, yt.author, yt.length, yt.views
            )
            
            # Get stream info
            streams_data = []
            
            # Progressive streams
            progressive = yt.streams.filter(progressive=True, file_extension='mp4')
            for s in progressive:
                size = format_bytes(s.filesize) if s.filesize else "Unknown"
                streams_data.append(("✅ Progressive", s.resolution, s.mime_type, size))
                
            # Video only streams
            video_only = yt.streams.filter(adaptive=True, type="video", file_extension='mp4')
            for s in video_only:
                size = format_bytes(s.filesize) if s.filesize else "Unknown"
                streams_data.append(("🎬 Video Only", s.resolution, s.mime_type, size))
                
            # Audio only streams
            audio_only = yt.streams.filter(adaptive=True, type="audio")
            for s in audio_only:
                size = format_bytes(s.filesize) if s.filesize else "Unknown"
                streams_data.append(("🎵 Audio Only", s.abr, s.mime_type, size))
                
            self.app.call_from_thread(self.update_streams_table, streams_data)
            self.app.call_from_thread(self.log_message, f"✅ Loaded info for: {yt.title}")
            
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            
    def update_video_info(self, title: str, author: str, duration: int, views: int):
        info_panel = self.query_one("#video-info", VideoInfoPanel)
        info_panel.update_info(title, author, duration, views)
        
    def update_streams_table(self, streams_data: List[Tuple[str, str, str, str]]):
        table = self.query_one("#streams-table", DataTable)
        table.clear()
        for stream_type, res_or_abr, mime, size in streams_data:
            table.add_row(stream_type, res_or_abr, mime, size)
            
    def log_message(self, message: str):
        log = self.query_one("#log", RichLog)
        log.write(message)
