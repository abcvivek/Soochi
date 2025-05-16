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
- **Pinecone**: Primary source of truth for ideas and similarity detection
- **Notion**: User-friendly interface for viewing and managing ideas, kept in sync with Pinecone
- **MongoDB**: Storage for URL metadata and batch job tracking

### Data Flow
1. Content is collected from RSS feeds
2. Ideas are extracted using AI models (OpenAI or Google Gemini)
3. Ideas are stored in Pinecone for vector similarity search
4. Ideas are simultaneously added to Notion for user-friendly management
5. Pinecone is used for similarity detection to avoid duplicate ideas

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

# For production
export SOOCHI_ENV=prod
```

## Usage

### Processing Content with OpenAI
```bash
python -m soochi.openai_publisher
```

### Processing OpenAI Batch Results
```bash
python -m soochi.openai_subscriber
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
