import hashlib
import json
import os
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import unittest


BASE = "http://127.0.0.1:18444"
JOURNAL = "/var/lib/beamjournal/journal.bin"
PLAN = "/var/lib/beamjournal/fold.plan"


def u16(n: int) -> bytes:
    return struct.pack("<H", n)


def legacy_frame(scope: str, kind: int, payload: bytes, enabled: int = 1) -> bytes:
    s = scope.encode()
    return u16(len(payload)) + bytes([enabled, len(s)]) + s + bytes([kind]) + payload


def extended_frame(scope: str, kind: int, flags: int, payload: bytes, enabled: int = 1) -> bytes:
    s = scope.encode()
    return u16(len(payload) + 2) + bytes([enabled, len(s)]) + s + bytes([255, kind, flags]) + payload


def legacy_rule(scope: str, kind: int, action: int, arg: int, enabled: int = 1) -> bytes:
    s = scope.encode()
    return bytes([len(s)]) + s + bytes([kind, action, arg, enabled])


def extended_rule(scope: str, kind: int, action: int, arg: int, enabled: int, window: int, repeat: int, salt: int) -> bytes:
    s = scope.encode()
    return bytes([255, len(s)]) + s + bytes([kind, action, arg, enabled, window, repeat, salt])


def finish(blob: bytes) -> bytes:
    return blob + b"DONE"


def lcg(seed: int, n: int) -> bytes:
    x = seed & 0xFFFFFFFF
    out = bytearray()
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0xFFFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def rle(seed: int, n: int) -> bytes:
    out = bytearray()
    for i in range(n):
        count = (i % 4) + 1
        if i % 6 == 0:
            count = 0
        out.extend([count, (seed + i * 29) & 0xFF])
    return bytes(out)


def base_transform(payload: bytes, kind: int) -> bytes:
    b = bytearray(payload)
    if kind == 0:
        return bytes(b)
    if kind == 1:
        return bytes(reversed(b))
    if kind == 2:
        return bytes(b[1:] + b[:1]) if len(b) > 1 else bytes(b)
    if kind == 3:
        return bytes([b[0], *[b[i] ^ b[i - 1] for i in range(1, len(b))]]) if b else b""
    if kind == 4:
        return bytes(b[1::2] + b[0::2])
    if kind == 5:
        out = bytearray()
        for i in range(0, len(b), 2):
            if i + 1 < len(b):
                out.extend([b[i + 1], b[i]])
            else:
                out.append(b[i])
        return bytes(out)
    raise ValueError(f"bad kind {kind}")


def expand_rle(payload: bytes) -> bytes:
    if len(payload) % 2:
        raise ValueError("odd rle")
    out = bytearray()
    for i in range(0, len(payload), 2):
        out.extend([payload[i + 1]] * payload[i])
    return bytes(out)


def interleave(payload: bytes) -> bytes:
    first_len = (len(payload) + 1) // 2
    first, second = payload[:first_len], payload[first_len:]
    out = bytearray()
    for i in range(first_len):
        if i < len(second):
            out.append(second[i])
        out.append(first[i])
    return bytes(out)


def rotate_left(payload: bytes, n: int) -> bytes:
    if not payload:
        return payload
    n %= len(payload)
    return payload[n:] + payload[:n]


def rotate_right(payload: bytes, n: int) -> bytes:
    if not payload:
        return payload
    n %= len(payload)
    return payload[-n:] + payload[:-n] if n else payload


def parse_plan(path: str):
    with open(path, "rb") as f:
        data = f.read()
    rules = []
    off = 0
    limit = len(data) - 4
    while off < limit:
        if data[off] == 255:
            if off + 3 > limit:
                raise ValueError("truncated extended plan")
            scope_len = data[off + 1]
            end = off + 2 + scope_len + 7
            if end > limit:
                raise ValueError("truncated extended plan body")
            scope = data[off + 2 : off + 2 + scope_len].decode()
            kind, action, arg, enabled, window, repeat, salt = data[off + 2 + scope_len : end]
            if enabled:
                rules.append((scope, kind, action, arg, window, repeat, salt, len(rules)))
            off = end
        else:
            scope_len = data[off]
            end = off + 1 + scope_len + 4
            if end > limit:
                raise ValueError("truncated legacy plan")
            scope = data[off + 1 : off + 1 + scope_len].decode()
            kind, action, arg, enabled = data[off + 1 + scope_len : end]
            if enabled:
                rules.append((scope, kind, action, arg, 0, 0, 0, len(rules)))
            off = end
    return rules


