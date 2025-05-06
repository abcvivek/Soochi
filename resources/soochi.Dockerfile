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

# Make command configurable with build argument
ARG COMMAND_PATH=soochi/openai_publisher.py
ENV COMMAND_PATH=$COMMAND_PATH

# Default command (override with --build-arg COMMAND_PATH=path/to/script.py)
# Using ENV with ARG ensures the variable is available at runtime
CMD ["poetry", "run", "python", "$COMMAND_PATH"]
