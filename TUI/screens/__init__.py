"""
TUI Screens Package

Screen classes for the YouTube Video Downloader TUI.
"""

from TUI.screens.main_menu import MainMenuScreen
from TUI.screens.simple_download import SimpleDownloadScreen
from TUI.screens.advanced_download import AdvancedDownloadScreen
from TUI.screens.video_info import VideoInfoScreen
from TUI.screens.ffmpeg_check import FFmpegCheckScreen

__all__ = [
    "MainMenuScreen",
    "SimpleDownloadScreen",
    "AdvancedDownloadScreen",
    "VideoInfoScreen",
    "FFmpegCheckScreen",
]
