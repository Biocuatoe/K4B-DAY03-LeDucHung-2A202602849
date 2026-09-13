# 🏫 BÀI LAB 3: CHATBOT VS REACT AGENT — TỪ LÝ THUYẾT ĐẾN THỰC THI (MCP ENHANCED)

> **Mã bài học:** `DAY03-REACT-AGENT`  
> **Hình thức thực hiện:** **CÁ NHÂN** *(Mỗi học viên tự làm và tự nộp 1 bài cá nhân)*  
> **Quy chuẩn nộp bài:** Học viên Fork Repo này về GitHub cá nhân và đổi tên theo đúng cú pháp:  
> 📌 **`K4-DAY03-HoVaTen-MSSV`** *(Ví dụ: `K4-DAY03-NguyenVanA-SV2026001`)*  

---

## ⚡ 1. QUICKSTART — CÀI ĐẶT MÔI TRƯỜNG & CHẠY THỬ (3 PHÚT)

> 🐍 **Yêu cầu môi trường Python:** **Python 3.10 – 3.12** *(Tránh Python 3.9 do thiếu type hinting hiện đại và Python 3.13 do nhiều thư viện AI chưa hỗ trợ pre-built wheel)*.

Thực hiện 3 bước lệnh Terminal thiết thực ngay khi clone repo về máy:

### Bước 1: Clone Repo & Tạo môi trường ảo
```bash
git clone https://github.com/<tai_khoan_cua_ban>/K4-DAY03-HoVaTen-MSSV.git
cd K4-DAY03-HoVaTen-MSSV

python -m venv .venv
# Trên Windows PowerShell:
.venv\Scripts\Activate.ps1
# Trên macOS / Linux / Bash / Zsh:
source .venv/bin/activate
```

### Bước 2: Cài đặt thư viện & Tạo file cấu hình môi trường
```bash
pip install -r requirements.txt
# Trên Windows CMD/PowerShell:
copy .env.example .env
copy config\test_cases.example.json config\test_cases.json
# Trên macOS / Linux:
cp .env.example .env
cp config/test_cases.example.json config/test_cases.json
```

### Bước 3: Chạy thử Baseline kiểm tra môi trường
```bash
python src/app.py --all
```

**Kỳ vọng Output màn hình:**
```text
✅ [MOCK OFFLINE MODE PASS]: Môi trường đã sẵn sàng! 
📊 [KẾT QUẢ TEST SUITE]: 2 Đã chạy (TC01, TC02 mẫu) | 3 Đang chờ viết câu hỏi (TODO)
```

> 🔑 **QUY ĐỊNH BẮT BUỘC VỀ API KEY VÀ NỘP BÀI (SUBMISSION REQUIREMENT):**  
> 
> 1. **Giai đoạn gõ code & debug (Miễn phí 0đ):** Hệ thống mặc định chạy `MockOfflineProvider` giúp bạn thực hành gõ code, kiểm thử logic ban đầu hoàn toàn miễn phí, không tốn token, không lo nghẽn mạng.  
> 2. **Giai đoạn NỘP BÀI CHÍNH THỨC (Bắt buộc dùng LLM thật):** Khi chạy nghiệm thu để lấy dữ liệu dán vào báo cáo [`docs/trace_eval.md`](docs/trace_eval.md) nộp bài, **học viên BẮT BUỘC phải mở file `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`)** để Agent giao tiếp với mô hình LLM thật.  
> 
> ⚠️ *Lưu ý:* Bài nộp chỉ chạy trên Mock Provider mà không kết nối LLM API thật sẽ bị trừ điểm phần nghiệm thu thực tế (Tiêu chí 2 & Tiêu chí 3 trong Rubric).

---

## 🎯 2. BỨC TRANH TỔNG THỂ & MỤC TIÊU DÀI HẠN (NORTH STAR GOAL)

