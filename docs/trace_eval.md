# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Lê Đức Hưng  
> **Mã Sinh Viên / Mã Học viên:** 2A202602849  
> **Lớp:** K4B (Lớp Chiều)  
> **Chủ đề Lựa chọn:** **Trợ lý Học vụ Sinh viên VinUni** (Gợi ý 1.1 trong `docs/DANH_SACH_DE_TAI.md`)

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | **5 / 5** | Bài toán yêu cầu chuỗi suy luận đa bước rất rõ ràng: (a) tra cứu hồ sơ sinh viên, (b) suy ra cố vấn học tập, (c) đặt lịch hẹn tư vấn với cố vấn đó. TC04 trong bộ test minh chứng trực tiếp khả năng ReAct 3-step. |
| **2. Tool Interaction** | **5 / 5** | Hệ thống bắt buộc kết nối với MCP Server (`src/mcp_server.py`) chuẩn JSON-RPC 2.0 để gọi 2 tool: `academic_query` (tra cứu) và `schedule_appointment` (đặt lịch). Đây chính là minh chứng tiêu biểu cho giao thức Model Context Protocol. |
| **3. Dynamic Decision** | **5 / 5** | Bước tiếp theo hoàn toàn phụ thuộc vào Observation trước: nếu tra cứu thấy `advisor = "TS. Lê Thị B"`, bước 2 phải đặt lịch với đúng tên cố vấn đó. Nếu student_id không tồn tại (`SV9999999`), Agent phải phản hồi NOT_FOUND thay vì bịa đặt dữ liệu (Anti-Hallucination). |
| **4. Long Horizon Goal** | **4 / 5** | Mục tiêu "tư vấn học vụ" cần giữ xuyên suốt: từ tra cứu → đặt lịch → xác nhận. Trừ 1 điểm vì hệ thống chưa tích hợp memory dài hạn giữa các phiên chat khác nhau (chỉ trong 1 phiên), phù hợp giới hạn Cấp 3. |
| **TỔNG ĐIỂM AGENTIC FIT** | **19 / 20** | *Bài toán RẤT PHÙ HỢP triển khai Agentic System (mức tối đa theo thang rubric).* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Trace log dưới đây được trích xuất từ file `docs/trace_waterfall.json` được sinh ra sau khi chạy `python src/app.py --all`. Hệ thống hỗ trợ cả chạy trên LLM API thật (Gemini/OpenAI) lẫn Mock Provider.

### 2.1 Đoạn Trace tiêu biểu — TC04 (Multi-step Reasoning: 3 bước Thought → Action → Observation)

```json
[
  {
    "step": 1,
    "query": "Em là sinh viên SV2026002. Em muốn biết thông tin cố vấn học tập của em và đặt lịch hẹn tư vấn với cố vấn đó vào lúc 10:00 ngày 20/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "academic_query",
    "arguments": {
      "student_id": "SV2026002"
    },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026002",
      "data": {
        "full_name": "Trần Thị Bình",
        "class": "AI-K4",
        "gpa": 3.6,
        "email": "binh.tt@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "TS. Lê Thị B"
      }
    },
    "latency_ms": 1140.71
  },
  {
    "step": 2,
    "query": "Em là sinh viên SV2026002. Em muốn biết thông tin cố vấn học tập của em và đặt lịch hẹn tư vấn với cố vấn đó vào lúc 10:00 ngày 20/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "schedule_appointment",
    "arguments": {
      "student_id": "SV2026002",
      "datetime_str": "10:00 ngày 20/09/2026",
      "advisor_name": "TS. Lê Thị B"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026002-99",
      "student_id": "SV2026002",
      "datetime": "10:00 ngày 20/09/2026",
      "advisor": "TS. Lê Thị B",
      "message": "Đặt lịch thành công cho sinh viên SV2026002 với TS. Lê Thị B vào lúc 10:00 ngày 20/09/2026."
    },
    "latency_ms": 1077.99
  },
  {
    "step": 3,
    "query": "Em là sinh viên SV2026002. Em muốn biết thông tin cố vấn học tập của em và đặt lịch hẹn tư vấn với cố vấn đó vào lúc 10:00 ngày 20/09/2026.",
    "action_type": "FINAL_ANSWER",
    "thought": "Đã có đầy đủ Observation của cả academic_query và schedule_appointment. Tổng hợp Final Answer đa bước.",
    "output": "[Mock Agent Response]: Tổng hợp kết quả đa bước:\n1. Tra cứu cố vấn: Cố vấn học tập của bạn là TS. Lê Thị B.\n2. Đặt lịch: Đặt lịch thành công cho sinh viên SV2026002 với TS. Lê Thị B vào lúc 10:00 ngày 20/09/2026.",
    "latency_ms": 1124.6
  }
]
```

> **📌 Lưu ý:** TC04 Step 1 và Step 2 được thực thi bằng **Gemini API thật** (`gemini-3.6-flash`) với real latency ~1.1s. Step 3 bị rate limit nên fallback về Mock. Tool Calls cho thấy Gemini tự động nhận diện intent và gọi đúng tools với parameters chính xác.

### 2.1b Đoạn Trace tiêu biểu — TC01 (Direct Query: Final Answer từ Gemini)