def pick_rule(rules, scope: str, kind: int):
    best = None
    best_rank = (-1, -1)
    for r in rules:
        rule_scope, rule_kind, *_rest, order = r
        if rule_kind != kind or rule_scope not in (scope, "*"):
            continue
        rank = (1 if rule_scope == scope else 0, order)
        if rank >= best_rank:
            best = r
            best_rank = rank
    return best


def apply_plan(payload: bytes, rule) -> bytes:
    if rule is None or not payload:
        return payload
    _scope, _kind, action, arg, window, repeat, salt, _order = rule
    b = bytearray(payload)
    if action == 0:
        return bytes(b)
    if action == 1:
        return bytes(x ^ arg for x in b)
    if action == 2:
        return rotate_right(bytes(b), arg)
    if action == 3:
        step = max(1, window)
        keep = arg % step
        return bytes(x for i, x in enumerate(b) if i % step == keep)
    if action == 4:
        return bytes(b) + bytes([b[0]]) * repeat + bytes([salt])
    if action == 5:
        return rotate_left(bytes((x ^ ((arg + salt + i * window) & 0xFF)) for i, x in enumerate(b)), repeat)
    if action == 6:
        chunk = max(1, window)
        out = bytearray()
        for start in range(0, len(b), chunk):
            seen = set()
            for x in b[start : start + chunk]:
                y = x ^ arg
                if y not in seen:
                    seen.add(y)
                    out.append(y)
        if out:
            out.extend([salt] * repeat)
        return bytes(out)
    if action == 7:
        orig = bytes(b)
        out = bytes(b) + b"".join(orig[::-1] for _ in range(repeat))
        if window:
            out = out[:window]
        return bytes(x ^ (arg ^ salt) for x in out)
    raise ValueError(f"bad action {action}")


def expected(scope: str):
    rules = parse_plan(PLAN)
    with open(JOURNAL, "rb") as f:
        data = f.read()
    off = 0
    limit = len(data) - 4
    out = bytearray()
    entries = 0
    while off < limit:
        size = struct.unpack("<H", data[off : off + 2])[0]
        off += 2
        enabled = data[off]
        off += 1
        scope_len = data[off]
        off += 1
        rec_scope = data[off : off + scope_len].decode()
        off += scope_len
        kind = data[off]
        off += 1
        if kind == 255:
            kind = data[off]
            flags = data[off + 1]
            payload = data[off + 2 : off + size]
        else:
            flags = 0
            payload = data[off : off + size]
        off += size
        if not enabled or rec_scope not in (scope, "all"):
            continue
        work = bytes(payload)
        if flags & 0x01:
            work = expand_rle(work)
        if flags & 0x02:
            work = interleave(work)
        if flags & 0x08:
            work = bytes([(kind + len(work)) & 0xFF]) + work + bytes([flags])
        work = base_transform(work, kind)
        if flags & 0x04:
            work = base_transform(work, kind)
        work = apply_plan(work, pick_rule(rules, scope, kind))
        out.extend(work)
        entries += 1
    return bytes(out), entries