Mục tiêu cốt lõi của Bài Lab này là giúp học viên tự tay phát triển một **Trợ lý Tác tử ReAct (ReAct Agent)** hoàn chỉnh.

Thay vì chỉ sinh văn bản hội thoại đơn thuần như Chatbot cơ bản, tác tử (Agent) của bạn sẽ có khả năng:
1. **Tự suy luận và chọn công cụ:** Chủ động kích hoạt vòng lặp ReAct (`Thought -> Action -> Observation`) qua giao thức **Model Context Protocol (MCP)** để truy vấn dữ liệu thực tế.
2. **Tổng hợp câu trả lời chính xác:** Sử dụng dữ liệu thực tế từ Tool trả về để trả lời sinh viên, tránh hiện tượng ảo giác (Hallucination).
3. **Trích xuất bằng chứng (Trace Log):** Ghi lại file vết `docs/trace_waterfall.json` chứng minh chuỗi suy luận từng bước của Agent.

> 🌐 **GIAO THỨC MODEL CONTEXT PROTOCOL (MCP):**  
> Mã nguồn [`src/mcp_server.py`](src/mcp_server.py) mô phỏng kiến trúc MCP Server chuẩn (giao tiếp Client-Server độc lập qua giao thức JSON-RPC 2.0). Agent Core ([`src/app.py`](src/app.py)) đóng vai trò MCP Client gửi yêu cầu thực thi Tool tới MCP Server.

---

## 🗺️ 3. LUỒNG THỰC HÀNH TINH GIẢN 3 BƯỚC (DOCUMENTATION FLOW)

Học viên làm bài lần lượt theo đúng luồng 3 bước tinh giản dưới đây:

| Bước | Tài liệu / Hành động | Nội dung thực hiện |
| :---: | :--- | :--- |
| **Bước 1** | 📄 **`README.md`** *(Hiện tại)* | Nắm quy chế, chạy Quickstart verify môi trường offline miễn phí. |
| **Bước 2** | 🎓 **`docs/CODELAB.md`** | **[TRỌNG TÂM]** Chọn bài toán (Tham khảo gợi ý tại [docs/DANH_SACH_DE_TAI.md](docs/DANH_SACH_DE_TAI.md)) ➔ Phân tích Agentic Fit ➔ Điền `GEMINI_API_KEY` ➔ Code từng task theo checklist. |
| **Bước 3** | 📊 **`docs/trace_eval.md`** | Chạy test suite với API thật, xuất trace log, hoàn thiện báo cáo thu hoạch duy nhất và push repo nộp bài. |

---

## ⏱️ 4. PHÂN BỔ THỜI GIAN (180 PHÚT LÀM BÀI)

* **Phần 1 (45 phút):** Agentic Fit & Tool Schemas (Đánh giá 4 tiêu chí Fit & Khai báo Tool Schema chuẩn JSON Schema)
* **Phần 2 (60 phút):** ReAct Loop & MCP Integration (Viết hàm MCP Server & Vòng lặp Thought -> Action -> Observation)
* **Phần 3 (45 phút):** Test Execution & Waterfall Log (Cắm API Key thật, chạy 5 Test Cases & Xuất file docs/trace_waterfall.json)
* **Phần 4 (30 phút):** Self-Audit & Push GitHub (Tự kiểm tra code, hoàn thiện báo cáo docs/trace_eval.md & push bài nộp lên GitHub cá nhân)

---

