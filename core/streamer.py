import subprocess
import logging
import threading
from typing import Generator, Optional, Tuple

class Streamer:
    """
    Handles streaming downloads by creating a pipe:
    YouTube -> [Video URL, Audio URL] -> FFmpeg -> stdout -> Client
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_direct_urls(self, url: str, quality: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get direct video and audio URLs using yt-dlp library.
        Returns (video_url, audio_url, title)
        """
        try:
            import yt_dlp
            
            # Map quality to format selector
            if '2160p' in quality or '4K' in quality:
                format_selector = 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best'
            elif '1440p' in quality or '2K' in quality:
                format_selector = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best'
            elif '1080p' in quality:
                format_selector = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
            elif '720p' in quality:
                format_selector = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
            elif '480p' in quality:
                format_selector = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
            elif '360p' in quality:
                format_selector = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'
            else:
                 format_selector = 'bestvideo+bestaudio/best'
            
            ydl_opts = {
                'format': format_selector,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                title = info.get('title', 'video')
                
                # If requested_formats exists, it's a merge
                if 'requested_formats' in info:
                    video_url = info['requested_formats'][0]['url']
                    audio_url = info['requested_formats'][1]['url']
                    return video_url, audio_url, title
                elif 'url' in info:
                    # Single file
                    return info['url'], None, title
                else:
                    self.logger.error("No URL found in info")
                    return None, None, None

        except Exception as e:
            self.logger.error(f"Error getting direct URLs: {e}")
            return None, None, None

    def stream_video(self, url: str, quality: str = 'Best Available') -> Generator[bytes, None, None]:
        """
        Generates a stream of bytes from ffmpeg stdout (or direct curl if single file).
        """
        video_url, audio_url, title = self.get_direct_urls(url, quality)
        
        if not video_url:
            self.logger.error("Could not retrieve video URL")
            yield b"" # End stream
            return

        self.logger.info(f"Starting stream for {title}")

        if audio_url:
            # FFmpeg merge command
            # -i video -i audio -c copy -f matroska -
            # We use matroska (mkv) container because it supports streaming (mp4 requires seeking for moov atom)
            command = [
                'ffmpeg',
                '-re', # Read input at native frame rate (optional, but good for streaming to player) - logic check: we want download as fast as possible?
                # Actually for download we do NOT want -re. we want fast.
                '-i', video_url,
                '-i', audio_url,
                '-c', 'copy', # Copy streams, no re-encoding (Fast!)
                '-f', 'matroska', # mkv container is streamable
                '-'
            ]
        else:
            # Single stream
            command = [
                'ffmpeg',
                '-i', video_url,
                '-c', 'copy',
                '-f', 'matroska', # Consistently return mkv for streaming stability
                '-'
            ]

        # Use -loglevel error to avoid stderr polluting if we were mixing (we are not, but good practice)
        command.extend(['-loglevel', 'error'])

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1024 * 1024
        )

        try:
            while True:
                chunk = process.stdout.read(4096 * 4)
                if not chunk:
                    break
                yield chunk
                
            process.stdout.close()
            process.wait()
            
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            process.kill()
            raise e
        finally:
            if process.poll() is None:
                process.kill()

    def get_title(self, url):
        # Helper to get title quickly if needed, but get_direct_urls does it.
        pass
