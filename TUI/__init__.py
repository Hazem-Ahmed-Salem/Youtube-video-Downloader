"""
TUI - YouTube Video Downloader Terminal User Interface

A modular Textual-based TUI for downloading YouTube videos.
"""

from TUI.app import YouTubeDownloaderApp, main
from TUI.utils import (
    format_bytes,
    format_speed,
    format_duration,
    has_ffmpeg,
    get_available_resolutions,
)

__all__ = [
    "YouTubeDownloaderApp",
    "main",
    "format_bytes",
    "format_speed",
    "format_duration",
    "has_ffmpeg",
    "get_available_resolutions",
]
