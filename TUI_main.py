"""
YouTube Video Downloader TUI - Built with Textual
A beautiful terminal user interface for downloading YouTube videos.

This file is now a thin wrapper that imports from the modular TUI package.
Run this file directly or use 'python -m TUI' to launch the application.
"""

from TUI import main

if __name__ == "__main__":
    exit(main())
