ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM ${BUILD_FROM}

LABEL maintainer="t4c <t4c@ghcif.de>"

ARG NODE_EXPORTER_VERSION="1.11.1"

# Install Node Exporter
RUN apk add --no-cache \
    curl \
    && curl -LO https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz \
    && tar -xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz \
    && cp node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/ \
    && rm -rf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64* \
    && apk del curl

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
