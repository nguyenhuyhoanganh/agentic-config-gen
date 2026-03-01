"""Ollama + Triage agent setup for backend."""

from __future__ import annotations

import os

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


"""Ollama + Triage agent setup for backend."""

from __future__ import annotations

import os

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


_agent_cache = None
_run_config_cache = None


def get_runner():
    """Lazy init: call setup once, create triage agent with context limit."""
    global _agent_cache, _run_config_cache
    if _agent_cache is None:
        setup_ollama()
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        _agent_cache = create_triage_agent(model=model)
        _run_config_cache = run_config_with_context_limit(limit=50)
    return _agent_cache, _run_config_cache


async def run_chat_stream(conversation_id: str, message: str):
    """Run triage agent with session, stream events. Yields (event_type, data) for SSE."""
    agent, run_config = get_runner()
    session = create_session(conversation_id)

    result = await Runner.run_streamed(
        agent,
        message,
        session=session,
        run_config=run_config,
    )

    final_content = []
    async for event in result.stream_events():
        if event.type == "raw_response_event" and event.data is not None:
            if hasattr(event.data, "delta") and event.data.delta:
                delta = event.data.delta
                final_content.append(delta)
                yield ("token", delta)
        elif event.type == "run_item_stream_event" and event.item is not None:
            if getattr(event.item, "type", None) == "message_output_item":
                if hasattr(event.item, "output") and event.item.output:
                    out = getattr(event.item.output, "content", event.item.output)
                    if isinstance(out, list) and out:
                        text = out[0].get("text", "") if isinstance(out[0], dict) else str(out[0])
                    else:
                        text = str(out) if out else ""
                    if text:
                        yield ("token", text)

    full = "".join(final_content) if final_content else getattr(result, "final_output", "") or ""
    yield ("done", full)
