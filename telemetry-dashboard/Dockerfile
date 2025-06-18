# Streamlined single-stage build - no compilation needed
FROM python:3.9-slim

# Configure faster apt mirrors and install only essential runtime dependencies with cache mounts
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    echo 'deb http://deb.debian.org/debian bookworm main' > /etc/apt/sources.list && \
    echo 'deb http://security.debian.org/debian-security bookworm-security main' >> /etc/apt/sources.list && \
    apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set the working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Install dependencies with cache mounts for faster builds
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH=/home/appuser/.local/bin:$PATH
ENV FLASK_APP=server.py
ENV FLASK_ENV=production
ENV PORT=5001

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 5001

# Specify the command to run on container start
CMD ["python", "server.py"]