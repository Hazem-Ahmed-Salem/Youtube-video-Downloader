"""
TUI Widgets Package

Custom Textual widgets for the YouTube Video Downloader TUI.
"""

from TUI.widgets.status_panel import StatusPanel
from TUI.widgets.video_info_panel import VideoInfoPanel
from TUI.widgets.download_progress import DownloadProgressWidget

__all__ = [
    "StatusPanel",
    "VideoInfoPanel",
    "DownloadProgressWidget",
]
