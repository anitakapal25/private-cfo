"""Explicit public-only refresh; pinned DNS address, TLS hostname validation, no redirects."""
import hashlib
import http.client
import ipaddress
import json
import subprocess
import sys
import socket
import ssl
import time
import threading
from urllib.parse import urlsplit
from app.services.finance_knowledge import APPROVED_URLS

MAX_BYTES = 4_000_000

class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=3, context=ssl.create_default_context())
        self.address = address
    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise

def public_addresses(host):
    addresses = sorted({row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Source did not resolve exclusively to public addresses")
    return addresses

def fetch_approved(url):
    if url not in APPROVED_URLS:
        raise ValueError("URL is not in the approved catalogue")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Source URL is not permitted")
    # Connect to the already validated IP, never perform a second DNS lookup.
    # DNS resolution is bounded in a short-lived child; returned IPs are validated again.
    resolver = subprocess.run(
        [sys.executable, "-I", "-c", "import json,socket,sys; print(json.dumps(sorted({r[4][0] for r in socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)})))", parsed.hostname],
        capture_output=True, timeout=3, check=True,
    )
    addresses = json.loads(resolver.stdout)
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Source did not resolve exclusively to public addresses")
    address = addresses[0]
    connection = PinnedHTTPSConnection(parsed.hostname, address)
    started = time.monotonic()
    def interrupt_connection():
        sock = getattr(connection, "sock", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
    deadline = threading.Timer(10, interrupt_connection)
    deadline.daemon = True
    deadline.start()
    try:
        connection.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""), headers={"Accept-Encoding": "identity", "User-Agent": "ArthaOS-reviewed-source-refresh/1"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Source unavailable or redirected; manual review required")
        content_type = response.getheader("Content-Type", "").split(";")[0]
        if content_type not in {"text/html", "text/plain", "application/pdf"}:
            raise ValueError("Unsupported source media type")
        content = bytearray()
        while True:
            if time.monotonic() - started >= 10:
                raise TimeoutError("Source refresh deadline exceeded")
            chunk = response.read1(16_384)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > MAX_BYTES:
                raise ValueError("Source exceeded size limit")
        return {"url": url, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content), "content_type": content_type, "status": "pending_review"}, bytes(content)
    finally:
        deadline.cancel()
        connection.close()
