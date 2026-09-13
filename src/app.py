"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).

MCP Transport Modes:
- 'local': Gọi function Python trực tiếp (backward compatible)
- 'stdio': Kết nối tới MCP Server thật qua subprocess JSON-RPC stdio transport
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

load_env()

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider
from intent_classifier import classify_intent

# Optional: Real MCP Client (stdio transport)
try:
    from mcp_client import MCPClient
    HAS_MCP_CLIENT = True
except ImportError:
    HAS_MCP_CLIENT = False


# =============================================================================
# INTENT ROUTING HANDLERS
# =============================================================================

def handle_user_input(user_input: str, provider, mcp_transport) -> tuple:
    """
    Route user input tới handler phù hợp dựa trên intent.
    Trả về tuple (response_text, trace_logs)
    """
    intent = classify_intent(user_input)
    print(f"[Intent] {intent}")
    
    if intent == "CASUAL":
        return handle_casual(user_input, provider)
    else:
        return handle_academic(user_input, provider, mcp_transport)


def handle_casual(user_input: str, provider) -> tuple:
    """
    Câu hỏi không liên quan học vụ → gọi LLM thật (Gemini/OpenAI/Mock).
    Trả về tuple (response_text, trace_logs)
    """
    print(f"[CASUAL] → Gọi LLM trực tiếp (không qua ReAct loop)")
    
    # Log intent event
    trace_logs = [{
        "step": 0,
        "query": user_input,
        "action_type": "INTENT_CASUAL",
        "intent": "CASUAL",
        "handler": provider.__class__.__name__,
        "latency_ms": 0
    }]
    
    try:
        # Gọi LLM provider với generate() method
        response = provider.generate(user_input, system_prompt=CHATBOT_BASELINE_PROMPT)
        
        # Log LLM response
        trace_logs.append({
            "step": 0,
            "query": user_input,
            "action_type": "LLM_RESPONSE",
            "content": response[:200] if response else "",
            "provider": provider.__class__.__name__,
            "latency_ms": 0
        })
        
        return response, trace_logs
    except Exception as e:
        error_msg = f"⚠️ Lỗi LLM ({provider.__class__.__name__}): {str(e)}\n💡 Tip: kiểm tra API key trong .env"
        trace_logs.append({
            "step": 0,
            "query": user_input,
            "action_type": "LLM_ERROR",
            "error": str(e),
            "provider": provider.__class__.__name__,
            "latency_ms": 0
        })
        return error_msg, trace_logs


def handle_academic(user_input: str, provider, mcp_transport) -> tuple:
    """
    Câu hỏi học vụ → ReAct loop + MCP tools (logic cũ).
    Trả về tuple (final_answer_text, trace_logs)
    """
    print(f"[ACADEMIC] → ReAct loop với MCP tools")
    
    # Log intent event
    trace_logs = [{
        "step": 0,
        "query": user_input,
        "action_type": "INTENT_ACADEMIC",
        "intent": "ACADEMIC",
        "handler": "ReAct_Agent",
        "latency_ms": 0
    }]
    
    # Gọi ReAct loop hiện có (bỏ qua 2 trace_logs đầu tiên, lấy phần ReAct)
    react_logs = run_react_agent(user_input, provider, mcp_transport)
    
    # Tổng hợp trace logs
    trace_logs.extend(react_logs)
    
    # Lấy final answer từ trace logs
    final_answer = ""
    for log in reversed(react_logs):
        if log.get("action_type") == "FINAL_ANSWER":
            final_answer = log.get("output", "")
            break
    
    return final_answer, trace_logs


# =============================================================================
# MCP TRANSPORT MODES
# =============================================================================

