"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """
    Offline Mock Provider dùng để chạy thử mà không tốn API Key.

    Hỗ trợ mô phỏng Multi-step ReAct:
      - Step đầu: nhận diện intent từ prompt, gọi tool tương ứng.
      - Step kế: nếu đã có Observation academic_query trong history → Step 2: đặt lịch
        với advisor_name lấy từ Observation trước.
      - Step kế tiếp sau tool: sinh Final Answer tổng hợp.
    """
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def _extract_student_id(self, prompt: str, default: str = "SV2026001") -> str:
        for token in prompt.replace(",", " ").replace(".", " ").replace(";", " ").split():
            if token.upper().startswith("SV"):
                return token.upper()
        return default

    def _extract_advisor_name(self, prompt: str) -> str:
        """
        Trích tên cố vấn từ câu, loại bỏ các từ dẫn 'cố vấn', 'PGS.TS', v.v.
        hoặc trả về mặc định nếu không tìm thấy.
        """
        # Trường hợp có 'với cố vấn X vào/lúc ...'
        if "với" in prompt.lower():
            idx = prompt.lower().find("với")
            tail = prompt[idx + len("với"):]
            for stop in [" vào ", " lúc "]:
                if stop in tail.lower():
                    name = tail[:tail.lower().find(stop)].strip(" .,;")
                    # Loại bỏ tiền tố 'cố vấn' nếu có
                    for prefix in ["cố vấn học tập ", "cố vấn ", "ts.", "pgs.ts.", "pgs ", "ts "]:
                        if name.lower().startswith(prefix):
                            name = name[len(prefix):]
                    # Ghép lại title
                    name = " ".join([w for w in name.split() if w])
                    if name:
                        return name
                    break
        # Trường hợp không rõ → trả mặc định
        return "PGS.TS Nguyễn Văn A"

    def _extract_datetime(self, prompt: str, default: str = "14:00 15/09/2026") -> str:
        tokens = prompt.split()
        for i, tok in enumerate(tokens):
            if ":" in tok and tok[0].isdigit():
                window = tokens[max(0, i - 1): i + 4]
                s = " ".join(window).strip(" .,;")
                # Loại bỏ 'vào'/'lúc' ở đầu
                for prefix in ["vào ", "Vào ", "lúc ", "Lúc "]:
                    if s.startswith(prefix):
                        s = s[len(prefix):]
                return s
        return default

    def _finalize_observation(self, history: List[Dict[str, Any]], prompt: str = "", prompt_lower: str = "") -> Dict[str, Any]:
        """
        Tổng hợp Final Answer từ các Observation tool trong history.
        Nếu chưa hoàn tất các bước cần thiết cho prompt gốc (ví dụ TC04 yêu cầu đặt lịch),
        trả tool_call tiếp theo thay vì Final Answer.
        """
        obs_academic = next((m["content"] for m in reversed(history) if m.get("name") == "academic_query"), "")
        obs_schedule = next((m["content"] for m in reversed(history) if m.get("name") == "schedule_appointment"), "")

        # === Nếu prompt yêu cầu đặt lịch nhưng chưa có Observation schedule → sinh tiếp tool_call ===
        wants_booking = "đặt lịch" in prompt_lower or "dat lich" in prompt_lower
        if wants_booking and not obs_schedule:
            try:
                a = json.loads(obs_academic) if obs_academic else {}
            except Exception:
                a = {}
            advisor = a.get("data", {}).get("advisor", "PGS.TS Nguyễn Văn A")
            sid = self._extract_student_id(prompt, "SV2026002")
            datetime_str = self._extract_datetime(prompt, "10:00 20/09/2026")
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {"student_id": sid, "datetime_str": datetime_str, "advisor_name": advisor},
                "thought": f"Đã có thông tin cố vấn '{advisor}' từ Observation trước. Tôi tiến hành gọi schedule_appointment cho {sid}."
            }

        if obs_academic and obs_schedule:
            try:
                a = json.loads(obs_academic)
            except Exception:
                a = {}
            try:
                s = json.loads(obs_schedule)
            except Exception:
                s = {}
            advisor = ""
            if isinstance(a, dict):
                advisor = a.get("data", {}).get("advisor", "")
            return {
                "type": "text",
                "content": (
                    f"[Mock Agent Response]: Tổng hợp kết quả đa bước:\n"
                    f"1. Tra cứu cố vấn: Cố vấn học tập của bạn là {advisor or 'không rõ'}.\n"
                    f"2. Đặt lịch: {s.get('message') if isinstance(s, dict) else obs_schedule}"
                ),
                "thought": "Đã có đầy đủ Observation của cả academic_query và schedule_appointment. Tổng hợp Final Answer đa bước."
            }

        if obs_schedule:
            try:
                s = json.loads(obs_schedule)
                summary = s.get("message") or f"Đặt lịch thành công: {json.dumps(s, ensure_ascii=False)}"
            except Exception:
                summary = obs_schedule
            return {
                "type": "text",
                "content": f"[Mock Agent Response]: {summary}",
                "thought": "Đã nhận Observation từ schedule_appointment. Tổng hợp Final Answer."
            }

        if obs_academic:
            try:
                obs = json.loads(obs_academic)
                if obs.get("status") == "SUCCESS":
                    d = obs.get("data", {})
                    summary = (
                        f"Kết quả tra cứu cho sinh viên {obs.get('student_id', '')} ({d.get('full_name', '')}): "
                        f"Lớp {d.get('class', '')}, GPA: {d.get('gpa', '')}, Email: {d.get('email', '')}, "
                        f"Trạng thái: {d.get('status', '')}, Cố vấn: {d.get('advisor', '')}."
                    )
                elif obs.get("status") == "NOT_FOUND":
                    summary = obs.get("message", "Không tìm thấy thông tin sinh viên yêu cầu.")
                else:
                    summary = json.dumps(obs, ensure_ascii=False)
            except Exception:
                summary = obs_academic
            return {
                "type": "text",
                "content": f"[Mock Agent Response]: {summary}",
                "thought": "Đã nhận Observation từ academic_query. Tổng hợp Final Answer."
            }

        # Không có Observation → fallback
        return {
            "type": "text",
            "content": "[Mock Agent Response]: Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp.",
            "thought": "Câu hỏi chung về quy chế học vụ, trả lời trực tiếp không cần gọi Tool."
        }

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        history = conversation_history or []

        has_obs_academic = any(m.get("role") == "tool" and m.get("name") == "academic_query" for m in history)
        has_obs_schedule = any(m.get("role") == "tool" and m.get("name") == "schedule_appointment" for m in history)

        # === Bước Final Answer: Sau khi có Observation, Agent tổng hợp Final Answer ===
        # (Nếu đã có tool_call lần trước và đã có Observation, sinh Final Answer)
        if has_obs_academic or has_obs_schedule:
            return self._finalize_observation(history, prompt, prompt_lower)

        # === TC04 multi-step: Tra cứu trước rồi mới đặt lịch ===
        # Nếu prompt có cả "thông tin cố vấn" / "cố vấn học tập" và "đặt lịch"
        # → Bước 1: academic_query để tra cứu
        wants_advisor_info = any(kw in prompt_lower for kw in ["thông tin cố vấn", "cố vấn học tập"])
        wants_booking = "đặt lịch" in prompt_lower or "dat lich" in prompt_lower
        # Trường hợp TC04: câu hỏi yêu cầu CẢ tra cứu + đặt lịch → ưu tiên tra cứu trước
        if wants_advisor_info and wants_booking and not has_obs_academic:
            sid = self._extract_student_id(prompt, "SV2026002")
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": sid},
                "thought": f"Người dùng vừa yêu cầu tra cứu thông tin cố vấn vừa đặt lịch. Tôi cần tra cứu academic_query({sid}) trước để biết tên cố vấn."
            }

        # === TC04 step 2: Sau khi đã có academic_query observation → đặt lịch với advisor lấy từ obs ===
        if wants_booking and has_obs_academic and not has_obs_schedule:
            obs_academic = next((m["content"] for m in reversed(history) if m.get("name") == "academic_query"), "")
            try:
                a = json.loads(obs_academic)
                advisor = a.get("data", {}).get("advisor", "PGS.TS Nguyễn Văn A")
            except Exception:
                advisor = "PGS.TS Nguyễn Văn A"
            sid = self._extract_student_id(prompt, "SV2026002")
            datetime_str = self._extract_datetime(prompt, "10:00 20/09/2026")
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {"student_id": sid, "datetime_str": datetime_str, "advisor_name": advisor},
                "thought": f"Đã có thông tin cố vấn '{advisor}' từ Observation trước. Tôi tiến hành gọi schedule_appointment cho {sid}."
            }

        # === TC03 / TC04 step 1 chỉ đặt lịch: chưa có Observation nào ===
        if wants_booking and not has_obs_schedule:
            sid = self._extract_student_id(prompt, "SV2026001")
            datetime_str = self._extract_datetime(prompt)
            advisor_name = self._extract_advisor_name(prompt)
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {"student_id": sid, "datetime_str": datetime_str, "advisor_name": advisor_name},
                "thought": f"Người dùng yêu cầu đặt lịch hẹn tư vấn cho {sid} với cố vấn '{advisor_name}'. Tôi sẽ gọi tool schedule_appointment."
            }

        # === TC02 / TC05: Tra cứu học vụ ===
        if wants_advisor_info or "thông tin học vụ" in prompt_lower or "tra cứu" in prompt_lower or "sv" in prompt_lower:
            sid = self._extract_student_id(prompt, "SV2026001")
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": sid},
                "thought": f"Người dùng muốn tra cứu thông tin học vụ của sinh viên {sid}. Tôi sẽ gọi tool academic_query."
            }

        # === TC01: câu hỏi chung → trả lời text ===
        return {
            "type": "text",
            "content": "[Mock Agent Response]: Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp.",
            "thought": "Câu hỏi chung về quy chế học vụ, trả lời trực tiếp không cần gọi Tool."
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, conversation_history)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            # Xây dựng contents đầy đủ từ conversation_history (nếu có) để hỗ trợ multi-step
            if conversation_history:
                contents = _build_gemini_contents(conversation_history)
            else:
                contents = prompt

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, conversation_history)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, conversation_history)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            # Nếu có conversation_history, dùng nó; nếu không thì chỉ gồm prompt đầu vào
            if conversation_history:
                messages.extend(conversation_history)
            else:
                messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, conversation_history)


def _build_gemini_contents(conversation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Helper: Chuyển OpenAI-style conversation_history sang định dạng contents của Gemini SDK.
    Hỗ trợ 3 role: 'user', 'assistant' (kèm tool_calls), 'tool' (trả về Observation).
    """
    contents = []
    pending_parts = []
    for msg in conversation_history:
        role = msg.get("role")
        if role == "user":
            if pending_parts:
                # Đóng các phần function_call/response đang chờ
                contents.append({"role": "model", "parts": pending_parts})
                pending_parts = []
            contents.append({"role": "user", "parts": [{"text": msg.get("content", "")}]})
        elif role == "assistant":
            # Tool call được Agent thêm dưới dạng text; Gemini sẽ nhận thông tin hành động qua text.
            text = msg.get("content", "")
            pending_parts.append({"text": text})
        elif role == "tool":
            # Observation trả về từ Tool - Gemini cần parts thuộc 'function_response'
            try:
                payload = json.loads(msg.get("content", "{}"))
            except Exception:
                payload = {"raw": msg.get("content", "")}
            pending_parts.append({
                "function_response": {
                    "name": msg.get("name", ""),
                    "response": payload,
                }
            })
    # Đóng phần còn lại
    if pending_parts:
        contents.append({"role": "user", "parts": pending_parts})
    return contents


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
