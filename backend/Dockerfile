# Hyperborea API — Hugging Face Space (Docker SDK). Build context = deploy/hf-space (scripts/build_space.ps1).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HYPERBOREA_ROOT=/app HOME=/home/user

# HF Spaces run the container as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

COPY --chown=user backend/ backend/
COPY --chown=user data/ data/
COPY --chown=user config/ config/

USER user
EXPOSE 7860
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
