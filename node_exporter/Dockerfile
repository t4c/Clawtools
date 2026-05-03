ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM ${BUILD_FROM}

LABEL maintainer="t4c <t4c@ghcif.de>"

ARG NODE_EXPORTER_VERSION="1.11.1"
ARG BUILD_ARCH

# Map BUILD_ARCH to Node Exporter architecture
RUN case ${BUILD_ARCH} in \
    amd64) ARCH=amd64 ;; \
    aarch64) ARCH=arm64 ;; \
    armv7) ARCH=armv7 ;; \
    *) echo "Unsupported architecture: ${BUILD_ARCH}"; exit 1 ;; \
    esac \
    && apk add --no-cache curl \
    && curl -LO https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz \
    && tar -xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz \
    && cp node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}/node_exporter /usr/local/bin/ \
    && rm -rf node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}* \
    && apk del curl

# Register as s6 service (required by HA base images with s6-overlay)
RUN mkdir -p /etc/services.d/node_exporter
COPY run.sh /etc/services.d/node_exporter/run
RUN chmod a+x /etc/services.d/node_exporter/run
