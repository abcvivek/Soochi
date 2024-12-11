import os
import yaml
from pathlib import Path

class Config:
    def __init__(self):
        # Project paths
        self.project_root = Path(__file__).parent.parent
        self.feeds_file = self.project_root / "feeds.yaml"

        # OpenAI settings
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Database settings
        self.db_file = self.project_root / "soochi.db"
        self.db_timeout = int(os.getenv("DB_TIMEOUT", "30"))

        # Logging settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Load feeds from YAML
        self.feeds = self._load_feeds()

    def _load_feeds(self):
        """Load and parse feeds from YAML file."""
        if not self.feeds_file.exists():
            return {}
        
        with open(self.feeds_file, 'r') as file:
            feeds_config = yaml.safe_load(file)
            return {
                feed['name']: feed['url'] 
                for feed in feeds_config.get('feeds', [])
                if feed.get('enabled', True)
            }

# Create a global config instance
config = Config()
