# OpenAI Agents SDK – Tài liệu tóm tắt (Agentic)

Tài liệu này tóm tắt **Tools**, **Handoffs**, **Guardrails**, **Sessions** và các tính năng agentic của [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) để xây dựng ứng dụng agent.

---

## 1. Tổng quan

SDK dựa trên **3 primitive chính**:

| Primitive | Mô tả |
|-----------|--------|
| **Agents** | LLM + instructions + tools – đơn vị xử lý chính |
| **Handoffs** | Chuyển giao sang agent khác (decentralized, agent mới “nắm” hội thoại) |
| **Agents as tools** | Gọi agent khác như một tool (orchestrator giữ control) |
| **Guardrails** | Kiểm tra input/output (và tool) trước/sau khi chạy |

**Agent loop mặc định**: LLM → (tool calls → chạy tools → đưa kết quả lại LLM) → lặp đến khi có `final_output` hoặc handoff.

---

## 2. Agents

### 2.1 Cấu hình cơ bản

```python
from agents import Agent, function_tool

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"

agent = Agent(
    name="Haiku agent",           # Bắt buộc
    instructions="Always respond in haiku form",
    model="gpt-5-nano",
    tools=[get_weather],
    reset_tool_choice=True,       # Mặc định: tránh loop gọi tool vô hạn
    mcp_servers=[...],            # MCP servers cung cấp thêm tools
)
```

- **name**: Định danh agent (bắt buộc).
- **instructions**: System prompt / developer message.
- **model**: Tên model hoặc instance Model (OpenAI, LiteLLM, custom).
- **tools**: Danh sách tool (function, hosted, local runtime, agents as tools).
- **reset_tool_choice**: Sau mỗi lần gọi tool, reset `tool_choice` về `"auto"` để tránh loop.

### 2.2 Context (dependency injection)

Agent có thể generic trên **context type**. Context là object bạn tạo và truyền vào `Runner.run(..., context=...)`, được truyền xuống mọi agent/tool/handoff.

```python
from dataclasses import dataclass

@dataclass
class UserContext:
    name: str
    uid: str

agent = Agent[UserContext](name="Assistant", instructions="...")

# Khi chạy:
result = await Runner.run(agent, "Hello", context=UserContext(name="Alice", uid="1"))
```

### 2.3 Output type (structured output)

Dùng **output_type** (Pydantic model, dataclass, TypedDict, ...) để agent trả về cấu trúc cố định thay vì text.

```python
from pydantic import BaseModel
from agents import Agent

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

agent = Agent(
    name="Calendar extractor",
    instructions="Extract calendar events from text",
    output_type=CalendarEvent,
)
```

### 2.4 Tool use behavior

- **tool_choice** (trong `ModelSettings`): `"auto"` | `"required"` | `"none"` | `"tên_tool_cụ_thể"`.
- **tool_use_behavior**:
  - `"run_llm_again"` (mặc định): Chạy tool → đưa kết quả lại LLM → LLM có thể trả lời hoặc gọi thêm tool.
  - `"stop_on_first_tool"`: Dừng ngay sau lần gọi tool đầu tiên, dùng output của tool làm final response.
  - `StopAtTools(stop_at_tool_names=["tool_a"])`: Chỉ dừng khi gọi một trong các tool chỉ định.
  - `ToolsToFinalOutputFunction`: Hàm tùy chỉnh nhận tool results, trả về có dừng hay không và final output.

### 2.5 Lifecycle hooks

- **AgentHooks** (gắn trên từng agent qua `agent.hooks`): `on_agent_start`, `on_agent_end`, `on_llm_start`, `on_llm_end`, `on_tool_start`, `on_tool_end`, `on_handoff`.
- **RunHooks** (truyền vào `Runner.run(..., hooks=...)`): Quan sát toàn bộ run (bao gồm handoffs).

```python
from agents import Agent, RunHooks, Runner

class LoggingHooks(RunHooks):
    async def on_agent_start(self, context, agent):
        print(f"Starting {agent.name}")
    async def on_llm_end(self, context, agent, response):
        print(f"{agent.name} produced output")

result = await Runner.run(agent, "Hello", hooks=LoggingHooks())
```

### 2.6 Dynamic instructions

