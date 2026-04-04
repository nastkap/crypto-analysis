FROM python:3.11-slim

# Metadata
LABEL maintainer="ECIES Project"
LABEL description="ECIES Encryption Node - Python PyCryptodome library"
LABEL version="1.0.0"
LABEL org.opencontainers.image.title="ECIES Python PyCryptodome Node"
LABEL org.opencontainers.image.description="ECIES encryption node using Python PyCryptodome library"
LABEL org.opencontainers.image.vendor="ECIES"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.sbom.version="1.0"
LABEL org.sbom.format="cyclonedx"
LABEL org.sbom.scope="application"
LABEL org.sbom.tool="docker-buildx"

# Ustawienia zmiennych
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Tworzenie non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Kopiar requirements PRZED kodem (layer caching)
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiuj kod aplikacji
COPY --chown=appuser:appuser . .

# Switch do non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]