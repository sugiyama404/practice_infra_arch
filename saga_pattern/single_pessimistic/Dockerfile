# Python base image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port and run application
EXPOSE 8000
