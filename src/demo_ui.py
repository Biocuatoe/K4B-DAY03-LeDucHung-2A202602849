"""
🤖 DEMO UI CHO REACT AGENT — GIAO DIỆN WEB GRADIO
Trợ lý Học vụ Sinh viên VinUni với khả năng tương tác đa bước (Multi-turn).

YÊU CẦU CÀI ĐẶT:
    pip install gradio

CÁCH CHẠY:
    python src/demo_ui.py

GIAO DIỆN SẼ MỞ TẠI: http://localhost:7860
"""

# ============================================================================
# SECTION 1: IMPORTS & SETUP
# ============================================================================
import sys
import os

# Thêm thư mục cha vào sys.path để import được các module trong src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cấu hình UTF-8 output cho console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các module từ dự án
from src.mcp_server import MCPAcademicServer
from src.providers import get_llm_provider
from src.app import run_react_agent  # Reuse hàm chính từ app.py

# Import Gradio
import gradio as gr

# ============================================================================
# SECTION 2: KHỞI TẠO AGENT CORE (Một lần khi khởi động server)
# ============================================================================

# Biến toàn cục lưu trữ provider và MCP server
_provider = None
_mcp_server = None


def _get_agent_components():
    """
    Lazy initialization cho provider và MCP server.
    Đảm bảo chỉ khởi tạo một lần khi bắt đầu phiên trò chuyện đầu tiên.
    """
    global _provider, _mcp_server
    if _provider is None:
        _provider = get_llm_provider()
        print(f"🔌 [INIT] LLM Provider: {_provider.__class__.__name__}")
    if _mcp_server is None:
        _mcp_server = MCPAcademicServer()
        print(f"🌐 [INIT] MCP Server: {_mcp_server.server_name}")
    return _provider, _mcp_server


# ============================================================================
# SECTION 3: HANDLERS CHO GRADIO INTERFACE
# ============================================================================

def respond(
    user_message: str,
    chat_history: list,
    trace_state: dict
) -> tuple:
    """
    Xử lý mỗi câu hỏi từ user, gọi ReAct Agent và trả về kết quả.
    
    Args:
        user_message (str): Câu hỏi của sinh viên
        chat_history (list): Lịch sử hội thoại Gradio ChatInterface
        trace_state (dict): State chứa trace logs của phiên hiện tại
    
    Returns:
        tuple: (updated_chat_history, updated_trace_state, "")
        - updated_chat_history: Danh sách messages mới cho chatbot
        - updated_trace_state: Dict chứa trace logs cập nhật
        - "": Chuỗi rỗng để Gradio không hiển thị text phụ (chúng ta dùng components khác)
    """
    # Khởi tạo Agent components nếu chưa có
    provider, mcp_server = _get_agent_components()
    
    # Nếu trace_state rỗng, khởi tạo cấu trúc mới
    if not trace_state or not isinstance(trace_state, dict):
        trace_state = {"logs": [], "last_question": ""}
    
    # Thêm câu hỏi vào chat history (hiển thị user message)
    chat_history.append([user_message, None])  # None = chờ response
    
    # Gọi ReAct Agent xử lý câu hỏi
    try:
        # Gọi hàm run_react_agent từ app.py - trả về list[dict] trace logs
        trace_logs = run_react_agent(
            user_query=user_message,
            provider=provider,
            mcp_server=mcp_server
        )
        
        # Tìm Final Answer từ trace logs để hiển thị trong chat
        final_answer = _extract_final_answer(trace_logs)
        
        # Cập nhật chat history với phản hồi của Agent
        chat_history[-1][1] = final_answer
        
        # Cập nhật trace logs vào state
        trace_state["logs"] = trace_logs
        trace_state["last_question"] = user_message
        
        # Log ra console để debug
        print(f"\n✅ [RESPOND] Câu hỏi: {user_message}")
        print(f"📊 [TRACE] Số bước ReAct: {len(trace_logs)}")
        
    except Exception as e:
        # Xử lý lỗi nếu Agent gặp sự cố
        error_msg = f"⚠️ Đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}"
        chat_history[-1][1] = error_msg
        print(f"❌ [ERROR] {error_msg}")
    
    # Trả về tuple: (chat_history, trace_state, visible_text_for_textbox)
    return chat_history, trace_state, ""


