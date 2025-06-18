# Integration test runner Dockerfile
FROM python:3.9-slim

# Install Docker CLI for container management during tests
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy test files
COPY . .

# Copy the entire project for integration testing
COPY ../../ ./project/

# Set environment variables
ENV PYTHONPATH=/app/project
ENV DOCKER_HOST=unix:///var/run/docker.sock

# Default command runs the integration tests
CMD ["pytest", "-v", "--tb=short", "test_system_integration.py"]