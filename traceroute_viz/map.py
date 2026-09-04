"""Generate a standalone Leaflet map HTML (no Python map deps needed)."""
from __future__ import annotations

import html


def _points(hops: list[dict]) -> list[dict]:
    pts = []
    for h in hops:
        g = h.get("geo") or {}
        if g.get("lat") is not None and g.get("lon") is not None:
            pts.append({"hop": h["hop"], "ip": h.get("ip"),
                        "city": g.get("city", "?"), "country": g.get("country", "?"),
                        "lat": g["lat"], "lon": g["lon"],
                        "avg_ms": h.get("avg_ms")})
    return pts


def generate_map_html(hops: list[dict], target: str) -> str:
    pts = _points(hops)
    safe_target = html.escape(str(target))
    if pts:
        center = f"[{pts[0]['lat']}, {pts[0]['lon']}]"
        zoom = 2 if len(pts) > 1 else 6
    else:
        center = "[20, 0]"
        zoom = 2

    markers_js = ""
    for p in pts:
        popup = html.escape(f"#{p['hop']} {p['ip']} — {p['city']}, {p['country']} ({p['avg_ms']} ms)")
        markers_js += (
            f"L.marker([{p['lat']}, {p['lon']}]).addTo(map)"
            f".bindPopup({popup!r});\n"
        )
    line = ",\n".join(f"[{p['lat']}, {p['lon']}]" for p in pts)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Traceroute to {safe_target}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>html,body,#map{{height:100%;margin:0}} .info{{position:absolute;top:10px;left:10px;z-index:500;background:#111827;color:#fff;padding:8px 12px;border-radius:8px;font-family:sans-serif}}</style>
</head><body>
<div id="map"></div>
<div class="info">Traceroute to <b>{safe_target}</b> — {len(pts)} geo-located hops</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var map = L.map('map').setView({center}, {zoom});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{maxZoom: 20, attribution: '&copy; OSM &copy; CARTO'}}).addTo(map);
{markers_js}
var line = L.polyline([{line}], {{color: 'red'}}).addTo(map);
if ({str(len(pts) > 1).lower()}) map.fitBounds(line.getBounds());
</script></body></html>"""


def save_map(hops: list[dict], target: str, path: str) -> str:
    html_str = generate_map_html(hops, target)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
    return path
