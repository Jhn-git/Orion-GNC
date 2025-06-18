# Streamlined single-stage build with optimized AI dependencies
FROM python:3.9-slim as production

# Configure faster apt mirrors and install only essential runtime dependencies
RUN echo 'deb http://deb.debian.org/debian bookworm main' > /etc/apt/sources.list && \
    echo 'deb http://security.debian.org/debian-security bookworm-security main' >> /etc/apt/sources.list && \
    apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with proper ownership
COPY --chown=appuser:appuser server.py .
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser logging_config.py .


# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=4

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 5000

# Specify the command to run on container start
CMD gunicorn --workers $GUNICORN_WORKERS --threads $GUNICORN_THREADS --bind "0.0.0.0:5000" "server:app"

# --- Test Stage ---
FROM python:3.9-slim as tester

WORKDIR /app
ENV PYTHONPATH=/app

# Copy requirements and install test dependencies
COPY requirements.txt .
COPY requirements-test.txt .
RUN for i in 1 2 3; do pip install --no-cache-dir --timeout=100 -r requirements.txt -r requirements-test.txt && break || sleep 5; done

# Copy application and test code
COPY . .
COPY tests/ ./tests/

# Run tests
CMD python tests/mock_redis_entrypoint.py "gunicorn --workers $GUNICORN_WORKERS --threads $GUNICORN_THREADS --bind 0.0.0.0:5000 server:app" & \
    sleep 10 && \
    pytest tests