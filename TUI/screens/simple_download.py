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

from TUI.utils import (
    format_bytes,
    get_youtube_instance,
    has_ffmpeg,
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
            yt = get_youtube_instance(url)
            
            all_streams = list(yt.streams)
            best_video = get_best_video_stream(all_streams)
            best_res = best_video.resolution if best_video else "Unknown"

            self.app.call_from_thread(
                self.update_video_info,
                yt.title, yt.author, yt.length, yt.views, best_res
            )
            self.app.call_from_thread(
                self.log_message,
                f"✅ Loaded: {yt.title} | Resolution: [bold green]{best_res}[/bold green]"
            )
            
            # Store YouTube object for download
            self.yt = yt
            
        except (exceptions.BotDetection if exceptions else ()) as e:
            self.app.call_from_thread(
                self.log_message,
                "❌ Bot detection error: YouTube detected automated traffic. Try again or check network/VPN."
            )
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"❌ Error: {str(e)}")
            
    def update_video_info(self, title: str, author: str, duration: int, views: int, max_res: str = None):
        info_panel = self.query_one("#video-info", VideoInfoPanel)
        info_panel.update_info(title, author, duration, views, max_res)
        
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
            all_streams = list(yt.streams)
            download_folder = "youtube_downloads"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            best_video = get_best_video_stream(all_streams)
            if not best_video:
                self.app.call_from_thread(self.log_message, "❌ No video streams available")
                return

            if getattr(best_video, 'is_progressive', False):
                # Progressive stream - direct download
                self.app.call_from_thread(
                    self.log_message, 
                    f"📥 Downloading: {best_video.resolution} (with audio)"
                )
                if best_video.filesize:
                    self.app.call_from_thread(
                        self.log_message,
                        f"💾 Size: {format_bytes(best_video.filesize)}"
                    )
                    
                total_size = best_video.filesize or 0
                def progress_callback(s, chunk, bytes_remaining):
                    cur_size = getattr(s, 'filesize', 0) or total_size
                    bytes_downloaded = max(0, cur_size - bytes_remaining)
                    self.app.call_from_thread(
                        self.update_download_progress,
                        bytes_downloaded, cur_size, "Downloading video"
                    )
                    
                yt.register_on_progress_callback(progress_callback)
                best_video.download(output_path=download_folder)
                self.app.call_from_thread(self.complete_download, best_video.default_filename)
                
            elif has_ffmpeg():
                # Adaptive stream - download best video (1080p+) + best audio, then merge
                self.app.call_from_thread(
                    self.log_message,
                    f"🎯 Best resolution: {best_video.resolution}. Downloading video & audio separately..."
                )

                audio_stream = get_best_audio_stream(all_streams)
                if not audio_stream:
                    self.app.call_from_thread(self.log_message, "❌ Could not find suitable audio stream")
                    return

                v_ext = best_video.subtype or 'mp4'
                a_ext = audio_stream.subtype or 'mp4'
                v_filename = f"temp_video_{best_video.itag}.{v_ext}"
                a_filename = f"temp_audio_{audio_stream.itag}.{a_ext}"

                v_path = os.path.join(download_folder, v_filename)
                a_path = os.path.join(download_folder, a_filename)

                # Download video
                self.app.call_from_thread(
                    self.log_message,
                    f"📹 Downloading video ({best_video.resolution})..."
                )
                v_size = best_video.filesize or 0
                def v_progress(s, chunk, bytes_remaining):
                    cur_size = getattr(s, 'filesize', 0) or v_size
                    dl = max(0, cur_size - bytes_remaining)
                    self.app.call_from_thread(
                        self.update_download_progress,
                        dl, cur_size, f"Downloading video ({best_video.resolution})"
                    )

                yt.register_on_progress_callback(v_progress)
                best_video.download(output_path=download_folder, filename=v_filename)

                # Download audio
                self.app.call_from_thread(
                    self.log_message,
                    f"🎵 Downloading audio ({audio_stream.abr})..."
                )
                a_size = audio_stream.filesize or 0
                def a_progress(s, chunk, bytes_remaining):
                    cur_size = getattr(s, 'filesize', 0) or a_size
                    dl = max(0, cur_size - bytes_remaining)
                    self.app.call_from_thread(
                        self.update_download_progress,
                        dl, cur_size, "Downloading audio"
                    )

                yt.register_on_progress_callback(a_progress)
                audio_stream.download(output_path=download_folder, filename=a_filename)

                # Merge with FFmpeg
                self.app.call_from_thread(self.log_message, "🔄 Merging video and audio with FFmpeg...")
                safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_', '.')).strip()
                if not safe_title:
                    safe_title = f"video_{getattr(yt, 'video_id', 'download')}"
                final_filename = f"{safe_title}.mp4"
                final_path = os.path.join(download_folder, final_filename)

                merge(
                    video_path=v_path,
                    audio_path=a_path,
                    output_path=final_path,
                    cleanup=True
                )
                self.app.call_from_thread(self.complete_download, final_filename)
            else:
                # FFmpeg not found - fallback to progressive
                prog_streams = [s for s in all_streams if getattr(s, 'is_progressive', False)]
                if prog_streams:
                    prog_streams.sort(
                        key=lambda s: int(s.resolution[:-1]) if s.resolution and s.resolution[:-1].isdigit() else 0,
                        reverse=True
                    )
                    stream = prog_streams[0]
                    self.app.call_from_thread(
                        self.log_message,
                        f"⚠️ FFmpeg not installed. Falling back to {stream.resolution}. Install FFmpeg for 1080p+."
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
                    self.app.call_from_thread(self.log_message, "❌ FFmpeg is required to download this video.")
            
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
