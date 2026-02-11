"""
SQLite database manager for download history and statistics.
"""
import sqlite3
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import DownloadItem, DownloadStats


class DatabaseManager:
    """Manage SQLite database for download history"""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path.home() / ".VideoDownloader" / "history.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize database schema"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Create downloads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                download_type TEXT,
                quality TEXT,
                status TEXT,
                progress REAL,
                file_path TEXT,
                file_size INTEGER,
                created_at TEXT,
                completed_at TEXT,
                tags TEXT,
                category TEXT,
                channel TEXT,
                duration TEXT,
                error TEXT,
                output_template TEXT
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON downloads(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON downloads(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel ON downloads(channel)')
        
        self.conn.commit()
        logging.info("Database initialized successfully")
    
    def add_download(self, item: DownloadItem) -> None:
        """Add or update download item in database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO downloads 
                (id, url, title, download_type, quality, status, progress, 
                 file_path, file_size, created_at, completed_at, tags, 
                 category, channel, duration, error, output_template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.id, item.url, item.title, item.download_type, item.quality,
                item.status, item.progress, item.file_path, item.file_size,
                item.created_at, item.completed_at, json.dumps(item.tags),
                item.category, item.channel, item.duration, item.error,
                item.output_template
            ))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Error adding download to database: {e}")
            self.conn.rollback()
    
    def get_history(self, limit: int = 100, offset: int = 0, 
                   status_filter: Optional[str] = None,
                   search_query: Optional[str] = None) -> List[DownloadItem]:
        """Get download history with pagination and filtering"""
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM downloads WHERE 1=1"
            params = []
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            if search_query:
                query += " AND (title LIKE ? OR channel LIKE ? OR url LIKE ?)"
                search_pattern = f"%{search_query}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            items = []
            for row in rows:
                item = self._row_to_item(row)
                items.append(item)
            
            return items
        except Exception as e:
            logging.error(f"Error getting history: {e}")
            return []
    
    def get_statistics(self) -> DownloadStats:
        """Calculate and return download statistics"""
        stats = DownloadStats()
        
        try:
            cursor = self.conn.cursor()
            
            # Total downloads
            cursor.execute("SELECT COUNT(*) FROM downloads")
            stats.total_downloads = cursor.fetchone()[0]
            
            # Successful downloads
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM downloads WHERE status = 'Completed'")
            row = cursor.fetchone()
            stats.successful_downloads = row[0]
            stats.total_size_bytes = row[1]
            
            # Failed downloads
            cursor.execute("SELECT COUNT(*) FROM downloads WHERE status = 'Failed'")
            stats.failed_downloads = cursor.fetchone()[0]
            
            # Channel statistics
            cursor.execute("SELECT channel, COUNT(*) as count FROM downloads WHERE channel IS NOT NULL GROUP BY channel")
            for row in cursor.fetchall():
                stats.channels[row[0]] = row[1]
            
            # Category statistics
            cursor.execute("SELECT category, COUNT(*) as count FROM downloads GROUP BY category")
            for row in cursor.fetchall():
                stats.categories[row[0]] = row[1]
            
        except Exception as e:
            logging.error(f"Error calculating statistics: {e}")
        
        return stats
    
    def _row_to_item(self, row: sqlite3.Row) -> DownloadItem:
        """Convert database row to DownloadItem"""
        item = DownloadItem(
            url=row['url'],
            download_type=row['download_type'] or 'video',
            quality=row['quality'] or 'Best',
            options={},
            output_template=row['output_template'] or ''
        )
        item.id = row['id']
        item.title = row['title'] or 'Unknown'
        item.status = row['status'] or 'Unknown'
        item.progress = row['progress'] or 0.0
        item.file_path = row['file_path']
        item.file_size = row['file_size']
        item.created_at = row['created_at'] or datetime.now().isoformat()
        item.completed_at = row['completed_at']
        item.error = row['error']
        
        # Parse JSON fields
        try:
            item.tags = json.loads(row['tags']) if row['tags'] else []
        except:
            item.tags = []
        
        item.category = row['category'] or 'General'
        item.channel = row['channel']
        item.duration = row['duration']
        
        return item
    
    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed")