class MCPTransport:
    """
    MCP Transport Abstraction Layer
    Hỗ trợ 2 chế độ:
    - 'local': Gọi function Python trực tiếp (MCPAcademicServer)
    - 'stdio': Kết nối tới MCP Server thật qua subprocess
    """
    
    def __init__(self, mode: str = None):
        self.mode = mode or os.getenv("MCP_TRANSPORT", "local").lower()
        self._local_server: Optional[MCPAcademicServer] = None
        self._stdio_client: Optional[MCPClient] = None
        
        if self.mode == "stdio":
            if not HAS_MCP_CLIENT:
                print("⚠️ [MCPTransport] mcp_client not available, falling back to local mode")
                self.mode = "local"
            else:
                print("🔌 [MCPTransport] Using stdio transport (Real MCP Server)")
        else:
            print("🔌 [MCPTransport] Using local transport (in-process function calls)")
    
    def start(self):
        """Initialize MCP connection"""
        if self.mode == "stdio":
            self._stdio_client = MCPClient("src/mcp_server_stdio.py")
            self._stdio_client.start()
            print(f"   Connected to: {self._stdio_client.server_info}")
        else:
            self._local_server = MCPAcademicServer()
            print(f"   Server: {self._local_server.server_name}")
    
    def stop(self):
        """Cleanup MCP connection"""
        if self.mode == "stdio" and self._stdio_client:
            self._stdio_client.stop()
            self._stdio_client = None
        self._local_server = None
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        if self.mode == "stdio":
            return self._stdio_client.list_tools()
        else:
            return self._local_server.list_tools()
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool via MCP
        
        Returns:
            Dict with 'result' key containing the actual tool result
        """
        if self.mode == "stdio":
            # Real MCP Server returns result directly
            result = self._stdio_client.call_tool(tool_name, arguments)
            # Wrap in same format as local server for compatibility
            return {
                "jsonrpc": "2.0",
                "server": "vinuni-mcp-server",
                "tool": tool_name,
                "result": result
            }
        else:
            return self._local_server.call_tool(tool_name, arguments)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def run_react_agent(user_query: str, provider, mcp_transport: MCPTransport) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Hỗ trợ chuỗi suy luận đa bước (Multi-step ReAct):
      - Step k: LLM sinh Thought + Action (gọi Tool) hoặc Final Answer (text).
      - Nếu Tool: MCP Server trả Observation, nạp Observation vào lịch sử và gọi LLM ở Step k+1.
      - Nếu Text: đó là Final Answer, kết thúc vòng lặp.
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    step = 0
    trace_logs = []
    tools_list = mcp_transport.list_tools()
    # Lịch sử hội thoại dạng OpenAI-style messages (giúp LLM hiểu Observation ở step trước)
    conversation_history = [{"role": "user", "content": user_query}]

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        # Gọi LLM với toàn bộ lịch sử + Native Tool Calling Specs
        llm_response = provider.generate_with_tools(
            user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT,
            conversation_history=conversation_history,
        )
        latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")

        # === Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp (Final Answer) ===
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break

        # === Trường hợp 2: LLM đề xuất gọi Tool (Action) ===
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})

            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")

            # Thực thi Tool qua MCP Server (chuẩn JSON-RPC 2.0)
            mcp_result = mcp_transport.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})

            obs_str = json.dumps(obs_data, ensure_ascii=False)
            print(f"👁️ [Observation từ MCP Server]: {obs_str}")

            # Nạp Observation vào lịch sử để LLM có thể suy luận tiếp ở step sau
            conversation_history.append({
                "role": "assistant",
                "content": f"[Action] Gọi tool '{tool_name}' với args {json.dumps(arguments, ensure_ascii=False)}."
            })
            conversation_history.append({
                "role": "tool",
                "name": tool_name,
                "content": obs_str,
            })

            # Ghi nhận bước Tool Execution vào trace
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })

            # Nếu là bước cuối cùng (MAX_ITERATIONS), ép buộc tổng hợp Final Answer
            # để tránh vòng lặp vô hạn, đồng thời đảm bảo có trace kết quả.
            if step >= MAX_ITERATIONS:
                final_answer = _summarize_observation(obs_data, tool_name)
                print(f"🧠 [Thought]: Đã đạt giới hạn vòng lặp. Tổng hợp Final Answer từ Observation cuối.")
                print(f"🏁 [Final Answer]: {final_answer}")
                trace_logs.append({
                    "step": step + 1,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Tổng hợp Final Answer sau khi đạt MAX_ITERATIONS.",
                    "output": final_answer,
                    "latency_ms": 10.0
                })
                break

            # Nếu chưa hết vòng lặp, tiếp tục vòng lặp ReAct (cho LLM thấy Observation)
            continue

    # Nếu vòng lặp kết thúc mà chưa có Final Answer (hiếm gặp), tự tổng hợp từ Observation cuối
    has_final = any(t.get("action_type") == "FINAL_ANSWER" for t in trace_logs)
    if not has_final and trace_logs:
        last_tool = next((t for t in reversed(trace_logs) if t.get("action_type") == "TOOL_EXECUTION"), None)
        if last_tool:
            fallback_answer = _summarize_observation(last_tool.get("observation", {}), last_tool.get("tool_name", ""))
            trace_logs.append({
                "step": len(trace_logs) + 1,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": "Fallback tổng hợp Final Answer từ Observation cuối cùng.",
                "output": fallback_answer,
                "latency_ms": 5.0
            })

    return trace_logs


def _summarize_observation(obs_data: dict, tool_name: str = "") -> str:
    """
    Hàm phụ trợ: Tổng hợp Final Answer từ Observation do MCP Server trả về.
    Được dùng khi LLM không tự sinh được Final Answer (ví dụ đạt MAX_ITERATIONS).
    """
    if not obs_data:
        return "Chưa nhận được dữ liệu từ MCP Server."

    status = obs_data.get("status")
    if status == "SUCCESS":
        if "data" in obs_data:
            d = obs_data["data"]
            return (
                f"Kết quả tra cứu cho sinh viên {obs_data.get('student_id', '')} "
                f"({d.get('full_name', '')}): Lớp {d.get('class', '')}, "
                f"GPA: {d.get('gpa', '')}, Email: {d.get('email', '')}, "
                f"Trạng thái: {d.get('status', '')}, Cố vấn: {d.get('advisor', '')}."
            )
        if "message" in obs_data:
            return obs_data["message"]
        return f"Đã hoàn tất xử lý qua MCP Server: {json.dumps(obs_data, ensure_ascii=False)}"

    if status == "NOT_FOUND":
        return obs_data.get("message", "Không tìm thấy thông tin sinh viên yêu cầu.")

    if status in ("EXECUTION_ERROR", "UNKNOWN_TOOL", "PARSE_ERROR", "DISPATCH_ERROR"):
        return f"Lỗi thực thi tool '{tool_name}': {obs_data.get('error', 'Không rõ nguyên nhân.')}"

    return f"Phản hồi từ công cụ: {json.dumps(obs_data, ensure_ascii=False)}"


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    # Initialize LLM Provider
    provider = get_llm_provider()
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    
    # Initialize MCP Transport (local or stdio based on MCP_TRANSPORT env)
    mcp_transport = MCPTransport()
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    try:
        # Start MCP transport
        mcp_transport.start()
        print(f"🌐 MCP Transport: {mcp_transport.mode}")
        
        if "--interactive" in sys.argv:
            print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với AI Assistant:")
            print("💡 Gợi ý câu hỏi thử nghiệm:")
            print("   - Câu hỏi chung: 'Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?'")
            print("   - Tra cứu học vụ: 'Hãy tra cứu thông tin học vụ của sinh viên SV2026001'")
            print("   - Đặt lịch hẹn: 'Đặt lịch hẹn tư vấn cho SV2026001 vào 14:00 ngày 15/09/2026'")
            print("   - Câu hỏi casual: 'Hôm nay là thứ mấy?', 'Xin chào bạn', 'Thời tiết thế nào?'")
            print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
            while True:
                try:
                    user_input = input("👤 Sinh viên hỏi: ").strip()
                    if not user_input or user_input.lower() in ["exit", "quit"]:
                        print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                        break
                    response, logs = handle_user_input(user_input, provider, mcp_transport)
                    print(f"\n🤖 Assistant: {response}\n")
                    save_waterfall_trace(logs)
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 Đã thoát phiên tương tác.")
                    break
        elif "--all" in sys.argv:
            print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
            completed_count = 0
            todo_count = 0
            all_traces = []
            
            for tc in tests:
                print(f"\n==================================================")
                print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
                print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
                
                if tc["question"].strip().startswith("TODO"):
                    print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                    print(f"   {tc['question']}")
                    print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                    todo_count += 1
                else:
                    logs = run_react_agent(tc["question"], provider, mcp_transport)
                    all_traces.extend(logs)
                    completed_count += 1
                    
            print(f"\n==================================================")
            print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
            if all_traces:
                save_waterfall_trace(all_traces)
            print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
        else:
            # Chế độ mặc định khi chỉ gõ 'python src/app.py'
            print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
            print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
            print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
            
            # Demo: chạy 1 test case mẫu (vẫn dùng ReAct loop cho backward compat)
            sample_query = tests[1]["question"]
            print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu học vụ) ---")
            logs = run_react_agent(sample_query, provider, mcp_transport)
            save_waterfall_trace(logs)
            
            # Demo: câu hỏi casual để thể hiện intent routing
            print("\n--- 🏁 DEMO INTENT ROUTING ---")
            casual_query = "Xin chào bạn!"
            print(f"\n📝 Câu hỏi casual: '{casual_query}'")
            response, logs = handle_user_input(casual_query, provider, mcp_transport)
            print(f"🤖 Assistant: {response}")
            
            print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
    finally:
        # Cleanup MCP transport
        mcp_transport.stop()
