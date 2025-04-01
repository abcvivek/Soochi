# Soochi AI Content Aggregation Project

## Project Overview
Soochi is an AI-powered content aggregation and processing system designed to collect, process, and analyze content from various sources, primarily using Google Alerts RSS feeds.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/soochi.git
   cd soochi
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add your OpenAI API key and other configurations:
   ```env
   OPENAI_API_KEY=your_api_key_here
   LOG_LEVEL=INFO
   DB_TIMEOUT=30
   ```


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
To run the application, use the following command:
```bash
python soochi/main.py
```

## Configuration
- **feeds.yaml**: Configure your RSS feeds and their enabled/disabled status.
- **.env**: Set environment variables for API keys and logging levels.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.