def _extract_final_answer(trace_logs: list) -> str:
    """
    Trích xuất Final Answer từ trace logs của ReAct Agent.
    Nếu không có Final Answer, trả về thông báo mặc định.
    """
    if not trace_logs:
        return "Agent chưa có phản hồi. Vui lòng thử lại."
    
    # Tìm bước FINAL_ANSWER cuối cùng
    for log in reversed(trace_logs):
        if log.get("action_type") == "FINAL_ANSWER":
            return log.get("output", "Agent không có nội dung phản hồi.")
    
    # Nếu không có FINAL_ANSWER, trả về observation cuối cùng
    for log in reversed(trace_logs):
        if log.get("action_type") == "TOOL_EXECUTION":
            obs = log.get("observation", {})
            if isinstance(obs, dict):
                if obs.get("status") == "SUCCESS":
                    data = obs.get("data", {})
                    return f"Kết quả: {data}"
                elif obs.get("status") == "NOT_FOUND":
                    return obs.get("message", "Không tìm thấy thông tin.")
                elif obs.get("message"):
                    return obs.get("message")
    
    return "Agent đã xử lý xong nhưng không có phản hồi cuối cùng."


def format_trace_for_display(trace_state: dict) -> dict:
    """
    Format trace logs thành cấu trúc hiển thị đẹp trong gr.JSON.
    Mỗi step được format với màu sắc và icon tương ứng.
    """
    logs = trace_state.get("logs", []) if trace_state else []
    
    if not logs:
        return {
            "status": "Chưa có trace logs",
            "message": "Hãy đặt câu hỏi để xem quá trình suy luận của Agent."
        }
    
    # Format mỗi step để hiển thị đẹp hơn
    formatted_steps = []
    for log in logs:
        step_info = {
            "step": log.get("step", "?"),
            "type": log.get("action_type", "UNKNOWN"),
        }
        
        if log.get("action_type") == "TOOL_EXECUTION":
            step_info["icon"] = "🛠️"
            step_info["tool"] = log.get("tool_name", "unknown")
            step_info["arguments"] = log.get("arguments", {})
            step_info["observation"] = log.get("observation", {})
            step_info["thought"] = log.get("thought", "")
        else:  # FINAL_ANSWER
            step_info["icon"] = "🏁"
            step_info["final_answer"] = log.get("output", "")
            step_info["thought"] = log.get("thought", "")
        
        step_info["latency_ms"] = log.get("latency_ms", 0)
        formatted_steps.append(step_info)
    
    return {
        "total_steps": len(logs),
        "steps": formatted_steps
    }


def clear_session() -> tuple:
    """
    Reset toàn bộ phiên trò chuyện và trace logs.
    Được gọi khi user click nút "Làm mới".
    """
    return [], {}, ""


def apply_quick_prompt(prompt_text: str) -> tuple:
    """
    Auto-fill quick prompt vào textbox khi user click nút bấm.
    """
    return gr.update(value=prompt_text)


# ============================================================================
# SECTION 4: BUILD GRADIO UI
# ============================================================================

