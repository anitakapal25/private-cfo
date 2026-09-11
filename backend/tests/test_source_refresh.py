import socket
import pytest
from app.services.source_refresh import public_addresses, fetch_approved

@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1"])
def test_source_dns_rejects_nonpublic_addresses(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(None, None, None, None, (address, 443))])
    with pytest.raises(ValueError, match="public"):
        public_addresses("approved.example")

@pytest.mark.parametrize("url", ["http://127.0.0.1", "https://evil.example", "file:///etc/passwd", "https://investor.sebi.gov.in/unknown"])
def test_fetch_rejects_unapproved_url_before_network(monkeypatch, url):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("Network must not be called"))
    with pytest.raises(ValueError, match="approved"):
        fetch_approved(url)

@pytest.mark.parametrize("status,content_type,chunk", [(302, "text/html", b""), (200, "application/octet-stream", b""), (200, "text/html", b"x" * 4_000_001)])
def test_redirect_media_and_size_are_rejected(monkeypatch, status, content_type, chunk):
    from types import SimpleNamespace
    from app.services import source_refresh as refresh
    from app.services.finance_knowledge import BUDGET
    monkeypatch.setattr(refresh.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=b'["93.184.216.34"]'))
    class Response:
        def __init__(self):
            self.status = status
        def getheader(self, *a):
            return content_type
        def read1(self, *a):
            return chunk
    class Connection:
        def __init__(self, host, address):
            assert host == "investor.sebi.gov.in" and address == "93.184.216.34"
        def request(self, *a, **kw):
            pass
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr(refresh, "PinnedHTTPSConnection", Connection)
    with pytest.raises(ValueError):
        refresh.fetch_approved(BUDGET)
