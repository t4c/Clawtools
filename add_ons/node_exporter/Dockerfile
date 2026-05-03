ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bookworm
FROM ${BUILD_FROM}

# Install Node Exporter
RUN mkdir -p /tmp/ne && \
    cd /tmp/ne && \
    apt-get update && \
    apt-get install -y curl && \
    curl -L https://github.com/prometheus/node_exporter/releases/download/v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz -o ne.tar.gz && \
    tar xzf ne.tar.gz && \
    cp node_exporter-1.11.1.linux-amd64/node_exporter /usr/local/bin/ && \
    chmod +x /usr/local/bin/node_exporter && \
    rm -rf /tmp/ne && \
    apt-get remove -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create textfile collector directory
RUN mkdir -p /var/lib/node_exporter/textfile_collector

# Copy run script
COPY run.sh /
RUN chmod +x /run.sh

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9100/metrics > /dev/null 2>&1 || exit 1

CMD ["/run.sh"]
