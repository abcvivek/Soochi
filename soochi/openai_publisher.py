"""
Main entry point for Soochi's OpenAI batch processing pipeline.
"""

from dotenv import load_dotenv

from soochi.utils.logger import logger
from soochi.utils.config import config
from soochi.factory import create_pipeline

load_dotenv()

def main():
    """
    Initialize and run the OpenAI batch processing pipeline.
    """
    try:
        pipeline = create_pipeline("openai")
        pipeline.process(config.feeds)
        
        logger.info("OpenAI batch processing pipeline completed successfully")
    except Exception as e:
        logger.error(f"Error in OpenAI batch processing pipeline: {e}")
        raise

if __name__ == "__main__":
    main()
