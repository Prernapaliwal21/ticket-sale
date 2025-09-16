# Use a Python version that works locally
FROM python:3.12.9-slim

# Install system dependencies needed for Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev libtiff5-dev libfreetype6-dev \
    liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Upgrade pip/build tools
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --prefer-binary -r requirements.txt

# Command to run your app
CMD ["python", "app.py"]
