# Soochi AI Content Aggregation Project

## Project Overview
Soochi is an AI-powered content aggregation and processing system designed to collect, process, and analyze content from various sources, primarily using Google Alerts RSS feeds. The system extracts ideas from content, stores them in Pinecone vector database, and syncs them with Notion for easy access and management.

## Key Features
- RSS feed aggregation and content extraction
- AI-powered idea extraction using OpenAI and Google Gemini models
- Vector similarity search with Pinecone
- Notion integration for idea management
- Batch processing support for OpenAI

## Architecture
- **Pinecone**: Source of truth for ideas and similarity detection
- **Notion**: User-friendly interface for viewing and managing ideas
- **MongoDB**: Storage for URL metadata and batch job tracking

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/abcvivek/soochi.git
   cd soochi
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory using the `.env.example` file as a reference.

## Available Environments

- **dev**: Development environment (default)
- **prod**: Production environment

## Switching Environments

To switch between environments, set the `SOOCHI_ENV` environment variable before running your application:

```bash
# For development (default)
export SOOCHI_ENV=dev
python -m soochi.main

# For production
export SOOCHI_ENV=prod
python -m soochi.main
```

## Usage

### Processing Content with OpenAI
```bash
python -m soochi.main
```

### Checking Batch Status (OpenAI)
```bash
python -m soochi.fetch_batch_status
```

### Processing Content with Google Gemini
```bash
python -m soochi.gemini_processor
```


## Configuration
- **feeds.yaml**: Configure your RSS feeds and their enabled/disabled status
- **.env**: Set environment variables for API keys and logging levels
- **.env.prod**: Production-specific environment variables

## Testing
Run the tests using pytest:
```bash
pytest
```

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.
