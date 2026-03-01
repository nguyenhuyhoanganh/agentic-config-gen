"""Fake API tools: list devices, get device by id, get running config by device_id."""

from __future__ import annotations

import json
from pathlib import Path

from agents import function_tool

# Project root: agents_and_tools/tools/device_tools.py -> parent.parent.parent
_BASE = Path(__file__).resolve().parent.parent.parent
_DATA = _BASE / "data"


def _load_json(name: str) -> dict:
    p = _DATA / name
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@function_tool
def list_devices(site: str | None = None, vendor_id: str | None = None) -> str:
    """List all devices. Optionally filter by site (e.g. Hanoi-DC1) or vendor_id (e.g. cisco-001).

    Args:
        site: Filter by site name.
        vendor_id: Filter by vendor id.
    """
    data = _load_json("devices.json")
    devices = data.get("devices", [])
    if site:
        devices = [d for d in devices if d.get("site") == site]
    if vendor_id:
        devices = [d for d in devices if d.get("vendor_id") == vendor_id]
    out = []
    for d in devices:
        out.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "model": d.get("model"),
            "site": d.get("site"),
            "vendor_id": d.get("vendor_id"),
            "series_id": d.get("series_id"),
            "management_ip": d.get("management", {}).get("ip"),
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


@function_tool
def get_device(device_id: str) -> str:
    """Get full device info by device_id (e.g. device-001). Excludes passwords for security in response summary.

    Args:
        device_id: Device ID, e.g. device-001.
    """
    data = _load_json("devices.json")
    for d in data.get("devices", []):
        if d.get("id") == device_id:
            out = dict(d)
            if "credentials" in out:
                out["credentials"] = {k: "***" for k in out["credentials"]}
            return json.dumps(out, indent=2, ensure_ascii=False)
    return json.dumps({"error": f"Device {device_id} not found"})


@function_tool
def get_device_config(device_id: str) -> str:
    """Get running config (full text) for a device by device_id.

    Args:
        device_id: Device ID, e.g. device-001.
    """
    data = _load_json("configs.json")
    configs = data.get("configs", {})
    if device_id not in configs:
        return json.dumps({"error": f"No config found for device {device_id}"})
    return configs[device_id].get("content", "")
