# Agents & Tools – Config Chatbot

Chatbot dùng **OpenAI Agents SDK**, kết nối **Ollama**, với kiến trúc **Triage + Handoffs**:

- **Triage Agent** (entry): Phân loại ý user → handoff sang **Device Lookup Agent** hoặc **Config Generator Agent**.
- **Device Lookup Agent**: Tools `list_devices`, `get_device`, `get_device_config` (tra cứu device/config).
- **Config Generator Agent**: Tools template + `get_device` (prefill) + `render_config` (thu thập biến → sinh config CLI).

Có **session** (SQLite) và **giới hạn context** (limit 50 item) để tối ưu độ dài history.

**Backend**: FastAPI + SSE stream tại `backend/` – xem `docs/ARCHITECTURE.md` và `backend/README.md`.

## Cấu trúc

- **tools/**
  - `device_tools.py`: list_devices, get_device, get_device_config
  - `template_tools.py`: list_vendors_and_series, list_templates_for_series, get_template_required_vars, render_config
- **agents/**
  - `triage_agent.py`: entry, handoffs → Device Lookup / Config Generator
  - `device_lookup_agent.py`: tools device only
  - `config_generator_agent.py`: tools template + get_device + render_config
  - `config_chatbot.py`: single-agent legacy (optional)
- **session_utils.py**: create_session(conversation_id), run_config_with_context_limit(limit=50)
- **chatbot.py**: CLI loop với Triage + session

## Chạy

1. **Tạo venv và cài dependency** (từ project root):

   **Windows (CMD/PowerShell):**
   ```batch
   setup_venv.bat
   ```
   Hoặc thủ công:
   ```batch
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   **Linux/macOS:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Chạy Ollama và pull model (vd: `llama3.2` hoặc `gpt-oss20b` nếu bạn có):

   ```bash
   ollama serve
   ollama pull llama3.2
   ```

3. **Kích hoạt venv** (nếu chưa bật), rồi chạy chatbot:

   **Windows:**
   ```batch
   .venv\Scripts\activate
   python -m agents_and_tools.chatbot
   ```

   **Linux/macOS:**
   ```bash
   source .venv/bin/activate
   python -m agents_and_tools.chatbot
   ```

4. **Biến môi trường** (tuỳ chọn):

   - `OLLAMA_MODEL`: model name (mặc định `llama3.2`)
   - `OLLAMA_BASE_URL`: base URL Ollama (mặc định `http://localhost:11434/v1`)
   - `OLLAMA_API_KEY`: API key (mặc định `ollama`)

## Nhúng vào app khác

- Entry agent: `from agents_and_tools.agents import create_triage_agent`
- Setup Ollama như trong `chatbot.py` hoặc `backend/agents_runner.py`
- Multi-turn: dùng `session=create_session(conversation_id)` và `run_config=run_config_with_context_limit(50)`; stream thì dùng `Runner.run_streamed` như trong `backend/agents_runner.run_chat_stream`
