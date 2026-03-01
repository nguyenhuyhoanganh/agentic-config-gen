"""
Chatbot CLI: multi-turn chat with Triage agent (handoffs to Device Lookup / Config Generator), Ollama.

Chạy từ project root:
  python -m agents_and_tools.chatbot

Yêu cầu: Ollama đang chạy, đã pull model. Có thể set OLLAMA_MODEL, OLLAMA_BASE_URL.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI

from agents import Runner, set_default_openai_api, set_default_openai_client, set_tracing_disabled
from agents_and_tools.agents import create_triage_agent
from agents_and_tools.session_utils import create_session, run_config_with_context_limit


def setup_ollama():
    set_tracing_disabled(True)
    set_default_openai_api("chat_completions")
    set_default_openai_client(
        AsyncOpenAI(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        )
    )


async def run_chatbot():
    setup_ollama()
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    agent = create_triage_agent(model=model)
    session = create_session("cli-session")
    run_config = run_config_with_context_limit(limit=50)

    print("Config Chatbot (Triage + Device Lookup / Config Gen). Gõ 'quit' hoặc 'exit' để thoát.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        try:
            result = await Runner.run(agent, user_input, session=session, run_config=run_config)
            print("\nBot:", result.final_output or "(no output)", "\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(run_chatbot())
