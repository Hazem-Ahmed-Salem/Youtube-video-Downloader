# 🎬 YouTube Video Downloader

A feature-rich YouTube video downloader built with Python, offering both a beautiful **Terminal User Interface (TUI)** and a classic **Command-Line Interface (CLI)**.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- 📹 **Download YouTube videos** in various resolutions (up to 4K)
- 🎵 **Automatic audio merging** for high-resolution videos using FFmpeg
- 🎯 **Resolution selection** - choose your preferred quality
- 📊 **Real-time progress tracking** with download speed and ETA
- 🖥️ **Dual interface options**:
  - **TUI Mode**: Modern, interactive terminal UI built with [Textual](https://textual.textualize.io/)
  - **CLI Mode**: Classic command-line interface
- 📄 **Video information display** - view details before downloading
- 🔧 **FFmpeg integration** for merging video and audio streams

## 📋 Requirements

- Python 3.8+
- FFmpeg (optional, but required for high-resolution videos with audio)

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Hazem-Ahmed-Salem/Youtube-video-Downloader.git
cd Youtube-video-Downloader
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg 

FFmpeg is required for downloading high-resolution videos (above 720p) with audio.

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
1. Download from: https://www.gyan.dev/ffmpeg/builds/
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your PATH environment variable

## 📖 Usage

### TUI Mode (Recommended)

Launch the beautiful terminal user interface:

```bash
python TUI_main.py
```

**Features:**
- Interactive menu navigation
- Visual progress bars
- Dark/Light mode toggle (`D` key)
- Keyboard shortcuts for quick actions

### CLI Mode

Launch the classic command-line interface:

```bash
python CLI_main.py
```

**Menu Options:**
1. **Simple Download** - Automatically downloads the best quality with audio
2. **Advanced Download** - Choose your preferred resolution
3. **Show Video Information** - View video details and available streams
4. **Check FFmpeg Installation** - Verify FFmpeg is properly configured
5. **Exit**

### Merger Utility

Merge separate video and audio files:

```bash
python merger.py -v video.mp4 -a audio.mp4 -o output.mp4
```

**Options:**
- `-v, --video` - Path to the video file (required)
- `-a, --audio` - Path to the audio file (required)
- `-o, --output` - Output file path (optional, defaults to video path)
- `-c, --cleanup` - Remove original files after merging

## 📁 Project Structure

```
Youtube-video-Downloader/
├── TUI_main.py           # TUI entry point
├── CLI_main.py           # CLI entry point
├── merger.py             # Video/audio merger utility
├── requirements.txt      # Python dependencies
├── TUI/                  # TUI package
│   ├── __init__.py       # Package exports
│   ├── app.py            # Main Textual application
│   ├── utils.py          # Utility functions
│   ├── screens/          # TUI screens
│   │   ├── main_menu.py
│   │   ├── simple_download.py
│   │   ├── advanced_download.py
│   │   ├── video_info.py
│   │   └── ffmpeg_check.py
│   └── widgets/          # Custom TUI widgets
│       ├── download_progress.py
│       ├── status_panel.py
│       └── video_info_panel.py
└── youtube_downloads/    # Downloaded videos (auto-created)
```

## 🔑 Key Dependencies

| Package | Description |
|---------|-------------|
| [pytubefix](https://github.com/JuanBindez/pytubefix) | YouTube video downloading library |
| [textual](https://textual.textualize.io/) | Modern TUI framework |
| [rich](https://rich.readthedocs.io/) | Rich text and beautiful formatting |

## 📝 Notes

- **Resolution with Audio**: Videos at 720p and below typically come with audio included. Higher resolutions (1080p, 1440p, 4K) require FFmpeg to merge separate video and audio streams.
- **Download Location**: All downloads are saved to the `youtube_downloads/` folder in the project directory.
- **Keyboard Shortcuts (TUI)**:
  - `Q` - Quit the application
  - `D` - Toggle dark/light mode
  - `Enter` - Select menu options

## ⚠️ Disclaimer

This tool is for personal use only. Please respect YouTube's Terms of Service and copyright laws. Only download videos that you have the right to download.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

---

Made with ❤️ using Python, Textual, and pytubefix
