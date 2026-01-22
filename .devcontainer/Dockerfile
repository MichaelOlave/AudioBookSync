# Base image with Python 3.10
FROM mcr.microsoft.com/devcontainers/python:3.10

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Install any additional system dependencies here (if needed)
# e.g., RUN apt-get install -y libxml2-dev

# Upgrade pip
RUN pip install --upgrade pip

# Set up working directory
WORKDIR /workspace

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]