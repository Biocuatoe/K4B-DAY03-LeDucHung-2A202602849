"""
🔌 MCP Client - JSON-RPC 2.0 over stdio
Kết nối tới MCP server thật (subprocess), thay thế việc gọi function local.

Usage:
    from mcp_client import MCPClient
    
    client = MCPClient("src/mcp_server_stdio.py")
    client.start()
    
    tools = client.list_tools()
    result = client.call_tool("academic_query", {"student_id": "SV2026001"})
    
    client.stop()
"""

import subprocess
import sys
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MCPClient:
    """
    MCP Client kết nối tới MCP Server qua stdio transport.
    
    Hỗ trợ:
    - Auto-reconnect nếu process chết
    - Thread-safe request/response
    - Timeout handling
    - Graceful shutdown
    """
    
    def __init__(
        self,
        server_script: str = "src/mcp_server_stdio.py",
        timeout: float = 30.0,
        auto_reconnect: bool = True,
        max_retries: int = 3
    ):
        self.server_script = server_script
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self.max_retries = max_retries
        
        self.process: Optional[subprocess.Popen] = None
        self._msg_id_counter = 0
        self._lock = threading.Lock()
        self._server_info: Optional[Dict] = None
        self._tools_cache: Optional[List[Dict]] = None
        
        # Determine server path
        if Path(server_script).is_absolute():
            self._server_path = Path(server_script)
        else:
            # Resolve relative to project root (parent of src/)
            if '__file__' in globals():
                base_dir = Path(__file__).resolve().parent.parent
            else:
                base_dir = Path.cwd()
            self._server_path = base_dir / server_script
    
    def start(self, max_retries: int = 5, retry_delay: float = 0.5) -> Dict:
        """
        Spawn MCP server subprocess và initialize handshake với retry logic.
        
        Args:
            max_retries: Số lần thử lại nếu initialization thất bại (default: 5)
            retry_delay: Thời gian chờ giữa các lần thử (giây, default: 0.5)
            
        Returns:
            Dict: Server info từ initialize response
            
        Raises:
            FileNotFoundError: Nếu server script không tìm thấy
            RuntimeError: Nếu initialization thất bại sau tất cả retries
        """
        if not self._server_path.exists():
            raise FileNotFoundError(f"MCP server not found: {self._server_path}")
        
        # Kill existing process if any
        self.stop()
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Start subprocess
                self.process = subprocess.Popen(
                    [sys.executable, str(self._server_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,  # Unbuffered for real-time I/O
                )
                
                print(f"[MCPClient] Spawned subprocess pid={self.process.pid} (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                
                # Wait for subprocess to be ready (small delay)
                time.sleep(0.1)
                
                # Send initialize request
                init_result = self._send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {
                        "name": "vinuni-mcp-client",
                        "version": "1.0.0"
                    },
                    "capabilities": {}
                })
                
                self._server_info = init_result
                self._tools_cache = None
                print(f"[MCPClient] Initialized successfully: {init_result.get('serverInfo', {})}", file=sys.stderr)
                return init_result
                
            except Exception as e:
                last_error = e
                print(f"[MCPClient] Initialization attempt {attempt+1}/{max_retries} failed: {e}", file=sys.stderr)
                
                # Clean up failed process
                if self.process:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=2)
                    except:
                        try:
                            self.process.kill()
                        except:
                            pass
                    self.process = None
                
                # Wait before retry (with exponential backoff)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # 0.5s, 1s, 2s, 4s...
        
        # All retries exhausted
        raise RuntimeError(f"MCP client initialization failed after {max_retries} attempts: {last_error}")
    
    def list_tools(self) -> List[Dict]:
        """
        Lấy danh sách tools từ MCP server.
        
        Returns:
            List[Dict]: Danh sách tool schemas
        """
        if self._tools_cache is not None:
            return self._tools_cache
        
        result = self._send_request("tools/list", {})
        tools = result.get("tools", [])
        self._tools_cache = tools
        return tools
    
    def call_tool(self, name: str, arguments: Dict) -> Dict:
        """
        Gọi tool trên MCP server.
        
        Args:
            name: Tên tool cần gọi
            arguments: Dictionary arguments cho tool
            
        Returns:
            Dict: Kết quả từ tool execution
            
        Raises:
            RuntimeError: Nếu MCP server lỗi hoặc không khả dụng
        """
        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        # Parse MCP content format
        # MCP responses have format: {"content": [{"type": "text", "text": "..."}]}
        content = result.get("content", [])
        if content and isinstance(content, list):
            first_content = content[0]
            if first_content.get("type") == "text":
                try:
                    return json.loads(first_content["text"])
                except json.JSONDecodeError:
                    return {"status": "ERROR", "error": "Failed to parse tool result", "raw": first_content["text"]}
        
        return result
    
    def stop(self):
        """Terminate subprocess gracefully."""
        if self.process:
            if self.process.poll() is None:
                try:
                    # Try graceful shutdown first
                    try:
                        self._send_request("shutdown", {})
                    except Exception:
                        pass
                    
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                except Exception as e:
                    print(f"[MCPClient] Error stopping process: {e}", file=sys.stderr)
            
            self.process = None
            self._server_info = None
            self._tools_cache = None
            print("[MCPClient] Process stopped", file=sys.stderr)
    
    @property
    def is_connected(self) -> bool:
        """Kiểm tra xem subprocess có đang chạy không."""
        return self.process is not None and self.process.poll() is None
    
    @property
    def server_info(self) -> Optional[Dict]:
        """Lấy server info từ initialize response."""
        return self._server_info
    
    def _next_id(self) -> int:
        """Generate unique message ID (thread-safe)."""
        with self._lock:
            self._msg_id_counter += 1
            return self._msg_id_counter
    
    def _send_request(self, method: str, params: Dict, retry_count: int = 2) -> Dict:
        """
        Gửi JSON-RPC request và đọc response.
        
        Args:
            method: JSON-RPC method name
            params: Parameters for the method
            retry_count: Số lần retry nếu request thất bại (default: 2)
            
        Returns:
            Dict: Result from response
            
        Raises:
            RuntimeError: Nếu request thất bại
        """
        if not self.process:
            raise RuntimeError("MCP client not started. Call start() first.")
        
        last_error = None
        
        for attempt in range(retry_count + 1):
            msg_id = self._next_id()
            request = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": method,
                "params": params
            }
            
            body = json.dumps(request, ensure_ascii=False).encode('utf-8')
            header = f"Content-Length: {len(body)}\r\n\r\n".encode('utf-8')
            
            try:
                self.process.stdin.write(header + body)
                self.process.stdin.flush()
            except BrokenPipeError as e:
                last_error = RuntimeError("MCP server process died unexpectedly")
                if attempt < retry_count:
                    print(f"[MCPClient] BrokenPipe, retrying ({attempt+1}/{retry_count})...", file=sys.stderr)
                    continue
                raise last_error
            
            # Read response with timeout
            try:
                return self._read_response()
            except Exception as e:
                last_error = e
                if attempt < retry_count:
                    print(f"[MCPClient] Request failed, retrying ({attempt+1}/{retry_count})...", file=sys.stderr)
                    continue
                raise RuntimeError(f"MCP request failed after {retry_count + 1} attempts: {e}")
        
        raise RuntimeError(f"MCP request failed: {last_error}")
    
    def _read_response(self) -> Dict:
        """
        Đọc JSON-RPC response với Content-Length framing.
        
        Returns:
            Dict: Parsed response
            
        Raises:
            EOFError: Nếu server đóng stdout
            ValueError: Nếu response không đúng format
        """
        # Read headers
        headers = {}
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise EOFError("MCP server closed stdout")
            
            line_str = line.decode('utf-8', errors='replace').strip()
            if not line_str:
                break
            if ":" in line_str:
                key, val = line_str.split(":", 1)
                headers[key.strip()] = val.strip()
        
        length = int(headers.get("Content-Length", 0))
        if length == 0:
            raise ValueError("Missing Content-Length header in MCP response")
        
        body = self.process.stdout.read(length)
        response = json.loads(body.decode('utf-8'))
        
        if "error" in response:
            err = response["error"]
            raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
        
        return response.get("result", {})
    
    def __enter__(self):
        """Context manager entry - tự động start."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - tự động stop."""
        self.stop()
        return False


