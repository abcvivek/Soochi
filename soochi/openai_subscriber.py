"""
Batch status checker for Soochi - fetches and processes batch job results from OpenAI.
"""

from dotenv import load_dotenv

from soochi.utils.logger import logger
from soochi.utils.mongodb_client import MongoDBClient
from soochi.factory import create_pipeline


load_dotenv()

def main():
    """
    Main function to fetch and process OpenAI batch job results.
    """
    try:
        pipeline = create_pipeline("openai")
        
        # Get the latest batch ID
        with MongoDBClient() as mongodb_client:
            batch_id = mongodb_client.get_latest_batch_id()
            
        if not batch_id:
            logger.warning("No batch jobs found")
            return
        
        pipeline.process_batch_results(batch_id)
        
        logger.info(f"Successfully completed batch processing for {batch_id}")
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        raise

if __name__ == "__main__":
    main()
