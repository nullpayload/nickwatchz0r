# ====================================================================
# STAGE 1: BUILDER - Handles installation and cleanup
# ====================================================================
FROM debian:bookworm-slim AS builder

# 1. Install System Dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        build-essential libssl-dev libffi-dev zlib1g-dev ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the virtual environment path and pip cache directory
ENV VENV_PATH=/app/.venv
ENV PATH="$VENV_PATH/bin:$PATH"
ENV PIP_CACHE_DIR=/tmp/pip_cache

# 2. Setup VENV and Install Dependencies
WORKDIR /tmp/build
COPY requirements.txt .

# Create VENV and install application dependencies - Simplified and corrected
# This command automatically installs pip/setuptools/wheel into the VENV
# and then runs the install from requirements.txt.
RUN python3 -m venv $VENV_PATH && \
    pip install --no-cache-dir -r requirements.txt

# 3. VULNERABILITY PATCH (Crucial: Upgrade setuptools AFTER dependencies)
RUN pip install --no-cache-dir --upgrade setuptools pip wheel


# ====================================================================
# STAGE 2: RUNTIME - Minimal image for execution
# ====================================================================
FROM debian:bookworm-slim AS final

# This installs the base python interpreter required by the VENV symlinks.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv && \ 
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 1. Create Non-Root User (Must happen in the final stage)
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set working directory
WORKDIR /app

# 2. Copy ONLY the VENV and Source Code from the builder stage
# This step leaves behind all build tools, caches, and old package metadata.
COPY --from=builder /app/.venv /app/.venv

# Copy source code and ensure data volume exists

COPY src/ /app/src/
RUN mkdir -p /app/data
COPY app/data/ /app/data/

# 3. Final Security and Command
# Change ownership to the non-root user
RUN chown -R appuser:appgroup /app


# Switch to the non-root user
USER appuser

# Command to run the bot
CMD ["/app/.venv/bin/python3", "src/nickwatchz0r.py"]