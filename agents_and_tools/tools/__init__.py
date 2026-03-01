# Tools for config chatbot
from agents_and_tools.tools.device_tools import get_device, get_device_config, list_devices
from agents_and_tools.tools.template_tools import (
    get_template_required_vars,
    list_templates_for_series,
    list_vendors_and_series,
    render_config,
)

__all__ = [
    "list_devices",
    "get_device",
    "get_device_config",
    "list_vendors_and_series",
    "list_templates_for_series",
    "get_template_required_vars",
    "render_config",
]