def build_ui():
    """
    Xây dựng giao diện Gradio với các thành phần:
    - Header với tiêu đề và mô tả
    - Quick prompt buttons
    - ChatInterface cho multi-turn conversation
    - Trace log panel hiển thị JSON
    """
    
    # --- 4.1: Mô tả & Hướng dẫn (Header) ---
    header_md = """
# 🤖 VinUni ReAct Agent — Trợ lý Học vụ Sinh viên

Chào mừng bạn đến với **Trợ lý Học vụ AI** của VinUni! 

🎯 **Agent này có thể làm gì?**
- Tra cứu thông tin học vụ sinh viên (GPA, lớp, cố vấn...)
- Đặt lịch hẹn tư vấn với cố vấn học tập
- Tự động suy luận đa bước (ReAct Loop) để hỗ trợ yêu cầu phức tạp

📖 **Cách sử dụng:**
1. Nhập câu hỏi vào ô chat bên dưới
2. Xem phản hồi của Agent trong cùng khung chat
3. Kiểm tra **"📋 Trace Log"** bên dưới để xem chi tiết từng bước suy luận

⚡ **Mẹo:** Dùng các nút **Quick Prompt** để thử nghiệm nhanh các câu hỏi mẫu!
"""
    
    # --- 4.2: Các Quick Prompts mẫu ---
    quick_prompts = [
        # Label, Prompt text
        ("📚 TC02: Tra cứu", "Cho tôi biết thông tin học vụ của sinh viên SV2026001"),
        ("📅 TC03: Đặt lịch", "Đặt lịch hẹn tư vấn cho SV2026001 với PGS.TS Nguyễn Văn A vào 14:00 ngày 15/09/2026"),
        ("🔄 TC04: Đa bước", "Em là sinh viên SV2026002, hãy cho em biết cố vấn học tập và đặt lịch hẹn với cố vấn đó vào 10:00 ngày 20/09/2026"),
        ("❌ Edge Case", "Cho tôi xin thông tin sinh viên SV9999999"),
    ]
    
    # --- 4.3: Xây dựng UI với Blocks ---
    with gr.Blocks(
        title="VinUni ReAct Agent Demo",
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="cyan",
        )
    ) as demo:
        
        # --- State để lưu trace logs giữa các lượt chat ---
        trace_state = gr.State({})
        
        # --- Header ---
        gr.Markdown(header_md)
        
        # --- Quick Prompts Buttons ---
        with gr.Row():
            for label, prompt_text in quick_prompts:
                # Mỗi nút sẽ trigger hàm apply_quick_prompt để fill textbox
                btn = gr.Button(
                    label,
                    variant="secondary",
                    size="sm"
                )
        
        # --- Main Chat Interface ---
        gr.ChatInterface(
            fn=respond,
            type="messages",  # Sử dụng format messages mới của Gradio 5.x
            title="💬 Trò chuyện với Agent",
            description="Nhập câu hỏi về học vụ VinUni...",
            textbox=gr.Textbox(
                placeholder="Nhập câu hỏi của bạn ở đây... (VD: Cho tôi biết thông tin học vụ của sinh viên SV2026001)",
                label="Câu hỏi",
                lines=2,
            ),
            chatbot=gr.Chatbot(
                height=400,
                show_copy_button=True,
                avatar_images=("👤", "🤖"),  # Avatar user và assistant
            ),
            examples=[
                ["Cho tôi biết thông tin học vụ của sinh viên SV2026001"],
                ["Đặt lịch hẹn tư vấn cho SV2026001 với PGS.TS Nguyễn Văn A vào 14:00 ngày 15/09/2026"],
                ["Em là sinh viên SV2026002, hãy cho em biết cố vấn học tập và đặt lịch hẹn với cố vấn đó vào 10:00 ngày 20/09/2026"],
                ["Cho tôi xin thông tin sinh viên SV9999999"],
            ],
            cacheable=False,  # Không cache để mỗi câu hỏi đều được xử lý mới
        )
        
        # --- Trace Log Panel ---
        with gr.Accordion("📋 Trace Log — Chi tiết từng bước suy luận của Agent", open=False):
            gr.Markdown("""
            **Trace Log** ghi lại toàn bộ quá trình suy luận của Agent:
            - 🧠 **Thought**: Suy nghĩ của Agent tại mỗi bước
            - 🛠️ **Action**: Tool mà Agent gọi (nếu có)
            - 👁️ **Observation**: Kết quả từ MCP Server
            - ⏱️ **Latency**: Thời gian xử lý (ms)
            """)
            
            trace_json = gr.JSON(
                label="ReAct Trace Logs",
                show_label=True,
                container=True,
            )
        
        # --- Cập nhật trace JSON khi có thay đổi ---
        demo.load(
            fn=format_trace_for_display,
            inputs=[trace_state],
            outputs=[trace_json],
        )
        
        # --- Nút làm mới phiên trò chuyện ---
        with gr.Row():
            clear_btn = gr.Button("🔄 Làm mới phiên trò chuyện", variant="stop")
            clear_btn.click(
                fn=clear_session,
                outputs=[gr.Chatbot(), trace_state, gr.Textbox()],
            )
        
        # --- Footer ---
        gr.Markdown("""
        ---
        💡 **Ghi chú:**
        - Chế độ **Mock Offline** đang được kích hoạt (không cần API Key).
        - Để sử dụng LLM thật, hãy điền `GEMINI_API_KEY` vào file `.env`.
        - Source code: [`src/demo_ui.py`](src/demo_ui.py) | [`src/app.py`](src/app.py)
        """)
    
    return demo


# ============================================================================
# SECTION 5: MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 KHỞI ĐỘNG VINUNI REACT AGENT DEMO UI")
    print("=" * 60)
    print("📌 Yêu cầu: pip install gradio")
    print("🌐 Giao diện sẽ mở tại: http://localhost:7860")
    print("=" * 60)
    
    # Khởi tạo Agent components trước
    _get_agent_components()
    
    # Build và launch UI
    demo = build_ui()
    demo.launch(
        share=False,           # True để tạo public link (cần tài khoản Gradio)
        server_name="0.0.0.0", # Bind tất cả interfaces
        server_port=7860,      # Port mặc định của Gradio
        show_error=True,       # Hiển thị chi tiết lỗi
        favicon_path=None,     # Có thể đổi thành icon .ico nếu muốn
    )
