FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy main backend code first (needed for imports)
# The observability backend code expects to find "backend" directory at parent level
COPY backend ./backend

# Copy observability backend requirements and install
COPY observability/backend/requirements.txt ./observability-requirements.txt
RUN pip install --no-cache-dir -r observability-requirements.txt

# Copy observability backend application code
COPY observability/backend/app ./observability/app

# Set working directory to observability backend
WORKDIR /app/observability

# Expose port
EXPOSE 8001

# Run the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

