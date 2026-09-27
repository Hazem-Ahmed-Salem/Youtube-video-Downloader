"""
VideoInfoPanel Widget

Panel widget for displaying video information.
"""

from textual.app import ComposeResult
from textual.widgets import Static

from TUI.utils import format_duration


class VideoInfoPanel(Static):
    """Panel to display video information"""
    
    DEFAULT_CSS = """
    VideoInfoPanel {
        border: solid $primary;
        padding: 1;
        margin: 1;
        background: $surface;
    }
    
    VideoInfoPanel .info-label {
        color: $text-muted;
    }
    
    VideoInfoPanel .info-value {
        color: $text;
        text-style: bold;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.video_data = {}
        
    def compose(self) -> ComposeResult:
        yield Static("📹 No video loaded", id="video-info-content")
        
    def update_info(self, title: str, author: str, duration: int, views: int, max_res: str = None):
        self.video_data = {
            "title": title,
            "author": author,
            "duration": duration,
            "views": views,
            "max_res": max_res
        }
        content = self.query_one("#video-info-content", Static)
        lines = [
            f"[bold cyan]📹 Title:[/bold cyan] {title}",
            f"[bold cyan]👤 Author:[/bold cyan] {author}",
            f"[bold cyan]⏱️ Duration:[/bold cyan] {format_duration(duration)}",
            f"[bold cyan]👀 Views:[/bold cyan] {views:,}",
        ]
        if max_res:
            lines.append(f"[bold cyan]🎯 Max Resolution:[/bold cyan] [bold green]{max_res}[/bold green]")
        info_text = "\n".join(lines)
        content.update(info_text)
        
    def clear_info(self):
        self.video_data = {}
        content = self.query_one("#video-info-content", Static)
        content.update("📹 No video loaded")
