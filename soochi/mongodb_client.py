from datetime import datetime, timedelta
from pymongo import MongoClient
from soochi.config import config
from soochi.logger import logger

class MongoDBClient:
    def __init__(self):
        self.mongo_uri = config.mongo_uri
        self.client = MongoClient(self.mongo_uri)

        self.db = self.client[config.mongo_db_name]
        self.seen_urls = self.db.seen_urls
        self.batch_jobs = self.db.batch_jobs
        self.create_indexes()

    def create_indexes(self):
        """Create necessary indexes for collections."""
        # Create unique index on url_hash for seen_urls collection
        self.seen_urls.create_index("url_hash", unique=True)
        
        # Create index on created_at for seen_urls collection
        self.seen_urls.create_index("created_at")
        
        # Create unique index on batch_id for batch_jobs collection
        self.batch_jobs.create_index("batch_id", unique=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def fetch_seen_urls_hash(self):
        """Fetch all seen URL hashes from the database."""
        cursor = self.seen_urls.find({}, {"url_hash": 1, "_id": 0})
        return [doc["url_hash"] for doc in cursor]

    def bulk_insert_seen_urls(self, url_hashes):
        """Insert multiple URL hashes into the database."""
        if not url_hashes:
            return
            
        documents = [
            {"url_hash": url_hash, "created_at": datetime.utcnow()} 
            for url_hash in url_hashes
        ]
        
        try:
            # Use ordered=False to continue inserting even if some documents fail
            result = self.seen_urls.insert_many(documents, ordered=False)
            logger.info(f"Inserted {len(result.inserted_ids)} URL hashes")
        except Exception as e:
            # Some documents might have been inserted even if there was an error
            logger.error(f"Error during bulk insert: {e}")

    def bulk_delete_seen_urls(self):
        """Delete seen URLs older than 7 days."""
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        result = self.seen_urls.delete_many({"created_at": {"$lt": cutoff_date}})
        logger.info(f"Deleted {result.deleted_count} old URL hashes")

    def create_batch_job(self, batch_id):
        """Create a new batch job record."""
        self.batch_jobs.insert_one({
            "batch_id": batch_id,
            "created_at": datetime.utcnow()
        })
        logger.info(f"Created batch job with ID: {batch_id}")

    def get_latest_batch_id(self):
        """Fetch the latest batch ID from the database."""
        latest_batch = self.batch_jobs.find_one(
            sort=[("created_at", -1)]
        )
        
        if latest_batch:
            return latest_batch["batch_id"]
        return None

    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
