"""
Utility functions for the YouTube Video Downloader TUI.
"""

import subprocess
from typing import List
from youtube_helper import (
    get_youtube_instance,
    is_stream_accessible,
    get_available_resolutions,
    get_best_video_stream,
    get_best_audio_stream,
    download_and_merge_streams,
    clean_youtube_url,
    extract_youtube_video_id,
    is_playlist_url,
)


def format_bytes(bytes_val: int) -> str:
    """Convert bytes to human readable format"""
    if bytes_val >= 1024**3:
        return f"{bytes_val / (1024**3):.2f} GB"
    elif bytes_val >= 1024**2:
        return f"{bytes_val / (1024**2):.2f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} KB"
    else:
        return f"{bytes_val} B"


def format_speed(speed: float) -> str:
    """Convert speed to human readable format"""
    if speed >= 1024**2:
        return f"{speed / (1024**2):.2f} MB/s"
    elif speed >= 1024:
        return f"{speed / 1024:.2f} KB/s"
    else:
        return f"{speed:.2f} B/s"


def format_duration(seconds: int) -> str:
    """Format seconds to mm:ss format"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def has_ffmpeg() -> bool:
    """Check if FFmpeg is installed and available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
