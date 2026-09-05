import subprocess
import os
import shutil
import argparse
from unittest import result


def merge(video_path: str, audio_path: str, output_path: str = None, cleanup: bool = False) -> str:
    """
    Merge video and audio files using ffmpeg.
    
    Args:
        video_path: Path to the video file
        audio_path: Path to the audio file
        output_path: Path for the merged output file (optional, auto-generated if not provided)
        cleanup: If True, remove the original video and audio files after merging
    
    Returns:
        Path to the merged output file
    """
    # Validate input files exist
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Generate output path if not provided
    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_merged{ext}"
    
    # Check if output is same as input - use temp file if so
    output_same_as_input = os.path.abspath(output_path) == os.path.abspath(video_path)
    if output_same_as_input:
        base, ext = os.path.splitext(output_path)
        temp_output_path = f"{base}_temp_merge{ext}"
    else:
        temp_output_path = output_path
    
    # Ensure output directory exists
    output_dir = os.path.dirname(temp_output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Build ffmpeg command
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_path,      # Input video
        '-i', audio_path,      # Input audio
        '-c:v', 'copy',        # Copy video codec (no re-encoding)
        '-c:a', 'aac',         # Encode audio to AAC for compatibility
        '-map', '0:v:0',       # Map video from first input
        '-map', '1:a:0',       # Map audio from second input
        '-shortest',           # Use duration of shortest stream
        '-y',                  # Overwrite output file without asking
        temp_output_path
    ]
    
    print("🎬 Merging video and audio...")
    print(f"   Video: {video_path}")
    print(f"   Audio: {audio_path}")
    print(f"   Output: {output_path}")
    
    try:
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # If output was same as input, replace original with merged file
        if output_same_as_input:
            os.remove(video_path)
            shutil.move(temp_output_path, output_path)
        
        print("✅ Successfully merged video and audio!")
        print(f"📄 File saved as: {output_path}")
        
        # Clean up audio file if requested (video already replaced if same as output)
        if cleanup:
            print("🧹 Cleaning up original files...")
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"   Removed: {audio_path}")
            # Only remove video if it wasn't already replaced
            if not output_same_as_input and os.path.exists(video_path):
                os.remove(video_path)
                print(f"   Removed: {video_path}")
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        # Clean up temp file on error
        if output_same_as_input and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        print("❌ Error merging files!")
        print(f"   FFmpeg stderr: {e.stderr}")
        raise RuntimeError(f"FFmpeg failed: {e.stderr}")


def main():
    parser = argparse.ArgumentParser(
        description="Merge video and audio files using ffmpeg"
    )
    parser.add_argument(
        "-v", "--video",
        required=True,
        help="Path to the video file"
    )
    parser.add_argument(
        "-a", "--audio",
        required=True,
        help="Path to the audio file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Path for the output merged file (optional, defaults to video path)"
    )
    parser.add_argument(
        "-c", "--cleanup",
        action="store_true",
        help="Remove original video and audio files after successful merge"
    )
    
    args = parser.parse_args()
    
    # Use video path as output if not specified
    output_path = args.output if args.output else args.video
    
    try:
        merge(
            video_path=args.video,
            audio_path=args.audio,
            output_path=output_path,
            cleanup=args.cleanup
        )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
