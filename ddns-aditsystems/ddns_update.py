"""
ddns_update.py — Core DDNS updater for AD IT Systems DNS API (SOAP)

Usage (standalone):
    python ddns_update.py               # fetch IP automatically, update if changed
    python ddns_update.py --force       # update even if IP unchanged
    python ddns_update.py --ip 1.2.3.4  # use given IP

Environment variables (or .env file):
    See .env.example for full list.
"""

import os
import sys
import logging
import argparse
import requests
from ipaddress import IPv4Address, AddressValueError
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _validate_ipv4(ip: str) -> bool:
    """Validate that ip is a valid IPv4 address."""
    try:
        IPv4Address(ip.strip())
        return True
    except (AddressValueError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_file: str | None = None) -> logging.Logger:
    log_file = log_file or _env("DDNS_LOG_FILE")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except OSError as exc:
            print(f"[ddns] WARNING: Cannot open log file {log_file}: {exc}", file=sys.stderr)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    return logging.getLogger("ddns")


# ---------------------------------------------------------------------------
# SOAP envelope templates
# ---------------------------------------------------------------------------

_SOAP_ENVELOPE = """\
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
    xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
    xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/1999/XMLSchema"
    xmlns:ns="urn:http://dns.aditsystems.de/api/">
  <SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    {body}
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

_LOGIN_BODY = """\
<ns:login>
  <username xsi:type="xsd:string">{username}</username>
  <password xsi:type="xsd:string">{password}</password>
</ns:login>"""

_SET_RECORD_BODY = """\
<ns:setRecord>
  <record_name xsi:type="xsd:string">{record_name}</record_name>
  <record_type xsi:type="xsd:string">A</record_type>
  <record_prio xsi:type="xsd:int">0</record_prio>
  <record_content SOAP-ENC:arrayType="xsd:string[1]">
    <item xsi:type="xsd:string">{ip}</item>
  </record_content>
  <record_ttl xsi:type="xsd:int">{ttl}</record_ttl>
