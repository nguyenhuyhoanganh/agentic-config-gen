"""Device Lookup Agent: only device/list/config tools. Used via handoff from Triage."""

from agents import Agent

from agents_and_tools.tools.device_tools import get_device, get_device_config, list_devices

DEVICE_LOOKUP_INSTRUCTIONS = """You are a device lookup specialist. You ONLY answer questions about devices and their running config.

- Use list_devices() to list devices (optional filters: site, vendor_id).
- Use get_device(device_id) to get full device info (without passwords).
- Use get_device_config(device_id) to get the full running config text.

Summarize results clearly for the user. Do not generate new configs or discuss templates. If the user asks for something else, say you only handle device lookup and suggest they ask for "generate config" or "add vlan" etc. elsewhere."""


def create_device_lookup_agent(model: str):
    return Agent(
        name="DeviceLookupAgent",
        handoff_description="Use when the user wants to list devices, view device info, or view running config of a device. Hand off for: 'xem device', 'danh sách thiết bị', 'config của device-001', 'thông tin device'.",
        instructions=DEVICE_LOOKUP_INSTRUCTIONS,
        model=model,
        tools=[list_devices, get_device, get_device_config],
    )