## 📂 5. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
📁 K4-Day03-Lab-Chatbot-vs-ReAct-Agent-MCP/
├── 📄 README.md                 <-- ⚡ [BƯỚC 1] Quickstart setup & Cảnh báo quy định API Key
├── 📄 .env.example              <-- 🔑 File cấu hình API Key (Gemini, OpenAI, Anthropic, Mock)
├── 📄 requirements.txt          <-- 📦 Thư viện Python tương thích đa nền tảng
│
├── 📁 config/
│   ├── 📄 test_cases.example.json <-- 🟢 Mẫu Bộ 5 Test Cases (Copy thành test_cases.json)
│   └── 📄 test_cases.json         <-- 🟢 Bộ 5 Test Cases tùy biến theo đề tài của bạn
│
├── 📁 src/                      <-- 💻 MÃ NGUỒN PYTHON
│   ├── 📄 mcp_server.py         <-- 🌐 MCP Server quản lý Tool Registry & JSON-RPC Dispatcher
│   ├── 📄 tools.py              <-- 🛠️ Backend Tool Schemas JSON & Execution Layer
│   ├── 📄 prompts.py            <-- 🛡️ System Prompts cho Chatbot và ReAct Agent
│   ├── 📄 providers.py          <-- 🔌 Multi-Provider LLM Adapter (Gemini/OpenAI/Mock)
│   ├── 📄 app.py                <-- 🚀 MCP Client & Core Agent App ghép nối ReAct Loop & Trace Log
│   └── 📁 ai_levels/            <-- 📚 [REFERENCE ONLY] Code mẫu kiến trúc tham khảo (Không sửa/debug)
│       └── 📄 README.md         <-- ⚠️ Chú thích mã nguồn tham khảo
│
└── 📁 docs/                     <-- 📚 TÀI LIỆU HƯỚNG DẪN CHUẨN VLEARN CODELAB
    ├── 📄 DANH_SACH_DE_TAI.md    <-- 💡 Gợi ý chủ đề theo Lĩnh vực & Đề tài Mở
    ├── 📄 CODELAB.md            <-- 🎓 [BƯỚC 2 - TRỌNG TÂM] Hướng dẫn Codelab thực hành theo checklist
    └── 📄 trace_eval.md          <-- 📊 [BƯỚC 3] File Báo cáo Nộp bài duy nhất (Submission Report Artifact)
