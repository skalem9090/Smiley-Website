FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Node.js and npm
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY package*.json ./
COPY requirements.txt ./

# Install Node.js dependencies
RUN npm install

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run migrations and start application
CMD python -m flask db upgrade && python start_production.py
