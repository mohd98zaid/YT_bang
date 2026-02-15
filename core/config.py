import json
import logging
import os
from pathlib import Path

class ConfigManager:
    """Manage application configuration"""
    def __init__(self):
        self.app_data_dir = Path.home() / ".VideoDownloader"
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.app_data_dir / "config.json"
        
        self.default_config = {
            "download_path": "/tmp" if os.environ.get('VERCEL') else str(Path.home() / "Downloads"),
            "concurrent_downloads": 3,
            "max_retries": 3,
            "embed_thumbnail": True,
            "embed_metadata": True,
            "embed_subtitles": False,
        }
        self.config = self.load_config()

    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    merged = self.default_config.copy()
                    merged.update(config)
                    return merged
            return self.default_config.copy()
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
