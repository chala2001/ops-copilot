# Dockerfile
# ── Recipe for building the SRE Ops Copilot container ───

# ── Stage 1: Start from Python base image ────────────────
FROM python:3.11-slim

# ── Stage 2: Set environment variables ───────────────────
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── Stage 3: Set working directory ───────────────────────
WORKDIR /app

# ── Stage 4: Install system dependencies ─────────────────
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 5: Copy requirements first (caching) ───────────
COPY requirements.txt .

# ── Stage 6: Install Python libraries ────────────────────
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 7: Copy all project files ──────────────────────
COPY . .

# ── Stage 8: Expose Streamlit port ──────────────────────
EXPOSE 8501

# ── Stage 9: Health check ─────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Stage 10: Start command ───────────────────────────────
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]