</ns:setRecord>"""


# ---------------------------------------------------------------------------
# DDNSUpdater
# ---------------------------------------------------------------------------

class DDNSUpdater:
    """Handles DDNS updates against the AD IT Systems SOAP API."""

    SOAP_ENDPOINT = "https://dns.aditsystems.de/api/api.php"
    SOAP_ACTION   = "urn:DNSAPIAction"
    IP_CHECK_URL  = "https://api4.ipify.org"

    def __init__(
        self,
        *,
        api_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        hostname: str | None = None,
        ttl: int | None = None,
        ip_cache_path: str | None = None,
        ip_check_url: str | None = None,
        log_file: str | None = None,
    ):
        self.api_url       = (api_url       or _env("DDNS_API_URL", self.SOAP_ENDPOINT)).rstrip("?wsdl").rstrip("/")
        self.username      = username      or _env("DDNS_USERNAME")
        self.password      = password      or _env("DDNS_PASSWORD")
        self.hostname      = hostname      or _env("DDNS_HOSTNAME")
        self.ttl           = ttl           or _env_int("DDNS_TTL", 300)
        self.ip_cache_path = ip_cache_path or _env("DDNS_IP_CACHE", "/tmp/ddns-last-ip")
        self.ip_check_url  = ip_check_url  or _env("DDNS_IP_CHECK_URL", self.IP_CHECK_URL)

        self.log = setup_logging(log_file)
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": self.SOAP_ACTION,
        })

        self._validate_config()

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        missing = [k for k, v in {
            "DDNS_USERNAME": self.username,
            "DDNS_PASSWORD": self.password,
            "DDNS_HOSTNAME": self.hostname,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    # ------------------------------------------------------------------
    # IP helpers
    # ------------------------------------------------------------------

    def get_external_ip(self) -> str:
        """Fetch current external IPv4 via ip-check service."""
        try:
            resp = requests.get(self.ip_check_url, timeout=10)
            resp.raise_for_status()
            ip = resp.text.strip()
            self.log.debug("External IP: %s", ip)
            return ip
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to fetch external IP from {self.ip_check_url}: {exc}") from exc

    def get_cached_ip(self) -> str | None:
        """Return last known IP from cache file, or None."""
        try:
            return Path(self.ip_cache_path).read_text().strip() or None
        except (OSError, FileNotFoundError):
            return None

    def set_cached_ip(self, ip: str) -> None:
        """Write IP to cache file."""
        try:
            path = Path(self.ip_cache_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(ip)
        except OSError as exc:
            self.log.warning("Cannot write IP cache to %s: %s", self.ip_cache_path, exc)

    # ------------------------------------------------------------------
    # SOAP helpers
    # ------------------------------------------------------------------

    def _soap_request(self, body_xml: str) -> requests.Response:
        envelope = _SOAP_ENVELOPE.format(body=body_xml)
        resp = self._session.post(self.api_url, data=envelope.encode("utf-8"), timeout=30)
        resp.raise_for_status()
        return resp

    def soap_login(self) -> bool:
        """Authenticate against SOAP API; session cookie is stored in self._session."""
        self.log.debug("SOAP login as %s", self.username)
        body = _LOGIN_BODY.format(username=self.username, password=self.password)
        resp = self._soap_request(body)
        if "true" in resp.text.lower() or "1" in resp.text:
            self.log.debug("SOAP login successful")
            return True
        self.log.error("SOAP login failed. Response: %s", resp.text[:200])
        return False

    def soap_set_record(self, ip: str) -> bool:
        """Set the A record for self.hostname to ip."""
        self.log.info("Setting %s → %s (TTL %s)", self.hostname, ip, self.ttl)
        body = _SET_RECORD_BODY.format(record_name=self.hostname, ip=ip, ttl=self.ttl)
        resp = self._soap_request(body)
        if "true" in resp.text.lower() or "<return>1</return>" in resp.text:
            self.log.info("Record updated successfully")
            return True
        self.log.error("setRecord failed. Response: %s", resp.text[:400])
        return False

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def update_if_changed(self, ip: str | None = None, force: bool = False) -> dict:
        """
        Update DNS if the IP has changed (or force=True).

        Args:
            ip:    IP to use. If None, fetched via get_external_ip().
            force: Update even if cached IP matches.

        Returns:
            dict with keys: changed, old_ip, new_ip, success, message
        """
        old_ip = self.get_cached_ip()

        if ip is None:
            try:
                ip = self.get_external_ip()
            except RuntimeError as exc:
                self.log.error("%s", exc)
                return {"changed": False, "old_ip": old_ip, "new_ip": None, "success": False, "message": str(exc)}

        new_ip = ip.strip()

        if not _validate_ipv4(new_ip):
            msg = f"Invalid IPv4 address: {new_ip}"
            self.log.error(msg)
            return {"changed": False, "old_ip": old_ip, "new_ip": new_ip, "success": False, "message": msg}

        if not force and new_ip == old_ip:
            self.log.info("IP unchanged (%s), skipping update", new_ip)
            return {"changed": False, "old_ip": old_ip, "new_ip": new_ip, "success": True, "message": "IP unchanged"}

        self.log.info("IP change detected: %s → %s", old_ip, new_ip)

        try:
            if not self.soap_login():
                msg = "SOAP login failed"
                return {"changed": True, "old_ip": old_ip, "new_ip": new_ip, "success": False, "message": msg}

            if not self.soap_set_record(new_ip):
                msg = "setRecord call failed"
                return {"changed": True, "old_ip": old_ip, "new_ip": new_ip, "success": False, "message": msg}
        except requests.RequestException as exc:
            msg = f"Network error during SOAP call: {exc}"
            self.log.error(msg)
            return {"changed": True, "old_ip": old_ip, "new_ip": new_ip, "success": False, "message": msg}

        self.set_cached_ip(new_ip)
        return {"changed": True, "old_ip": old_ip, "new_ip": new_ip, "success": True, "message": "Updated successfully"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="DDNS updater for AD IT Systems DNS API")
    parser.add_argument("--ip",    help="Use this IP instead of auto-detecting")
    parser.add_argument("--force", action="store_true", help="Update even if IP is unchanged")
    parser.add_argument("--check", action="store_true", help="Only print current external IP, do not update")
    args = parser.parse_args()

    updater = DDNSUpdater()

    if args.check:
        ip = updater.get_external_ip()
        print(ip)
        return

    result = updater.update_if_changed(ip=args.ip, force=args.force)
    if result["success"]:
        if result["changed"]:
            print(f"Updated: {result['old_ip']} → {result['new_ip']}")
        else:
            print(f"No change needed (IP: {result['new_ip']})")
        sys.exit(0)
    else:
        print(f"ERROR: {result['message']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
