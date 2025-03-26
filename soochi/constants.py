"""Constants used throughout the application."""

# Pinecone related constants
PINECONE_INDEX_NAME = "soochi-idea-index"
EMBEDDING_DIMENSION = 1536
EMBEDDING_METRIC = "cosine"
SIMILARITY_THRESHOLD = 0.75
EMBEDDING_MODEL = "text-embedding-3-small"

# Pinecone AWS configuration
AWS_REGION = "us-east-1"
AWS_CLOUD = "aws"

# File paths
BATCH_RESULTS_FILE = "data/batch_job_results.jsonl"