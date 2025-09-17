FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ./choreography_pattern/inventory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ./shared /app/shared

# Copy application code
COPY ./choreography_pattern/inventory_service/app.py .

# Expose port
EXPOSE 8002
