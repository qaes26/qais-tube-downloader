# Base image
FROM python:3.9-slim-buster

# Install LibreOffice and other dependencies
RUN apt-get update && apt-get install -y \
    libreoffice \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for LibreOffice (if needed)
ENV UNO_PATH=/usr/lib/libreoffice/program

# Copy your application code
WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run your Flask app
CMD exec gunicorn --bind 0.0.0.0:$PORT app:app