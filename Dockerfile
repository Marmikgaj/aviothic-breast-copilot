# ============================================================================
# Aviothic Breast Cancer Report Copilot — Dockerfile
# Multi-stage build for minimal production image
# ============================================================================

# --------------- Stage 1: Builder ---------------
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ ./src/

# --------------- Stage 2: Runtime ---------------
FROM python:3.12-slim AS runtime

# Install system dependencies for OCR and PDF handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Security: run as non-root user
RUN groupadd --gid 1001 aviothic \
    && useradd --uid 1001 --gid aviothic --shell /bin/bash --create-home aviothic

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Create uploads directory with correct permissions
RUN mkdir -p /app/uploads && chown -R aviothic:aviothic /app

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER aviothic

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