Instructions có thể là **hàm** nhận `(context, agent)` và trả về chuỗi prompt.

```python
def dynamic_instructions(ctx: RunContextWrapper[UserContext], agent: Agent[UserContext]) -> str:
    return f"The user's name is {ctx.context.name}. Help them."

agent = Agent[UserContext](name="Triage", instructions=dynamic_instructions)
```

---

## 3. Tools

### 3.1 Các loại tool

| Loại | Mục đích |
|------|----------|
| **Function tools** | Bọc Python function, schema tự sinh từ signature + docstring |
| **Agents as tools** | Agent con được gọi như tool bởi agent trung tâm |
| **Hosted OpenAI tools** | WebSearch, FileSearch, CodeInterpreter, ImageGeneration, HostedMCP |
| **Local runtime** | ShellTool, ApplyPatchTool, ComputerTool |
| **MCP** | Tool từ MCP server (qua `mcp_servers` trên agent) |

### 3.2 Function tools (`@function_tool`)

- Schema từ **inspect** + **docstring** (google/sphinx/numpy).
- Có thể nhận **RunContextWrapper** làm tham số đầu tiên để dùng context.
- Hỗ trợ **Pydantic Field** cho constraint và description.

```python
from agents import function_tool, RunContextWrapper
from typing import Any

@function_tool
async def fetch_weather(city: str) -> str:
    """Fetch the weather for a given location.
    Args:
        city: The city name.
    """
    return f"Weather in {city}: sunny"

@function_tool(name_override="read_file")
def read_file(ctx: RunContextWrapper[Any], path: str, directory: str | None = None) -> str:
    """Read file. Args: path: Path. directory: Optional dir."""
    return "<contents>"
```

Tùy chọn:

- **timeout**: Cho async tool; khi timeout có thể `error_as_result` (mặc định) hoặc `raise_exception`.
- **failure_error_function**: Hàm tùy chỉnh trả về message lỗi gửi cho LLM khi tool crash.
- **tool_input_guardrails** / **tool_output_guardrails**: Kiểm tra trước/sau khi gọi tool.

### 3.3 Agents as tools (orchestrator pattern)

Agent trung tâm **giữ control**, gọi agent chuyên biệt như **tool** (không handoff).

```python
from agents import Agent, Runner

spanish_agent = Agent(name="Spanish", instructions="Translate to Spanish.")
french_agent = Agent(name="French", instructions="Translate to French.")

orchestrator = Agent(
    name="Orchestrator",
    instructions="Use tools to translate.",
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate the user's message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate to French",
        ),
    ],
)

result = await Runner.run(orchestrator, "Say hello in Spanish.")
```

Tùy chọn `as_tool`:

- **parameters**: Pydantic model cho input có cấu trúc.
- **input_builder**: Tùy chỉnh cách argument → input cho agent con.
- **custom_output_extractor**: Hàm `(RunResult) -> str` để chỉ trả về phần cần thiết.
- **needs_approval**: Human-in-the-loop trước khi chạy tool.
- **on_stream**: Callback nhận streaming events của agent con.

---

## 4. Handoffs

Handoff = agent **chuyển giao** sang agent khác; agent mới **nhận** toàn bộ hội thoại và “làm chủ” từ đó (decentralized).

### 4.1 Cơ bản

Handoff được biểu diễn như **tool** với tên dạng `transfer_to_<agent_name>`.

```python
from agents import Agent, handoff

billing_agent = Agent(name="Billing agent", instructions="...")
refund_agent = Agent(name="Refund agent", instructions="...")

triage_agent = Agent(
    name="Triage agent",
    instructions="Hand off to Billing or Refund as appropriate.",
    handoffs=[billing_agent, handoff(refund_agent)],
)
```

### 4.2 Tùy chỉnh với `handoff()`

- **agent**: Agent đích.
- **tool_name_override** / **tool_description_override**: Đổi tên/mô tả tool.
- **input_filter**: Hàm nhận `HandoffInputData`, trả về `HandoffInputData` mới (lọc/sửa history trước khi đưa sang agent mới).
- **input_type**: Kiểu input có cấu trúc (Pydantic) khi gọi handoff.
- **on_handoff**: Callback khi handoff được gọi (vd. log, fetch data).
- **is_enabled**: Bật/tắt handoff (bool hoặc hàm).
- **nest_handoff_history**: Thu gọn history thành một message summary (beta). Có thể cấu hình ở `RunConfig.nest_handoff_history` hoặc từng handoff.

