import os
import subprocess
import time
from pytubefix import YouTube

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
    def __init__(self):
        self.start_time = None
        self.last_time = None
        self.last_bytes = 0
        self.speeds = []
        
    def __call__(self, stream, chunk, bytes_remaining):
        current_time = time.time()
        bytes_downloaded = stream.filesize - bytes_remaining
        
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
            percent = (bytes_downloaded / stream.filesize) * 100
            
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
            filled_length = int(bar_length * bytes_downloaded // stream.filesize)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Display progress
            print(f"\r📥 Progress: [{bar}] {percent:.1f}% | 🚀 Speed: {format_speed(avg_speed)} | ⏱️ ETA: {eta_str} | 📊 {format_bytes(bytes_downloaded)}/{format_bytes(stream.filesize)}", end='', flush=True)
        
        # Update last values
        self.last_time = current_time
        self.last_bytes = bytes_downloaded

def get_available_resolutions(streams):
    """Get all available resolutions for the video"""
    resolutions = set()
    for stream in streams:
        if stream.resolution:
            resolutions.add(stream.resolution)
    return sorted(resolutions, key=lambda x: int(x.replace('p', '')), reverse=True)

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
        print(f"🔄 Downloading {video_resolution} video and audio separately...")
        
        # Get the best video stream for the selected resolution
        video_stream = yt.streams.filter(
            adaptive=True, 
            file_extension='mp4', 
            type="video",
            res=video_resolution
        ).first()
        
        # Get the best audio stream
        audio_stream = yt.streams.filter(
            adaptive=True, 
            type="audio",
            file_extension='mp4'
        ).order_by('abr').desc().first()
        
        if not video_stream or not audio_stream:
            print("❌ Could not find suitable video or audio streams.")
            return False
        
        download_folder = "youtube_downloads"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        
        
        # Download video
        print(f"\n📹 Downloading video ({video_resolution})...")
        video_filename = f"temp_video_{video_stream.itag}.mp4"
        video_path = os.path.join(download_folder, video_filename)
        video_stream.download(output_path=download_folder, filename=video_filename)
        print()  # New line after progress
        
        # Download audio
        print(f"🎵 Downloading audio ({audio_stream.abr})...")
        audio_filename = f"temp_audio_{audio_stream.itag}.mp4"
        audio_path = os.path.join(download_folder, audio_filename)
        audio_stream.download(output_path=download_folder, filename=audio_filename)
        print()  # New line after progress
        
        # Merge with FFmpeg
        print("🔄 Merging video and audio...")
        
        # Clean filename of invalid characters
        final_filename = f"{yt.title}.mp4"
        final_filename = "".join(c for c in final_filename if c.isalnum() or c in (' ', '-', '_', '.'))
        final_path = os.path.join(download_folder, final_filename)
        
        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path, '-i', audio_path,
            '-c', 'copy',
            '-shortest',
            '-y',
            final_path
        ]
        
        # Show FFmpeg progress (simple version)
        print("Merging: [░░░░░░░░░░] 0%", end='', flush=True)
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\rMerging: [██████████] 100%")
        else:
            print("\r❌ Merge failed")
        
        # Clean up temporary files
        try:
            os.remove(video_path)
            os.remove(audio_path)
        except Exception:
            pass  # Ignore cleanup errors
        
        print("✅ Successfully merged video and audio!")
        print(f"📄 File saved as: {final_filename}")
        return True
        
    except subprocess.CalledProcessError:
        print("❌ FFmpeg merge failed. Please check if FFmpeg is installed correctly.")
        return False
    except Exception as e:
        print(f"❌ Error during merge: {e}")
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
        yt = YouTube(url)
        
        print(f"\n📹 Title: {yt.title}")
        print(f"👤 Author: {yt.author}")
        print(f"⏱️ Duration: {yt.length} seconds")
        print(f"👀 Views: {yt.views:,}")
        
        # Get all streams
        all_streams = yt.streams.filter(file_extension='mp4')
        progressive_streams = all_streams.filter(progressive=True)
        adaptive_streams = all_streams.filter(adaptive=True)
        
        # Get video-only and audio-only streams correctly
        video_only_streams = adaptive_streams.filter(type="video")
        
        available_resolutions = get_available_resolutions(all_streams)
        
        if not available_resolutions:
            print("❌ No MP4 streams available for this video.")
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
                audio_info = "(Video+Audio)"
            elif adaptive_available and ffmpeg_available:
                marker = "🔄"
                audio_info = "(Video only - will merge with audio)"
            elif adaptive_available:
                marker = "🎬"
                audio_info = "(Video only - no audio)"
            else:
                marker = "❓"
                audio_info = "(Unknown)"
            
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
        
        # Create progress callback
        progress_callback = DownloadProgress()
        yt.register_on_progress_callback(progress_callback)
        
        # Try progressive stream first (has audio)
        selected_stream = progressive_streams.filter(res=selected_resolution).first()
        
        if selected_stream:
            # Progressive stream with audio
            print(f"\n📥 Downloading: {yt.title}")
            print(f"📊 Resolution: {selected_resolution} (with audio)")
            if selected_stream.filesize:
                print(f"💾 Size: {format_bytes(selected_stream.filesize)}")
            print("-" * 50)
            
            selected_stream.download(output_path=download_folder)
            print("\n\n✅ Download completed!")  # Extra newline after progress bar
            print(f"📄 File saved as: {selected_stream.default_filename}")
            
        else:
            # Adaptive stream (video only) - need to handle audio
            if ffmpeg_available:
                # Try to download and merge
                success = download_with_audio_merge(yt, selected_resolution)
                if not success:
                    print("❌ Failed to download with audio. Downloading video only...")
                    # Fallback to video only
                    video_stream = video_only_streams.filter(res=selected_resolution).first()
                    if video_stream:
                        print(f"\n📥 Downloading video only: {yt.title}")
                        print(f"📊 Resolution: {selected_resolution} (video only)")
                        if video_stream.filesize:
                            print(f"💾 Size: {format_bytes(video_stream.filesize)}")
                        video_stream.download(output_path=download_folder)
                        print("\n\n⚠️ Downloaded video only (no audio)")
            else:
                print("❌ FFmpeg not found. Cannot merge audio for high resolution videos.")
                print("🔧 Please install FFmpeg or choose a resolution with audio (720p or lower).")
                return
        
        input("\nPress Enter to continue...")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Download cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        input("\nPress Enter to continue...")

