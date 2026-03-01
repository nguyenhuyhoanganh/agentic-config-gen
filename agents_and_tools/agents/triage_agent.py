"""Triage Agent: entry point, classifies intent and handoffs to Device Lookup or Config Generator."""

from agents import Agent, handoff

from agents_and_tools.agents.config_generator_agent import create_config_generator_agent
from agents_and_tools.agents.device_lookup_agent import create_device_lookup_agent

TRIAGE_INSTRUCTIONS = """You are the triage agent for a network config chatbot. You see the full conversation history and the latest user message.

Your ONLY job is to decide:
1. **Device lookup**: User wants to list devices, see device info, or see running config (e.g. "xem device", "danh sách thiết bị", "config của device-001", "thông tin device"). → Hand off to Device Lookup Agent.
2. **Config generation**: User wants to generate/create config (e.g. "thêm vlan", "cấu hình OSPF/BGP/SNMP", "tạo config", "add vlan"). Or the conversation is already in a "config generation" flow (you previously handed off to Config Generator and they asked for vendor/series/template/variables). → Hand off to Config Generator Agent with the latest user message in context.
3. **Other**: Greetings, unclear intent, or off-topic. → Reply briefly yourself; do NOT hand off.

If the last turn was a handoff to Config Generator or Device Lookup and the user is now replying (e.g. "cisco", "device-001", "vlan 10"), hand off again to the SAME agent so they can continue the flow. Do not answer in place.

You have no tools. You must use handoffs to delegate. Be very short when you reply in place (other case)."""


def create_triage_agent(model: str):
    device_lookup = create_device_lookup_agent(model)
    config_generator = create_config_generator_agent(model)

    return Agent(
        name="TriageAgent",
        instructions=TRIAGE_INSTRUCTIONS,
        model=model,
        tools=[],  # no tools, only handoffs
        handoffs=[
            device_lookup,
            config_generator,
        ],
    )
