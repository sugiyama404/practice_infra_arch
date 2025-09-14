FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ./orchestration_pattern/order_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ./shared /app/shared

# Set PYTHONPATH to include shared modules
ENV PYTHONPATH=/app

# Copy application code
COPY ./orchestration_pattern/order_service/app.py .

# Expose port
EXPOSE 8001

# Run the application
CMD ["python", "app.py"]
