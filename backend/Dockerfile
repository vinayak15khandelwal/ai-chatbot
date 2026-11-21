# ---- Stage 1: build dependencies into a virtualenv ----
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install -r requirements.txt

# ---- Stage 2: small runtime image (no pip cache, no build tools, no tests) ----
FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=sqlite:////data/app.db \
    PORT=8000
RUN useradd --system --create-home --uid 10001 app && mkdir -p /data && chown app:app /data
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4)"
# Starts as root only to fix ownership of the mounted /data volume (hosting disks are often root-owned),
# then drops to the unprivileged 'app' user before launching the server.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
