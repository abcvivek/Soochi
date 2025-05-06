from dotenv import load_dotenv

from soochi.utils.logger import logger
from soochi.utils.config import config
from soochi.factory import create_pipeline

load_dotenv()

def main():
    try:
        pipeline = create_pipeline("gemini")
        pipeline.process(config.feeds)
        
        logger.info("Gemini processing pipeline completed successfully")
    except Exception as e:
        logger.error(f"Error in Gemini processing pipeline: {e}")
        raise

if __name__ == "__main__":
    main()
