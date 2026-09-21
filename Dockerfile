# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Unified Server
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source, data, models, and outputs
COPY src/ ./src/
COPY data/ ./data/
COPY models/ ./models/
COPY outputs/ ./outputs/
COPY run_api.py ./

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port (default 8000 or $PORT)
ENV PORT=8000
EXPOSE 8000

CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
