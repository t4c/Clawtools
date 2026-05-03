# Node Exporter Add-on for Home Assistant OS

This add-on provides the Prometheus Node Exporter for Home Assistant OS, allowing you to monitor the host system metrics.

## Installation

1.  **Restart Home Assistant** (or reload the Supervisor).
2.  Go to **Home Assistant > Settings > Add-ons**.
3.  Click the **three dots** in the top right corner and select **Repositories**.
4.  Add the following URL as a new repository:
    `https://github.com/t4c/Clawtools/tree/main/add_ons`
5.  The "Node Exporter" add-on should now appear in the add-on store.
6.  Click on the "Node Exporter" add-on and then **Install**.
7.  After installation, **Start** the add-on.

## Usage

The Node Exporter will be accessible on port 9100 of your Home Assistant instance. You can configure Prometheus to scrape metrics from `homeassistant_ip:9100`.

## Configuration

This add-on runs with default settings. Advanced configuration might be added in future versions.
