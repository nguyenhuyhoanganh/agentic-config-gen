# Kiến trúc hệ thống Config Chatbot

Tài liệu mô tả kiến trúc đầy đủ: multi-agent (triage + handoffs), tối ưu context, và backend FastAPI stream SSE.

---

## 1. Tổng quan

- **Mục tiêu**: Chat với user → phân loại ý (lookup device/config vs generate config vs general) → thu thập đủ thông tin → sinh đoạn config CLI và trả về (stream) cho user.
- **Thành phần chính**:
  - **Agents**: Triage (entry, handoffs) → Device Lookup Agent | Config Generator Agent.
  - **Tools**: Device API (list/get/config), Template API (list vendors/series/templates, required vars, render).
  - **Session + context optimization**: Giới hạn số message, gộp/tóm tắt history khi cần (RAG-like cho message).
  - **Backend**: FastAPI, endpoint chat stream SSE, mỗi conversation một session.

---

## 2. Luồng xử lý (flows)

### 2.1 Case phân biệt khi chat

| User intent | Nhận diện (từ nội dung + history) | Hành động |
|-------------|-----------------------------------|-----------|
| **Lookup device** | "xem device", "danh sách thiết bị", "config của device-001", "thông tin device" | Handoff → Device Lookup Agent. Agent gọi list_devices / get_device / get_device_config và trả lời. |
| **Generate config** | "thêm vlan", "cấu hình OSPF/BGP/SNMP", "tạo config", "add vlan", "config cho Juniper" | Handoff → Config Generator Agent. Agent hỏi lần lượt: vendor/series (hoặc device_id) → template → từng biến template; khi đủ gọi render_config và trả về config. |
| **General / unclear** | Chào hỏi, câu hỏi chung, hoặc chưa rõ ý | Triage trả lời trực tiếp hoặc hỏi lại (không handoff). |

- Mỗi **turn**: User gửi message → Backend gọi Runner với **entry agent = Triage** và **session** (session_id = conversation_id).
- Triage nhìn **history + message mới**:
  - Nếu đang trong luồng generate (history có handoff sang Config Generator và chưa có config cuối) → handoff lại Config Generator với message mới.
  - Nếu đang trong luồng lookup tương tự → handoff lại Device Lookup.
  - Nếu turn mới là intent mới → phân loại và handoff tương ứng hoặc trả lời tại chỗ.

### 2.2 Multi-turn và handoff

- **Handoff** = chuyển quyền “sở hữu” hội thoại sang agent chuyên biệt. Agent đó thấy toàn bộ history (có thể lọc qua `input_filter`).
- Sau khi specialist trả lời xong, run kết thúc; output cuối là của specialist.
- Turn tiếp theo: user gửi message mới → run lại với **Triage** + **cùng session**. Session đã lưu toàn bộ (bao gồm handoff và reply). Triage thấy “lần trước đã handoff Config Generator và hỏi vendor” → handoff lại Config Generator với message mới (“cisco”) → Config Generator hỏi series/template/… hoặc gọi render_config khi đủ.

---

## 3. Kiến trúc Agents

### 3.1 Sơ đồ

```
                    ┌─────────────────────────────────────────┐
                    │           Triage Agent (entry)           │
                    │  - Phân loại: lookup | generate | other  │
                    │  - Handoffs: [Device Lookup, Config Gen]│
                    │  - Không tools (chỉ handoff)             │
                    └──────────────┬──────────────────────────┘
                                   │
           ┌──────────────────────┼──────────────────────┐
           │ handoff               │ handoff              │
           ▼                       ▼                      │
┌──────────────────────┐  ┌──────────────────────────────┐ │
│ Device Lookup Agent  │  │ Config Generator Agent      │ │
│ - list_devices       │  │ - list_vendors_and_series   │ │
│ - get_device         │  │ - list_templates_for_series │ │
│ - get_device_config  │  │ - get_template_required_vars│ │
│                      │  │ - get_device (prefill)      │ │
│                      │  │ - render_config             │ │
└──────────────────────┘  └──────────────────────────────┘ │
```

### 3.2 Triage Agent

- **Name**: `TriageAgent`
- **Instructions**: 
  - Đọc toàn bộ hội thoại (có thể có handoff trước đó).
  - Phân loại ý user hiện tại: (1) Tra cứu device/config, (2) Tạo config mới, (3) Khác/chào hỏi.
  - Nếu history cho thấy đang trong luồng “generate config” (đã handoff Config Generator, chưa có config hoàn chỉnh) hoặc “lookup” → handoff lại đúng agent đó với message mới.
  - Nếu turn mới là intent rõ: “xem device”, “config device-001” → handoff Device Lookup; “thêm vlan”, “cấu hình OSPF” → handoff Config Generator.
  - Nếu không rõ hoặc general → trả lời ngắn, có thể hỏi lại.
- **Tools**: không (chỉ handoff).
- **Handoffs**: `[Device Lookup Agent, Config Generator Agent]`.
- Dùng `handoff_description` trên từng specialist để model dễ chọn.

### 3.3 Device Lookup Agent

- **Name**: `DeviceLookupAgent`
- **Instructions**: Chỉ trả lời về danh sách device, thông tin device, running config. Dùng tools để lấy dữ liệu rồi tóm tắt cho user. Không làm việc khác.
- **Tools**: `list_devices`, `get_device`, `get_device_config`.