def download_simple():
    """Simple download - always gets the best quality with audio"""
    try:
        print("\n" + "="*50)
        print("🚀 SIMPLE DOWNLOAD (BEST QUALITY WITH AUDIO)")
        print("="*50)
        
        url = input("Enter YouTube video URL: ").strip()
        if not url:
            print("❌ No URL provided!")
            return
        
        print("⏳ Loading video information...")
        yt = YouTube(url)
        
        print(f"\n📹 Title: {yt.title}")
        print(f"👤 Author: {yt.author}")
        
        # Get the highest progressive stream (always has audio)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not stream:
            print("❌ No streams with audio available. Try the advanced download instead.")
            return
        
        download_folder = "youtube_downloads"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        # Create progress callback
        progress_callback = DownloadProgress()
        yt.register_on_progress_callback(progress_callback)
        
        print(f"\n📥 Downloading: {stream.resolution} (with audio)")
        if stream.filesize:
            print(f"💾 Size: {format_bytes(stream.filesize)}")
        print("-" * 50)
        
        stream.download(output_path=download_folder)
        
        print("\n\n✅ Download completed!")  # Extra newline after progress bar
        print(f"📄 File saved as: {stream.default_filename}")
        
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
        yt = YouTube(url)
        
        print(f"\n📹 Title: {yt.title}")
        print(f"👤 Author: {yt.author}")
        if hasattr(yt, 'publish_date') and yt.publish_date:
            print(f"📅 Publish Date: {yt.publish_date}")
        print(f"⏱️ Duration: {yt.length} seconds ({yt.length//60}:{yt.length%60:02d})")
        print(f"👀 Views: {yt.views:,}")
        
        print("\n🎯 Available Streams:")
        print("-" * 50)
        
        # Show progressive streams first (with audio)
        progressive_streams = yt.streams.filter(progressive=True, file_extension='mp4')
        if progressive_streams:
            print("\n✅ Progressive Streams (Video + Audio):")
            for stream in progressive_streams:
                filesize = f" - {format_bytes(stream.filesize)}" if stream.filesize else ""
                print(f"  {stream.resolution} - {stream.mime_type}{filesize}")
        
        # Show adaptive video streams (video only)
        video_streams = yt.streams.filter(adaptive=True, type="video", file_extension='mp4')
        if video_streams:
            print("\n🎬 Adaptive Video Streams (Video Only):")
            for stream in video_streams:
                filesize = f" - {format_bytes(stream.filesize)}" if stream.filesize else ""
                print(f"  {stream.resolution} - {stream.mime_type}{filesize}")
        
        # Show adaptive audio streams
        audio_streams = yt.streams.filter(adaptive=True, type="audio")
        if audio_streams:
            print("\n🎵 Adaptive Audio Streams:")
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