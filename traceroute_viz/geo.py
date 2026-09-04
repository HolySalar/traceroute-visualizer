"""IP geolocation with fallback providers + in-memory cache.

Primary: https://ipwho.is/{ip} (free, no key, HTTPS — works from IR)
Fallback: http://ip-api.com/json/{ip} (free, no key, HTTP)
"""
from __future__ import annotations

import ipaddress
import time

import requests

_cache: dict[str, dict] = {}


def is_private(ip: str | None) -> bool:
    if not ip:
        return True
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return True


def _from_ipwho(ip: str, timeout: float = 8.0) -> dict | None:
    try:
        r = requests.get(f"https://ipwho.is/{ip}", timeout=timeout)
        d = r.json()
        if d.get("success"):
            conn = d.get("connection") or {}
            return {"ip": ip, "ok": True, "private": False,
                    "country": d.get("country", "?"),
                    "countryCode": d.get("country_code", "?"),
                    "city": d.get("city", "?"),
                    "lat": d.get("latitude"), "lon": d.get("longitude"),
                    "isp": conn.get("isp", "") or d.get("isp", ""),
                    "org": conn.get("org", ""), "as": conn.get("asn", ""),
                    "provider": "ipwho.is"}
    except Exception:
        pass
    return None


def _from_ipapi(ip: str, timeout: float = 5.0) -> dict | None:
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon,isp,org,as,query",
            timeout=timeout)
        d = r.json()
        if d.get("status") == "success":
            return {"ip": ip, "ok": True, "private": False,
                    "country": d.get("country", "?"),
                    "countryCode": d.get("countryCode", "?"),
                    "city": d.get("city", "?"),
                    "lat": d.get("lat"), "lon": d.get("lon"),
                    "isp": d.get("isp", ""), "org": d.get("org", ""),
                    "as": d.get("as", ""), "provider": "ip-api"}
    except Exception:
        pass
    return None


def geolocate_ip(ip: str | None, timeout: float = 8.0) -> dict:
    """Return geo dict for one IP. Never raises."""
    if not ip:
        return {"ip": None, "ok": False, "private": True}
    if ip in _cache:
        return _cache[ip]
    if is_private(ip):
        res = {"ip": ip, "ok": True, "private": True,
               "country": "Private/LAN", "city": "-", "lat": None, "lon": None,
               "isp": "LAN", "org": "", "as": "", "provider": "local"}
        _cache[ip] = res
        return res
    res = _from_ipwho(ip, timeout=timeout)
    if res is None:
        res = _from_ipapi(ip, timeout=5.0)
    if res is None:
        res = {"ip": ip, "ok": False, "private": False,
               "error": "geolocation unavailable (both providers failed)"}
    _cache[ip] = res
    return res


def batch_geolocate(hops: list[dict], delay: float = 0.25) -> list[dict]:
    """Enrich hops with 'geo' key."""
    seen: dict[str, dict] = {}
    for h in hops:
        ip = h.get("ip")
        if not ip:
            h["geo"] = {"ip": None, "ok": False}
            continue
        if ip in seen:
            h["geo"] = seen[ip]
            continue
        g = geolocate_ip(ip)
        seen[ip] = g
        h["geo"] = g
        if not g.get("private") and g.get("ok") and delay:
            time.sleep(delay)
    return hops


def clear_cache() -> None:
    _cache.clear()
