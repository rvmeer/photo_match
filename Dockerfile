# Multi-stage build voor optimale image grootte

# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY public ./public
COPY src ./src

# Build production bundle
RUN npm run build

# Stage 2: Python backend met FastAPI
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies voor OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY orgineel.JPG .

# Copy built React app from frontend-builder stage
COPY --from=frontend-builder /app/build ./build

# Create uploads directory
RUN mkdir -p uploads

# Expose port 80 for HTTP (443 voor HTTPS wordt gehandeld door AWS ALB)
EXPOSE 80

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application on port 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
