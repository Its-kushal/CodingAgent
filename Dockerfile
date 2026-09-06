FROM python:3.12-slim

# Install system dependencies (git, ripgrep for fast code search, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ripgrep \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user
RUN useradd -m -s /bin/bash agentuser

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set ownership
RUN chown -R agentuser:agentuser /app

USER agentuser

CMD ["tail", "-f", "/dev/null"]
