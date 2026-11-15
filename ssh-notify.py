#!/usr/bin/env python3
"""Send a Discord notification when someone logs in over SSH.

Install this file as /usr/local/bin/ssh-notify (mode 755). It is started on
login by the ssh-notify.sh shim placed in /etc/profile.d/.

The Discord webhook URL is read from /etc/ssh_notify_webhook, which should be
owned by root with mode 644.

Only the Python 3 standard library is used, so it runs on a stock Debian.
"""

import ipaddress
import json
import os
import pwd
import signal
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BOT_NAME = "SSH-Bot"
WEBHOOK_FILE = "/etc/ssh_notify_webhook"
EMBED_COLOR = 12976176
HTTP_TIMEOUT = 10  # seconds
# Discord (via Cloudflare) rejects the default "Python-urllib" user agent.
USER_AGENT = "ssh-notify/2.0"


def http_request(url, data=None):
    """Make a GET (or a JSON POST if data is given) request and return the body."""
    headers = {"User-Agent": USER_AGENT}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def remote_ip():
    """Return the client's IP address from $SSH_CLIENT ("ip port localport")."""
    ssh_client = os.environ.get("SSH_CLIENT", "").split()
    return ssh_client[0] if ssh_client else None


def describe_local_address(ip):
    """Return a label if the address cannot be geo-located, None otherwise."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "Unparseable address"

    # SSH may report IPv4 clients as IPv4-mapped IPv6 (e.g. ::ffff:192.168.1.10).
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped

    if addr.is_loopback:
        return "Loopback"
    if addr.is_link_local:
        return "Link-local network"
    if addr.is_private:
        return "Local network"
    if not addr.is_global:
        # e.g. carrier-grade NAT (100.64.0.0/10), reserved ranges...
        return "Non-public network"
    return None


def origin(ip):
    """Build the "Origin" field value for the given client IP."""
    if not ip:
        return "Unknown"

    local = describe_local_address(ip)
    if local:
        return f"{ip} | :house: {local}"

    try:
        info = json.loads(http_request(f"https://ipinfo.io/{ip}/json"))
    except (urllib.error.URLError, OSError, ValueError):
        return f"{ip} | geolocation unavailable"

    country = info.get("country", "")
    city = info.get("city", "")
    isp = info.get("org", "")

    location = ", ".join(part for part in (country, city) if part)
    if country:
        location = f":flag_{country.lower()}: {location}"

    return " | ".join(part for part in (ip, location, isp) if part)


def main():
    # Keep running if the user logs out before the notification is sent.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    ip = remote_ip()
    if ip is None:
        # Not an SSH session (e.g. local console login): nothing to report.
        return 0

    try:
        with open(WEBHOOK_FILE) as f:
            webhook = f.read().strip()
    except OSError as e:
        print(f"ssh-notify: cannot read {WEBHOOK_FILE}: {e}", file=sys.stderr)
        return 1

    host = socket.gethostname()
    now = datetime.now()

    payload = {
        "username": BOT_NAME,
        "embeds": [{
            "color": EMBED_COLOR,
            "title": f"New login on ***{host}***",
            "fields": [
                {"name": "User", "value": pwd.getpwuid(os.geteuid()).pw_name},
                {"name": "Host", "value": host},
                {"name": "Date", "value": now.strftime("%d-%m-%Y-%H:%M:%S")},
                {"name": "Origin", "value": origin(ip)},
                {"name": "Terminal", "value": os.environ.get("TERM") or "none"},
            ],
            "timestamp": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        }],
    }

    try:
        http_request(webhook, payload)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"ssh-notify: failed to send notification: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
