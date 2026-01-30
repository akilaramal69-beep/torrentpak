FROM python:3.11-slim as backend

# Install node for frontend build
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs

WORKDIR /app

# Copy and install backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install frontend dependencies
COPY package*.json ./
RUN npm install

# Copy project files
COPY . .

# Build frontend
RUN npm run build

# Expose port
EXPOSE 5000

# Start command
CMD ["python", "app.py"]
