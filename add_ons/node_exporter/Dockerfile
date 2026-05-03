FROM alpine:3.18
LABEL maintainer="t4c <t4c@ghcif.de>"

ARG NODE_EXPORTER_VERSION="1.11.1"

RUN apk add --no-cache curl && \
    curl -LO https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz && \
    tar -xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz && \
    mv node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/ && \
    rm -rf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64

WORKDIR /
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
