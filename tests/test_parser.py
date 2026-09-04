"""Parser + map tests (no network needed except geo test which is optional)."""
from traceroute_viz.map import generate_map_html
from traceroute_viz.tracer import _parse_unix, _parse_windows

WIN_SAMPLE = """
Tracing route to dns.google [8.8.8.8]
over a maximum of 30 hops:

  1    <1 ms    <1 ms    <1 ms  192.168.1.1
  2     *        *        *     Request timed out.
  3    10 ms    12 ms    11 ms  8.8.8.8
"""

UNIX_SAMPLE = """
traceroute to 8.8.8.8 (8.8.8.8), 30 hops max
 1  192.168.1.1 (192.168.1.1)  0.5 ms  0.4 ms  0.3 ms
 2  * * *
 3  8.8.8.8 (8.8.8.8)  10.1 ms  11.2 ms  9.8 ms
"""


def test_parse_windows():
    hops = _parse_windows(WIN_SAMPLE)
    assert len(hops) == 3
    assert hops[0]["ip"] == "192.168.1.1"
    assert hops[0]["avg_ms"] == 0.5
    assert hops[1]["ip"] is None
    assert hops[1]["avg_ms"] is None
    assert hops[2]["ip"] == "8.8.8.8"


def test_parse_unix():
    hops = _parse_unix(UNIX_SAMPLE)
    assert len(hops) == 3
    assert hops[0]["ip"] == "192.168.1.1"
    assert hops[1]["ip"] is None
    assert hops[2]["ip"] == "8.8.8.8"


def test_map_html():
    hops = [{"hop": 1, "ip": "8.8.8.8", "avg_ms": 10.0,
             "geo": {"lat": 37.75, "lon": -97.82, "city": "Mountain View",
                     "country": "United States", "ok": True}}]
    out = generate_map_html(hops, "8.8.8.8")
    assert "leaflet" in out.lower()
    assert "8.8.8.8" in out
