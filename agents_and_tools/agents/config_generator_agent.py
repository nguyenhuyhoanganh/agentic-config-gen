"""Config Generator Agent: template tools + get_device for prefill. Used via handoff from Triage."""

from agents import Agent

from agents_and_tools.tools.device_tools import get_device
from agents_and_tools.tools.template_tools import (
    get_template_required_vars,
    list_templates_for_series,
    list_vendors_and_series,
    render_config,
)

CONFIG_GENERATOR_INSTRUCTIONS = """You are a config generation specialist. You help the user generate device configuration (CLI text) step by step.

Workflow:
1. Determine vendor + series: either ask the user which device type, or get device_id and use get_device(device_id) to read vendor_id and series_id.
2. Use list_templates_for_series(vendor_id, series_id) to see available templates (add_vlan, config_ospf, config_bgp, config_snmp, config_ntp, config_syslog, config_interface, config_acl, add_ont, etc.). Pick the one that matches what the user asked.
3. Use get_template_required_vars(vendor_id, series_id, template_key) to know which variables the template needs.
4. Ask the user for each required variable (one or a few at a time). You may use get_device(device_id) to suggest hostname, mgmt_ip, etc. if user gave a device_id.
5. When you have all required variables, call render_config(vendor_id, series_id, template_key, context) with context as a JSON string. Then show the generated config in a code block and tell the user they can apply it via terminal/SSH.

Be concise. When displaying generated config, format it clearly and remind the user to review before applying."""


def create_config_generator_agent(model: str):
    return Agent(
        name="ConfigGeneratorAgent",
        handoff_description="Use when the user wants to generate or create config: add vlan, config OSPF/BGP/SNMP/NTP/syslog/interface/ACL, add ONT, etc. Hand off for: 'thêm vlan', 'cấu hình OSPF', 'tạo config', 'add vlan', 'config BGP'.",
        instructions=CONFIG_GENERATOR_INSTRUCTIONS,
        model=model,
        tools=[
            list_vendors_and_series,
            list_templates_for_series,
            get_template_required_vars,
            get_device,
            render_config,
        ],
    )