```

---

## 💯 6. THANG ĐIỂM ĐÁNH GIÁ (SCORING RUBRIC 100%)

| Tiêu chí | Trọng số | Mô tả chi tiết | Bằng chứng kiểm tra (Artifacts) |
| :--- | :---: | :--- | :--- |
| **1. Agentic Fit & Tool Specs** | **25%** | Phân tích đúng 4 tiêu chí Agentic Fit. Khai báo Tool Schema chuẩn JSON Schema. | Bảng Scoring Matrix (`docs/trace_eval.md`) + `config/test_cases.json`. |
| **2. ReAct Loop & MCP Integration** | **35%** | Vòng lặp ReAct chạy mượt mà qua Native Tool Calling & MCP Server **trên LLM API thật (Gemini/OpenAI)**. | Code trong `src/mcp_server.py` + `src/tools.py` + `src/app.py` + Log API thật. |
| **3. Waterfall Trace & Observation** | **25%** | File log `trace_waterfall.json` trích xuất đầy đủ chuỗi suy luận Thought $\rightarrow$ Action $\rightarrow$ Observation. | File log `docs/trace_waterfall.json` + `docs/trace_eval.md`. |
| **4. Git Repository & Submission** | **15%** | Cấu trúc Repo sạch sẽ, commit chuẩn chỉ và nộp đúng hạn trên LMS VLearn. | Link Repo GitHub cá nhân. |

---

## ✅ 7. TRẠNG THÁI HOÀN THÀNH CÁC TASK (SUBMISSION CHECKLIST)

- [x] **Bước 1 — Quickstart:** Đã thiết lập môi trường ảo và cài đặt thư viện (`pip install -r requirements.txt`).
- [x] **Task 1.1 — Agentic Fit Scoring Matrix:** Đã điền đầy đủ 4 tiêu chí trong `docs/trace_eval.md` (tổng **19/20**).
- [x] **Task 1.1 — Bộ 5 Test Cases:** Đã hoàn thiện `config/test_cases.json` theo đề tài *Trợ lý Học vụ Sinh viên VinUni*.
- [x] **Task 1.2 — Tool Schema JSON:** Đã khai báo đầy đủ `parameters` cho `schedule_appointment` (3 tham số bắt buộc: `student_id`, `datetime_str`, `advisor_name`).
- [x] **Task 2.1 — MCP Server JSON-RPC 2.0:** Đã hoàn thiện hàm `call_tool()` chuẩn `jsonrpc: "2.0"` với xử lý lỗi `PARSE_ERROR` / `DISPATCH_ERROR`.
- [x] **Task 2.2 — ReAct Loop Multi-step:** Đã nâng cấp vòng lặp `run_react_agent()` trong `src/app.py` hỗ trợ conversation_history, đa bước ReAct và tổng hợp Final Answer sau MAX_ITERATIONS.
- [x] **Task 3.1 — Test Suite & Trace:** Đã chạy `python src/app.py --all`, kết quả **5/5 test cases PASS**, xuất **10 sự kiện** trong `docs/trace_waterfall.json`.
- [x] **Task 3.2 — Báo cáo:** Đã hoàn thiện `docs/trace_eval.md` với trích đoạn trace log + bảng tổng kết.
- [x] **Đa nền tảng LLM:** `src/providers.py` hỗ trợ `Gemini` / `OpenAI` / `Mock` với cùng interface `generate_with_tools(prompt, tools, system_prompt, conversation_history)`.

---

## 🔌 8. REAL MCP SERVER (stdio JSON-RPC Transport)

### 8.1 Tổng quan

Lab 3 đã được nâng cấp để hỗ trợ **MCP Server thật qua JSON-RPC stdio transport** thay vì gọi trực tiếp function Python local. Điều này mang lại:

- **Isolation:** MCP Server chạy trong subprocess riêng biệt, không chia sẻ memory space với Agent
- **Standard Compliance:** Tuân thủ đầy đủ MCP protocol (Model Context Protocol)
- **Language Agnostic:** Có thể thay thế MCP Server bằng implementation bằng ngôn ngữ khác (Rust, TypeScript, Go...)
- **Debugging:** Dễ dàng trace request/response qua stderr

### 8.2 Kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Core (app.py)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  ReAct Loop │──│   LLM Call   │──│  MCPTransport Layer  │  │
│  └──────────────┘  └──────────────┘  └──────────┬───────────┘  │
└─────────────────────────────────────────────────│───────────────┘
                                                  │ JSON-RPC 2.0
                                                  │ stdio subprocess
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server (mcp_server_stdio.py)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Content-   │──│   JSON-RPC   │──│   Tool Execution     │  │
│  │   Length     │  │   Handler    │  │  (academic_query,    │  │
│  │   Framing    │  │              │  │   schedule_appt)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Các file mới

| File | Mô tả |
|:-----|:------|
| `src/mcp_server_stdio.py` | MCP Server thật - nhận JSON-RPC request qua stdin, gửi response qua stdout |
| `src/mcp_client.py` | MCP Client - quản lý subprocess, giao tiếp JSON-RPC với server |
| `src/api_server.py` | HTTP wrapper - cho phép demo HTML gọi MCP server qua fetch() |

### 8.4 Sử dụng Real MCP Server

#### Bước 1: Kích hoạt stdio transport

Chỉnh sửa file `.env`:

```env
MCP_TRANSPORT=stdio
```

#### Bước 2: Chạy với Real MCP Server

```bash
# Chế độ mặc định (1 test case mẫu)
python src/app.py

# Chế độ tương tác
python src/app.py --interactive

# Chạy tất cả test cases
python src/app.py --all
```

Output sẽ hiển thị:
```
🔌 [MCPTransport] Using stdio transport (Real MCP Server)
   Connected to: {'name': 'vinuni-mcp-server', 'version': '1.0.0'}
