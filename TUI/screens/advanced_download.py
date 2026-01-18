"""
AdvancedDownloadScreen

Advanced download screen - choose resolution with FFmpeg merge support.
"""

import os
import subprocess
from typing import List, Tuple

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, 
    Label, DataTable, Select, RichLog
)
from textual.screen import Screen
from textual.binding import Binding
from textual import work

from TUI.utils import format_bytes, get_available_resolutions, has_ffmpeg
from TUI.widgets import VideoInfoPanel, DownloadProgressWidget

try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None


class AdvancedDownloadScreen(Screen):
    """Advanced download screen - choose resolution"""
    
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]
    
    DEFAULT_CSS = """
    AdvancedDownloadScreen {
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
    
    .resolution-select {
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
    
    DataTable {
        height: 10;
        margin: 1 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            with Container(classes="download-container"):
                yield Static("🎯 ADVANCED DOWNLOAD (CHOOSE RESOLUTION)", classes="screen-title")
                yield Label("Enter YouTube URL:")
                yield Input(placeholder="https://www.youtube.com/watch?v=...", id="url-input", classes="url-input")
                yield VideoInfoPanel(id="video-info")
                yield Label("Available Resolutions:")
                yield DataTable(id="resolution-table")
                yield Label("Select Resolution:")
                yield Select([], id="resolution-select", classes="resolution-select", allow_blank=True)
                yield DownloadProgressWidget(id="progress-widget")
                with Horizontal(classes="action-buttons"):
                    yield Button("📥 Download", id="btn-download", variant="success")
                    yield Button("🔍 Load Info", id="btn-load", variant="primary")
                    yield Button("⬅️ Back", id="btn-back", variant="default")
                yield RichLog(id="log", classes="log-container", highlight=True, markup=True)
        yield Footer()
        
    def on_mount(self):
        table = self.query_one("#resolution-table", DataTable)
        table.add_columns("Resolution", "Type", "Has Audio")
        
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
            
            # Get streams info
            all_streams = yt.streams.filter(file_extension='mp4')
            progressive_streams = all_streams.filter(progressive=True)
            video_only_streams = all_streams.filter(adaptive=True, type="video")
            
            resolutions = get_available_resolutions(all_streams)
            ffmpeg_available = has_ffmpeg()
            
            resolution_data = []
            for res in resolutions:
                is_progressive = any(s.resolution == res for s in progressive_streams)
                is_adaptive = any(s.resolution == res for s in video_only_streams)
                
                if is_progressive:
                    stream_type = "Progressive"
                    has_audio = "✅ Yes"
                elif is_adaptive and ffmpeg_available:
                    stream_type = "Adaptive (will merge)"
                    has_audio = "🔄 Will merge"
                elif is_adaptive:
                    stream_type = "Adaptive"
                    has_audio = "❌ No (need FFmpeg)"
                else:
                    stream_type = "Unknown"
                    has_audio = "❓"
                    
                resolution_data.append((res, stream_type, has_audio))
                
            self.app.call_from_thread(self.update_resolution_table, resolution_data)
            self.app.call_from_thread(self.log_message, f"✅ Loaded: {yt.title}")
            
            self.yt = yt
            self.progressive_streams = progressive_streams
            self.video_only_streams = video_only_streams
            
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            
    def update_video_info(self, title: str, author: str, duration: int, views: int):
        info_panel = self.query_one("#video-info", VideoInfoPanel)
        info_panel.update_info(title, author, duration, views)
        
    def update_resolution_table(self, resolution_data: List[Tuple[str, str, str]]):
        table = self.query_one("#resolution-table", DataTable)
        table.clear()
        for res, stream_type, has_audio in resolution_data:
            table.add_row(res, stream_type, has_audio)
            
        # Update select widget
        select = self.query_one("#resolution-select", Select)
        options = [(res, res) for res, _, _ in resolution_data]
        select.set_options(options)
        
    def log_message(self, message: str):
        log = self.query_one("#log", RichLog)
        log.write(message)
        
    def start_download(self):
        if not hasattr(self, 'yt') or self.yt is None:
            self.log_message("❌ Please load a video first")
            return
            
        select = self.query_one("#resolution-select", Select)
        if select.value is None or select.value == Select.BLANK:
            self.log_message("❌ Please select a resolution")
            return
            
        selected_resolution = select.value
        self._download_task(selected_resolution)
        
    @work(thread=True)
    def _download_task(self, selected_resolution: str):
        try:
            yt = self.yt
            download_folder = "youtube_downloads"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)
                
            # Try progressive stream first
            stream = self.progressive_streams.filter(res=selected_resolution).first()
            
            if stream:
                # Progressive stream - has audio
                self.app.call_from_thread(
                    self.log_message,
                    f"📥 Downloading: {selected_resolution} (with audio)"
                )
                
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
                
            else:
                # Adaptive stream - need to merge
                if not has_ffmpeg():
                    self.app.call_from_thread(
                        self.log_message,
                        "❌ FFmpeg not found. Cannot merge audio for high resolution videos."
                    )
                    return
                    
                self.app.call_from_thread(
                    self.log_message,
                    f"🔄 Downloading {selected_resolution} video and audio separately..."
                )
                
                # Download video
                video_stream = self.video_only_streams.filter(res=selected_resolution).first()
                audio_stream = yt.streams.filter(
                    adaptive=True, type="audio", file_extension='mp4'
                ).order_by('abr').desc().first()
                
                if not video_stream or not audio_stream:
                    self.app.call_from_thread(
                        self.log_message,
                        "❌ Could not find suitable video or audio streams"
                    )
                    return
                    
                # Download video
                self.app.call_from_thread(
                    self.log_message,
                    f"📹 Downloading video ({selected_resolution})..."
                )
                
                video_filename = f"temp_video_{video_stream.itag}.mp4"
                
                video_size = video_stream.filesize or 0
                
                def video_progress(stream, chunk, bytes_remaining):
                    bytes_downloaded = video_size - bytes_remaining
                    self.app.call_from_thread(
                        self.update_download_progress,
                        bytes_downloaded, video_size, "Downloading video"
                    )
                    
                yt.register_on_progress_callback(video_progress)
                # Capture the actual path returned by download()
                video_path = video_stream.download(output_path=download_folder, filename=video_filename)
                
                # Reset progress for audio
                self.app.call_from_thread(self.reset_progress)
                
                # Download audio
                self.app.call_from_thread(
                    self.log_message,
                    f"🎵 Downloading audio ({audio_stream.abr})..."
                )
                
                audio_filename = f"temp_audio_{audio_stream.itag}.mp4"
                
                audio_size = audio_stream.filesize or 0
                
                def audio_progress(stream, chunk, bytes_remaining):
                    bytes_downloaded = audio_size - bytes_remaining
                    self.app.call_from_thread(
                        self.update_download_progress,
                        bytes_downloaded, audio_size, "Downloading audio"
                    )
                    
                yt.register_on_progress_callback(audio_progress)
                # Capture the actual path returned by download()
                audio_path = audio_stream.download(output_path=download_folder, filename=audio_filename)
                
                # Merge with FFmpeg
                self.app.call_from_thread(self.log_message, "🔄 Merging video and audio...")
                
                final_filename = f"{yt.title}.mp4"
                final_filename = "".join(c for c in final_filename if c.isalnum() or c in (' ', '-', '_', '.'))
                final_path = os.path.join(download_folder, final_filename)
                
                ffmpeg_cmd = [
                    'ffmpeg', '-i', video_path, '-i', audio_path,
                    '-c', 'copy',
                    '-shortest',
                    '-y',
                    final_path
                ]
                
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Cleanup temp files
                    try:
                        os.remove(video_path)
                        os.remove(audio_path)
                    except:
                        pass
                        
                    self.app.call_from_thread(self.complete_download, final_filename)
                else:
                    self.app.call_from_thread(
                        self.log_message,
                        f"❌ FFmpeg merge failed: {result.stderr}"
                    )
                    
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            self.app.call_from_thread(self.set_download_error, str(e))
            
    def update_download_progress(self, bytes_downloaded: int, total_bytes: int, stage: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.update_progress(bytes_downloaded, total_bytes, stage)
        
    def reset_progress(self):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.reset()
        
    def complete_download(self, filename: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.set_complete("Merged successfully!")
        self.log_message(f"✅ Download completed!")
        self.log_message(f"📄 File saved as: {filename}")
        
    def set_download_error(self, error: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.set_error(error)
