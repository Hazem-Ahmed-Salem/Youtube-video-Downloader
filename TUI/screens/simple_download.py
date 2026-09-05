"""
SimpleDownloadScreen

Simple download screen - best quality with audio.
"""

import os

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Input, Label, RichLog
from textual.screen import Screen
from textual.binding import Binding
from textual import work

from TUI.utils import format_bytes
from TUI.widgets import VideoInfoPanel, DownloadProgressWidget

try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None


class SimpleDownloadScreen(Screen):
    """Simple download screen - best quality with audio"""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]
    
    DEFAULT_CSS = """
    SimpleDownloadScreen {
        padding: 1;
    }
    
    .download-container {
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
    
    .log-container {
        height: 15;
        border: solid $accent;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            with Container(classes="download-container"):
                yield Static("🚀 SIMPLE DOWNLOAD (BEST QUALITY WITH AUDIO)", classes="screen-title")
                yield Label("Enter YouTube URL:")
                yield Input(placeholder="https://www.youtube.com/watch?v=...", id="url-input", classes="url-input")
                yield VideoInfoPanel(id="video-info")
                yield DownloadProgressWidget(id="progress-widget")
                with Horizontal(classes="action-buttons"):
                    yield Button("📥 Download", id="btn-download", variant="success")
                    yield Button("🔍 Load Info", id="btn-load", variant="primary")
                    yield Button("⬅️ Back", id="btn-back", variant="default")
                yield RichLog(id="log", classes="log-container", highlight=True, markup=True)
        yield Footer()
        
    def action_go_back(self) -> None:
        self.app.pop_screen()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-load":
            self.load_video_info()
        elif event.button.id == "btn-download":
            self.start_download()
            
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
            self.app.call_from_thread(self.log_message, f"✅ Loaded: {yt.title}")
            
            # Store YouTube object for download
            self.yt = yt
            
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            
    def update_video_info(self, title: str, author: str, duration: int, views: int):
        info_panel = self.query_one("#video-info", VideoInfoPanel)
        info_panel.update_info(title, author, duration, views)
        
    def log_message(self, message: str):
        log = self.query_one("#log", RichLog)
        log.write(message)
        
    def start_download(self):
        if not hasattr(self, 'yt') or self.yt is None:
            self.log_message("❌ Please load a video first")
            return
        self._download_task()
        
    @work(thread=True)
    def _download_task(self):
        try:
            yt = self.yt
            
            # Get the best progressive stream
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                self.app.call_from_thread(self.log_message, "❌ No streams with audio available")
                return
                
            download_folder = "youtube_downloads"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)
                
            self.app.call_from_thread(
                self.log_message, 
                f"📥 Downloading: {stream.resolution} (with audio)"
            )
            
            if stream.filesize:
                self.app.call_from_thread(
                    self.log_message,
                    f"💾 Size: {format_bytes(stream.filesize)}"
                )
                
            # Download with progress callback
            total_size = stream.filesize or 0
            
            def progress_callback(stream, chunk, bytes_remaining):
                bytes_downloaded = total_size - bytes_remaining
                self.app.call_from_thread(
                    self.update_download_progress,
                    bytes_downloaded, total_size, "Downloading video"
                )
                
            yt.register_on_progress_callback(progress_callback)
            stream.download(output_path=download_folder)
            
            self.app.call_from_thread(self.complete_download, stream.default_filename)
            
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            self.app.call_from_thread(self.set_download_error, str(e))
            
    def update_download_progress(self, bytes_downloaded: int, total_bytes: int, stage: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.update_progress(bytes_downloaded, total_bytes, stage)
        
    def complete_download(self, filename: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.set_complete()
        self.log_message("✅ Download completed!")
        self.log_message(f"📄 File saved as: {filename}")
        
    def set_download_error(self, error: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.set_error(error)
