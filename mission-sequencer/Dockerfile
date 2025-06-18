# Use the official Python image.
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser
USER appuser

# Copy the requirements file and install dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --user --timeout=100 -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Expose the port the app runs on
EXPOSE 5001

# Default command to run the Gunicorn server for the Flask app.
# To run the Celery worker, override the command when running the container:
# docker run <image_name> celery -A worker worker --loglevel=info
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "main:app"]