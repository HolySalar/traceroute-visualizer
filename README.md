# 🌐 Traceroute Visualizer

Cross-platform traceroute tool with IP geolocation and interactive map.
No admin rights needed — uses system `tracert` / `traceroute`.

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features
- 🖥️ Works on **Windows / Linux / macOS** (parses `tracert` + `traceroute`)
- 🗺️ Geolocates every public hop via [ip-api.com](http://ip-api.com) (free, no key) + cache
- 📊 CLI table + JSON export + standalone Leaflet map HTML
- 🌍 Flask web UI with live map (OpenStreetMap)
- 🔍 Reverse DNS per hop, private-IP detection, timeout handling

## Quickstart

```powershell
pip install -r requirements.txt

# CLI
python -m traceroute_viz.cli 8.8.8.8 --map trace.html --output trace.json

# Web UI
python app.py
# open http://127.0.0.1:5000
```

## CLI options

```
python -m traceroute_viz.cli google.com --max-hops 20 --timeout 2 --no-geo --no-dns -o out.json -m map.html
```

## API

`POST /api/trace`:
```json
{"host": "8.8.8.8", "max_hops": 30}
```

Response: `{ok, target, resolved, hops[]}` where each hop is:
```json
{"hop": 3, "ip": "8.8.8.8", "rtts": [10.1, 11.2, 9.8], "avg_ms": 10.37,
 "hostname": "dns.google",
 "geo": {"country": "United States", "city": "Ashburn", "lat": 39.03, "lon": -77.5, "isp": "Google LLC"}}
```

## Tests

```powershell
pip install pytest
pytest -q
```

## Docker

```powershell
docker build -t traceroute-viz .
docker run -p 5000:5000 traceroute-viz
```

> ⚠️ Note: inside Docker, traceroute shows container gateway hops. For real path, run natively.

## Project structure
```
app.py                  # Flask web UI
traceroute_viz/
  tracer.py             # cross-platform tracert/traceroute engine + parsers
  geo.py                # ip-api geolocation + cache + private detection
  map.py                # standalone Leaflet HTML generator
  cli.py                # terminal interface
templates/index.html    # web UI (FA + map)
tests/test_parser.py    # parser tests, no network needed
examples/sample_trace.json
```

## برای رزومه
ایده‌های توسعه: نمودار latency با matplotlib، تشخیص ASN، خروجی CSV، حالت MTR پیوسته، تست سرعت per-hop.
```

---

## 🇮🇷 توضیح فارسی

ابزار تریس‌روت که مسیر بسته تا مقصد را پیدا می‌کند، هر هاپ را روی نقشه نشان می‌دهد و پینگ و ISP را گزارش می‌دهد. بدون نیاز به دسترسی ادمین کار می‌کند.
