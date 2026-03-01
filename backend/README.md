# Backend – Config Chatbot API

FastAPI app: chat stream qua **SSE** (Server-Sent Events).

## Chạy

Từ **project root** (có venv đã activate, đã cài requirements):

```bash
# Cài dependency (một lần)
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Chạy server
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

- **API**: http://localhost:8000/docs  
- **Test UI**: http://localhost:8000/static/index.html  
- **Health**: GET http://localhost:8000/health  

## Endpoints

- **POST /chat/stream**  
  Body: `{ "message": "...", "conversation_id": "optional-id" }`  
  Response: `text/event-stream`  
  Mỗi event: `data: {"type": "token"|"done"|"error", "content": "..."}`  

- **GET /health**  
  Trả về `{"status": "ok"}`  

## Luồng

1. Client gửi message + conversation_id (nếu không có thì dùng "default").
2. Backend lấy/tao session cho conversation_id (SQLite trong `session_data/`).
3. Chạy Triage agent với session + RunConfig(limit=50); stream từ `Runner.run_streamed`.
4. Gửi từng token qua SSE; cuối gửi event "done" với full text.
