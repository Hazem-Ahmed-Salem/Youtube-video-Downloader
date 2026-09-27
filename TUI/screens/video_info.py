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

from TUI.utils import format_bytes, get_youtube_instance
from TUI.widgets import VideoInfoPanel

try:
    from pytubefix import YouTube, exceptions
except ImportError:
    YouTube = None
    exceptions = None


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
            yt = get_youtube_instance(url)
            
            all_streams = list(yt.streams)
            video_streams = [s for s in all_streams if s.type == 'video' and s.resolution]
            res_list = sorted(
                set(s.resolution for s in video_streams),
                key=lambda x: int(x.replace('p', '')) if x.replace('p', '').isdigit() else 0,
                reverse=True
            )
            max_res = res_list[0] if res_list else None

            self.app.call_from_thread(
                self.update_video_info,
                yt.title, yt.author, yt.length, yt.views, max_res
            )
            
            # Get stream info
            streams_data = []
            
            # Progressive streams
            progressive = [s for s in all_streams if getattr(s, 'is_progressive', False)]
            for s in progressive:
                size = format_bytes(s.filesize) if s.filesize else "Unknown"
                streams_data.append(("✅ Progressive", s.resolution, s.mime_type, size))
                
            # Video only streams (all formats, mp4 and webm)
            video_only = [s for s in all_streams if getattr(s, 'is_adaptive', False) and s.type == 'video']
            for s in video_only:
                size = format_bytes(s.filesize) if s.filesize else "Unknown"
                fps_str = f" ({s.fps}fps)" if hasattr(s, 'fps') and s.fps else ""
                streams_data.append(("🎬 Video Only", f"{s.resolution}{fps_str}", s.mime_type, size))
                
            # Audio only streams
            audio_only = [s for s in all_streams if s.type == 'audio']
            for s in audio_only:
                size = format_bytes(s.filesize) if s.filesize else "Unknown"
                streams_data.append(("🎵 Audio Only", s.abr or "Audio", s.mime_type, size))
                
            self.app.call_from_thread(self.update_streams_table, streams_data)
            self.app.call_from_thread(self.log_message, f"✅ Loaded info for: {yt.title} | Max: [bold green]{max_res}[/bold green]")
            
        except (exceptions.BotDetection if exceptions else ()) as e:
            self.app.call_from_thread(
                self.log_message,
                "❌ Bot detection error: YouTube detected automated traffic. Try again or check network/VPN."
            )
            self.app.call_from_thread(self.update_streams_table, [])
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            self.app.call_from_thread(self.update_streams_table, [])
            
    def update_video_info(self, title: str, author: str, duration: int, views: int, max_res: str = None):
        info_panel = self.query_one("#video-info", VideoInfoPanel)
        info_panel.update_info(title, author, duration, views, max_res)
        
    def update_streams_table(self, streams_data: List[Tuple[str, str, str, str]]):
        table = self.query_one("#streams-table", DataTable)
        table.clear()
        for stream_type, res_or_abr, mime, size in streams_data:
            table.add_row(stream_type, res_or_abr, mime, size)
            
    def log_message(self, message: str):
        log = self.query_one("#log", RichLog)
        log.write(message)
