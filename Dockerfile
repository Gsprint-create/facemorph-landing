# Use an official Python base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app
COPY . .

# Expose port
EXPOSE 8080

# Environment for Flask
ENV PORT=8080

# Command to run your app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
