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

# Start command
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
