"""
FastAPI backend: chat stream SSE.

Chạy từ project root:
  uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

Hoặc:
  python -m uvicorn backend.app:app --reload
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root for agents_and_tools
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agents_runner import run_chat_stream

app = FastAPI(title="Config Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str
    conversation_id: str | None = None


async def sse_generator(conversation_id: str, message: str):
    """Yield SSE events: data: {json}\n\n"""
    try:
        async for event_type, data in run_chat_stream(conversation_id, message):
            payload = json.dumps({"type": event_type, "content": data}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/chat/stream")
async def chat_stream(body: ChatMessage):
    """Stream chat response via Server-Sent Events (SSE)."""
    conversation_id = body.conversation_id or "default"
    return StreamingResponse(
        sse_generator(conversation_id, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# Static test UI (mount last): http://localhost:8000/static/index.html
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
