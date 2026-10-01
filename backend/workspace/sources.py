"""Protected source storage and bounded, isolated extraction/fetching."""
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time
from typing import Protocol
from urllib.parse import urlsplit, urljoin
from uuid import uuid4

MAX_FILE = 2 * 1024 * 1024
MAX_TEXT = 200000
import threading
_parser_slots = threading.BoundedSemaphore(2)

class Storage(Protocol):
    def put(self, organization_id: str, content: bytes) -> str: ...
    def read(self, organization_id: str, key: str) -> bytes: ...

class LocalStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def path(self, org, key):
        if len(org) != 32 or len(key) != 32 or any(c not in "0123456789abcdef" for c in org + key):
            raise ValueError("Invalid storage identifier")
        return self.root / org / key

    def put(self, organization_id, content):
        if len(content) > MAX_FILE:
            raise ValueError("Source exceeds 2 MiB")
        key = uuid4().hex
        target = self.path(organization_id, key)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open("xb") as output:
            os.chmod(target, 0o600)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        return key

    def read(self, organization_id, key):
        with self.path(organization_id, key).open("rb") as source:
            return source.read(MAX_FILE + 1)


def validate_url(url, hosts, resolver=socket.getaddrinfo):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443) or host not in hosts or parsed.fragment:
        raise ValueError("HTTPS URL must use an administrator-allowed host, port 443 and no credentials or fragment")
    records = resolver(host, 443, type=socket.SOCK_STREAM)
    ips = {r[4][0] for r in records}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("URL resolves to a non-public destination")
    return parsed, sorted(ips)


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, address, timeout):
        super().__init__(hostname, 443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def fetch(url, hosts):
    deadline = time.monotonic() + 8
    for redirect in range(4):
        parsed, addresses = validate_url(url, hosts)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("URL deadline exceeded")
        conn = PinnedHTTPS(parsed.hostname, addresses[0], remaining)
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            conn.request("GET", path, headers={"Accept": "text/plain,text/markdown,application/pdf,text/html", "Accept-Encoding": "identity", "User-Agent": "PNG5-PolicyImporter/1"})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location or redirect == 3:
                    raise ValueError("Redirect limit exceeded")
                url = urljoin(url, location)
                continue
            if response.status != 200 or response.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("Unsupported URL response")
            content = response.read(MAX_FILE + 1)
            if len(content) > MAX_FILE:
                raise ValueError("Download exceeds 2 MiB")
            mime = response.getheader("Content-Type", "").split(";")[0].lower()
            extension = {"application/pdf": ".pdf", "text/plain": ".txt", "text/markdown": ".md", "text/html": ".html"}.get(mime)
            if not extension:
                raise ValueError("Unsupported source content type")
            return content, extension
        finally:
            conn.close()
    raise ValueError("Redirect limit exceeded")


def _resource_limit():
    if os.name != "nt":
        import resource
        try:
            resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024,) * 2)
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        except (ValueError, OSError):
            pass
    # Windows runs this worker inside a Job Object with a process memory limit.
    else:
        import ctypes
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [("per_process", ctypes.c_int64), ("per_job", ctypes.c_int64), ("flags", w.DWORD),
                        ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t), ("active", w.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("ro", "wo", "oo", "rb", "wb", "ob")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.restype = w.HANDLE
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        kernel.GetCurrentProcess.restype = w.HANDLE
        handle = kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
        limits.process_memory = 384 * 1024 * 1024
        if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
            raise RuntimeError("Could not apply parser memory isolation")
        # Keep handle open for this short-lived process. OS releases it on exit.


def extract(content, extension):
    if len(content) > MAX_FILE:
        raise ValueError("File exceeds 2 MiB")
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF signature")
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError("Encrypted PDF or page limit exceeded")
        texts = [(f"Page {i}", page.extract_text() or "") for i, page in enumerate(reader.pages, 1)]
        if not any(t.strip() for _, t in texts):
            raise ValueError("Image-only PDF: OCR is unavailable; upload extractable text")
    else:
        text = content.decode("utf-8-sig", errors="strict")
        if "\x00" in text:
            raise ValueError("Binary content is not a text policy")
        if extension == ".html":
            from html.parser import HTMLParser
            class TextOnly(HTMLParser):
                def __init__(self):
                    super().__init__(); self.parts = []; self.hidden = 0
                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style"):
                        self.hidden += 1
                def handle_endtag(self, tag):
                    if tag in ("script", "style"):
                        self.hidden = max(0, self.hidden - 1)
                def handle_data(self, data):
                    if not self.hidden:
                        self.parts.append(data)
            parser = TextOnly(); parser.feed(text); text = "\n".join(parser.parts)
        elif extension not in (".txt", ".md"):
            raise ValueError("Only PDF, Markdown and plain text uploads are supported")
        texts = [("Section " + str(i), text[offset:offset+3000]) for i, offset in enumerate(range(0, len(text), 3000), 1)]
    if not texts or sum(len(t) for _, t in texts) > MAX_TEXT:
        raise ValueError("Source is empty or exceeds extracted-text limit")
    return [{"index": i, "reference": ref, "text": text} for i, (ref, text) in enumerate(texts, 1)]


def isolated(content=None, extension=None, url=None):
    if not _parser_slots.acquire(blocking=False):
        raise ValueError("Source processing is busy; retry later")
    try:
        return _isolated(content, extension, url)
    finally:
        _parser_slots.release()


def _isolated(content=None, extension=None, url=None):
    import base64
    payload = {"content": base64.b64encode(content).decode() if content is not None else None, "extension": extension,
               "url": url, "hosts": [h.strip().lower() for h in os.getenv("POLICY_URL_HOSTS", "").split(",") if h.strip()]}
    result = subprocess.run([sys.executable, "-m", "workspace.sources"], input=json.dumps(payload).encode(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12,
                            cwd=Path(__file__).resolve().parents[1], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode or len(result.stdout) > 4 * MAX_FILE:
        raise ValueError("Policy extraction failed within resource limits")
    response = json.loads(result.stdout)
    if "error" in response:
        raise ValueError(response["error"])
    return base64.b64decode(response["content"]), response["segments"], response["extension"]


if __name__ == "__main__":
    import base64
    try:
        _resource_limit()
        args = json.loads(sys.stdin.buffer.read(4 * MAX_FILE))
        data, ext = fetch(args["url"], args["hosts"]) if args["url"] else (base64.b64decode(args["content"]), args["extension"])
        print(json.dumps({"content": base64.b64encode(data).decode(), "segments": extract(data, ext), "extension": ext}))
    except Exception as error:
        # No URLs, credentials or exception details returned from network/parser libraries.
        message = str(error) if isinstance(error, ValueError) else "Source parsing or fetching failed"
        print(json.dumps({"error": message[:200]}))
