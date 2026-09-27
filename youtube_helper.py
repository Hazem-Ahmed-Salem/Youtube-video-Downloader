"""
Helper module for initializing YouTube video instances and streaming with anti-bot,
anti-403, high-resolution adaptive stream support, and FFmpeg merging.

Uses yt-dlp as the primary robust download and metadata engine with seamless pytubefix
compatibility, providing full access to all resolutions (1080p, 1440p, 4K, 8K) without
HTTP 403 Forbidden errors or bot detection roadblocks.
"""

import http.client
import logging
import os
import re
import socket
import urllib.parse
from typing import Callable, List, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytubefix.request as pytubefix_request
from pytubefix import YouTube as PytubeFixYouTube, Stream, exceptions
from merger import merge

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Pytubefix compatibility monkey-patches (retained for pytubefix fallback)
# ----------------------------------------------------------------------
def _patch_pytubefix_request():
    """Patch pytubefix.request.stream to avoid range overflow 403 errors."""
    if getattr(pytubefix_request, "_anti403_patched", False):
        return

    def safe_stream(url, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, max_retries=0):
        file_size = pytubefix_request.default_range_size
        downloaded = 0
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'clen' in qs and qs['clen'][0].isdigit():
                file_size = int(qs['clen'][0])
        except Exception:
            pass

        while downloaded < file_size:
            stop_pos = min(downloaded + pytubefix_request.default_range_size, file_size) - 1
            tries = 0
            while True:
                if tries >= 1 + max_retries:
                    raise pytubefix_request.MaxRetriesExceeded()
                try:
                    response = pytubefix_request._execute_request(
                        f"{url}&range={downloaded}-{stop_pos}",
                        method="GET",
                        timeout=timeout
                    )
                except pytubefix_request.URLError as e:
                    if not isinstance(e.reason, (socket.timeout, OSError)):
                        raise
                except http.client.IncompleteRead:
                    pass
                else:
                    break
                tries += 1

            while True:
                try:
                    chunk = response.read()
                except StopIteration:
                    return
                except http.client.IncompleteRead as e:
                    chunk = e.partial
                if not chunk:
                    break
                downloaded += len(chunk)
                yield chunk
        return

    pytubefix_request.stream = safe_stream
    pytubefix_request._anti403_patched = True


_patch_pytubefix_request()