```python
from agents import Agent, handoff, RunContextWrapper
from agents.extensions import handoff_filters

agent = Agent(name="FAQ agent")
handoff_obj = handoff(
    agent=agent,
    input_filter=handoff_filters.remove_all_tools,  # Xóa tool calls khỏi history
)
```

### 4.3 Handoff với input có cấu trúc

LLM có thể truyền dữ liệu khi gọi handoff (vd. lý do escalate).

```python
from pydantic import BaseModel
from agents import Agent, handoff, RunContextWrapper

class EscalationData(BaseModel):
    reason: str

async def on_handoff(ctx: RunContextWrapper[None], input_data: EscalationData):
    print(f"Escalation: {input_data.reason}")

handoff_obj = handoff(
    agent=escalation_agent,
    on_handoff=on_handoff,
    input_type=EscalationData,
)
```

### 4.4 Prompt gợi ý cho handoff

Dùng prefix hoặc helper để model hiểu khi nào handoff:

```python
from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX, prompt_with_handoff_instructions

agent = Agent(
    name="Triage",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\n<phần còn lại của prompt>.",
)
```

---

## 5. Guardrails

Guardrails = kiểm tra **input** hoặc **output** (và **tool**) trước/sau khi chạy; có thể **chặn** (tripwire) hoặc chỉ ghi nhận.

### 5.1 Input guardrails

- Chạy trên **input** truyền vào agent (thường là user message).
- **run_in_parallel=True** (mặc định): Chạy song song với agent → latency tốt nhưng agent có thể đã chạy khi tripwire bật.
- **run_in_parallel=False**: Chạy xong guardrail rồi mới chạy agent → tripwire thì agent không chạy (tiết kiệm token).

```python
from pydantic import BaseModel
from agents import Agent, GuardrailFunctionOutput, InputGuardrailTripwireTriggered, input_guardrail, Runner

class MathHomeworkOutput(BaseModel):
    is_math_homework: bool
    reasoning: str

guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking you to do their math homework.",
    output_type=MathHomeworkOutput,
)

@input_guardrail
async def math_guardrail(ctx, agent, input) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_math_homework,
    )

agent = Agent(
    name="Support",
    instructions="Help customers.",
    input_guardrails=[math_guardrail],
)
# Khi tripwire_triggered=True -> ném InputGuardrailTripwireTriggered
```

### 5.2 Output guardrails

- Chạy trên **output** cuối của agent.
- Luôn chạy **sau** khi agent hoàn thành.

```python
@output_guardrail
async def math_output_guardrail(ctx, agent, output: MessageOutput) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, output.response, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_math,
    )

agent = Agent(..., output_type=MessageOutput, output_guardrails=[math_output_guardrail])
```

### 5.3 Tool guardrails

Chỉ áp dụng cho **function tools** (không áp dụng cho hosted/local runtime tools).

- **tool_input_guardrail**: Trước khi gọi tool; có thể skip, thay output, hoặc tripwire.
- **tool_output_guardrail**: Sau khi tool chạy; có thể thay output hoặc tripwire.

```python
from agents import function_tool, tool_input_guardrail, tool_output_guardrail, ToolGuardrailFunctionOutput

@tool_input_guardrail
def block_secrets(data):
    args = json.loads(data.context.tool_arguments or "{}")
    if "sk-" in json.dumps(args):
        return ToolGuardrailFunctionOutput.reject_content("Remove secrets.")
    return ToolGuardrailFunctionOutput.allow()

@function_tool(tool_input_guardrails=[block_secrets])
def my_tool(x: str) -> str:
    return x
```

---

## 6. Sessions (bộ nhớ hội thoại)

Sessions lưu **lịch sử** giữa các lần gọi `Runner.run`, không cần tự quản lý `to_input_list()`.

### 6.1 Cách dùng

