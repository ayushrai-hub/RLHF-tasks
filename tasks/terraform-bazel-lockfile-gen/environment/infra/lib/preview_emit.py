import hashlib
import json
import urllib.request


def link_digest(lock_rows, checksum_rows):
    payload = {"lock": lock_rows, "checksum": checksum_rows}
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def fetch_sidecar(url="http://127.0.0.1:8787/catalog"):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def preview(lock):
    return str(lock)[:80]
