"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPAcademicServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "vinuni-academic-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC 2.0.

        Quy trình xử lý:
          1. Nhận yêu cầu gọi Tool từ MCP Client (Agent Core).
          2. Điều phối Tool thực thi qua hàm `dispatch_tool_call()` trong tools.py.
          3. Parse chuỗi JSON trả về thành Python Dict.
          4. Đóng gói phản hồi theo chuẩn JSON-RPC 2.0 với các trường:
             jsonrpc, server (tên MCP Server), tool (tên tool), result (payload).
          5. Nếu Tool dispatch trả về chuỗi rỗng hoặc parse lỗi, vẫn đóng gói JSON-RPC
             với result rỗng để Agent nhận biết cần xử lý tiếp.
        """
        try:
            # (1) Gọi Tool Router để thực thi Tool và nhận về chuỗi JSON
            raw_response = dispatch_tool_call(tool_name, arguments)

            # (2) Parse chuỗi JSON thành Python Dictionary
            try:
                content = json.loads(raw_response) if raw_response else {}
            except (json.JSONDecodeError, TypeError):
                # Nếu Tool trả về chuỗi không phải JSON hợp lệ, gói vào dict báo lỗi parse
                content = {
                    "status": "PARSE_ERROR",
                    "error": f"Tool '{tool_name}' trả về chuỗi không hợp lệ JSON.",
                    "raw_output": raw_response,
                }

        except Exception as e:
            # (3) Bảo vệ lỗi ngoại lệ trong quá trình dispatch tool
            content = {
                "status": "DISPATCH_ERROR",
                "error": f"Lỗi khi dispatch tool '{tool_name}': {str(e)}",
            }

        # (4) Đóng gói phản hồi chuẩn JSON-RPC 2.0
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content,
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (vinuni-academic-mcp-server)")
    print("==========================================================")
    
    server = MCPAcademicServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # Kiểm tra trạng thái TODO 1.2 (Tool Schema)
    sched_tool = next((t for t in tools if t.get("name") == "schedule_appointment"), None)
    if sched_tool and not sched_tool.get("parameters", {}).get("properties"):
        print("⏳ [TODO 1.2]: Tool 'schedule_appointment' chưa được định nghĩa properties trong 'src/tools.py'.")
    else:
        print("✅ [TODO 1.2]: Tool 'schedule_appointment' đã có schema đầy đủ.")

    # Kiểm tra trạng thái TODO 2.1 (call_tool)
    test_result = server.call_tool("academic_query", {"student_id": "SV2026001"})
    if not test_result:
        print("⏳ [TODO 2.1]: Hàm call_tool() đang trả về rỗng. Học viên hãy hoàn thiện TODO 2.1 trong 'src/mcp_server.py'!")
    else:
        print(f"✅ [TODO 2.1]: Test dispatch tool 'academic_query' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")