```python
from agents import Agent, Runner, SQLiteSession

agent = Agent(name="Assistant", instructions="Reply concisely.")
session = SQLiteSession("conversation_123")

# Turn 1
result = await Runner.run(agent, "Golden Gate Bridge ở thành phố nào?", session=session)

# Turn 2 – agent tự nhìn thấy history
result = await Runner.run(agent, "Nó ở bang nào?", session=session)
```

- Sau mỗi run: items mới (user, assistant, tool calls) được **lưu** vào session.
- Trước mỗi run: runner **lấy** history từ session và prepend vào input.

### 6.2 Điều khiển history

- **RunConfig.session_input_callback(new_input, history)**: Tùy chỉnh cách merge input mới với history (vd. giữ N message gần nhất).
- **RunConfig.session_settings**: Vd. `SessionSettings(limit=50)` để chỉ lấy 50 item gần nhất.

### 6.3 Thao tác session

- `session.get_items()` – lấy toàn bộ items.
- `session.add_items(items)` – thêm items.
- `session.pop_item()` – xóa và trả về item cuối (dùng để “sửa” turn trước).
- `session.clear_session()` – xóa hết.

### 6.4 Backend

- **SQLiteSession**: File hoặc in-memory, phù hợp dev / app đơn giản.
- **AsyncSQLiteSession**, **RedisSession**, **SQLAlchemySession**: Dùng khi cần async hoặc shared/production DB.

---

## 7. Running agents

### 7.1 Runner

- **Runner.run(agent, input, ...)** – async, trả về `RunResult`.
- **Runner.run_sync(agent, input, ...)** – sync.
- **Runner.run_streamed(agent, input, ...)** – streaming events.

`input` có thể là:

- **str** – coi như một user message.
- **list** – danh sách input items (Responses API format).
- **RunState** – khi resume run bị gián đoạn.

### 7.2 Multi-turn (không dùng Session)

Dùng `result.to_input_list()` rồi append user message mới:

```python
result = await Runner.run(agent, "First message")
history = result.to_input_list() + [{"role": "user", "content": "Follow-up?"}]
result = await Runner.run(agent, history)
```

### 7.3 RunConfig

Một số tùy chọn thường dùng:

- **model** / **model_provider** / **model_settings**: Override model cho run.
- **max_turns**: Giới hạn số vòng (tool/LLM); vượt thì ném `MaxTurnsExceeded`.
- **session** / **session_settings** / **session_input_callback**: Session và cách merge.
- **input_guardrails** / **output_guardrails**: Guardrails cho run.
- **hooks**: RunHooks.
- **call_model_input_filter**: Sửa input gửi cho model (vd. cắt history, inject prompt).
- **nest_handoff_history**: Thu gọn history khi handoff (beta).

---

## 8. So sánh nhanh: Handoff vs Agents as tools

| | Handoff | Agents as tools |
|--|--------|------------------|
| **Ai giữ control** | Agent mới nhận và “sở hữu” hội thoại | Orchestrator giữ control, gọi agent con như tool |
| **Input cho agent con** | Toàn bộ conversation (có thể lọc bằng input_filter) | Thường một input string/structured do orchestrator quyết định |
| **Output** | Final output từ agent mới | Output của tool (có thể custom_output_extractor) |
| **Pattern** | Decentralized, triage → specialist | Centralized, manager → experts |

---

## 9. Áp dụng cho Config Chatbot

- **Tools**: Giữ nguyên function tools (list_devices, get_device, get_device_config, list_vendors_and_series, list_templates_for_series, get_template_required_vars, render_config).
- **Một agent đủ**: Có thể chỉ dùng 1 agent với đủ tools; model tự extract intent, hỏi thêm, gọi tool, rồi trả config.
- **Nếu tách agent**:
  - **Handoff**: Agent “triage” phân loại ý (tra cứu device/config vs tạo config) → handoff sang “device lookup agent” hoặc “config generator agent”.
  - **Agents as tools**: Một “orchestrator” gọi “config generator” như tool với (vendor_id, series_id, template_key, context) và nhận về config text.
- **Guardrails**: Có thể thêm input guardrail kiểm tra prompt không phải prompt injection; output guardrail kiểm tra config không chứa credential thật.
- **Sessions**: Dùng `SQLiteSession(session_id)` trong chatbot để multi-turn tự lưu history thay vì tự gọi `to_input_list()`.

---

Tài liệu gốc: [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/).
