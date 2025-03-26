# Use official lightweight Python image
FROM --platform=linux/amd64 python:3.12.9-slim

# Set environment variables
ENV POETRY_VERSION=2.0.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PATH="/app/.venv/bin:$PATH"

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Set working directory
WORKDIR /app

# Copy only essential files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-root

# Copy all source code
COPY . .

# Install the project itself
RUN poetry install

# Default command (override in Cloud Run Job)
CMD ["poetry", "run", "python", "soochi/fetch_batch_status.py"]
