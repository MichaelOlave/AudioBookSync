# Use the Python Dev Containers image
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system-level dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python utilities globally
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
    black \
    flake8 \
    mypy \
    pytest \
    pre-commit \
    python-dotenv \
    tqdm