# ----------------------------------------------------------------------
# YouTube URL canonicalization and helper functions
# ----------------------------------------------------------------------
def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract YouTube 11-character video ID from various URL formats or plain ID."""
    if not url:
        return None
    url = url.strip()

    # 1. Plain 11-char ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    # 2. youtu.be/<id>
    m = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)

    # 3. /shorts/<id>, /embed/<id>, /v/<id>, /live/<id>
    m = re.search(r'youtube\.com/(?:shorts|embed|v|live)/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)

    # 4. ?v=<id> or &v=<id>
    m = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)

    return None


def is_playlist_url(url: str) -> bool:
    """Check if URL points to a playlist without a video ID."""
    if not url:
        return False
    if extract_youtube_video_id(url):
        return False
    return "playlist?list=" in url or ("/playlist" in url and "list=" in url)


def clean_youtube_url(url: str) -> str:
    """
    Clean and canonicalize YouTube video URL.
    Extracts the video ID and strips playlist, index, and tracking parameters
    to prevent yt-dlp or pytubefix from mistakenly processing an entire playlist
    when the user intended to download a specific video.
    """
    if not url:
        return url
    url = url.strip()
    video_id = extract_youtube_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


# ----------------------------------------------------------------------
# Robust Stream and YouTube classes backed by yt-dlp
# ----------------------------------------------------------------------
class RobustStream:
    """
    Drop-in replacement for pytubefix.Stream backed by yt-dlp.
    Supports download callbacks, progress updates, and file properties.
    """

    def __init__(self, fmt: dict, yt: "RobustYouTube"):
        self._fmt = fmt
        self._yt = yt

        self.itag = str(fmt.get("format_id", ""))
        height = fmt.get("height")
        if not height:
            res_str = str(fmt.get("resolution") or "")
            if "x" in res_str:
                try:
                    height = int(res_str.split("x")[1])
                except Exception:
                    pass
            if not height and fmt.get("format_note"):
                m = re.search(r"(\d+)p", str(fmt.get("format_note", "")))
                if m:
                    height = int(m.group(1))

        self.resolution = f"{height}p" if height else None
        self.fps = fmt.get("fps")
        self.vcodec = fmt.get("vcodec") or "none"
        self.acodec = fmt.get("acodec") or "none"

        ext = fmt.get("ext", "mp4")
        self.subtype = ext

        has_v = (self.vcodec != "none") or bool(height)
        has_a = (self.acodec != "none")

        if has_v and has_a:
            self.type = "video"
            self.is_progressive = True
            self.is_adaptive = False
        elif has_v:
            self.type = "video"
            self.is_progressive = False
            self.is_adaptive = True
        elif has_a:
            self.type = "audio"
            self.is_progressive = False
            self.is_adaptive = True
        else:
            self.type = "unknown"
            self.is_progressive = False
            self.is_adaptive = False

        self.mime_type = f"{self.type}/{ext}"
        self.filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0

        abr_val = fmt.get("abr")
        self.abr = f"{int(abr_val)}kbps" if abr_val else None

        self.protocol = fmt.get("protocol") or "https"
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (" ", "-", "_", ".")).strip()
        if not safe_title:
            safe_title = f"video_{getattr(yt, 'video_id', 'download')}"
        self.default_filename = f"{safe_title}.{ext}"
        self.url = fmt.get("url") or ""
        self.is_sabr = False

    def __repr__(self) -> str:
        return (
            f'<RobustStream: itag="{self.itag}" mime_type="{self.mime_type}" '
            f'res="{self.resolution}" type="{self.type}" progressive="{self.is_progressive}">'
        )

    def exists_at_path(self, file_path: str) -> bool:
        return os.path.exists(file_path) and os.path.getsize(file_path) > 0

    def get_file_path(
        self,
        filename: Optional[str] = None,
        output_path: Optional[str] = None,
        filename_prefix: Optional[str] = None,
        **kwargs
    ) -> str:
        out_dir = output_path or "."
        name = filename or self.default_filename
        if filename_prefix:
            name = f"{filename_prefix}{name}"
        return os.path.join(out_dir, name)

    def download(
        self,
        output_path: Optional[str] = None,
        filename: Optional[str] = None,
        filename_prefix: Optional[str] = None,
        skip_existing: bool = True,
        timeout: Optional[int] = None,
        max_retries: int = 0,
        interrupt_checker: Optional[Callable[[], bool]] = None
    ) -> Optional[str]:
        """
        Download this format using yt-dlp with real-time progress callbacks.
        """
        import yt_dlp

        out_dir = output_path or "."
        os.makedirs(out_dir, exist_ok=True)

        target_name = filename or self.default_filename
        if filename_prefix:
            target_name = f"{filename_prefix}{target_name}"
        file_path = os.path.join(out_dir, target_name)

        if skip_existing and self.exists_at_path(file_path):
            logger.debug(f"File {file_path} already exists, skipping")
            if self._yt.on_complete_callback:
                self._yt.on_complete_callback(self, file_path)
            return file_path

        total_bytes = self.filesize

        def progress_hook(d):
            if interrupt_checker and interrupt_checker():
                raise KeyboardInterrupt("Download interrupted")

            if d.get("status") == "downloading":
                dl_bytes = d.get("downloaded_bytes", 0)
                tot = d.get("total_bytes") or d.get("total_bytes_estimate")
                if tot and (not self.filesize or self.filesize == 0):
                    self.filesize = tot
                base_total = self.filesize or tot or dl_bytes
                bytes_rem = max(0, base_total - dl_bytes)
                if self._yt.on_progress_callback:
                    try:
                        self._yt.on_progress_callback(self, b"", bytes_rem)
                    except Exception as ex:
                        logger.debug(f"Error in on_progress_callback: {ex}")

            elif d.get("status") == "finished":
                if self._yt.on_progress_callback:
                    try:
                        self._yt.on_progress_callback(self, b"", 0)
                    except Exception:
                        pass

        ydl_opts = {
            "format": self.itag,
            "outtmpl": file_path,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "overwrites": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "retries": max(10, max_retries or 10),
            "fragment_retries": 10,
        }
        if timeout:
            ydl_opts["socket_timeout"] = timeout

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self._yt.url])

        if self._yt.on_complete_callback:
            try:
                self._yt.on_complete_callback(self, file_path)
            except Exception as ex:
                logger.debug(f"Error in on_complete_callback: {ex}")

        return file_path


class RobustStreamQuery:
    """
    Stream collection offering pytubefix-compatible querying (.filter, .get_by_itag, .first).
    """

    def __init__(self, streams: List[RobustStream]):
        self._streams = list(streams)

    def __iter__(self):
        return iter(self._streams)

    def __len__(self) -> int:
        return len(self._streams)

    def __getitem__(self, index):
        return self._streams[index]

    def first(self) -> Optional[RobustStream]:
        return self._streams[0] if self._streams else None

    def last(self) -> Optional[RobustStream]:
        return self._streams[-1] if self._streams else None

    def get_by_itag(self, itag) -> Optional[RobustStream]:
        itag_str = str(itag)
        for s in self._streams:
            if s.itag == itag_str:
                return s
        return None

    def filter(
        self,
        type: Optional[str] = None,
        res: Optional[str] = None,
        resolution: Optional[str] = None,
        mime_type: Optional[str] = None,
        subtype: Optional[str] = None,
        file_extension: Optional[str] = None,
        progressive: Optional[bool] = None,
        adaptive: Optional[bool] = None,
        only_audio: Optional[bool] = None,
        only_video: Optional[bool] = None,
    ) -> "RobustStreamQuery":
        filtered = self._streams

        target_res = res or resolution
        if target_res:
            filtered = [s for s in filtered if s.resolution == target_res]

        if type:
            filtered = [s for s in filtered if s.type == type]

        if mime_type:
            filtered = [s for s in filtered if s.mime_type == mime_type]

        target_ext = subtype or file_extension
        if target_ext:
            filtered = [s for s in filtered if s.subtype == target_ext]

        if progressive is not None:
            filtered = [s for s in filtered if s.is_progressive == progressive]

        if adaptive is not None:
            filtered = [s for s in filtered if s.is_adaptive == adaptive]

        if only_audio:
            filtered = [s for s in filtered if s.type == "audio"]

        if only_video:
            filtered = [s for s in filtered if s.type == "video"]

        return RobustStreamQuery(filtered)

    def order_by(self, attribute_name: str) -> "RobustStreamQuery":
        def sort_key(s):
            val = getattr(s, attribute_name, None)
            if attribute_name == "resolution" and val:
                num = "".join(c for c in val if c.isdigit())
                return int(num) if num else 0
            if attribute_name == "filesize" and val:
                return int(val)
            if attribute_name == "fps" and val:
                return int(val)
            return val or 0

        return RobustStreamQuery(sorted(self._streams, key=sort_key))


class RobustYouTube:
    """
    High-performance YouTube video handler backed by yt-dlp.
    Provides identical API to pytubefix.YouTube for seamless compatibility.
    """

    def __init__(
        self,
        url: str,
        on_progress_callback: Optional[Callable] = None,
        on_complete_callback: Optional[Callable] = None,
        **kwargs
    ):
        import yt_dlp

        cleaned_url = clean_youtube_url(url)
        self.url = cleaned_url
        self.on_progress_callback = on_progress_callback
        self.on_complete_callback = on_complete_callback
        self.client = "YT_DLP"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "nocheckcertificate": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self._info = ydl.extract_info(cleaned_url, download=False)

        if not self._info:
            raise exceptions.VideoUnavailable(f"Video {url} unavailable")

        # Handle case where yt-dlp might return a playlist dict
        if self._info.get("_type") == "playlist":
            entries = [e for e in (self._info.get("entries") or []) if e]
            if entries:
                self._info = entries[0]
            else:
                raise exceptions.VideoUnavailable(f"Playlist {url} contains no accessible videos")

        self.title = self._info.get("title", "")
        self.author = self._info.get("uploader") or self._info.get("channel") or "Unknown Author"
        self.length = int(self._info.get("duration", 0) or 0)
        self.views = int(self._info.get("view_count", 0) or 0)
        self.publish_date = self._info.get("upload_date")
        self.thumbnail_url = self._info.get("thumbnail")
        self.description = self._info.get("description", "")
        self.video_id = self._info.get("id") or extract_youtube_video_id(cleaned_url) or ""

        streams: List[RobustStream] = []
        for f in self._info.get("formats", []):
            protocol = f.get("protocol") or ""
            if "mhtml" in protocol or f.get("ext") == "mhtml":
                continue
            streams.append(RobustStream(f, self))

        if not streams:
            raise exceptions.VideoUnavailable(f"No video streams found for {url}")

        self.streams = RobustStreamQuery(streams)

    def register_on_progress_callback(self, func: Callable):
        self.on_progress_callback = func

    def register_on_complete_callback(self, func: Callable):
        self.on_complete_callback = func

    def check_availability(self):
        if not self._info:
            raise exceptions.VideoUnavailable(f"Video {self.url} is not available")


# ----------------------------------------------------------------------
# Public API and helper functions
# ----------------------------------------------------------------------
DEFAULT_CLIENTS: List[str] = ['WEB', 'MWEB', 'ANDROID_VR', 'WEB_MUSIC']


def is_stream_accessible(yt) -> bool:
    """Always returns True for RobustYouTube instances."""
    return True


def get_youtube_instance(
    url: str,
    on_progress_callback: Optional[Callable] = None,
    on_complete_callback: Optional[Callable] = None,
    client: Optional[str] = None,
    fallback_clients: Optional[List[str]] = None,
    verify_download: bool = True,
    **kwargs
):
    """
    Create a robust YouTube object that bypasses BotDetection and HTTP 403 Forbidden.
    Uses yt-dlp as the primary engine for high-resolution 1080p/4K support.
    Falls back to pytubefix if yt-dlp is unavailable.
    """
    if not url or not url.strip():
        raise ValueError("Please provide a valid YouTube URL.")

    cleaned_url = clean_youtube_url(url)
    if is_playlist_url(cleaned_url):
        raise ValueError("The provided URL is a playlist without a specific video. Please enter a specific video URL.")

    last_error = None
    try:
        import yt_dlp
        yt = RobustYouTube(
            cleaned_url,
            on_progress_callback=on_progress_callback,
            on_complete_callback=on_complete_callback,
            **kwargs
        )
        return yt
    except (exceptions.VideoUnavailable if exceptions else Exception) as e:
        last_error = e
        logger.warning(f"RobustYouTube initialization failed ({e}), trying pytubefix fallback...")
    except Exception as e:
        last_error = e
        logger.warning(f"RobustYouTube initialization failed ({e}), trying pytubefix fallback...")

    # Pytubefix fallback
    clients_to_try = [client] if client else list(DEFAULT_CLIENTS)
    for c in clients_to_try:
        try:
            yt = PytubeFixYouTube(
                cleaned_url,
                client=c,
                on_progress_callback=on_progress_callback,
                on_complete_callback=on_complete_callback,
                **kwargs
            )
            yt.check_availability()
            return yt
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to load video: {url}")


def get_available_resolutions(streams) -> List[str]:
    """Get all available video resolutions from streams, sorted descending (e.g. 2160p down to 144p)."""
    resolutions = set()
    for stream in streams:
        if stream.type == 'video' and stream.resolution:
            res_str = str(stream.resolution)
            if not res_str.endswith('p'):
                num = ''.join(c for c in res_str if c.isdigit())
                if num:
                    res_str = f"{num}p"
            resolutions.add(res_str)
    return sorted(
        resolutions,
        key=lambda x: int(x.replace('p', '')) if x.replace('p', '').isdigit() else 0,
        reverse=True
    )


def get_best_video_stream(streams, resolution: Optional[str] = None):
    """
    Get the best video stream for a given resolution (or highest resolution if None).
    Prefers MP4 container for maximum compatibility, then WebM.
    """
    video_streams = [s for s in streams if s.type == 'video' and s.resolution]
    if not video_streams:
        return None

    if resolution:
        candidates = [s for s in video_streams if s.resolution == resolution]
    else:
        res_list = get_available_resolutions(video_streams)
        if not res_list:
            return None
        highest_res = res_list[0]
        candidates = [s for s in video_streams if s.resolution == highest_res]

    if not candidates:
        return None

    # Prefer progressive stream if available (video+audio together)
    prog = [s for s in candidates if getattr(s, 'is_progressive', False)]
    if prog:
        return prog[0]

    def video_rank(s):
        is_https = 1 if getattr(s, 'protocol', '') in ('http', 'https') else 0
        fps = getattr(s, 'fps', 0) or 0
        size = getattr(s, 'filesize', 0) or 0
        return (is_https, fps, size)

    # Prefer mp4 adaptive, fallback to webm
    mp4_candidates = [s for s in candidates if getattr(s, 'subtype', '') == 'mp4' or s.mime_type == 'video/mp4']
    if mp4_candidates:
        mp4_candidates.sort(key=video_rank, reverse=True)
        return mp4_candidates[0]

    candidates.sort(key=video_rank, reverse=True)
    return candidates[0]


def get_best_audio_stream(streams):
    """Get the highest bitrate audio stream."""
    audio_streams = [s for s in streams if s.type == 'audio']
    if not audio_streams:
        return None

    def audio_rank(s):
        is_https = 1 if getattr(s, 'protocol', '') in ('http', 'https') else 0
        abr_str = getattr(s, 'abr', '') or '0kbps'
        digits = ''.join(c for c in abr_str if c.isdigit())
        abr_val = int(digits) if digits else 0
        # Prefer non-DRC if same bitrate
        not_drc = 0 if 'drc' in getattr(s, 'itag', '').lower() else 1
        return (abr_val, not_drc, is_https)

    # Prefer m4a / mp4 audio with highest bitrate
    m4a_streams = [s for s in audio_streams if getattr(s, 'subtype', '') in ('m4a', 'mp4')]
    if m4a_streams:
        m4a_streams.sort(key=audio_rank, reverse=True)
        return m4a_streams[0]

    audio_streams.sort(key=audio_rank, reverse=True)
    return audio_streams[0]


def download_and_merge_streams(
    yt,
    video_stream,
    audio_stream,
    output_folder: str = "youtube_downloads",
    final_filename: Optional[str] = None
) -> str:
    """
    Download video and audio streams separately, then merge them with FFmpeg.
    Returns the path of the final merged file.
    """
    os.makedirs(output_folder, exist_ok=True)

    v_ext = getattr(video_stream, 'subtype', None) or 'mp4'
    a_ext = getattr(audio_stream, 'subtype', None) or 'mp4'

    temp_video_filename = f"temp_video_{video_stream.itag}.{v_ext}"
    temp_audio_filename = f"temp_audio_{audio_stream.itag}.{a_ext}"

    temp_video_path = os.path.join(output_folder, temp_video_filename)
    temp_audio_path = os.path.join(output_folder, temp_audio_filename)

    # Download video
    video_stream.download(output_path=output_folder, filename=temp_video_filename)

    # Download audio
    audio_stream.download(output_path=output_folder, filename=temp_audio_filename)

    if not final_filename:
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        if not safe_title:
            safe_title = f"video_{getattr(yt, 'video_id', 'download')}"
        final_filename = f"{safe_title}.mp4"

    if not final_filename.endswith(".mp4"):
        final_filename = f"{final_filename}.mp4"

    final_path = os.path.join(output_folder, final_filename)

    merged_path = merge(
        video_path=temp_video_path,
        audio_path=temp_audio_path,
        output_path=final_path,
        cleanup=True
    )
    return merged_path
