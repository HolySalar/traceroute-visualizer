"""Cross-platform traceroute engine (no admin rights needed).

On Windows uses `tracert -d`, on Linux/macOS uses `traceroute -n`.
Output is parsed into a uniform list of hops:

    {"hop": 1, "ip": "192.168.1.1" | None,
     "rtts": [0.5, 0.6, 0.4], "avg_ms": 0.5,
     "hostname": "router.local" | None}
"""
from __future__ import annotations

import platform
import re
import shutil
import socket
import subprocess

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# matches "12 ms", "12.5 ms", "<1 ms" ; stars handled separately
RTT_RE = re.compile(r"(?:<\s*1|(\d+(?:\.\d+)?))\s*ms", re.IGNORECASE)


def resolve_target(target: str) -> str:
    """Resolve hostname -> IPv4. Returns IP string, raises ValueError."""
    target = target.strip()
    if IP_RE.fullmatch(target):
        return target
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host '{target}': {exc}") from exc


def reverse_dns(ip: str, timeout: float = 1.0) -> str | None:
    """Best-effort PTR lookup. Returns hostname or None (never raises)."""
    if not ip:
        return None
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return None
    finally:
        socket.setdefaulttimeout(old)


def _parse_rtts_windows(segment: str) -> list[float | None]:
    seg = segment.replace("<1 ms", "0.5 ms").replace("< 1 ms", "0.5 ms")
    rtts: list[float | None] = []
    # split probes: windows always sends 3 probes; stars mean timeout
    tokens = seg.split()
    # walk tokens looking for "X ms" or "*"
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "*":
            rtts.append(None)
            i += 1
        elif tok == "<1" or re.fullmatch(r"\d+(?:\.\d+)?", tok):
            # next token should be ms
            if i + 1 < len(tokens) and tokens[i + 1].lower() == "ms":
                try:
                    rtts.append(float(tok.replace("<", "")))
                except ValueError:
                    rtts.append(0.5)
                i += 2
            else:
                i += 1
        else:
            i += 1
    return rtts[:3]


def _parse_windows(output: str) -> list[dict]:
    hops: list[dict] = []
    for line in output.splitlines():
        m = re.match(r"^\s*(\d+)\s+(.*)$", line)
        if not m:
            continue
        hop_no = int(m.group(1))
        if hop_no > 64:
            continue
        rest = m.group(2)
        # skip header lines like "Tracing route to ..."
        if "ms" not in rest and "*" not in rest:
            continue
        ip_m = IP_RE.search(rest)
        ip = ip_m.group(0) if ip_m else None
        # "Request timed out" lines have no IP
        rtts = _parse_rtts_windows(rest)
        while len(rtts) < 3:
            rtts.append(None)
        vals = [x for x in rtts if x is not None]
        avg = round(sum(vals) / len(vals), 2) if vals else None
        hops.append({"hop": hop_no, "ip": ip, "rtts": rtts, "avg_ms": avg,
                     "hostname": None})
    hops.sort(key=lambda h: h["hop"])
    return hops


def _parse_unix(output: str) -> list[dict]:
    hops: list[dict] = []
    for line in output.splitlines():
        m = re.match(r"^\s*(\d+)\s+(.*)$", line)
        if not m:
            continue
        hop_no = int(m.group(1))
        rest = m.group(2).strip()
        if not rest:
            continue
        if rest.startswith("*") or set(rest) <= {"*", " "}:
            hops.append({"hop": hop_no, "ip": None, "rtts": [None, None, None],
                         "avg_ms": None, "hostname": None})
            continue
        ip_m = IP_RE.search(rest)
        ip = ip_m.group(0) if ip_m else None
        # hostname is first token if not IP and not *
        hostname = None
        first = rest.split()[0]
        if first != "*" and not IP_RE.fullmatch(first.strip("()")):
            hostname = first.strip("()")
        rtts: list[float | None] = []
        for rm in RTT_RE.finditer(rest.replace("<1", "0.5")):
            if rm.group(1):
                try:
                    rtts.append(float(rm.group(1)))
                except ValueError:
                    pass
        stars = rest.count("*")
        # unix may print "* " per timed-out probe
        for _ in range(stars):
            if len(rtts) < 3:
                rtts.append(None)
        while len(rtts) < 3:
            # if line had IP but fewer rtts, pad with None
            if len(rtts) < stars + 1:
                rtts.append(None)
            else:
                break
        vals = [x for x in rtts if x is not None]
        avg = round(sum(vals) / len(vals), 2) if vals else None
        hops.append({"hop": hop_no, "ip": ip, "rtts": rtts[:3],
                     "avg_ms": avg, "hostname": hostname})
    hops.sort(key=lambda h: h["hop"])
    return hops


def run_traceroute(target: str, max_hops: int = 30, timeout: float = 2.0,
                   resolve_hostnames: bool = True) -> tuple[str, list[dict]]:
    """Run system traceroute. Returns (resolved_ip, hops). Raises RuntimeError/ValueError."""
    if not (1 <= max_hops <= 64):
        raise ValueError("max_hops must be 1..64")
    resolved = resolve_target(target)
    system = platform.system().lower()

    if system == "windows":
        cmd = ["tracert", "-d", "-h", str(max_hops),
               "-w", str(int(timeout * 1000)), resolved]
        if not shutil.which("tracert"):
            raise RuntimeError("tracert not found on this system")
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=max_hops * (timeout + 1) + 15)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        hops = _parse_windows(out)
    else:
        bin_ = shutil.which("traceroute") or shutil.which("tracepath")
        if not bin_:
            raise RuntimeError("traceroute not found. Install it: apt install traceroute")
        if "tracepath" in bin_:
            cmd = [bin_, "-m", str(max_hops), resolved]
        else:
            cmd = ["traceroute", "-n", "-m", str(max_hops),
                   "-w", str(timeout), resolved]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=max_hops * (timeout + 1) + 15)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        hops = _parse_unix(out)

    if resolve_hostnames:
        for h in hops:
            if h["ip"] and not h.get("hostname"):
                h["hostname"] = reverse_dns(h["ip"])

    return resolved, hops
