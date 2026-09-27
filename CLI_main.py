import os
import subprocess
import time
from pytubefix import YouTube, exceptions
from youtube_helper import (
    get_youtube_instance,
    get_available_resolutions,
    get_best_video_stream,
    get_best_audio_stream,
)
from merger import merge

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_bytes(bytes):
    """Convert bytes to human readable format"""
    if bytes >= 1024**3:  # GB
        return f"{bytes / (1024**3):.2f} GB"
    elif bytes >= 1024**2:  # MB
        return f"{bytes / (1024**2):.2f} MB"
    elif bytes >= 1024:  # KB
        return f"{bytes / 1024:.2f} KB"
    else:
        return f"{bytes} B"

def format_speed(speed):
    """Convert speed to human readable format"""
    if speed >= 1024**2:  # MB/s
        return f"{speed / (1024**2):.2f} MB/s"
    elif speed >= 1024:  # KB/s
        return f"{speed / 1024:.2f} KB/s"
    else:
        return f"{speed:.2f} B/s"

class DownloadProgress:
    """Custom progress callback with speed calculation"""
    def __init__(self, label="Progress"):
        self.label = label
        self.start_time = None
        self.last_time = None
        self.last_bytes = 0
        self.speeds = []
        
    def __call__(self, stream, chunk, bytes_remaining):
        current_time = time.time()
        filesize = stream.filesize or (self.last_bytes + bytes_remaining)
        bytes_downloaded = filesize - bytes_remaining
        
        # Initialize timing
        if self.start_time is None:
            self.start_time = current_time
            self.last_time = current_time
            self.last_bytes = bytes_downloaded
            return
            
        # Calculate current speed
        time_diff = current_time - self.last_time
        if time_diff > 0:  # Avoid division by zero
            current_speed = (bytes_downloaded - self.last_bytes) / time_diff
            self.speeds.append(current_speed)
            
            # Keep only last 5 speeds for average
            if len(self.speeds) > 5:
                self.speeds.pop(0)
                
            # Calculate average speed
            avg_speed = sum(self.speeds) / len(self.speeds) if self.speeds else 0
            
            # Calculate progress percentage
            percent = (bytes_downloaded / filesize) * 100 if filesize > 0 else 0
            
            # Calculate ETA
            if avg_speed > 0:
                eta_seconds = bytes_remaining / avg_speed
                eta_minutes = int(eta_seconds // 60)
                eta_seconds = int(eta_seconds % 60)
                eta_str = f"{eta_minutes:02d}:{eta_seconds:02d}"
            else:
                eta_str = "Calculating..."
            
            # Create progress bar
            bar_length = 30
            filled_length = int(bar_length * bytes_downloaded // filesize) if filesize > 0 else 0
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Display progress
            print(f"\r📥 {self.label}: [{bar}] {percent:.1f}% | 🚀 Speed: {format_speed(avg_speed)} | ⏱️ ETA: {eta_str} | 📊 {format_bytes(bytes_downloaded)}/{format_bytes(filesize)}", end='', flush=True)
        
        # Update last values
        self.last_time = current_time
        self.last_bytes = bytes_downloaded

def has_ffmpeg():
    """Check if FFmpeg is installed and available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def download_with_audio_merge(yt, video_resolution):
    """Download video and audio separately, then merge with FFmpeg"""
    try:
        print(f"🔄 Downloading {video_resolution} video and best audio separately...")

        video_stream = get_best_video_stream(yt.streams, video_resolution)
        audio_stream = get_best_audio_stream(yt.streams)

        if not video_stream or not audio_stream:
            print(f"❌ Could not find suitable video ({video_resolution}) or audio streams.")
            return False
        
        download_folder = "youtube_downloads"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        v_ext = video_stream.subtype or 'mp4'
        a_ext = audio_stream.subtype or 'mp4'

        video_filename = f"temp_video_{video_stream.itag}.{v_ext}"
        audio_filename = f"temp_audio_{audio_stream.itag}.{a_ext}"

        video_path = os.path.join(download_folder, video_filename)
        audio_path = os.path.join(download_folder, audio_filename)
        
        # Download video
        print(f"\n📹 Downloading video ({video_resolution}, {video_stream.mime_type})...")
        video_progress = DownloadProgress(label="Video")
        yt.register_on_progress_callback(video_progress)
        video_stream.download(output_path=download_folder, filename=video_filename)
        print()  # New line after progress
        
        # Download audio
        print(f"🎵 Downloading audio ({audio_stream.abr}, {audio_stream.mime_type})...")
        audio_progress = DownloadProgress(label="Audio")
        yt.register_on_progress_callback(audio_progress)
        audio_stream.download(output_path=download_folder, filename=audio_filename)
        print()  # New line after progress
        
        # Merge with FFmpeg
        print("🔄 Merging video and audio with FFmpeg...")
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        if not safe_title:
            safe_title = f"video_{getattr(yt, 'video_id', 'download')}"
        final_filename = f"{safe_title}.mp4"
        final_path = os.path.join(download_folder, final_filename)

        merge(
            video_path=video_path,
            audio_path=audio_path,
            output_path=final_path,
            cleanup=True
        )
        return True
        
    except Exception as e:
        print(f"❌ Error during download & merge: {e}")
        return False

def download_youtube_video():
    """Download YouTube video with resolution selection"""
    try:
        print("\n" + "="*50)
        print("📥 DOWNLOAD WITH RESOLUTION SELECTION")
        print("="*50)
        
        url = input("Enter YouTube video URL: ").strip()
        if not url:
            print("❌ No URL provided!")
            return
        
        print("⏳ Loading video information...")
        yt = get_youtube_instance(url)
        
        print(f"\n📹 Title: {yt.title}")
        print(f"👤 Author: {yt.author}")
        print(f"⏱️ Duration: {yt.length} seconds")
        print(f"👀 Views: {yt.views:,}")
        
        all_streams = list(yt.streams)
        progressive_streams = [s for s in all_streams if getattr(s, 'is_progressive', False)]
        video_only_streams = [s for s in all_streams if getattr(s, 'is_adaptive', False) and s.type == 'video']

        available_resolutions = get_available_resolutions(all_streams)
        
        if not available_resolutions:
            print("❌ No video streams available for this video.")
            return
        
        # Display available resolutions with audio info
        print("\n🎯 Available Resolutions:")
        print("-" * 50)
        
        ffmpeg_available = has_ffmpeg()
        
        for i, resolution in enumerate(available_resolutions, 1):
            progressive_available = any(stream.resolution == resolution for stream in progressive_streams)
            adaptive_available = any(stream.resolution == resolution for stream in video_only_streams)
            
            if progressive_available:
                marker = "✅"
                audio_info = "(Video+Audio directly)"
            elif adaptive_available and ffmpeg_available:
                marker = "🔄"
                audio_info = "(Full HD/HD - will merge with audio via FFmpeg)"
            elif adaptive_available:
                marker = "🎬"
                audio_info = "(Video only - install FFmpeg for audio merge)"
            else:
                marker = "❓"
                audio_info = "(Available)"
            
            print(f"{i}. {resolution} {marker} {audio_info}")
        
        # Let user choose resolution
        while True:
            try:
                choice = input(f"\nChoose resolution (1-{len(available_resolutions)}): ").strip()
                if not choice:
                    continue
                choice = int(choice)
                if 1 <= choice <= len(available_resolutions):
                    selected_resolution = available_resolutions[choice - 1]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(available_resolutions)}")
            except ValueError:
                print("❌ Please enter a valid number.")
            except KeyboardInterrupt:
                print("\n⚠️ Download cancelled by user.")
                return
        
        download_folder = "youtube_downloads"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        # Check if a progressive stream is available for this resolution
        prog_matches = [s for s in progressive_streams if s.resolution == selected_resolution]
        selected_stream = prog_matches[0] if prog_matches else None
        
        if selected_stream:
            # Progressive stream with audio
            print(f"\n📥 Downloading: {yt.title}")
            print(f"📊 Resolution: {selected_resolution} (with audio)")
            if selected_stream.filesize:
                print(f"💾 Size: {format_bytes(selected_stream.filesize)}")
            print("-" * 50)
            
            progress_callback = DownloadProgress(label="Progress")
            yt.register_on_progress_callback(progress_callback)
            selected_stream.download(output_path=download_folder)
            print("\n\n✅ Download completed!")
            print(f"📄 File saved as: {selected_stream.default_filename}")
            
        else:
            # Adaptive stream (video only) - merge with audio using FFmpeg
            if ffmpeg_available:
                success = download_with_audio_merge(yt, selected_resolution)
                if not success:
                    print("❌ Failed to download and merge with audio.")
            else:
                print("❌ FFmpeg not found. Cannot merge audio for high resolution videos.")
                print("🔧 Please install FFmpeg or choose a resolution with audio (like 360p).")
                download_video_only = input("Do you want to download video only without audio? (y/N): ").strip().lower()
                if download_video_only == 'y':
                    vid_stream = get_best_video_stream(all_streams, selected_resolution)
                    if vid_stream:
                        print(f"\n📥 Downloading video only: {yt.title}")
                        print(f"📊 Resolution: {selected_resolution} (video only)")
                        progress_callback = DownloadProgress(label="Video")
                        yt.register_on_progress_callback(progress_callback)
                        vid_stream.download(output_path=download_folder)
                        print("\n\n⚠️ Downloaded video only (no audio)")
        
        input("\nPress Enter to continue...")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Download cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        input("\nPress Enter to continue...")

def download_simple():
    """Simple download - always gets the highest quality available with audio (up to 4K/1080p)"""
    try:
        print("\n" + "="*50)
        print("🚀 SIMPLE DOWNLOAD (BEST QUALITY WITH AUDIO)")
        print("="*50)
        
        url = input("Enter YouTube video URL: ").strip()
        if not url:
            print("❌ No URL provided!")
            return
        
        print("⏳ Loading video information...")
        yt = get_youtube_instance(url)
        
        print(f"\n📹 Title: {yt.title}")
        print(f"👤 Author: {yt.author}")
        
        download_folder = "youtube_downloads"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        ffmpeg_available = has_ffmpeg()
        all_streams = list(yt.streams)
        
        # Get highest resolution video stream available
        best_video = get_best_video_stream(all_streams)
        
        if not best_video:
            print("❌ No video streams available.")
            return

        if getattr(best_video, 'is_progressive', False):
            # Progressive stream
            print(f"\n📥 Downloading best progressive stream: {best_video.resolution} (with audio)")
            if best_video.filesize:
                print(f"💾 Size: {format_bytes(best_video.filesize)}")
            print("-" * 50)
            progress_callback = DownloadProgress(label="Progress")
            yt.register_on_progress_callback(progress_callback)
            best_video.download(output_path=download_folder)
            print("\n\n✅ Download completed!")
            print(f"📄 File saved as: {best_video.default_filename}")
        elif ffmpeg_available:
            # Download highest resolution video (e.g. 1080p, 1440p, 4K) + best audio, and merge
            print(f"\n🎯 Best resolution found: {best_video.resolution}")
            success = download_with_audio_merge(yt, best_video.resolution)
            if not success:
                print("❌ Failed to download and merge best quality video.")
        else:
            # FFmpeg not available - fallback to highest progressive stream
            prog_streams = [s for s in all_streams if getattr(s, 'is_progressive', False)]
            if prog_streams:
                prog_streams.sort(
                    key=lambda s: int(s.resolution[:-1]) if s.resolution and s.resolution[:-1].isdigit() else 0,
                    reverse=True
                )
                stream = prog_streams[0]
                print(f"\n⚠️ FFmpeg not found! Falling back to highest progressive stream: {stream.resolution}")
                print("💡 Install FFmpeg to download 1080p and higher resolutions with audio.")
                progress_callback = DownloadProgress(label="Progress")
                yt.register_on_progress_callback(progress_callback)
                print(f"\n📥 Downloading: {stream.resolution} (with audio)")
                if stream.filesize:
                    print(f"💾 Size: {format_bytes(stream.filesize)}")
                print("-" * 50)
                stream.download(output_path=download_folder)
                print("\n\n✅ Download completed!")
                print(f"📄 File saved as: {stream.default_filename}")
            else:
                print("❌ No progressive stream available and FFmpeg is not installed.")
        
        input("\nPress Enter to continue...")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Download cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        input("\nPress Enter to continue...")

def show_video_info():
    """Show detailed information about the video"""
    try:
        print("\n" + "="*50)
        print("📊 VIDEO INFORMATION")
        print("="*50)
        
        url = input("Enter YouTube video URL: ").strip()
        
        if not url:
            print("❌ No URL provided!")
            return
        
        print("⏳ Loading video information...")
        yt = get_youtube_instance(url)
        
        print(f"\n📹 Title: {yt.title}")
        print(f"👤 Author: {yt.author}")
        if hasattr(yt, 'publish_date') and yt.publish_date:
            print(f"📅 Publish Date: {yt.publish_date}")
        print(f"⏱️ Duration: {yt.length} seconds ({yt.length//60}:{yt.length%60:02d})")
        print(f"👀 Views: {yt.views:,}")
        
        print("\n🎯 Available Streams:")
        print("-" * 50)
        
        # Show progressive streams first (with audio)
        progressive_streams = [s for s in yt.streams if getattr(s, 'is_progressive', False)]
        if progressive_streams:
            print("\n✅ Progressive Streams (Video + Audio directly):")
            for stream in progressive_streams:
                filesize = f" - {format_bytes(stream.filesize)}" if stream.filesize else ""
                print(f"  {stream.resolution} - {stream.mime_type}{filesize}")
        
        # Show adaptive video streams (video only)
        video_streams = [s for s in yt.streams if getattr(s, 'is_adaptive', False) and s.type == 'video']
        if video_streams:
            print("\n🎬 Adaptive Video Streams (High Resolution - merged with audio):")
            for stream in video_streams:
                filesize = f" - {format_bytes(stream.filesize)}" if stream.filesize else ""
                fps_info = f" ({stream.fps}fps)" if hasattr(stream, 'fps') and stream.fps else ""
                print(f"  {stream.resolution}{fps_info} - {stream.mime_type}{filesize}")
        
        # Show adaptive audio streams
        audio_streams = [s for s in yt.streams if s.type == 'audio']
        if audio_streams:
            print("\n🎵 Audio Streams:")
            for stream in audio_streams:
                filesize = f" - {format_bytes(stream.filesize)}" if stream.filesize else ""
                print(f"  {stream.abr} - {stream.mime_type}{filesize}")
            
        input("\nPress Enter to continue...")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        input("\nPress Enter to continue...")

def check_ffmpeg_installation():
    """Check and guide for FFmpeg installation"""
    print("\n🔧 FFmpeg Installation Check")
    print("="*30)
    
    if has_ffmpeg():
        print("✅ FFmpeg is installed and available!")
        print("You can download high resolution videos with audio.")
        return True
    else:
        print("❌ FFmpeg is NOT installed or not in PATH")
        print("\n📥 To install FFmpeg:")
        print("Windows:")
        print("  1. Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract to C:\\ffmpeg")
        print("  3. Add C:\\ffmpeg\\bin to your PATH environment variable")
        print("\nmacOS:")
        print("  brew install ffmpeg")
        print("\nLinux (Ubuntu/Debian):")
        print("  sudo apt install ffmpeg")
        print("\nWithout FFmpeg, you can only download up to 720p with audio.")
        return False

def main():
    """Main menu"""
    ffmpeg_available = has_ffmpeg()
    
    while True:
        clear_screen()
        print("🎬 YOUTUBE VIDEO DOWNLOADER (pytubefix)")
        print("=" * 50)
        if ffmpeg_available:
            print("✅ FFmpeg: Available (All resolutions with audio supported)")
        else:
            print("❌ FFmpeg: Not available (720p max with audio)")
        print("=" * 50)
        print("📋 Options:")
        print("1. Simple download (best quality with audio)")
        print("2. Advanced download (choose resolution)")
        print("3. Show video information")
        print("4. Check FFmpeg installation")
        print("5. Exit")
        print("=" * 50)
        
        choice = input("\nChoose option (1-5): ").strip()
        
        if choice == '1':
            download_simple()
        elif choice == '2':
            download_youtube_video()
        elif choice == '3':
            show_video_info()
        elif choice == '4':
            check_ffmpeg_installation()
            input("\nPress Enter to continue...")
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program terminated by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")