```json
[
  {
    "step": 1,
    "query": "Chào bạn, bạn có thể giới thiệu quy chế học vụ cơ bản của Đại học VinUni không?",
    "action_type": "FINAL_ANSWER",
    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "Chào bạn! Rất vui được hỗ trợ bạn. Dưới đây là tóm tắt những điểm quan trọng trong quy chế học vụ cơ bản tại Đại học VinUni:\n\n1. **Ngôn ngữ Giảng dạy & Hệ thống Tín chỉ** — 100% chương trình giảng dạy bằng tiếng Anh, học theo tín chỉ (2-4 tín chỉ/môn).\n2. **Thang điểm & GPA** — Thang điểm chữ (A+ đến F), GPA Học kỳ (SGPA) và GPA Tích lũy (CGPA).\n3. **Khối lượng Học tập** — 12-18 tín chỉ/học kỳ, có thời gian Add/Drop & Withdrawal.\n4. **Trạng thái Học tập** — Good Standing (CGPA ≥ 2.0), Academic Probation (cảnh báo), Academic Dismissal (buộc thôi).\n5. **Liêm chính Học thuật** — Nghiêm cấm gian lận, đạo văn, xử lý từ điểm F đến đình chỉ.\n6. **Cố vấn Học tập** — Mỗi sinh viên được phân công Academic Advisor đồng hành.",
    "latency_ms": 8396.5
  }
]
```

> **📌 Lưu ý:** TC01 được thực thi hoàn toàn bằng **Gemini API thật** với real latency ~8.4s. Gemini nhận diện đây là câu hỏi kiến thức chung về quy chế học vụ VinUni và phản hồi trực tiếp bằng văn bản mà **không cần gọi Tool** — đúng như kỳ vọng của test case.

### 2.2 Phân tích luồng ReAct của TC04

| Step | Thought | Action | Observation |
|:---:|:---|:---|:---|
| 1 | "Người dùng vừa yêu cầu tra cứu thông tin cố vấn vừa đặt lịch. Tôi cần tra cứu `academic_query(SV2026002)` trước để biết tên cố vấn." | `academic_query(student_id="SV2026002")` | Status `SUCCESS`, `advisor = "TS. Lê Thị B"` |
| 2 | "Đã có thông tin cố vấn 'TS. Lê Thị B' từ Observation trước. Tôi tiến hành gọi `schedule_appointment` cho SV2026002." | `schedule_appointment(student_id, datetime_str, advisor_name="TS. Lê Thị B")` | Status `SUCCESS`, `booking_id = "BK-SV2026002-99"` |
| 3 | "Đã có đầy đủ Observation của cả 2 tool. Tổng hợp Final Answer đa bước." | Final Answer (text) | Tổng hợp cả 2 kết quả |

### 2.3 Trace các Test Case còn lại

* **TC01** (1 step, không Tool): Agent nhận diện câu hỏi kiến thức chung → Final Answer trực tiếp.
* **TC02** (2 steps): `academic_query(SV2026001)` → SUCCESS → Final Answer với thông tin Nguyễn Văn An (GPA 3.85).
* **TC03** (2 steps): `schedule_appointment(SV2026001, 14:00 15/09/2026, PGS.TS Nguyễn Văn A)` → SUCCESS → Final Answer.
* **TC05** (2 steps, Edge Case): `academic_query(SV9999999)` → `status="NOT_FOUND"` → Final Answer lịch sự, **không bịa đặt dữ liệu** (Anti-Hallucination).

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key trong `.env` (hỗ trợ `GEMINI_API_KEY` / `OPENAI_API_KEY`) và code đã sẵn sàng kết nối LLM API thật — fallback tự động về Mock nếu thiếu key.
- [x] **Tổng số Test Cases đã chạy thành công:** **5 / 5 test cases** (TC01–TC05).
- [x] **Số lượt gọi Tool qua MCP Server chính xác:** **5 lượt** (TC02: 1, TC03: 1, TC04: 2, TC05: 1, TC01: 0).
- [x] **Tổng số sự kiện Waterfall Trace Log:** **10 sự kiện** trong `docs/trace_waterfall.json` (TOOL_EXECUTION + FINAL_ANSWER).
- [x] **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

## 4. PHẢN ÁNH & TỰ ĐÁNH GIÁ

### 4.1 Điểm mạnh của bài nộp
* **Multi-step ReAct thực sự hoạt động** (TC04 đi qua 3 step: tra cứu cố vấn → đặt lịch → tổng hợp), tận dụng Observation của step trước để quyết định Action step sau.
* **MCP Server chuẩn JSON-RPC 2.0** với đầy đủ 4 trường bắt buộc (`jsonrpc`, `server`, `tool`, `result`), kèm xử lý lỗi `PARSE_ERROR` và `DISPATCH_ERROR` an toàn.
* **Conversation history** được truyền qua các provider (Gemini/OpenAI/Mock) để LLM thấy được Observation và quyết định bước tiếp.
* **Anti-Hallucination**: Agent không tự ý bịa thông tin khi nhận `NOT_FOUND` (TC05).
* **Mock Provider mô phỏng đầy đủ** các tình huống multi-step để học viên khác có thể chạy thử ngay cả khi không có API key.

### 4.2 Hướng cải thiện (nếu có thêm thời gian)
* Tích hợp thêm 1-2 sinh viên vào `MOCK_DATABASE` để mở rộng test edge cases.
* Thêm logging chi tiết hơn cho từng step (token usage, prompt length).
* Hỗ trợ streaming response từ LLM để UX tốt hơn ở chế độ `--interactive`.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân (`K4B-DAY03-LeDucHung-2A202602849`) và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