### 3.4 Config Generator Agent

- **Name**: `ConfigGeneratorAgent`
- **Instructions**: 
  - Thu thập lần lượt: vendor/series (hoặc device_id để suy ra), loại config (template_key), từng biến của template.
  - Có thể gọi get_device(device_id) để prefill hostname, IP, v.v.
  - Khi đủ biến → gọi render_config; trả về config dạng text và hướng dẫn user apply qua terminal.
- **Tools**: `list_vendors_and_series`, `list_templates_for_series`, `get_template_required_vars`, `get_device`, `render_config`.

---

## 4. Tối ưu context length (RAG-like cho message)

- **Vấn đề**: History dài → vượt context window → lỗi hoặc cắt mất thông tin.
- **Giải pháp**:
  1. **Session + limit items**: Dùng `SessionSettings(limit=N)` (vd. 50 item gần nhất) khi gọi run. Chỉ lấy N message gần nhất từ session trước mỗi run.
  2. **session_input_callback**: Merge tùy chỉnh. Có thể:
     - Giữ K message gần nhất + 1 “summary” message đầu (nếu có summarizer) cho phần cũ.
     - Hoặc chỉ cắt đuôi: `history[-M:] + new_input`.
  3. **Summarization (tùy chọn)**: Khi số item > ngưỡng, gọi LLM (hoặc agent nhỏ) tóm tắt các message cũ thành 1 message “Tóm tắt hội thoại trước: …”, rồi session chỉ lưu summary + message gần đây. Có thể làm trong `session_input_callback`: nếu `len(history) > L`, gọi summarizer với `history[:-K]`, thay bằng 1 item summary, rồi `summary + history[-K:] + new_input`.
- **Khuyến nghị**: Bắt đầu với `SessionSettings(limit=50)`; sau nếu cần thêm mới thêm summarization trong callback.

---

## 5. Backend (FastAPI + SSE)

### 5.1 Vai trò

- Nhận message từ client (chat UI).
- Duy trì 1 session per conversation (session_id = conversation_id).
- Gọi Runner với Triage + session; stream token/event từ agent về client qua SSE.

### 5.2 API

- **POST /chat** (hoặc **POST /conversations/{id}/messages**):
  - Body: `{ "message": "..." }`.
  - Query hoặc body: `conversation_id` (nếu không có thì tạo mới).
  - Response: **StreamingResponse** `text/event-stream` (SSE).
  - Mỗi event: `data: {"type": "token", "content": "..."}` hoặc `{"type": "done", "content": "..."}` để client append token hoặc coi như kết thúc.

- **Cách stream**:
  - Dùng `Runner.run_streamed(triage_agent, input, session=session)`.
  - Trong `result.stream_events()`: lọc `raw_response_event` với `ResponseTextDeltaEvent` → gửi delta qua SSE.
  - Khi stream xong, gửi event `done` với `final_output` (hoặc để client tự ghép từ các token).

### 5.3 Session backend

- Trong app: dùng **SQLiteSession(session_id)** hoặc backend session khác (Redis, v.v.) với `session_id = conversation_id`.
- Mỗi conversation_id một session; khi user gửi message mới, load session cũ, append user message, run với session đó, sau run session tự lưu items mới.

### 5.4 Cấu trúc thư mục backend

```
backend/
  __init__.py
  app.py              # FastAPI app, route POST /chat/stream (SSE)
  agents_runner.py    # Setup Ollama, create triage agent, run_streamed -> SSE
  requirements.txt   # fastapi, uvicorn (+ project requirements cho agents)
```

- **app.py**: POST `/chat/stream` body `{ "message": "...", "conversation_id": "..." }`; trả về `text/event-stream` với các event `data: {"type": "token"|"done"|"error", "content": "..."}`.
- **agents_runner.py**: `get_runner()` lazy init Triage agent + RunConfig (session limit 50); `run_chat_stream(conversation_id, message)` async generator yield `("token", delta)` và `("done", full_text)`.
- Session: `session_utils.create_session(conversation_id)` → SQLiteSession, file lưu tại `session_data/{conversation_id}.db`.

---

## 6. Triển khai từng bước

1. **Agents**: Implement Triage (handoffs), Device Lookup (tools), Config Generator (tools); export một hàm `create_triage_agent()` trả về agent entry (đã gắn handoffs).
2. **Session + context**: Dùng `SQLiteSession(conversation_id)`; `RunConfig(session_settings=SessionSettings(limit=50))`; (tùy chọn) `session_input_callback` để summarization.
3. **Backend**: FastAPI app, POST stream endpoint, gọi `run_streamed` và stream SSE; lưu session theo conversation_id.
4. **Client**: Gọi POST với conversation_id và message; nhận EventSource; hiển thị token khi nhận, khi `done` thì coi như xong turn.

---

## 7. Lưu ý

- **Ollama**: Set `set_default_openai_client(base_url=..., api_key=...)`, `set_default_openai_api("chat_completions")` trước mọi run.
- **Handoff history**: Có thể dùng `input_filter=handoff_filters.remove_all_tools` trên handoff để specialist không thấy chi tiết tool call cũ, giảm nhiễu.
- **Guardrails** (sau này): Input guardrail kiểm tra prompt injection; output guardrail kiểm tra config không lộ credential thật.

Tài liệu này đủ để triển khai kiến trúc và backend theo đúng luồng đã thiết kế.
