"""
DownloadProgressWidget

Widget to show download progress with speed and ETA.
"""

import time

from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar

from TUI.utils import format_bytes, format_speed


class DownloadProgressWidget(Static):
    """Widget to show download progress with speed and ETA"""
    
    DEFAULT_CSS = """
    DownloadProgressWidget {
        height: auto;
        padding: 1;
        margin: 1;
        border: solid $accent;
        background: $surface;
    }
    
    DownloadProgressWidget ProgressBar {
        margin-top: 1;
    }
    
    DownloadProgressWidget .progress-info {
        margin-top: 1;
        color: $text;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_time = None
        self.last_time = None
        self.last_bytes = 0
        self.speeds = []
        
    def compose(self) -> ComposeResult:
        yield Static("📥 Download Progress", id="progress-title", classes="progress-title")
        yield ProgressBar(id="download-progress", show_eta=False)
        yield Static("", id="progress-info", classes="progress-info")
        
    def reset(self):
        self.start_time = None
        self.last_time = None
        self.last_bytes = 0
        self.speeds = []
        self.query_one("#download-progress", ProgressBar).update(progress=0, total=100)
        self.query_one("#progress-info", Static).update("")
        self.query_one("#progress-title", Static).update("📥 Download Progress")
        
    def update_progress(self, bytes_downloaded: int, total_bytes: int, stage: str = "Downloading"):
        current_time = time.time()
        
        if self.start_time is None:
            self.start_time = current_time
            self.last_time = current_time
            self.last_bytes = bytes_downloaded
            return
            
        time_diff = current_time - self.last_time
        if time_diff > 0:
            current_speed = (bytes_downloaded - self.last_bytes) / time_diff
            self.speeds.append(current_speed)
            
            if len(self.speeds) > 5:
                self.speeds.pop(0)
                
            avg_speed = sum(self.speeds) / len(self.speeds) if self.speeds else 0
            
            percent = (bytes_downloaded / total_bytes) * 100 if total_bytes > 0 else 0
            
            bytes_remaining = total_bytes - bytes_downloaded
            if avg_speed > 0:
                eta_seconds = bytes_remaining / avg_speed
                eta_str = f"{int(eta_seconds // 60):02d}:{int(eta_seconds % 60):02d}"
            else:
                eta_str = "Calculating..."
                
            progress_bar = self.query_one("#download-progress", ProgressBar)
            progress_bar.update(progress=percent, total=100)
            
            info_text = (
                f"🚀 Speed: [bold green]{format_speed(avg_speed)}[/bold green] | "
                f"⏱️ ETA: [bold yellow]{eta_str}[/bold yellow] | "
                f"📊 {format_bytes(bytes_downloaded)}/{format_bytes(total_bytes)}"
            )
            self.query_one("#progress-info", Static).update(info_text)
            self.query_one("#progress-title", Static).update(f"📥 {stage}")
            
        self.last_time = current_time
        self.last_bytes = bytes_downloaded
        
    def set_complete(self, message: str = "Download Complete!"):
        progress_bar = self.query_one("#download-progress", ProgressBar)
        progress_bar.update(progress=100, total=100)
        self.query_one("#progress-title", Static).update(f"✅ {message}")
        self.query_one("#progress-info", Static).update("")
        
    def set_error(self, message: str = "Download Failed"):
        self.query_one("#progress-title", Static).update(f"❌ {message}")
