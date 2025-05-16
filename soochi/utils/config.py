import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load appropriate .env file based on environment
        self.env = os.getenv("SOOCHI_ENV", "dev")
        self._load_env_file()

        self.test_feeds_file = os.getenv("TEST_FEEDS_FILE", "feeds.yaml")
        
        # Project paths
        self.project_root = Path(__file__).parent.parent.parent
        self.feeds_file = self.project_root / self.test_feeds_file

        # OpenAI settings
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")

        # Google AI settings
        self.google_ai_api_key = os.getenv("GOOGLE_AI_API_KEY")
        self.google_ai_model = os.getenv("GOOGLE_AI_MODEL", "gemini-2.0-flash")

        # Pinecone settings
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")

        # Notion settings
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID")
        
        # MongoDB settings
        self.mongo_uri = os.getenv("MONGO_URI")
        self.mongo_db_name = os.getenv("MONGO_DB_NAME")

        # Logging settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        self.urls_to_test = int(os.getenv("URLS_TO_TEST", -1))

        # Load feeds from YAML
        self.feeds = self._load_feeds()
        
    def _load_env_file(self):
        """Load the appropriate .env file based on the environment."""
        env_file = ".env"
        
        # Check for environment-specific .env file
        if self.env != "dev":
            env_specific_file = f".env.{self.env}"
            if Path(env_specific_file).exists():
                env_file = env_specific_file
                print(f"Loading environment from {env_file}")
            else:
                print(f"Warning: {env_specific_file} not found, falling back to .env")
        
        # Load the environment file
        load_dotenv(env_file)

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
