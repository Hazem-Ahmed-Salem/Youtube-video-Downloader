"""
Utility functions for the YouTube Video Downloader TUI.
"""

import subprocess
from typing import List


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


def get_available_resolutions(streams) -> List[str]:
    """Get all available resolutions for the video"""
    resolutions = set()
    for stream in streams:
        if stream.resolution:
            resolutions.add(stream.resolution)
    return sorted(resolutions, key=lambda x: int(x.replace('p', '')), reverse=True)
