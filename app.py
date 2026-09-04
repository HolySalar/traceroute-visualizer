"""Flask web UI — run: python app.py then open http://127.0.0.1:5000"""
from flask import Flask, jsonify, render_template, request

from traceroute_viz.geo import batch_geolocate
from traceroute_viz.tracer import resolve_target, run_traceroute

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/trace")
def api_trace():
    data = request.get_json(force=True, silent=True) or {}
    target = str(data.get("host", "")).strip()
    if not target:
        return jsonify({"ok": False, "error": "host is required"}), 400
    try:
        max_hops = min(max(int(data.get("max_hops", 30)), 1), 64)
    except (ValueError, TypeError):
        max_hops = 30
    no_geo = bool(data.get("no_geo", False))
    try:
        resolved, hops = run_traceroute(target, max_hops=max_hops)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    if not no_geo:
        batch_geolocate(hops)
    return jsonify({"ok": True, "target": target, "resolved": resolved, "hops": hops})


@app.get("/api/resolve")
def api_resolve():
    host = request.args.get("host", "").strip()
    if not host:
        return jsonify({"ok": False}), 400
    try:
        return jsonify({"ok": True, "ip": resolve_target(host)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/demo")
def api_demo():
    """Sample trace so the map can be tested even offline/filtered."""
    hops = [
        {"hop": 1, "ip": "192.168.1.1", "rtts": [0.5, 0.4, 0.6], "avg_ms": 0.5,
         "hostname": "router.local",
         "geo": {"ip": "192.168.1.1", "ok": True, "private": True,
                 "country": "Private/LAN", "city": "-", "lat": None, "lon": None, "isp": "LAN"}},
        {"hop": 2, "ip": "185.55.226.1", "rtts": [12.0, 11.5, 12.4], "avg_ms": 11.97,
         "hostname": None,
         "geo": {"ip": "185.55.226.1", "ok": True, "private": False,
                 "country": "Iran", "city": "Tehran", "lat": 35.6892, "lon": 51.3890,
                 "isp": "Demo ISP", "provider": "demo"}},
        {"hop": 3, "ip": "8.8.8.8", "rtts": [85.0, 84.2, 86.1], "avg_ms": 85.1,
         "hostname": "dns.google",
         "geo": {"ip": "8.8.8.8", "ok": True, "private": False,
                 "country": "United States", "city": "San Jose",
                 "lat": 37.3361, "lon": -121.8905, "isp": "Google LLC", "provider": "demo"}},
    ]
    return jsonify({"ok": True, "target": "demo", "resolved": "8.8.8.8", "hops": hops})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
