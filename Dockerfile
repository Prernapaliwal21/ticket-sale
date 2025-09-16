# Dockerfile
FROM python:3.12.9-slim

WORKDIR /app

# Install system dependencies for Pillow & WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev zlib1g-dev \
    libcairo2 libcairo2-dev \
    libpango-1.0-0 libpango1.0-dev \
    libgdk-pixbuf2.0-0 libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Expose port
ENV PORT 5000

# Start the app
CMD ["python", "app.py"]
