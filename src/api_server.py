"""
HTTP Wrapper cho MCP Server
Cho phep demo HTML goi MCP server that qua fetch() HTTP request.

Chay: python src/api_server.py
Server se khoi dong tai http://localhost:8765

Endpoints:
- GET / - Server info
- POST /chat - Gui cau hoi, nhan ket qua tu MCP Server
- GET /health - Health check
- GET /tools - List available tools
"""

import sys
import os
import re
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify
from flask_cors import CORS
from mcp_client import MCPClient
from intent_classifier import classify_intent

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes - allows browser fetch from file:// or other origins

# Global MCP client
_mcp_client: MCPClient = None


@app.route("/", methods=["GET"])
def index():
    """Root endpoint - returns server info"""
    return jsonify({
        "name": "VinUni MCP API Server",
        "version": "1.1.0",
        "description": "HTTP wrapper for MCP Server (ReAct Agent Demo)",
        "endpoints": {
            "GET /": "This info",
            "GET /health": "Health check",
            "GET /tools": "List available tools (legacy)",
            "POST /chat": "Send chat message (legacy, body: {prompt: string})",
            "GET /api/tools": "List available tools (new)",
        "POST /api/chat": "Send chat with intent (new, body: {message: string} or {prompt: string})"
        },
        "documentation": "See docs/demo/demo.html"
    })


@app.errorhandler(404)
def not_found(error):
    """Custom 404 handler - returns JSON instead of HTML"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested URL was not found on this server",
        "status": 404,
        "hint": "Available endpoints: /, /health, /tools, /chat, /api/tools, /api/chat"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Custom 500 handler - returns JSON for errors"""
    return jsonify({
        "error": "Internal Server Error",
        "message": str(error),
        "status": 500
    }), 500


