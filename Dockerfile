# ============================================================
# 1) Base Image
# ============================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# ============================================================
# 2) Install OS-level system dependencies
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    curl \
 && rm -rf /var/lib/apt/lists/*

# ============================================================
# 3) Create working directory
# ============================================================
WORKDIR /app

# ============================================================
# 4) Copy requirements first (layer caching)
# ============================================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# 5) Copy project files
# ============================================================
COPY server.py .
COPY app2.py .
COPY py2pdf_extraction.py .
COPY agents.py .
COPY prompts.py .

COPY static/ static/
COPY templates/ templates/
COPY uploads/ uploads/

# Also copy any JSONs (optional)
COPY *.json ./

# ============================================================
# 6) Runtime Environment Variables
# ============================================================
ENV FLASK_ENV=production

EXPOSE 5000

# ============================================================
# 7) Start the Flask server (no Gunicorn)
# ============================================================
CMD ["python", "server.py"]