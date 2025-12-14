# Stage 1: Build & Setup (Base Image: Debian Bookworm Slim)
FROM debian:bookworm-slim AS base

# Set the working directory for the application
WORKDIR /app

# 1. Install Python 3.11 and necessary build tools
# We install python3 and python3-pip directly from Debian repositories.
# The 'build-essential' and 'libssl-dev' packages are needed to correctly compile 
# some Python libraries (like those used by 'requests' or 'irc3') securely.
# We then clean up apt cache to keep the final image size minimal.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        libssl-dev \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python Dependencies 
COPY requirements.txt .

# Use pip to install dependencies globally
RUN pip install --no-cache-dir -r requirements.txt

# Add Non-Root User 
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy the source code (Assuming script is at 'src/nickwatchz0r.py')
COPY src/ /app/src/

# Change ownership of the /app directory (and all files) to the new non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user for running the application
USER appuser

# Command to run the bot when the container starts
CMD ["python3", "src/nickwatchz0r.py"]