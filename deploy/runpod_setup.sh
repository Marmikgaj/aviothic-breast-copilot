#!/usr/bin/env bash
# ============================================================================
# Aviothic Breast Cancer Report Copilot — RunPod / Vast.ai Deployment Script
# ============================================================================
# Automated cloud provisioning for dedicated GPU instances (A100 / RTX 4090 / L40S)
# Per PRD §6 and Architecture.md
# ============================================================================

set -euo pipefail

echo "================================================================="
echo "  Aviothic Breast Cancer Report Copilot — GPU Pod Provisioning   "
echo "================================================================="

# 1. Environment & CUDA Diagnostics
echo "==> [1/6] Checking GPU hardware and NVIDIA drivers..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
    echo "WARNING: nvidia-smi not found. Continuing in CPU-only/fallback mode."
fi

# 2. System Dependencies for Clinical OCR & PDF processing
echo "==> [2/6] Installing system dependencies (Tesseract OCR, Poppler)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq \
    curl \
    git \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    build-essential > /dev/null

# 3. Install Astral uv for high-speed Python package management
echo "==> [3/6] Setting up Python 3.12 environment via uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv --version

# 4. Install Application Dependencies
echo "==> [4/6] Installing Python dependencies..."
cd "$(dirname "$0")/.."
uv sync --frozen --no-dev

# 5. Launch vLLM Inference Engine (Background Daemon)
echo "==> [5/6] Starting vLLM model server..."
MODEL_ID="${AVIOTHIC_MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"
VLLM_PORT="${VLLM_PORT:-8001}"

if command -v vllm &> /dev/null; then
    echo "Starting vLLM with model: ${MODEL_ID} on port ${VLLM_PORT}..."
    nohup vllm serve "${MODEL_ID}" \
        --port "${VLLM_PORT}" \
        --gpu-memory-utilization 0.85 \
        --max-model-len 4096 \
        --trust-remote-code \
        > /var/log/vllm.log 2>&1 &
    echo "vLLM launched with PID $!. Logs: /var/log/vllm.log"
else
    echo "vLLM CLI not in path; API server will utilize built-in deterministic fallback engine."
fi

# 6. Launch Aviothic FastAPI Copilot Service
echo "==> [6/6] Starting Aviothic Copilot FastAPI API..."
export AVIOTHIC_ENV="production"
export AVIOTHIC_DEBUG="false"
export AVIOTHIC_VLLM_URL="http://127.0.0.1:${VLLM_PORT}"

echo "Validating system test suite before startup..."
uv run pytest tests/ -q

echo "Launching production uvicorn server on port 8000..."
exec uv run uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --access-log