def get_mcp_client() -> MCPClient:
    """Get or create MCP client singleton"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient("src/mcp_server_stdio.py")
        _mcp_client.start()
        print("[API Server] MCP Client started successfully")
    return _mcp_client


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        client = get_mcp_client()
        return jsonify({
            "status": "healthy",
            "mcp_connected": client.is_connected,
            "server_info": client.server_info
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat endpoint - Nhận câu hỏi, gọi MCP Server, trả kết quả
    
    Request body:
    {
        "prompt": "Hãy tra cứu thông tin học vụ của sinh viên SV2026001"
    }
    
    Response:
    {
        "result": { ... },
        "tool_name": "academic_query",
        "status": "success"
    }
    """
    try:
        data = request.get_json() or {}
        prompt = data.get("prompt", "")
        
        if not prompt:
            return jsonify({
                "error": "Missing 'prompt' in request body"
            }), 400
        
        # Extract parameters from prompt
        student_id = _extract_student_id(prompt)
        datetime_str = _extract_datetime(prompt)
        advisor_name = _extract_advisor_name(prompt)
        
        # Determine which tool to call
        prompt_lower = prompt.lower()
        
        client = get_mcp_client()
        
        # Case 1: Multi-step (tra cứu + đặt lịch)
        wants_advisor = any(kw in prompt_lower for kw in ["thông tin cố vấn", "cố vấn học tập", "cố vấn"])
        wants_booking = "đặt lịch" in prompt_lower or "dat lich" in prompt_lower
        
        if wants_advisor and wants_booking and student_id:
            # Multi-step: first query, then book
            step1_result = client.call_tool("academic_query", {"student_id": student_id})
            
            if step1_result.get("status") == "SUCCESS":
                advisor = step1_result.get("data", {}).get("advisor", advisor_name or "PGS.TS Nguyễn Văn A")
                step2_result = client.call_tool("schedule_appointment", {
                    "student_id": student_id,
                    "datetime_str": datetime_str or "10:00 ngày 20/09/2026",
                    "advisor_name": advisor
                })
                return jsonify({
                    "result": {
                        "step1": step1_result,
                        "step2": step2_result
                    },
                    "steps": ["academic_query", "schedule_appointment"],
                    "status": "success"
                })
            else:
                return jsonify({
                    "result": step1_result,
                    "tool_name": "academic_query",
                    "status": step1_result.get("status", "error")
                })
        
        # Case 2: Chỉ tra cứu
        if wants_advisor or "tra cứu" in prompt_lower or "thông tin học vụ" in prompt_lower or student_id:
            result = client.call_tool("academic_query", {"student_id": student_id})
            return jsonify({
                "result": result,
                "tool_name": "academic_query",
                "status": "success"
            })
        
        # Case 3: Chỉ đặt lịch
        if wants_booking:
            result = client.call_tool("schedule_appointment", {
                "student_id": student_id or "SV2026001",
                "datetime_str": datetime_str or "14:00 ngày 15/09/2026",
                "advisor_name": advisor_name or "PGS.TS Nguyễn Văn A"
            })
            return jsonify({
                "result": result,
                "tool_name": "schedule_appointment",
                "status": "success"
            })
        
        # Case 4: Default - general question
        return jsonify({
            "result": {
                "status": "TEXT",
                "content": "Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp. Để tra cứu thông tin học vụ hoặc đặt lịch hẹn, vui lòng nhập mã sinh viên cụ thể."
            },
            "tool_name": None,
            "status": "success"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/tools", methods=["GET"])
def list_tools():
    """List available tools from MCP server (legacy endpoint)"""
    try:
        client = get_mcp_client()
        tools = client.list_tools()
        return jsonify({
            "tools": tools,
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


# =============================================================================
# NEW API ENDPOINTS (with /api/ prefix)
# =============================================================================

@app.route("/api/tools", methods=["GET"])
def api_list_tools():
    """
    List available tools from MCP server (new endpoint with /api/ prefix)
    
    Response:
    {
        "tools": [...],
        "status": "success"
    }
    """
    try:
        client = get_mcp_client()
        tools = client.list_tools()
        return jsonify({
            "tools": tools,
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Chat endpoint with Intent Classification (new endpoint with /api/ prefix)
    
    Request body (两种格式都支持):
    {
        "message": "Tra cứu SV2026001"  // demo.html format
    }
    或
    {
        "prompt": "Tra cứu SV2026001"   // legacy format
    }
    
    Response:
    {
        "intent": "ACADEMIC" | "CASUAL",
        "response": "...",
        "trace": [...],
        "tool_name": "academic_query" | "schedule_appointment" | null,
        "status": "success"
    }
    """
    start_time = time.time()
    
    try:
        data = request.get_json() or {}
        
        # Support both "message" (demo.html) and "prompt" (legacy) formats
        user_message = data.get("message") or data.get("prompt", "")
        
        if not user_message:
            return jsonify({
                "error": "Missing 'message' or 'prompt' in request body"
            }), 400
        
        # Step 1: Classify intent
        intent = classify_intent(user_message)
        trace = [{
            "step": 0,
            "type": "INTENT_CLASSIFICATION",
            "intent": intent,
            "latency_ms": 0
        }]
        
        if intent == "CASUAL":
            # CASUAL: Call AI model for natural language response
            response_text = get_ai_response(user_message)
            trace.append({
                "step": 1,
                "type": "LLM_RESPONSE",
                "content": response_text,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            })
            return jsonify({
                "intent": intent,
                "response": response_text,
                "trace": trace,
                "tool_name": None,
                "status": "success"
            })
        
        # ACADEMIC: Route to MCP tools
        prompt_lower = user_message.lower()
        student_id = _extract_student_id(user_message)
        datetime_str = _extract_datetime(user_message)
        advisor_name = _extract_advisor_name(user_message)
        
        client = get_mcp_client()
        
        # Multi-step: tra cứu cố vấn + đặt lịch
        wants_advisor = any(kw in prompt_lower for kw in ["thông tin cố vấn", "cố vấn học tập", "cố vấn"])
        wants_booking = "đặt lịch" in prompt_lower or "dat lich" in prompt_lower
        
        if wants_advisor and wants_booking and student_id:
            # Step 1: Query student info
            step1_result = client.call_tool("academic_query", {"student_id": student_id})
            trace.append({
                "step": 1,
                "type": "TOOL_CALL",
                "tool": "academic_query",
                "arguments": {"student_id": student_id},
                "result": step1_result,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            })
            
            if step1_result.get("status") == "SUCCESS":
                # Step 2: Book appointment with advisor from step 1
                advisor = step1_result.get("data", {}).get("advisor", advisor_name or "PGS.TS Nguyễn Văn A")
                step2_result = client.call_tool("schedule_appointment", {
                    "student_id": student_id,
                    "datetime_str": datetime_str or "10:00 ngày 20/09/2026",
                    "advisor_name": advisor
                })
                trace.append({
                    "step": 2,
                    "type": "TOOL_CALL",
                    "tool": "schedule_appointment",
                    "arguments": {
                        "student_id": student_id,
                        "datetime_str": datetime_str,
                        "advisor_name": advisor
                    },
                    "result": step2_result,
                    "latency_ms": round((time.time() - start_time) * 1000, 2)
                })
                
                response_text = _format_multi_step_response(step1_result, step2_result)
                return jsonify({
                    "intent": intent,
                    "response": response_text,
                    "trace": trace,
                    "tool_name": "academic_query + schedule_appointment",
                    "steps": ["academic_query", "schedule_appointment"],
                    "status": "success"
                })
            else:
                return jsonify({
                    "intent": intent,
                    "response": f"Không tìm thấy thông tin sinh viên {student_id}",
                    "trace": trace,
                    "tool_name": "academic_query",
                    "status": "not_found"
                })
        
        # Chỉ tra cứu
        if wants_advisor or "tra cứu" in prompt_lower or "thông tin học vụ" in prompt_lower or student_id:
            result = client.call_tool("academic_query", {"student_id": student_id})
            trace.append({
                "step": 1,
                "type": "TOOL_CALL",
                "tool": "academic_query",
                "arguments": {"student_id": student_id},
                "result": result,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            })
            response_text = _format_academic_response(result)
            return jsonify({
                "intent": intent,
                "response": response_text,
                "trace": trace,
                "tool_name": "academic_query",
                "status": "success"
            })
        
        # Chỉ đặt lịch
        if wants_booking:
            result = client.call_tool("schedule_appointment", {
                "student_id": student_id or "SV2026001",
                "datetime_str": datetime_str or "14:00 ngày 15/09/2026",
                "advisor_name": advisor_name or "PGS.TS Nguyễn Văn A"
            })
            trace.append({
                "step": 1,
                "type": "TOOL_CALL",
                "tool": "schedule_appointment",
                "arguments": {
                    "student_id": student_id,
                    "datetime_str": datetime_str,
                    "advisor_name": advisor_name
                },
                "result": result,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            })
            response_text = _format_booking_response(result)
            return jsonify({
                "intent": intent,
                "response": response_text,
                "trace": trace,
                "tool_name": "schedule_appointment",
                "status": "success"
            })
        
        # Default: general question
        response_text = "Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp. Để tra cứu thông tin học vụ hoặc đặt lịch hẹn, vui lòng nhập mã sinh viên cụ thể."
        return jsonify({
            "intent": intent,
            "response": response_text,
            "trace": trace,
            "tool_name": None,
            "status": "success"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


def get_ai_response(message: str) -> str:
    """
    Gọi AI model (Groq - miễn phí) để trả lời casual questions một cách tự nhiên.
    Fallback về datetime-based responses nếu AI không khả dụng.
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
        response = client.chat.completions.create(
            model="llama-3.2-3b-preview",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý học vụ VinUni thân thiện. "
                        "Trả lời ngắn gọn, tự nhiên bằng tiếng Việt. "
                        "Nếu hỏi ngày tháng - cung cấp ngày hiện tại. "
                        "Nếu hỏi thời tiết - nói bạn không có thông tin thời tiết nhưng có thể hỗ trợ học vụ. "
                        "Nếu chào hỏi - trả lời ấm áp và hỏi có cần hỗ trợ gì không."
                    )
                },
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content
    except ImportError:
        # Fallback: groq not installed
        print("[AI Response] Groq not installed, using datetime fallback")
        return _get_casual_response(message)
    except Exception as e:
        # Fallback: API error or no key
        print(f"[AI Response] Groq error: {e}, using datetime fallback")
        return _get_casual_response(message)


def _get_casual_response(message: str) -> str:
    """Get response for casual (non-academic) messages - datetime-based fallback"""
    msg_lower = message.lower().strip()
    now = datetime.now()
    days_vi = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    
    # Hỏi thứ mấy / ngày mấy
    if any(kw in msg_lower for kw in ["thứ", "thu", "ngày", "ngay", "mấy", "may"]):
        if any(kw in msg_lower for kw in ["hôm nay", "hom nay", "nay", "bây giờ", "bay gio"]):
            day_name = days_vi[now.weekday()]
            return f"Hôm nay là {day_name}, ngày {now.strftime('%d/%m/%Y')}. Bạn cần tôi hỗ trợ gì về học vụ VinUni không? 😊"
    
    # Hỏi giờ
    if any(kw in msg_lower for kw in ["giờ", "gio", "mấy giờ", "may gio"]):
        return f"Bây giờ là {now.strftime('%H:%M:%S')}."
    
    # Hỏi thời tiết
    if any(kw in msg_lower for kw in ["thời tiết", "thoi tiet", "mưa", "mua", "nắng", "nang"]):
        return "Tôi không có thông tin thời tiết, nhưng tôi có thể giúp bạn về học vụ VinUni như tra cứu điểm, lịch học, hay đặt lịch tư vấn cố vấn!"
    
    # Chào hỏi
    greetings = ["xin chào", "chào", "hello", "hi", "hey", "chao", "xin chao"]
    if any(g in msg_lower for g in greetings):
        return "Xin chào! 👋 Tôi là Trợ lý Học vụ VinUni. Tôi có thể giúp bạn tra cứu thông tin học vụ, đặt lịch tư vấn cố vấn, hoặc trả lời về quy chế VinUni. Bạn cần gì ạ?"
    
    # Cảm ơn
    if any(kw in msg_lower for kw in ["cảm ơn", "cam on", "thank"]):
        return "Không có gì! 😊 Nếu cần hỗ trợ gì thêm, cứ hỏi tôi nhé!"
    
    # Tên / giới thiệu
    if any(kw in msg_lower for kw in ["tên", "ten", "ai", "ban la", "bạn là"]):
        return "Tôi là Trợ lý Học vụ VinUni - giúp bạn tra cứu điểm, lịch học và đặt lịch tư vấn cố vấn!"
    
    # Default casual
    return "Cảm ơn bạn! 😊 Tôi là Trợ lý Học vụ VinUni. Nếu bạn cần tra cứu điểm, lịch học, hoặc đặt lịch cố vấn, cứ hỏi tôi nhé!"


def _format_academic_response(result: dict) -> str:
    """Format academic query result to readable text"""
    if result.get("status") == "NOT_FOUND":
        return f"Không tìm thấy thông tin sinh viên. Vui lòng kiểm tra lại mã sinh viên."
    
    if result.get("status") == "SUCCESS":
        data = result.get("data", {})
        return (
            f"Kết quả tra cứu cho sinh viên {result.get('student_id', '')} "
            f"({data.get('full_name', '')}): "
            f"Lớp {data.get('class', '')}, GPA: {data.get('gpa', '')}, "
            f"Email: {data.get('email', '')}, Trạng thái: {data.get('status', '')}, "
            f"Cố vấn: {data.get('advisor', '')}."
        )
    
    return str(result)


def _format_booking_response(result: dict) -> str:
    """Format booking result to readable text"""
    if result.get("status") == "SUCCESS":
        return (
            f"Đặt lịch thành công! "
            f"Mã đặt lịch: {result.get('booking_id', '')}. "
            f"Sinh viên: {result.get('student_id', '')}. "
            f"Cố vấn: {result.get('advisor', '')}. "
            f"Thời gian: {result.get('datetime', '')}."
        )
    
    return str(result)


def _format_multi_step_response(step1: dict, step2: dict) -> str:
    """Format multi-step (query + booking) result to readable text"""
    parts = []
    
    # Step 1 result
    if step1.get("status") == "SUCCESS":
        data = step1.get("data", {})
        parts.append(
            f"Thông tin sinh viên {step1.get('student_id', '')} ({data.get('full_name', '')}): "
            f"Lớp {data.get('class', '')}, GPA: {data.get('gpa', '')}, "
            f"Cố vấn: {data.get('advisor', '')}."
        )
    else:
        parts.append(f"Không tìm thấy thông tin sinh viên {step1.get('student_id', '')}.")
    
    # Step 2 result
    if step2.get("status") == "SUCCESS":
        parts.append(
            f"Đã đặt lịch thành công với cố vấn {step2.get('advisor', '')} "
            f"vào lúc {step2.get('datetime', '')}. "
            f"Mã đặt lịch: {step2.get('booking_id', '')}."
        )
    else:
        parts.append("Không thể đặt lịch. Vui lòng thử lại sau.")
    
    return " ".join(parts)


def _extract_student_id(prompt: str) -> str:
    """Extract student ID from prompt"""
    match = re.search(r"SV\d+", prompt, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return "SV2026001"  # Default


def _extract_datetime(prompt: str) -> str:
    """Extract datetime from prompt"""
    # Simple extraction - look for time patterns
    time_patterns = [
        r'\d{1,2}:\d{2}\s*(?:ngày)?\s*\d{1,2}/\d{1,2}/\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
    ]
    for pattern in time_patterns:
        match = re.search(pattern, prompt)
        if match:
            return match.group(0)
    
    # Look for time with hour
    hour_match = re.search(r'(\d{1,2})\s*h(?:(?:r)|(?:ọ))?\s*(\d{1,2})?', prompt)
    if hour_match:
        hour = hour_match.group(1)
        minute = hour_match.group(2) or "00"
        return f"{hour}:{minute} ngày 15/09/2026"
    
    return "14:00 ngày 15/09/2026"  # Default


def _extract_advisor_name(prompt: str) -> str:
    """Extract advisor name from prompt"""
    # Look for patterns like "với PGS.TS X" or "với TS. Y"
    patterns = [
        r'với\s+(PGS\.?TS\.?\s+\S+(?:\s+\S+)*)',
        r'với\s+(TS\.?\s+\S+(?:\s+\S+)*)',
        r'cố vấn\s+(PGS\.?TS\.?\s+\S+(?:\s+\S+)*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up title
            name = re.sub(r'\s+', ' ', name)
            return name
    
    return "PGS.TS Nguyễn Văn A"  # Default


@app.teardown_appcontext
def cleanup(exception=None):
    """Cleanup on app shutdown"""
    pass  # Keep MCP client alive for reuse


def main():
    """Main entry point"""
    print("=" * 60)
    print("VinUni MCP API Server (HTTP Wrapper for MCP)")
    print("=" * 60)
    print("Starting HTTP wrapper for MCP Server...")
    print()
    print("Server: http://localhost:8765")
    print()
    print("Available Endpoints:")
    print("  - GET  /           - Server info")
    print("  - GET  /health    - Health check")
    print("  - GET  /tools     - List tools (legacy)")
    print("  - POST /chat      - Chat (legacy)")
    print("  - GET  /api/tools - List tools (new)")
    print("  - POST /api/chat  - Chat with intent (new)")
    print()
    print("Test Commands:")
    print('  curl -X POST http://localhost:8765/api/chat ^&^&')
    print("    -H 'Content-Type: application/json' \\")
    print('    -d "{\"message\":\"Tra cuu SV2026001\"}"')
    print()
    print("  # Or use legacy format:")
    print('  curl -X POST http://localhost:8765/chat ^&^&')
    print("    -H 'Content-Type: application/json' \\")
    print('    -d "{\"prompt\":\"Tra cuu SV2026001\"}"')
    print("=" * 60)
    
    # Initialize MCP client
    try:
        get_mcp_client()
        print("[OK] MCP Client initialized successfully")
    except Exception as e:
        print(f"[WARN] MCP Client initialization failed: {e}")
        print("   The server will start but /chat endpoint may fail.")
    
    # Run Flask app
    app.run(
        host="0.0.0.0",
        port=8765,
        debug=False,
        threaded=True
    )


if __name__ == "__main__":
    main()
