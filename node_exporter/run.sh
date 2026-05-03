#!/usr/bin/with-contenv bashio

exec node_exporter --web.listen-address=":9100"
