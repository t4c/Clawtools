#!/bin/bash
set -e

echo "Starting Node Exporter..."

# Read options from Home Assistant config (if available)
TEXTFILE_DIR="/var/lib/node_exporter/textfile_collector"
if [ -f /data/options.json ]; then
  TEXTFILE_DIR=$(grep -o '"textfile_directory":"[^"]*"' /data/options.json | cut -d'"' -f4 || echo "$TEXTFILE_DIR")
fi

# Start Node Exporter
exec /usr/local/bin/node_exporter \
  --collector.textfile.directory="$TEXTFILE_DIR" \
  --web.listen-address=:9100
