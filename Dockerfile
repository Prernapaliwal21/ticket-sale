# Use Python 3.12 slim image
FROM python:3.12.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by Pillow and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libtiff5-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    tcl8.6-dev \
    tk8.6-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --prefer-binary -r requirements.txt

# Expose port (Flask default)
EXPOSE 5000

# Command to run your app
CMD ["python", "app.py"]
