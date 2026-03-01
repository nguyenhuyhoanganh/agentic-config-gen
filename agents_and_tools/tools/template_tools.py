"""Template tools: list vendors/series, list templates for series, get required variables, render config."""

from __future__ import annotations

import json
from pathlib import Path

from agents import function_tool
from jinja2 import Environment, FileSystemLoader, meta

_BASE = Path(__file__).resolve().parent.parent.parent
_DATA = _BASE / "data"
_TEMPLATES = _BASE / "templates"


def _load_json(name: str) -> dict:
    p = _DATA / name
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _vendor_series_to_path(vendor_id: str, series_id: str) -> Path:
    v = vendor_id.split("-")[0] if vendor_id else ""
    s = series_id.split("-", 1)[1] if "-" in series_id else series_id
    return _TEMPLATES / v / s


@function_tool
def list_vendors_and_series() -> str:
    """List all vendors and their series (for template selection). Returns vendor id, name, series id, series name."""
    data = _load_json("vendors.json")
    vendors = data.get("vendors", [])
    out = []
    for v in vendors:
        for s in v.get("series", []):
            out.append({
                "vendor_id": v.get("id"),
                "vendor_name": v.get("name"),
                "series_id": s.get("id"),
                "series_name": s.get("name"),
            })
    return json.dumps(out, indent=2, ensure_ascii=False)


@function_tool
def list_templates_for_series(vendor_id: str, series_id: str) -> str:
    """List available config template names for a vendor/series. Use these as template_key in render_config.

    Args:
        vendor_id: Vendor ID from list_vendors_and_series, e.g. juniper-001.
        series_id: Series ID, e.g. juniper-mx.
    """
    folder = _vendor_series_to_path(vendor_id, series_id)
    if not folder.exists():
        return json.dumps({"error": f"Template folder not found: {folder}", "templates": []})
    names = [f.stem for f in folder.glob("*.j2")]
    return json.dumps({"vendor_id": vendor_id, "series_id": series_id, "templates": sorted(names)})


@function_tool
def get_template_required_vars(vendor_id: str, series_id: str, template_key: str) -> str:
    """Get required variables for a template (from Jinja). template_key is filename without .j2, e.g. add_vlan.

    Args:
        vendor_id: e.g. juniper-001.
        series_id: e.g. juniper-mx.
        template_key: Template name without .j2, e.g. add_vlan, config_ospf.
    """
    folder = _vendor_series_to_path(vendor_id, series_id)
    if not folder.exists():
        return json.dumps({"error": f"Template folder not found: {folder}"})
    path = folder / f"{template_key}.j2"
    if not path.exists():
        return json.dumps({"error": f"Template not found: {path}", "available": [f.stem for f in folder.glob("*.j2")]})
    env = Environment(loader=FileSystemLoader(str(folder)))
    try:
        ast = env.parse(path.read_text(encoding="utf-8"))
        vars_found = list(meta.find_undeclared_variables(ast))
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"template_key": template_key, "required_variables": sorted(vars_found)})


@function_tool
def render_config(vendor_id: str, series_id: str, template_key: str, context: str) -> str:
    """Render config from template with given context. context is JSON string of variables.

    Args:
        vendor_id: e.g. juniper-001.
        series_id: e.g. juniper-mx.
        template_key: Template name without .j2, e.g. add_vlan.
        context: JSON object with variable names as keys and values for the template.
    """
    folder = _vendor_series_to_path(vendor_id, series_id)
    if not folder.exists():
        return json.dumps({"error": f"Template folder not found: {folder}"})
    path = folder / f"{template_key}.j2"
    if not path.exists():
        return json.dumps({"error": f"Template not found: {path}"})
    try:
        ctx = json.loads(context)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON context: {e}"})
    env = Environment(loader=FileSystemLoader(str(folder)))
    template = env.get_template(f"{template_key}.j2")
    try:
        out = template.render(**ctx)
    except Exception as e:
        return json.dumps({"error": f"Template render failed: {e}"})
    return out
