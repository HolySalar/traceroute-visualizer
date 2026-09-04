"""CLI: python -m traceroute_viz.cli google.com --map trace.html --output trace.json"""
from __future__ import annotations

import argparse
import json
import sys

from .geo import batch_geolocate
from .map import save_map
from .tracer import run_traceroute


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Traceroute + geolocation + map")
    p.add_argument("target", help="hostname or IP, e.g. 8.8.8.8")
    p.add_argument("--max-hops", type=int, default=30)
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--no-geo", action="store_true", help="skip ip-api geolocation")
    p.add_argument("--no-dns", action="store_true", help="skip reverse DNS")
    p.add_argument("--output", "-o", default=None, help="save JSON result")
    p.add_argument("--map", "-m", default=None, help="save Leaflet map HTML")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        resolved, hops = run_traceroute(
            args.target, max_hops=args.max_hops, timeout=args.timeout,
            resolve_hostnames=not args.no_dns)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.no_geo:
        batch_geolocate(hops)

    print(f"Target: {args.target} ({resolved}) — {len(hops)} hops\n")
    print(f"{'Hop':<5}{'IP':<17}{'Avg':<9}Location / Host")
    print("-" * 60)
    for h in hops:
        ip = h["ip"] or "***"
        avg = f"{h['avg_ms']} ms" if h["avg_ms"] is not None else "timeout"
        g = h.get("geo") or {}
        loc = ""
        if g.get("city") and g.get("city") != "-":
            loc = f"{g.get('city')}, {g.get('country')}"
        elif h.get("hostname"):
            loc = h["hostname"]
        print(f"{h['hop']:<5}{ip:<17}{avg:<9}{loc}")

    result = {"target": args.target, "resolved": resolved, "hops": hops}
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved JSON -> {args.output}")
    if args.map:
        save_map(hops, args.target, args.map)
        print(f"Saved map  -> {args.map}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
