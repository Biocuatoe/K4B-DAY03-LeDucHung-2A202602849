"""
🔌 MCP Server thật - JSON-RPC 2.0 over stdio
Tuân thủ MCP protocol (Model Context Protocol)
https://modelcontextprotocol.io/

Chạy: python src/mcp_server_stdio.py
Giao tiếp qua stdin/stdout với Content-Length framing (chuẩn LSP/MCP)
"""

import sys
import json
from typing import Any, Dict, List

# Import tool implementations từ module hiện có
sys.path.insert(0, str(__file__).rsplit('/', 1)[0] if '/' in __file__ else '.')
from tools import execute_academic_query, execute_schedule_appointment


# ===== JSON-RPC 2.0 helpers =====
def send_response(msg_id: Any, result: Any) -> None:
    """Gửi JSON-RPC response qua stdout"""
    response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
    msg = json.dumps(response, ensure_ascii=False)
    _write_message(msg)


def send_error(msg_id: Any, code: int, message: str, data: Any = None) -> None:
    """Gửi JSON-RPC error response qua stdout"""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    response = {"jsonrpc": "2.0", "id": msg_id, "error": error}
    msg = json.dumps(response, ensure_ascii=False)
    _write_message(msg)


def _write_message(msg: str) -> None:
    """Write message với Content-Length header"""
    body = msg.encode('utf-8')
    header = f"Content-Length: {len(body)}\r\n\r\n".encode('utf-8')
    sys.stdout.buffer.write(header + body)
    sys.stdout.buffer.flush()


def read_message() -> Dict:
    """Đọc 1 JSON-RPC message từ stdin theo Content-Length protocol"""
    # Read headers
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            raise EOFError("stdin closed")
        line = line.strip()
        if not line:
            break
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()
    
    length = int(headers.get("Content-Length", 0))
    if length == 0:
        raise ValueError("Missing Content-Length")
    
    body = sys.stdin.read(length)
    return json.loads(body)


# ===== Tool Schemas theo MCP spec =====
TOOLS_SCHEMA = [
    {
        "name": "academic_query",
        "description": "Tra cứu thông tin học vụ của sinh viên theo mã SV",
        "inputSchema": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên (VD: SV2026001)"
                }
            },
            "required": ["student_id"]
        }
    },
    {
        "name": "schedule_appointment",
        "description": "Đặt lịch hẹn tư vấn học vụ với cố vấn",
        "inputSchema": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần đặt lịch"
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian đặt lịch (VD: '14:00 ngày 15/09/2026')"
                },
                "advisor_name": {
                    "type": "string",
                    "description": "Tên cố vấn học tập"
                }
            },
            "required": ["student_id", "datetime_str", "advisor_name"]
        }
    }
]


# ===== MCP method handlers =====
def handle_initialize(msg_id, params) -> Dict:
    """Xử lý initialize request - MCP handshake"""
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "vinuni-mcp-server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {}
        }
    }


def handle_tools_list(msg_id, params) -> Dict:
    """Xử lý tools/list request - trả về danh sách tools"""
    return {"tools": TOOLS_SCHEMA}


def handle_tools_call(msg_id, params) -> Dict:
    """Xử lý tools/call request - thực thi tool"""
    name = params.get("name")
    arguments = params.get("arguments", {})
    
    if name == "academic_query":
        raw_result = execute_academic_query(arguments.get("student_id", ""))
        try:
            result_data = json.loads(raw_result)
        except json.JSONDecodeError:
            result_data = {"status": "ERROR", "error": "Failed to parse result"}
    elif name == "schedule_appointment":
        raw_result = execute_schedule_appointment(
            arguments.get("student_id", ""),
            arguments.get("datetime_str", ""),
            arguments.get("advisor_name", "")
        )
        try:
            result_data = json.loads(raw_result)
        except json.JSONDecodeError:
            result_data = {"status": "ERROR", "error": "Failed to parse result"}
    else:
        send_error(msg_id, -32601, f"Unknown tool: {name}")
        return
    
    # Trả về theo MCP content format
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result_data, ensure_ascii=False)
            }
        ],
        "isError": result_data.get("status") in ("ERROR", "NOT_FOUND", "EXECUTION_ERROR", "DISPATCH_ERROR", "PARSE_ERROR")
    }


# ===== MCP notifications ( responses without id) =====
def handle_initialized(msg_id, params) -> None:
    """Xử lý initialized notification - không cần reply"""
    print("[mcp_server_stdio] Server initialized successfully", file=sys.stderr)


def handle_shutdown(msg_id, params) -> Dict:
    """Xử lý shutdown request"""
    return {"success": True}


# ===== Main loop =====
def main():
    """Main loop - đọc JSON-RPC requests từ stdin, gửi responses ra stdout"""
    print("[mcp_server_stdio] Started, listening on stdio...", file=sys.stderr)
    print("[mcp_server_stdio] Protocol: JSON-RPC 2.0 over Content-Length framing", file=sys.stderr)
    
    while True:
        try:
            msg = read_message()
            method = msg.get("method")
            msg_id = msg.get("id")
            params = msg.get("params", {})
            
            print(f"[mcp_server_stdio] Received: method={method}, id={msg_id}", file=sys.stderr)
            
            # Initialize
            if method == "initialize":
                send_response(msg_id, handle_initialize(msg_id, params))
            
            # Tools
            elif method == "tools/list":
                send_response(msg_id, handle_tools_list(msg_id, params))
            elif method == "tools/call":
                send_response(msg_id, handle_tools_call(msg_id, params))
            
            # Notifications (no response needed)
            elif method == "initialized":
                handle_initialized(msg_id, params)
            
            # Shutdown
            elif method == "shutdown":
                send_response(msg_id, handle_shutdown(msg_id, params))
                print("[mcp_server_stdio] Shutdown requested, exiting.", file=sys.stderr)
                break
            
            # Unknown method
            else:
                send_error(msg_id, -32601, f"Method not found: {method}")
                
        except EOFError:
            print("[mcp_server_stdio] stdin closed, exiting.", file=sys.stderr)
            break
        except Exception as e:
            print(f"[mcp_server_stdio] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            send_error(None, -32603, f"Internal error: {str(e)}")


if __name__ == "__main__":
    main()
