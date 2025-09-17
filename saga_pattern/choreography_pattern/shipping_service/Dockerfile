FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ./choreography_pattern/shipping_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./choreography_pattern/shipping_service/app.py .

# Expose port
EXPOSE 8004
