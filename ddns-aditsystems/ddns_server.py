"""
ddns_server.py — Flask HTTP server for Fritz!Box DynDNS endpoint

Fritz!Box DynDNS URL format:
    http://<server>:<port>/update?ip=<ipaddr>

Endpoints:
    GET /update?ip=<ipaddr>   Fritz!Box DynDNS update (optional basic auth)
    GET /status               Show current IP and last update timestamp
    GET /force?ip=<ip>        Force update even if IP unchanged
    GET /health               Liveness probe

Environment variables (or .env file):
    See .env.example for full list.
"""

import os
import time
import logging
from datetime import datetime, timezone
from functools import wraps
from ipaddress import IPv4Address, AddressValueError

from flask import Flask, request, jsonify, Response

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ddns_update import DDNSUpdater, setup_logging

# ---------------------------------------------------------------------------
# App + config
# ---------------------------------------------------------------------------

app = Flask(__name__)

_log = setup_logging()

_AUTH_USER = os.environ.get("DDNS_SERVER_AUTH_USER", "")
_AUTH_PASS = os.environ.get("DDNS_SERVER_AUTH_PASS", "")

# Simple in-memory state (survives restarts via IP cache file)
_state: dict = {
    "last_update": None,
    "last_ip": None,
    "last_result": None,
}


def _get_updater() -> DDNSUpdater:
    return DDNSUpdater()


# ---------------------------------------------------------------------------
# Optional Basic Auth
# ---------------------------------------------------------------------------

def _validate_ipv4(ip: str) -> bool:
    """Validate that ip is a valid IPv4 address."""
    try:
        IPv4Address(ip.strip())
        return True
    except (AddressValueError, ValueError):
        return False


def _check_auth(username: str, password: str) -> bool:
    if not _AUTH_USER and not _AUTH_PASS:
        return True  # auth disabled
    return username == _AUTH_USER and password == _AUTH_PASS


def _requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _AUTH_USER and not _AUTH_PASS:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return Response(
                "Authentication required.",
                401,
                {"WWW-Authenticate": 'Basic realm="DDNS Server"'},
            )
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/update")
@_requires_auth
def update():
    """Fritz!Box DynDNS update endpoint."""
    ip = request.args.get("ip", "").strip()
    if not ip:
        _log.warning("/update called without ip parameter")
        return jsonify({"error": "Missing 'ip' parameter"}), 400

    if not _validate_ipv4(ip):
        _log.warning("/update called with invalid ip=%s from %s", ip, request.remote_addr)
        return jsonify({"error": "Invalid IPv4 address"}), 400

    _log.info("/update called with ip=%s from %s", ip, request.remote_addr)

    try:
        updater = _get_updater()
        result = updater.update_if_changed(ip=ip)
    except ValueError as exc:
        _log.error("Configuration error: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        _log.error("Unexpected error: %s", exc)
        return jsonify({"error": "Internal error"}), 500

    _state["last_update"] = datetime.now(timezone.utc).isoformat()
    _state["last_ip"]     = result.get("new_ip")
    _state["last_result"] = result

    status_code = 200 if result["success"] else 502
    return jsonify(result), status_code


@app.route("/force")
@_requires_auth
def force_update():
    """Force update even if IP has not changed."""
    ip = request.args.get("ip", "").strip() or None

    if ip is not None and not _validate_ipv4(ip):
        _log.warning("/force called with invalid ip=%s from %s", ip, request.remote_addr)
        return jsonify({"error": "Invalid IPv4 address"}), 400

    _log.info("/force called ip=%s from %s", ip or "auto", request.remote_addr)

    try:
        updater = _get_updater()
        if ip is None:
            ip = updater.get_external_ip()
        result = updater.update_if_changed(ip=ip, force=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        _log.error("Unexpected error: %s", exc)
        return jsonify({"error": "Internal error"}), 500

    _state["last_update"] = datetime.now(timezone.utc).isoformat()
    _state["last_ip"]     = result.get("new_ip")
    _state["last_result"] = result

    status_code = 200 if result["success"] else 502
    return jsonify(result), status_code


@app.route("/status")
def status():
    """Return current IP state (no auth required)."""
    try:
        updater = _get_updater()
        cached_ip = updater.get_cached_ip()
        hostname  = updater.hostname
    except ValueError:
        cached_ip = None
        hostname  = os.environ.get("DDNS_HOSTNAME", "unknown")

    return jsonify({
        "hostname":    hostname,
        "cached_ip":   cached_ip,
        "last_update": _state["last_update"],
        "last_ip":     _state["last_ip"],
    })


@app.route("/health")
def health():
    """Liveness probe for Docker / k8s."""
    return jsonify({"status": "ok", "ts": time.time()})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    host = os.environ.get("DDNS_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("DDNS_SERVER_PORT", "8053"))
    debug = os.environ.get("DDNS_SERVER_DEBUG", "").lower() in ("1", "true", "yes")

    _log.info("Starting DDNS server on %s:%s", host, port)
    if _AUTH_USER:
        _log.info("Basic Auth enabled for user: %s", _AUTH_USER)
    else:
        _log.warning("Basic Auth is DISABLED — consider setting DDNS_SERVER_AUTH_USER / DDNS_SERVER_AUTH_PASS")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
