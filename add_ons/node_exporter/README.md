# Node Exporter Add-on for Home Assistant

Prometheus Node Exporter running as an isolated Home Assistant add-on. Exposes system metrics for monitoring with Prometheus.

## Features

- **Auto-start on boot** — Supervisor automatically starts this add-on
- **Prometheus metrics endpoint** — Port 9100 (configurable in ports mapping)
- **Textfile collector support** — Collect custom metrics from scripts
- **Health checks built-in** — Supervisor monitors container health
- **Persistent across updates** — Unlike systemd services, survives HA OS updates

## Installation

1. Open Home Assistant > **Settings** > **Add-ons** > **Add-on Store**
2. Click the **⋮** (menu) in the top-right corner
3. Select **Repositories**
4. Add this repository URL: `https://github.com/t4c/Clawtools`
5. Click **Create** and wait for the repository to load
6. Find **Node Exporter** in the add-on list
7. Click **Install**
8. Toggle **Start on boot** (should be auto-enabled)
9. Click **Start**

## Configuration

### Default

No configuration needed. The add-on starts with sensible defaults:
- Listens on port **9100**
- Textfile collector directory: `/var/lib/node_exporter/textfile_collector`

### Custom Textfile Directory (Optional)

If you need to store custom metrics in a different location:

1. Open the add-on settings
2. Edit the **Textfile Directory** option
3. Click **Save** and restart

## Usage

Once running, Node Exporter metrics are available at:

```
http://homeassistant.local:9100/metrics
```

### Prometheus Scrape Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'homeassistant'
    static_configs:
      - targets: ['homeassistant.local:9100']
```

Or if using a different hostname/IP:

```yaml
scrape_configs:
  - job_name: 'homeassistant'
    static_configs:
      - targets: ['10.13.38.30:9100']
```

## Logs

View add-on logs:
- Home Assistant > **Settings** > **Add-ons & integrations** > **Node Exporter** > **Logs**

## Troubleshooting

### Metrics endpoint not responding
- Check add-on logs for errors
- Verify port 9100 is not blocked by firewall
- Restart the add-on via Home Assistant UI

### Port already in use
- Change the port mapping in add-on configuration
- Or check if another service is using port 9100

## Technical Details

- **Base image:** `ghcr.io/home-assistant/amd64-base-debian:bookworm`
- **Node Exporter version:** 1.11.1
- **Supported architectures:** amd64, armv7, aarch64

## License

Node Exporter is licensed under the Apache License 2.0. See the [official repository](https://github.com/prometheus/node_exporter) for details.
