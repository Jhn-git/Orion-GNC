# Use an official Python runtime as a parent image
FROM python:3.9-slim as production

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .
RUN mkdir -p tests
COPY tests tests

# Make port 8765 available to the world outside this container
EXPOSE 8765

# Run main.py when the container launches
CMD ["python", "main.py"]

# ---- Test Stage ----
FROM python:3.9-slim as test

WORKDIR /app

# Set PYTHONPATH to fix module import issues
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Use cache mounts for apt and pip to speed up subsequent builds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y curl

COPY requirements.txt .
COPY requirements-test.txt .

# Use cache mount for pip
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir -r requirements-test.txt

COPY . .
RUN mkdir -p tests
COPY tests tests

# Run tests
CMD ["pytest", "tests/test_websocket_handler.py"]