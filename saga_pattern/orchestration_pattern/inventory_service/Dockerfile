FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ./orchestration_pattern/inventory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include shared modules
ENV PYTHONPATH=/app

# Copy application code
COPY ./orchestration_pattern/inventory_service/app.py .

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "app.py"]