```

#### Bước 3: Chạy HTTP Wrapper cho Demo HTML

```bash
# Terminal 1: Khởi động HTTP wrapper
python src/api_server.py

# Terminal 2: Mở demo.html trong trình duyệt
# Hoặc test bằng curl:
```

**Các Endpoints có sẵn:**

| Method | Endpoint | Mô tả |
|:-------|:---------|:-------|
| GET | `/` | Server info |
| GET | `/health` | Health check |
| GET | `/tools` | List tools (legacy) |
| POST | `/chat` | Chat message (legacy) |
| GET | `/api/tools` | List tools (new) |
| POST | `/api/chat` | Chat with intent classification (new) |

**Test bằng curl (PowerShell):**

```powershell
# Test root endpoint
(Invoke-WebRequest -Uri 'http://127.0.0.1:8765/' -Method GET -UseBasicParsing).Content

# Test health check
(Invoke-WebRequest -Uri 'http://127.0.0.1:8765/health' -Method GET -UseBasicParsing).Content

# Test list tools (new endpoint)
(Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/tools' -Method GET -UseBasicParsing).Content

# Test chat với intent classification (new endpoint)
$headers = @{ "Content-Type" = "application/json" }
$body = '{"message":"Tra cuu SV2026001"}'
Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/chat' -Method POST -Body $body -Headers $headers -UseBasicParsing

# Test legacy chat endpoint
$body = '{"prompt":"Tra cuu SV2026001"}'
Invoke-WebRequest -Uri 'http://127.0.0.1:8765/chat' -Method POST -Body $body -Headers $headers -UseBasicParsing
```

**API Response Format (new `/api/chat`):**

```json
{
  "intent": "ACADEMIC",
  "response": "Ket qua tra cuu cho sinh vien SV2026001...",
  "trace": [
    {"step": 0, "type": "INTENT_CLASSIFICATION", "intent": "ACADEMIC"},
    {"step": 1, "type": "TOOL_CALL", "tool": "academic_query", ...}
  ],
  "tool_name": "academic_query",
  "status": "success"
}
```

### 8.5 Test trực tiếp MCP Client

```bash
python -c "
from src.mcp_client import MCPClient

client = MCPClient('src/mcp_server_stdio.py')
client.start()

print('Tools:', client.list_tools())
print('Result:', client.call_tool('academic_query', {'student_id': 'SV2026001'}))

client.stop()
"
```

### 8.6 So sánh Transport Modes

| Aspect | `local` (mặc định) | `stdio` (Real MCP) |
|:-------|:-------------------|:-------------------|
| **Kiến trúc** | In-process function call | Subprocess IPC |
| **Isolation** | Không | Có |
| **Protocol** | Python function | JSON-RPC 2.0 |
| **Latency** | ~0ms | ~5-15ms overhead |
| **Debugging** | Standard Python | Trace via stderr |
| **Compatibility** | 100% | Tuân thủ MCP spec |
| **Use case** | Development/Demo | Production |

### 8.7 Troubleshooting

**Lỗi: "MCP server not found"**
```bash
# Kiểm tra đường dẫn server script
python -c "from pathlib import Path; print(Path('src/mcp_server_stdio.py').resolve())"
```

**Lỗi: "Content-Length missing"**
- Đảm bảo subprocess không có buffered output
- Kiểm tra `bufsize=0` trong `subprocess.Popen`

**Lỗi: "Connection refused" khi gọi HTTP wrapper**
- Chạy `python src/api_server.py` trước
- Kiểm tra port 8765 không bị chiếm dụng

---

## 🧠 9. INTENT CLASSIFICATION

### 9.1 Tổng quan

Bài lab đã được nâng cấp với **Intent Classifier** - phân loại câu hỏi của user thành 2 loại:

| Intent | Mô tả | Handler |
|:-------|:------|:--------|
| **ACADEMIC** | Câu hỏi liên quan học vụ (tra cứu SV, đặt lịch, điểm, môn học...) | ReAct Loop + MCP Tools |
| **CASUAL** | Câu hỏi không liên quan (chào hỏi, hỏi ngày tháng, thời tiết...) | LLM trực tiếp (Gemini/OpenAI/Mock) |

### 9.2 Kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│                    User Input                                  │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              Intent Classifier (src/intent_classifier.py)       │
│  ┌────────────────────┐    ┌────────────────────┐           │
│  │ ACADEMIC patterns  │    │  CASUAL patterns   │           │
│  │ - SV2026001        │    │  - "Xin chao"      │           │
│  │ - "sinh vien"      │    │  - "thu may"       │           │
│  │ - "dat lich"       │    │  - "thoi tiet"     │           │
│  │ - "diem", "hoc phi"│    │  - "cam on"        │           │
│  └─────────┬──────────┘    └─────────┬──────────┘           │
└─────────────┼─────────────────────────┼──────────────────────┘
              │                         │
              ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────────────┐
│    ReAct Loop            │  │     LLM Direct Call              │
│    (MCP Tools)           │  │     (Gemini/OpenAI/Mock)        │
│  ┌──────────────────┐   │  │  ┌──────────────────────────┐  │
│  │ academic_query   │   │  │  │ provider.generate()      │  │
│  │ schedule_appt    │   │  │  │ system_prompt: baseline  │  │
│  └──────────────────┘   │  │  └──────────────────────────┘  │
└──────────────────────────┘  └──────────────────────────────────┘
```

### 9.3 Cách hoạt động

1. **Intent Classifier** (`src/intent_classifier.py`) dùng regex patterns để phân loại:
   - **CASUAL**: Câu hỏi bắt đầu bằng "Xin chào", "Hi", "Hello", hoặc chứa "thứ mấy", "thời tiết", "cảm ơn"...
   - **ACADEMIC**: Chứa mã SV (SV2026001), "sinh viên", "tra cứu", "đặt lịch", "cố vấn", "điểm"...
   - **Fallback**: Câu ngắn (<10 ký tự) → CASUAL; mặc định → ACADEMIC

2. **Routing logic** trong `src/app.py`:
   - Nếu `intent == CASUAL` → Gọi `provider.generate()` trực tiếp
   - Nếu `intent == ACADEMIC` → Gọi `run_react_agent()` với ReAct loop

### 9.4 Ví dụ Input/Output

| Input | Intent | Handler | Output |
|:------|:-------|:--------|:-------|
| `"Xin chao ban"` | CASUAL | LLM Direct | `[Mock Chatbot Response]: Xin chao! Tôi đã nhận được câu hỏi...` |
| `"Hôm nay là thứ mấy?"` | CASUAL | LLM Direct | `[Mock Chatbot Response]: Xin chao! Tôi đã nhận được câu hỏi...` |
| `"Tra cuu SV2026001"` | ACADEMIC | ReAct + MCP | `[Mock Agent Response]: Kết quả tra cứu cho sinh viên SV2026001...` |
| `"Dat lich hen tu van"` | ACADEMIC | ReAct + MCP | `[Mock Agent Response]: Đặt lịch thành công...` |

### 9.5 Lưu ý

- **Backward Compatibility**: Test suite `--all` vẫn dùng ReAct loop trực tiếp (không qua intent routing)
- **Trace format**: Event type mới được thêm vào trace: `INTENT_CASUAL`, `INTENT_ACADEMIC`, `LLM_RESPONSE`, `LLM_ERROR`
- **Error handling**: Nếu LLM API fail → trả message lỗi thân thiện + hướng dẫn check API key

### 9.6 Test Intent Classifier

```bash
# Test standalone
python test_intent.py

# Test end-to-end casual
python src/app.py --interactive
# > Xin chao ban
# > Hom nay la thu may?
# > exit
```

---

## 📊 9. SCORING RUBRIC (Full)