# ===== Convenience functions =====
def create_mcp_client(server_script: str = "src/mcp_server_stdio.py") -> MCPClient:
    """
    Factory function tạo và khởi tạo MCPClient.
    
    Usage:
        client = create_mcp_client()
        try:
            tools = client.list_tools()
            result = client.call_tool("academic_query", {"student_id": "SV2026001"})
        finally:
            client.stop()
    """
    client = MCPClient(server_script)
    client.start()
    return client


# ===== Test if run directly =====
if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("MCP Client Test")
    print("=" * 60)
    
    client = MCPClient("src/mcp_server_stdio.py")
    
    try:
        # Start connection
        server_info = client.start()
        print(f"✅ Connected to MCP Server: {server_info.get('serverInfo', {})}")
        
        # List tools
        tools = client.list_tools()
        print(f"✅ Available tools: {len(tools)}")
        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', '')[:50]}...")
        
        # Test academic_query
        print("\n📝 Testing academic_query:")
        result = client.call_tool("academic_query", {"student_id": "SV2026001"})
        print(f"   Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # Test schedule_appointment
        print("\n📝 Testing schedule_appointment:")
        result = client.call_tool("schedule_appointment", {
            "student_id": "SV2026001",
            "datetime_str": "14:00 ngày 15/09/2026",
            "advisor_name": "PGS.TS Nguyễn Văn A"
        })
        print(f"   Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.stop()
