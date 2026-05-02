# ddns-aditsystems

A universal Dynamic DNS updater for the **AD IT Systems DNS API** (`dns.aditsystems.de`).

Works in two modes:

| Mode | File | Use case |
|------|------|----------|
| **HTTP server** | `ddns_server.py` | Fritz!Box or router sends IP automatically via DynDNS URL |
| **Standalone / cron** | `ddns_update.py` | Run periodically; script detects and pushes IP changes |

The SOAP API of aditsystems.de requires a login call followed by a `setRecord` call. Both are handled transparently using `requests` — no external SOAP library needed.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Mode 1 — Standalone / Cron](#mode-1--standalone--cron)
5. [Mode 2 — HTTP Server (Fritz!Box)](#mode-2--http-server-fritzbox)
6. [Systemd Service](#systemd-service)
7. [Docker](#docker)
8. [Fritz!Box DynDNS Setup](#fritzbox-dyndns-setup)
9. [Environment Variables Reference](#environment-variables-reference)
10. [Troubleshooting](#troubleshooting)
11. [SOAP API Details](#soap-api-details)
12. [License](#license)

---

## Requirements

- Python 3.10+
- pip packages: `requests`, `flask`, `python-dotenv`
- An [AD IT Systems](https://aditsystems.de) account with at least one domain managed via their DNS panel

---

## Installation

### Option A — pip (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/ddns-aditsystems.git
cd ddns-aditsystems

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
$EDITOR .env          # fill in credentials and hostname
```

### Option B — system-wide install

```bash
sudo mkdir -p /opt/ddns-aditsystems
sudo cp -r . /opt/ddns-aditsystems/

cd /opt/ddns-aditsystems
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

sudo mkdir -p /etc/ddns-aditsystems /var/cache/ddns-aditsystems /var/log/ddns-aditsystems
sudo cp .env.example /etc/ddns-aditsystems/ddns.env
sudo $EDITOR /etc/ddns-aditsystems/ddns.env
sudo chmod 600 /etc/ddns-aditsystems/ddns.env
```

---

## Configuration

All settings are read from environment variables. The easiest way is a `.env` file in the project directory (loaded automatically via `python-dotenv`).

Copy the example and edit:

```bash
cp .env.example .env
```

At minimum you need:

```env
DDNS_USERNAME=your_username
DDNS_PASSWORD=your_password
DDNS_HOSTNAME=your.domain.example.com
```

See [Environment Variables Reference](#environment-variables-reference) for all options.

---

## Mode 1 — Standalone / Cron

The script fetches your current external IPv4, compares it with the cached value, and calls the API only if the IP changed.

### Manual run

```bash
# Auto-detect IP, update if changed
python ddns_update.py

# Check current external IP only
python ddns_update.py --check

# Force update (even if IP unchanged)
python ddns_update.py --force

# Use a specific IP (e.g. from a router script)
python ddns_update.py --ip 203.0.113.42
```

### Cron setup

Install the cron jobs from `ddns.cron`:

```bash
crontab -e
```

Paste:

```cron
# Update every 5 minutes if IP changed
*/5 * * * * /opt/ddns-aditsystems/.venv/bin/python /opt/ddns-aditsystems/ddns_update.py >> /var/log/ddns-aditsystems/cron.log 2>&1

# Force daily update at 03:00 to keep TTL fresh
0 3 * * * /opt/ddns-aditsystems/.venv/bin/python /opt/ddns-aditsystems/ddns_update.py --force >> /var/log/ddns-aditsystems/cron.log 2>&1
```

---

## Mode 2 — HTTP Server (Fritz!Box)

`ddns_server.py` starts a small Flask HTTP server. Your Fritz!Box sends a DynDNS request to this server whenever your IP changes, and the server calls the AD IT Systems API.

### Start manually

```bash
python ddns_server.py
# Listening on http://0.0.0.0:8053
```

### Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /update?ip=<ip>` | optional | Fritz!Box DynDNS update |
| `GET /force?ip=<ip>` | optional | Force update (ip optional, auto-detected if omitted) |
| `GET /status` | none | Current IP and last update time (JSON) |
| `GET /health` | none | Liveness probe (JSON `{"status":"ok"}`) |

### Example requests

```bash
# Trigger update
curl "http://localhost:8053/update?ip=203.0.113.42"

# Check status
curl http://localhost:8053/status

# Force update with current IP
curl "http://localhost:8053/force"
```

---

## Systemd Service

```bash
# Create dedicated user
sudo useradd --system --no-create-home --shell /sbin/nologin ddns

# Copy service file
sudo cp ddns.service /etc/systemd/system/

# Adjust paths in the service file if needed
sudo $EDITOR /etc/systemd/system/ddns.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now ddns

# Check status
sudo systemctl status ddns
sudo journalctl -u ddns -f
```

---

## Docker

### Build and run

```bash
docker build -t ddns-aditsystems .

docker run -d \
  --name ddns \
  --restart unless-stopped \
  -p 8053:8053 \
  -e DDNS_USERNAME=your_username \
  -e DDNS_PASSWORD=your_password \
  -e DDNS_HOSTNAME=your.domain.example.com \
  -v ddns-cache:/var/cache/ddns-aditsystems \
  ddns-aditsystems
```

### Docker Compose

```yaml
services:
  ddns:
    build: .
    restart: unless-stopped
    ports:
      - "8053:8053"
    env_file:
      - .env
    volumes:
      - ddns-cache:/var/cache/ddns-aditsystems

volumes:
  ddns-cache:
```

---

## Fritz!Box DynDNS Setup

The Fritz!Box can notify your server automatically whenever your IP changes.

### Step-by-step

1. Open the Fritz!Box web interface: **http://fritz.box**

2. Navigate to:
   ```
   Internet → Shares → DynDNS
   ```
   (German: *Internet → Freigaben → DynDNS*)

3. Enable DynDNS and select **"User-defined"** (Benutzerdefiniert) as provider.

4. Fill in the fields:

   | Field | Value |
   |-------|-------|
   | Update-URL | `http://<YOUR-SERVER-IP>:8053/update?ip=<ipaddr>` |
   | Domain name | `your.domain.example.com` |
   | Username | your AD IT Systems username (or Basic Auth user if enabled) |
   | Password | your AD IT Systems password (or Basic Auth pass if enabled) |

   Replace `<YOUR-SERVER-IP>` with the LAN IP of the machine running `ddns_server.py` (e.g. `192.168.1.100`).

   The placeholder `<ipaddr>` is automatically replaced by the Fritz!Box with the current public IP.

5. Click **Apply** (Übernehmen). The Fritz!Box will immediately send a test request.

6. Check the server logs to confirm the update was received:
   ```bash
   journalctl -u ddns -f
   # or
   tail -f /var/log/ddns-aditsystems/update.log
   ```

### With Basic Auth enabled

If you set `DDNS_SERVER_AUTH_USER` and `DDNS_SERVER_AUTH_PASS`, use this URL format:

```
http://username:password@<YOUR-SERVER-IP>:8053/update?ip=<ipaddr>
```

> **Note:** Fritz!Box supports credentials in the URL. For production use, consider placing the server behind a reverse proxy with HTTPS (nginx, Caddy).

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DDNS_API_URL` | `https://dns.aditsystems.de/api/api.php` | SOAP endpoint URL |
| `DDNS_USERNAME` | *(required)* | AD IT Systems login username |
| `DDNS_PASSWORD` | *(required)* | AD IT Systems login password |
| `DDNS_HOSTNAME` | *(required)* | FQDN of the A record to update |
| `DDNS_TTL` | `300` | DNS TTL in seconds |
| `DDNS_IP_CACHE` | `/var/cache/ddns-aditsystems/last-ip` | Path to cache file for last known IP |
| `DDNS_LOG_FILE` | *(empty — stdout only)* | Path to log file |
| `DDNS_IP_CHECK_URL` | `https://api4.ipify.org` | Service that returns external IPv4 as plain text |
| `DDNS_SERVER_HOST` | `0.0.0.0` | Flask bind address |
| `DDNS_SERVER_PORT` | `8053` | Flask listen port |
| `DDNS_SERVER_AUTH_USER` | *(empty — auth disabled)* | Basic Auth username for `/update` and `/force` |
| `DDNS_SERVER_AUTH_PASS` | *(empty — auth disabled)* | Basic Auth password |
| `DDNS_SERVER_DEBUG` | `false` | Enable Flask debug mode (dev only) |

---

## Troubleshooting

### "Missing required configuration"

You have not set `DDNS_USERNAME`, `DDNS_PASSWORD`, or `DDNS_HOSTNAME`.
Check your `.env` file (must be in the working directory) or environment variables.

### SOAP login fails

- Verify credentials by logging into https://my.aditsystems.de manually.
- Check that `DDNS_API_URL` points to `https://dns.aditsystems.de/api/api.php` (without `?wsdl`).
- The API uses session cookies; make sure your network allows HTTPS to `dns.aditsystems.de`.

### setRecord returns failure

- The hostname must exactly match a DNS record already existing in your AD IT Systems account.
- Only A records (IPv4) are supported by this tool.
- Check the full SOAP response in the log (set `DDNS_SERVER_DEBUG=true` or run with `-v`).

### Fritz!Box shows "DynDNS error"

- Confirm the update URL is reachable from the Fritz!Box LAN IP.
- Test manually: `curl "http://<server>:8053/update?ip=1.2.3.4"`
- The Fritz!Box expects an HTTP 200 response; check `/health` responds correctly.
- If the server is on a different subnet, ensure routing or port-forwarding is configured.

### IP cache causes stale updates

Delete the cache file to force a fresh update:

```bash
rm /var/cache/ddns-aditsystems/last-ip
python ddns_update.py
```

### Logs

```bash
# Systemd
journalctl -u ddns -f

# File log
tail -f /var/log/ddns-aditsystems/update.log

# Docker
docker logs -f ddns
```

---

## SOAP API Details

The AD IT Systems DNS API is a SOAP 1.1 service.

- **WSDL**: `https://dns.aditsystems.de/api/api.php?wsdl`
- **Endpoint**: `https://dns.aditsystems.de/api/api.php`
- **SOAPAction**: `urn:DNSAPIAction`
- **Namespace**: `urn:http://dns.aditsystems.de/api/`

### login

```xml
<ns:login>
  <username xsi:type="xsd:string">user</username>
  <password xsi:type="xsd:string">pass</password>
</ns:login>
```

Returns a session cookie used for subsequent calls.

### setRecord

```xml
<ns:setRecord>
  <record_name xsi:type="xsd:string">your.domain.example.com</record_name>
  <record_type xsi:type="xsd:string">A</record_type>
  <record_prio xsi:type="xsd:int">0</record_prio>
  <record_content SOAP-ENC:arrayType="xsd:string[1]">
    <item xsi:type="xsd:string">1.2.3.4</item>
  </record_content>
  <record_ttl xsi:type="xsd:int">300</record_ttl>
</ns:setRecord>
```

`record_content` is an `ArrayOfstring`; pass exactly one IP address.

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

*Not affiliated with AD IT Systems GmbH. Use at your own risk.*
