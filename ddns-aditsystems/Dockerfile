FROM python:3.12-slim

LABEL maintainer="your@email.example"
LABEL description="DDNS updater for AD IT Systems DNS API"

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ddns_update.py ddns_server.py ./

# Runtime directories
RUN mkdir -p /var/cache/ddns-aditsystems /var/log/ddns-aditsystems

ENV DDNS_IP_CACHE=/var/cache/ddns-aditsystems/last-ip
ENV DDNS_LOG_FILE=
ENV DDNS_SERVER_HOST=0.0.0.0
ENV DDNS_SERVER_PORT=8053

EXPOSE 8053

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${DDNS_SERVER_PORT}/health')"

CMD ["python", "ddns_server.py"]
