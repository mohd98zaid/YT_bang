import subprocess
import logging
import threading
from typing import Generator, Optional, Tuple

class Streamer:
    """
    Handles streaming downloads by piping yt-dlp output directly to the client.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_direct_urls(self, url: str, quality: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Legacy method kept for compatibility, but just returns title now if possible.
        """
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return "url_placeholder", "url_placeholder", info.get('title', 'video')
        except:
             return None, None, "video"

    def stream_video(self, url: str, quality: str = 'Best Available') -> Generator[bytes, None, None]:
        """
        Generates a stream of bytes from yt-dlp stdout.
        """
        # Command to stream to stdout
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

        command = [
            'yt-dlp',
            '--format', format_selector,
            '-o', '-',          # Output to stdout
            '--no-part',        # No .part files
            '--quiet',          # Suppress progress output
            '--no-warnings',    # Suppress warnings
            '--no-playlist',    # Single video only
            '--force-ipv4',     # Force IPv4 to avoid IPv6 blocks
            url
        ]
        
        self.logger.info(f"Starting direct yt-dlp piping for: {url}")
        
        # Start the process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1024 * 1024
        )

        try:
            # Read stdout chunk by chunk
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                yield chunk
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code != 0:
                stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                self.logger.error(f"Stream process failed with code {return_code}: {stderr_output}")
                
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            process.kill()
            raise e
        finally:
            if process.poll() is None:
                process.kill()
