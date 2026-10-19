FROM python:3.11-slim

LABEL description="RAG MCP service: knowledge base search and generation"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser

ENV RAG_PORT=18743
EXPOSE 18743

# Only meaningful in http mode (RAG_TRANSPORT=http), stdio mode has no port
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os,sys,urllib.request; sys.exit(0) if os.getenv('RAG_TRANSPORT')!='http' else urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('RAG_PORT'), timeout=5)"

# Start service
CMD ["python", "-m", "src.main"]
