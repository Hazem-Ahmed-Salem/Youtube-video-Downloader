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

from TUI.utils import (
    get_available_resolutions,
    has_ffmpeg,
    get_youtube_instance,
    get_best_video_stream,
    get_best_audio_stream,
)
from merger import merge
from TUI.widgets import VideoInfoPanel, DownloadProgressWidget

try:
    from pytubefix import YouTube, exceptions
except ImportError:
    YouTube = None
    exceptions = None


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
            yt = get_youtube_instance(url)
            
            all_raw = list(yt.streams)
            progressive_streams = [s for s in all_raw if getattr(s, 'is_progressive', False)]
            video_only_streams  = [s for s in all_raw if getattr(s, 'is_adaptive', False) and s.type == 'video']
            audio_only_streams  = [s for s in all_raw if s.type == 'audio']

            resolutions = get_available_resolutions(all_raw)
            ffmpeg_available = has_ffmpeg()
            max_res = resolutions[0] if resolutions else None

            self.app.call_from_thread(
                self.update_video_info,
                yt.title, yt.author, yt.length, yt.views, max_res
            )

            resolution_data = []
            for res in resolutions:
                is_progressive = any(s.resolution == res for s in progressive_streams)
                is_adaptive    = any(s.resolution == res for s in video_only_streams)

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
            res_summary = ", ".join(resolutions) if resolutions else "None"
            self.app.call_from_thread(
                self.log_message,
                f"✅ Loaded: {yt.title} | Resolutions: [bold green]{res_summary}[/bold green]"
            )

            if not resolutions:
                self.app.call_from_thread(
                    self.log_message,
                    "⚠️ No video resolutions available for this video."
                )

            self.yt = yt
            self.progressive_streams = progressive_streams
            self.video_only_streams  = video_only_streams
            self.audio_only_streams  = audio_only_streams
            
        except (exceptions.BotDetection if exceptions else ()) as e:
            self.app.call_from_thread(
                self.log_message,
                "❌ Bot detection error: YouTube detected automated traffic. Try again or check network/VPN."
            )
            self.app.call_from_thread(self.update_resolution_table, [])
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            self.app.call_from_thread(self.update_resolution_table, [])
            
    def update_video_info(self, title: str, author: str, duration: int, views: int, max_res: str = None):
        info_panel = self.query_one("#video-info", VideoInfoPanel)
        info_panel.update_info(title, author, duration, views, max_res)
        
    def update_resolution_table(self, resolution_data: List[Tuple[str, str, str]]):
        table = self.query_one("#resolution-table", DataTable)
        table.clear()
        for res, stream_type, has_audio in resolution_data:
            table.add_row(res, stream_type, has_audio)
            
        # Update select widget and auto-select highest / 1080p resolution
        select = self.query_one("#resolution-select", Select)
        options = [(res, res) for res, _, _ in resolution_data]
        select.set_options(options)
        if options:
            preferred = "1080p" if any(res == "1080p" for res, _, _ in resolution_data) else resolution_data[0][0]
            select.value = preferred

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#resolution-table", DataTable)
        row = table.get_row(event.row_key)
        if row:
            res = str(row[0])
            select = self.query_one("#resolution-select", Select)
            select.value = res
            self.log_message(f"Selected resolution: [bold cyan]{res}[/bold cyan]")

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        table = self.query_one("#resolution-table", DataTable)
        row = table.get_row_at(event.coordinate.row)
        if row:
            res = str(row[0])
            select = self.query_one("#resolution-select", Select)
            select.value = res
            self.log_message(f"Selected resolution: [bold cyan]{res}[/bold cyan]")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "resolution-select" and event.value and event.value != Select.BLANK:
            self.log_message(f"Resolution chosen: [bold cyan]{event.value}[/bold cyan]")
        
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
                
            prog_matches = [s for s in self.progressive_streams if s.resolution == selected_resolution]
            stream = prog_matches[0] if prog_matches else None

            if stream:
                # Progressive stream – already has audio, download directly
                self.app.call_from_thread(
                    self.log_message,
                    f"📥 Downloading: {selected_resolution} (with audio)"
                )

                total_size = stream.filesize or 0

                def progress_callback(s, chunk, bytes_remaining):
                    cur_size = getattr(s, 'filesize', 0) or total_size
                    bytes_downloaded = max(0, cur_size - bytes_remaining)
                    self.app.call_from_thread(
                        self.update_download_progress,
                        bytes_downloaded, cur_size, "Downloading video"
                    )

                yt.register_on_progress_callback(progress_callback)
                stream.download(output_path=download_folder)
                self.app.call_from_thread(self.complete_download, stream.default_filename)

            else:
                # Adaptive stream – separate video + audio, then merge with FFmpeg
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

                video_stream = get_best_video_stream(yt.streams, selected_resolution)
                audio_stream = get_best_audio_stream(yt.streams)

                if not video_stream or not audio_stream:
                    self.app.call_from_thread(
                        self.log_message,
                        f"❌ Could not find suitable video ({selected_resolution}) or audio streams"
                    )
                    return
                    
                v_ext = video_stream.subtype or 'mp4'
                a_ext = audio_stream.subtype or 'mp4'
                video_filename = f"temp_video_{video_stream.itag}.{v_ext}"
                audio_filename = f"temp_audio_{audio_stream.itag}.{a_ext}"

                video_path = os.path.join(download_folder, video_filename)
                audio_path = os.path.join(download_folder, audio_filename)

                # Download video
                self.app.call_from_thread(
                    self.log_message,
                    f"📹 Downloading video ({selected_resolution}, {video_stream.mime_type})..."
                )
                
                video_size = video_stream.filesize or 0
                def video_progress(s, chunk, bytes_remaining):
                    cur_size = getattr(s, 'filesize', 0) or video_size
                    bytes_downloaded = max(0, cur_size - bytes_remaining)
                    self.app.call_from_thread(
                        self.update_download_progress,
                        bytes_downloaded, cur_size, f"Downloading video ({selected_resolution})"
                    )
                    
                yt.register_on_progress_callback(video_progress)
                video_stream.download(output_path=download_folder, filename=video_filename)
                
                # Reset progress for audio
                self.app.call_from_thread(self.reset_progress)
                
                # Download audio
                self.app.call_from_thread(
                    self.log_message,
                    f"🎵 Downloading audio ({audio_stream.abr}, {audio_stream.mime_type})..."
                )
                
                audio_size = audio_stream.filesize or 0
                def audio_progress(s, chunk, bytes_remaining):
                    cur_size = getattr(s, 'filesize', 0) or audio_size
                    bytes_downloaded = max(0, cur_size - bytes_remaining)
                    self.app.call_from_thread(
                        self.update_download_progress,
                        bytes_downloaded, cur_size, "Downloading audio"
                    )
                    
                yt.register_on_progress_callback(audio_progress)
                audio_stream.download(output_path=download_folder, filename=audio_filename)
                
                # Merge with FFmpeg
                self.app.call_from_thread(self.log_message, "🔄 Merging video and audio with FFmpeg...")
                
                safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_', '.')).strip()
                if not safe_title:
                    safe_title = f"video_{getattr(yt, 'video_id', 'download')}"
                final_filename = f"{safe_title}.mp4"
                final_path = os.path.join(download_folder, final_filename)
                
                merge(
                    video_path=video_path,
                    audio_path=audio_path,
                    output_path=final_path,
                    cleanup=True
                )
                self.app.call_from_thread(self.complete_download, final_filename)
                    
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
        self.log_message("✅ Download completed!")
        self.log_message(f"📄 File saved as: {filename}")
        
    def set_download_error(self, error: str):
        progress = self.query_one("#progress-widget", DownloadProgressWidget)
        progress.set_error(error)
