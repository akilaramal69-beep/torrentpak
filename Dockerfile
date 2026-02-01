# --- Frontend Build Stage ---
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Runtime Stage ---
FROM python:3.11-slim
WORKDIR /app

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend assets from builder
COPY --from=frontend-builder /app/dist ./dist

# Copy backend code
COPY app.py .

# Expose port
EXPOSE 5000

# Start command: 4 workers, 2 threads each, 30s timeout, keepalive 5s
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "30", "--keep-alive", "5", "app:app"]
