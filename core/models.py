"""
Data models for the VideoDownloader application.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import threading
import uuid


class DownloadStatus(Enum):
    """Download status enumeration"""
    QUEUED = "Queued"
    DOWNLOADING = "Downloading"
    PROCESSING = "Processing"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class DownloadItem:
    """Represents a single download item with enhanced tracking"""
    
    def __init__(self, url: str, download_type: str, quality: str, 
                 options: Dict[str, Any], output_template: str):
        self.id = str(uuid.uuid4())
        self.url = url
        self.download_type = download_type
        self.quality = quality
        self.options = options
        self.output_template = output_template
        
        # Status tracking
        self.status = DownloadStatus.QUEUED.value
        self.progress = 0.0
        self.speed = "N/A"
        self.eta = "N/A"
        self.title = "Loading..."
        self.error: Optional[str] = None
        
        # Retry mechanism
        self.retry_count = 0
        self.max_retries = 3
        
        # Control flags
        self.paused = False
        self.cancelled = False
        
        # Metadata
        self.file_path: Optional[str] = None
        self.file_size: Optional[int] = None
        self.created_at = datetime.now().isoformat()
        self.completed_at: Optional[str] = None
        
        # New features
        self.tags: List[str] = []
        self.category = "General"
        self.channel: Optional[str] = None
        self.duration: Optional[str] = None
        self.thumbnail_url: Optional[str] = None
        self.direct_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'download_type': self.download_type,
            'quality': self.quality,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'tags': self.tags,
            'category': self.category,
            'channel': self.channel,
            'duration': self.duration,
            'direct_url': self.direct_url,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadItem':
        """Create DownloadItem from dictionary"""
        item = cls(
            url=data['url'],
            download_type=data['download_type'],
            quality=data['quality'],
            options={},
            output_template=data.get('output_template', '')
        )
        item.id = data.get('id', item.id)
        item.title = data.get('title', 'Unknown')
        item.status = data.get('status', DownloadStatus.QUEUED.value)
        item.progress = data.get('progress', 0.0)
        item.file_path = data.get('file_path')
        item.file_size = data.get('file_size')
        item.created_at = data.get('created_at', item.created_at)
        item.completed_at = data.get('completed_at')
        item.tags = data.get('tags', [])
        item.category = data.get('category', 'General')
        item.channel = data.get('channel')
        item.duration = data.get('duration')
        item.direct_url = data.get('direct_url')
        item.error = data.get('error')
        return item


class DownloadQueue:
    """Manages the download queue with enhanced functionality"""
    
    def __init__(self):
        self.items: List[DownloadItem] = []
        self.history: List[DownloadItem] = []
        self.lock = threading.Lock()
    
    def add(self, item: DownloadItem) -> None:
        """Add item to queue"""
        with self.lock:
            self.items.append(item)
    
    def remove(self, item: DownloadItem) -> None:
        """Remove item from queue"""
        with self.lock:
            if item in self.items:
                self.items.remove(item)
    
    def get_next(self) -> Optional[DownloadItem]:
        """Get next queued item that's not paused or cancelled"""
        with self.lock:
            for item in self.items:
                if item.status == DownloadStatus.QUEUED.value and not item.paused and not item.cancelled:
                    return item
        return None
    
    def move_to_history(self, item: DownloadItem) -> None:
        """Move item from queue to history"""
        with self.lock:
            if item in self.items:
                self.items.remove(item)
            item.completed_at = datetime.now().isoformat()
            self.history.append(item)
            
            # Limit history size in memory (database will store all)
            if len(self.history) > 1000:
                self.history = self.history[-1000:]
    
    def get_by_id(self, item_id: str) -> Optional[DownloadItem]:
        """Find item by ID in queue or history"""
        with self.lock:
            for item in self.items:
                if item.id == item_id:
                    return item
            for item in self.history:
                if item.id == item_id:
                    return item
        return None
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all queue items as dictionaries"""
        with self.lock:
            return [item.to_dict() for item in self.items]
    
    def clear_completed(self) -> int:
        """Remove completed items from queue, return count"""
        with self.lock:
            completed = [item for item in self.items 
                        if item.status in [DownloadStatus.COMPLETED.value, 
                                          DownloadStatus.FAILED.value,
                                          DownloadStatus.CANCELLED.value]]
            for item in completed:
                self.items.remove(item)
            return len(completed)


class DownloadStats:
    """Track download statistics"""
    
    def __init__(self):
        self.total_downloads = 0
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.total_size_bytes = 0
        self.total_duration = 0.0  # seconds
        self.channels: Dict[str, int] = {}  # channel -> count
        self.categories: Dict[str, int] = {}  # category -> count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_downloads': self.total_downloads,
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'total_size_bytes': self.total_size_bytes,
            'total_size_formatted': self.get_total_size_formatted(),
            'success_rate': self.get_success_rate(),
            'top_channel': self.get_most_downloaded_channel(),
            'channels': self.channels,
            'categories': self.categories
        }
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_downloads == 0:
            return 0.0
        return (self.successful_downloads / self.total_downloads) * 100
    
    def get_most_downloaded_channel(self) -> Optional[str]:
        """Get channel with most downloads"""
        if not self.channels:
            return None
        return max(self.channels.items(), key=lambda x: x[1])[0]
    
    def get_total_size_formatted(self) -> str:
        """Get total size in human-readable format"""
        size = self.total_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