def write_case(case: int) -> None:
    frames = bytearray()
    plan = bytearray()
    if case == 1:
        frames += legacy_frame("alpha", 0, b"beam")
        frames += legacy_frame("all", 1, b"abcde")
        frames += extended_frame("alpha", 4, 0x0B, bytes([2, 0x41, 1, 0x42, 3, 0x43]))
        frames += extended_frame("beta", 3, 0x04, b"\x10\x21\x45\x9a")
        frames += extended_frame("alpha", 2, 0x01, bytes([0, 0x77]), enabled=0)
        plan += legacy_rule("*", 0, 1, 0x11)
        plan += extended_rule("alpha", 4, 6, 0x20, 1, 2, 1, 0x51)
        plan += legacy_rule("*", 1, 2, 3)
        plan += extended_rule("beta", 3, 7, 0x31, 1, 9, 1, 0x44)
    elif case == 2:
        for i in range(24):
            scope = ["alpha", "beta", "gamma", "all"][i % 4]
            kind = (i * 2 + 1) % 6
            enabled = 0 if i % 10 == 4 else 1
            if i % 3 == 0:
                flags = 0x01 | (0x02 if i % 2 else 0) | (0x04 if i % 5 == 0 else 0) | (0x08 if i % 7 == 0 else 0)
                frames += extended_frame(scope, kind, flags, rle(0x30 + i, 2 + i % 5), enabled)
            elif i % 3 == 1:
                flags = (0x02 if i % 4 else 0) | (0x04 if i % 6 else 0) | (0x08 if i % 5 else 0)
                frames += extended_frame(scope, kind, flags, lcg(0x90 + i * 11, i % 9), enabled)
            else:
                frames += legacy_frame(scope, kind, lcg(0x150 + i * 17, 1 + i % 11), enabled)
        plan += legacy_rule("*", 0, 4, 0x00)
        plan += extended_rule("*", 1, 5, 0x7E, 1, 13, 5, 0x29)
        plan += legacy_rule("alpha", 1, 1, 0x99, 0)
        plan += extended_rule("alpha", 1, 7, 0x22, 1, 17, 2, 0x05)
        plan += extended_rule("beta", 3, 6, 0x42, 1, 4, 3, 0x24)
        plan += legacy_rule("*", 5, 3, 2)
        plan += extended_rule("gamma", 5, 5, 0x12, 1, 7, 9, 0xE0)
    elif case == 3:
        frames += extended_frame("alpha", 5, 0x0E, b"shadowclock")
        frames += extended_frame("all", 0, 0x08, b"z")
        frames += legacy_frame("beta", 2, b"rotate")
        frames += extended_frame("gamma", 1, 0x01, bytes([3, 0xA0, 2, 0xB1, 1, 0xC2]))
        frames += legacy_frame("alpha", 3, b"")
        plan += extended_rule("*", 5, 7, 0x6A, 1, 31, 3, 0xC0)
        plan += legacy_rule("*", 0, 4, 0)
        plan += extended_rule("alpha", 3, 4, 0x00, 1, 0, 4, 0x77)
        plan += extended_rule("beta", 2, 2, 250, 1, 0, 0, 0)
        plan += extended_rule("gamma", 1, 5, 4, 1, 2, 1, 8)
    else:
        raise ValueError(case)
    os.makedirs("/var/lib/beamjournal", exist_ok=True)
    with open(JOURNAL, "wb") as f:
        f.write(finish(bytes(frames)))
    with open(PLAN, "wb") as f:
        f.write(finish(bytes(plan)))


def helper(scope: str) -> bytes:
    return subprocess.check_output(["/usr/local/bin/beamjournal-fold", JOURNAL, PLAN, scope], timeout=3)


def wait_health() -> None:
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            body = urllib.request.urlopen(BASE + "/health", timeout=1).read().decode()
            if "ok" in body:
                return
        except Exception:
            time.sleep(0.1)
    raise AssertionError("health timeout")


def audit(scope: str) -> dict:
    url = BASE + "/ledger?" + urllib.parse.urlencode({"scope": scope})
    try:
        body = urllib.request.urlopen(url, timeout=3).read().decode()
    except urllib.error.HTTPError as exc:
        raise AssertionError(exc.read().decode()) from exc
    return json.loads(body)


def assert_scope(scope: str, epoch: int) -> None:
    folded, entries = expected(scope)
    got_helper = helper(scope)
    if got_helper != folded:
        raise AssertionError(f"helper mismatch for {scope}: {got_helper.hex()} != {folded.hex()}")
    payload = audit(scope)
    if set(payload) != {"ok", "scope", "epoch", "digest", "bytes", "entries"}:
        raise AssertionError(f"bad fields for {scope}: {payload}")
    want_digest = hashlib.sha256(folded).hexdigest()
    want = {"ok": True, "scope": scope, "epoch": epoch, "digest": want_digest, "bytes": len(folded), "entries": entries}
    if payload != want:
        raise AssertionError(f"bad audit for {scope}: want {want}, got {payload}")


class BeamJournalVerifier(unittest.TestCase):
    def test_folded_ledgers_survive_restarts_and_live_rewrites(self) -> None:
        for case in (1, 2):
            write_case(case)
            subprocess.run(["/usr/local/sbin/beamjournal-supervise", "restart"], check=True, timeout=90)
            wait_health()
            with open("/etc/beamjournal/service.toml", encoding="utf-8") as f:
                rendered = f.read().splitlines()
            for line in [
                'bind = "127.0.0.1:18444"',
                'journal_path = "/var/lib/beamjournal/journal.bin"',
                'plan_path = "/var/lib/beamjournal/fold.plan"',
                'folder_path = "/usr/local/bin/beamjournal-fold"',
                "epoch = 41",
            ]:
                self.assertIn(line, rendered)
            for scope in ("alpha", "beta", "gamma"):
                assert_scope(scope, 41)

        write_case(3)
        for scope in ("alpha", "beta", "gamma"):
            assert_scope(scope, 41)
        write_case(1)
        for scope in ("gamma", "alpha"):
            assert_scope(scope, 41)
        subprocess.run(["/usr/local/sbin/beamjournal-supervise", "stop"], check=False, timeout=10)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2)
    sys.exit(0 if result.result.wasSuccessful() else 1)
