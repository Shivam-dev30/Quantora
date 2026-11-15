# Multi-Stage Production Dockerfile

# Stage 1: Build React Frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and default configs
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create runtime directories
RUN mkdir -p logs data

# Expose HTTP & WebSocket port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start production application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
