import subprocess
import logging
import threading
from typing import Generator, Optional, Tuple
import os
import time
import uuid
import shutil
from pathlib import Path

class Streamer:
    """
    Handles streaming downloads using a disk buffer for reliability.
    yt-dlp -> Temp File -> Client
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = Path("temp_streams")
        self.temp_dir.mkdir(exist_ok=True)

    def get_direct_urls(self, url: str, quality: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Legacy method kept for compatibility.
        """
        return None, None, "video"

    def stream_video(self, url: str, quality: str = 'Best Available') -> Generator[bytes, None, None]:
        """
        Downloads to a temp file and yields its content as it grows.
        """
        # Unique ID for this stream
        stream_id = str(uuid.uuid4())
        temp_file = self.temp_dir / f"{stream_id}.mkv"
        
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
            '-o', str(temp_file),
            '--no-part',        # Write directly to file (no .part) so we can read it immediately
            '--quiet',          # Suppress progress output
            '--no-warnings',    # Suppress warnings
            '--no-playlist',    # Single video only
            '--force-ipv4',     # Force IPv4
            '--merge-output-format', 'mkv', # Ensure container is mkv
            url
        ]
        
        self.logger.info(f"Starting buffered stream for: {url} -> {temp_file}")
        
        # Start download in background
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a brief moment for file to be created
        start_time = time.time()
        while not temp_file.exists():
            if time.time() - start_time > 10:
                # Timeout waiting for file
                process.kill()
                stderr = process.stderr.read().decode('utf-8', errors='ignore') if process.stderr else ""
                self.logger.error(f"Timeout waiting for temp file: {stderr}")
                raise Exception(f"Stream failed to start (Timeout): {stderr}")
            if process.poll() is not None:
                # Process died before creating file
                stderr = process.stderr.read().decode('utf-8', errors='ignore') if process.stderr else ""
                self.logger.error(f"Download process died: {stderr}")
                raise Exception(f"Stream failed to start (Process died): {stderr}")
            time.sleep(0.1)

        # File exists, start reading
        try:
            with open(temp_file, 'rb') as f:
                while True:
                    # Check if process is still running
                    retcode = process.poll()
                    
                    # Read available data
                    chunk = f.read(8192)
                    if chunk:
                        yield chunk
                    else:
                        # No data read. 
                        if retcode is not None:
                            # Process finished. verified by poll(). 
                            # Check if we are really at EOF or just faster than writer?
                            # If process finished, and we read empty chunk, we are done.
                            # But double check stderr if it failed?
                            if retcode != 0:
                                stderr = process.stderr.read().decode('utf-8', errors='ignore') if process.stderr else ""
                                self.logger.error(f"Stream finished with error {retcode}: {stderr}")
                                # If we already sent data, we can't raise exception to client easily (headers sent).
                                # But we can stop yielding.
                            break
                        else:
                            # Process still running, just waiting for data
                            time.sleep(0.1)
                            
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            raise e
        finally:
            # Cleanup
            if process.poll() is None:
                process.kill()
            
            # Use a separate thread or delayed cleanup because file might be locked?
            # On Windows, we can't delete open file. 'f' is closed by with block exit.
            try:
                if temp_file.exists():
                    os.remove(temp_file)
            except Exception as cleanup_error:
                self.logger.error(f"Failed to delete temp file {temp_file}: {cleanup_error}")
