"""
Web-adapted downloader with SocketIO integration for real-time progress updates.
"""
import threading
import time
import logging
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any

import yt_dlp

from .models import DownloadItem, DownloadQueue, DownloadStatus
from .config import ConfigManager
from .database import DatabaseManager


class WebDownloader:
    """Web downloader with SocketIO event emission"""
    
    def __init__(self, config_manager: ConfigManager, database: DatabaseManager, socketio=None):
        self.config_manager = config_manager
        self.database = database
        self.socketio = socketio
        self.download_queue = DownloadQueue()
        
        # Concurrent download settings
        self.max_concurrent = config_manager.get("concurrent_downloads", 3)
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent, 
                                          thread_name_prefix="WebDownloader")
        self.active_downloads: Dict[str, DownloadItem] = {}
        self.active_downloads_lock = threading.Lock()
        
        # Control flags
        self.running = True
        self.queue_processor_thread: Optional[threading.Thread] = None
        
        # Load history from database
        self.load_history()
    
    def emit_event(self, event: str, data: Any) -> None:
        """Emit SocketIO event"""
        if self.socketio:
            try:
                self.socketio.emit(event, data)
            except Exception as e:
                logging.error(f"Error emitting event {event}: {e}")
    
    def log(self, message: str) -> None:
        """Log message and emit to clients"""
        logging.info(message)
        self.emit_event('log_message', {'message': message})
    
    def get_ydl_opts(self, item: DownloadItem) -> Dict[str, Any]:
        """Get yt-dlp options for download item"""
        ydl_opts = {
            'outtmpl': item.output_template,
            'progress_hooks': [lambda d: self.update_progress(d, item)],
            'postprocessor_hooks': [lambda d: self.postprocess_hook(d, item)],
            'quiet': True,
            'no_warnings': False,
            'ignoreerrors': True,
            'retries': 3,
        }
        
        # Audio downloads
        if item.download_type.lower() == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': item.options.get('format_type', 'mp3'),
                'preferredquality': '192',
            }]
            if item.options.get('embed_metadata'):
                ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})
            if item.options.get('embed_thumbnail'):
                ydl_opts['writethumbnail'] = True
                ydl_opts['postprocessors'].append({'key': 'EmbedThumbnailPP'})
        
        # Video downloads
        else:
            quality_format_map = {
                'Best Available': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best',
                '2160p (4K)': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best',
                '1440p (2K)': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440][ext=mp4]/bestvideo[height<=1440]+bestaudio/best[height<=1440]/best',
                '1080p (Full HD)': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                '720p (HD)': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
                '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/bestvideo[height<=480]+bestaudio/best[height<=480]/best',
                '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/bestvideo[height<=360]+bestaudio/best[height<=360]/best',
            }
            
            selected_quality = item.quality
            if selected_quality not in quality_format_map:
                match = re.search(r'(\d+p)', selected_quality)
                if match:
                    selected_quality = match.group(1)
            
            default_format = 'best[ext=mp4]/best'
            ydl_opts['format'] = quality_format_map.get(selected_quality, default_format)
            
            if item.options.get('embed_subtitles'):
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = ['en']
        
        # Playlist handling
        if item.download_type.lower() == 'playlist':
            ydl_opts['noplaylist'] = False
            ydl_opts['playlistend'] = 0
            ydl_opts['extract_flat'] = False
        else:
            ydl_opts['noplaylist'] = True
        
        return ydl_opts
    
    def update_progress(self, d: Dict[str, Any], item: DownloadItem) -> None:
        """Update download progress"""
        try:
            if d['status'] == 'downloading':
                if '_percent_str' in d:
                    clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', d['_percent_str']).strip()
                    percent_match = re.search(r'(\d+(?:\.\d+)?)', clean_percent)
                    if percent_match:
                        item.progress = float(percent_match.group(1))
                elif 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes'] > 0:
                    item.progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    item.progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                
                raw_speed = d.get('_speed_str', 'N/A')
                raw_eta = d.get('_eta_str', 'N/A')
                if isinstance(raw_speed, str):
                    item.speed = re.sub(r'\x1b\[[0-9;]*m', '', raw_speed).strip()
                if isinstance(raw_eta, str):
                    item.eta = re.sub(r'\x1b\[[0-9;]*m', '', raw_eta).strip()
                
                item.status = DownloadStatus.DOWNLOADING.value
                self.emit_event('download_progress', item.to_dict())
            
            elif d['status'] == 'finished':
                item.progress = 100
                item.status = DownloadStatus.PROCESSING.value
                if 'filename' in d:
                    item.file_path = d['filename']
                self.emit_event('download_progress', item.to_dict())
        except Exception as e:
            logging.error(f"Progress update error: {e}")
    
    def postprocess_hook(self, d: Dict[str, Any], item: DownloadItem) -> None:
        """Post-processing hook"""
        try:
            if d.get('status') == 'finished':
                final_path = d.get('filepath') or d.get('filename')
                if final_path:
                    item.file_path = final_path
                    try:
                        item.file_size = Path(final_path).stat().st_size
                    except:
                        pass
        except Exception as e:
            logging.error(f"Postprocess hook error: {e}")
    
    def download_item(self, item: DownloadItem) -> None:
        """Download a single item"""
        if item.cancelled:
            return
        
        # Add to active downloads
        with self.active_downloads_lock:
            self.active_downloads[item.id] = item
        
        try:
            item.status = DownloadStatus.DOWNLOADING.value
            self.log(f"Starting: {item.url}")
            self.emit_event('download_started', item.to_dict())
            
            ydl_opts = self.get_ydl_opts(item)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if item.cancelled:
                    self._handle_cancellation(item)
                    return
                
                try:
                    info = ydl.extract_info(item.url, download=False)
                    item.title = info.get('title', 'Unknown')
                    item.channel = info.get('uploader') or info.get('channel')
                    item.duration = info.get('duration_string')
                    item.thumbnail_url = info.get('thumbnail')
                    self.emit_event('download_progress', item.to_dict())
                except Exception as e:
                    logging.warning(f"Info extraction failed: {e}")
                    item.title = "Unknown Title"
                
                if item.cancelled:
                    self._handle_cancellation(item)
                    return
                
                ydl.download([item.url])
            
            if not item.cancelled:
                item.status = DownloadStatus.COMPLETED.value
                item.progress = 100
                self.log(f"[OK] Completed: {item.title}")
                self.download_queue.move_to_history(item)
                self.database.add_download(item)
                self.emit_event('download_completed', item.to_dict())
        
        except yt_dlp.DownloadError as e:
            self._handle_error(item, str(e))
        except Exception as e:
            self._handle_error(item, str(e))
        finally:
            # Remove from active downloads
            with self.active_downloads_lock:
                self.active_downloads.pop(item.id, None)
            
            if not item.cancelled:
                self.emit_event('queue_updated', None)
    
    def _handle_cancellation(self, item: DownloadItem) -> None:
        """Handle download cancellation"""
        item.status = DownloadStatus.CANCELLED.value
        self.log(f"Cancelled: {item.url}")
        self.download_queue.move_to_history(item)
        self.database.add_download(item)
        self.emit_event('download_cancelled', item.to_dict())
    
    def _handle_error(self, item: DownloadItem, error_msg: str) -> None:
        """Handle download error with retry logic"""
        if item.cancelled:
            self._handle_cancellation(item)
            return
        
        item.error = error_msg
        if item.retry_count < item.max_retries:
            item.retry_count += 1
            item.status = f"Retry {item.retry_count}/{item.max_retries}"
            self.log(f"[RETRY] Error, retrying {item.retry_count}/{item.max_retries}: {item.title}")
            time.sleep(min(2 ** item.retry_count, 30))
            self.download_item(item)
        else:
            item.status = DownloadStatus.FAILED.value
            self.log(f"[FAILED] {item.title} - {error_msg}")
            self.download_queue.move_to_history(item)
            self.database.add_download(item)
            self.emit_event('download_failed', item.to_dict())
    
    def queue_processor(self) -> None:
        """Process download queue with concurrent downloads"""
        while self.running:
            try:
                # Check how many downloads are active
                with self.active_downloads_lock:
                    active_count = len(self.active_downloads)
                
                # Start new downloads if under limit
                while active_count < self.max_concurrent:
                    item = self.download_queue.get_next()
                    if item:
                        # Submit to thread pool
                        self.executor.submit(self.download_item, item)
                        active_count += 1
                    else:
                        break
                
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"Queue processor error: {e}")
                time.sleep(1)
    
    def start_queue_processor(self) -> None:
        """Start the queue processor"""
        if self.queue_processor_thread is None or not self.queue_processor_thread.is_alive():
            self.queue_processor_thread = threading.Thread(
                target=self.queue_processor, 
                daemon=True, 
                name="QueueProcessor"
            )
            self.queue_processor_thread.start()
            self.log("Queue processor started")
    
    def add_download(self, url: str, download_type: str, quality: str, options: Dict[str, Any]) -> DownloadItem:
        """Add new download to queue"""
        download_path = Path(self.config_manager.get("download_path", str(Path.home() / "Downloads")))
        download_path.mkdir(parents=True, exist_ok=True)
        
        output_template = str(download_path / "%(title)s.%(ext)s")
        
        item = DownloadItem(
            url=url,
            download_type=download_type,
            quality=quality,
            options=options,
            output_template=output_template
        )
        
        self.download_queue.add(item)
        self.emit_event('queue_updated', None)
        self.log(f"Added to queue: {url}")
        
        return item
    
    def cancel_download(self, item_id: str) -> bool:
        """Cancel a download"""
        item = self.download_queue.get_by_id(item_id)
        if item:
            item.cancelled = True
            self.log(f"Cancelling: {item_id}")
            return True
        return False
    
    def load_history(self) -> None:
        """Load history from database"""
        try:
            items = self.database.get_history(limit=1000)
            with self.download_queue.lock:
                self.download_queue.history = items
            self.log(f"Loaded {len(items)} history items from database")
        except Exception as e:
            logging.error(f"Error loading history: {e}")
    
    def shutdown(self) -> None:
        """Shutdown downloader gracefully"""
        self.running = False
        self.executor.shutdown(wait=True)
        self.database.close()
        self.log("Downloader shutdown complete")
