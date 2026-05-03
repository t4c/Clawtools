FROM alpine:3.19

LABEL \
  io.hass.version="1.11.1" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64|armv7" \
  maintainer="t4c <t4c@ghcif.de>"

ARG NODE_EXPORTER_VERSION="1.11.1"
ARG BUILD_ARCH

RUN case ${BUILD_ARCH:-amd64} in \
    amd64) ARCH=amd64 ;; \
    aarch64) ARCH=arm64 ;; \
    armv7) ARCH=armv7 ;; \
    *) ARCH=amd64 ;; \
    esac \
    && apk add --no-cache curl \
    && curl -LO https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz \
    && tar -xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz \
    && cp node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}/node_exporter /usr/local/bin/ \
    && rm -rf node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}* \
    && apk del curl

EXPOSE 9100

CMD ["node_exporter", "--web.listen-address=:9100"]
