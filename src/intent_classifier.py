"""
Intent Classifier - Phân loại câu hỏi của user.
- ACADEMIC: liên quan học vụ (tra cứu SV, đặt lịch, điểm, môn học, ...) → dùng ReAct + MCP tools
- CASUAL: chào hỏi, hỏi ngày tháng, thời tiết, câu hỏi chung → gọi LLM trực tiếp
"""
import re
from typing import Literal

IntentType = Literal["ACADEMIC", "CASUAL"]

# Keywords mạnh cho intent ACADEMIC (ưu tiên check trước)
ACADEMIC_KEYWORDS = [
    r"\bSV\d+\b",           # Mã sinh viên (SV2026001)
    r"sinh vi(iên|en)\b",
    r"học vụ\b",
    r"mã sinh viên",
    r"tra cứu\b",
    r"đặt lịch\b",
    r"đặt hẹn\b",
    r"lịch hẹn\b",
    r"cố vấn\b",
    r"điểm\b",
    r"môn học\b",
    r"học kỳ\b",
    r"kết quả học tập",
    r"thời khóa biểu",
    r"tư vấn\b",
    r"đăng ký môn",
    r"học phí\b",
]

ACADEMIC_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ACADEMIC_KEYWORDS]

# Patterns CASUAL rõ ràng (hỗ trợ cả tiếng Việt có dấu và không dấu)
CASUAL_PATTERNS = [
    re.compile(r"hôm nay.*(ngày|thứ|mấy)", re.IGNORECASE),
    re.compile(r"hom nay.*(ngay|thu|may)", re.IGNORECASE),
    re.compile(r"(thứ|ngày)\s*mấy", re.IGNORECASE),
    re.compile(r"(thu|ngay)\s*may", re.IGNORECASE),
    re.compile(r"thời tiết", re.IGNORECASE),
    re.compile(r"thoi tiet", re.IGNORECASE),
    re.compile(r"^\s*(xin chào|chào|hello|hi|hey)\b", re.IGNORECASE),
    re.compile(r"^\s*(xin chao|chao)\b", re.IGNORECASE),
    re.compile(r"bạn là ai", re.IGNORECASE),
    re.compile(r"ban la ai", re.IGNORECASE),
    re.compile(r"bạn tên gì", re.IGNORECASE),
    re.compile(r"ban ten gi", re.IGNORECASE),
    re.compile(r"cảm ơn|thank", re.IGNORECASE),
    re.compile(r"cam on", re.IGNORECASE),
]


def classify_intent(user_input: str) -> IntentType:
    """
    Phân loại intent. Ưu tiên CASUAL patterns (cụ thể) trước,
    rồi mới check ACADEMIC keywords.
    """
    text = user_input.strip()
    
    # 1. Check CASUAL patterns cụ thể (ưu tiên cao)
    for pattern in CASUAL_PATTERNS:
        if pattern.search(text):
            return "CASUAL"
    
    # 2. Check ACADEMIC keywords
    for pattern in ACADEMIC_PATTERNS:
        if pattern.search(text):
            return "ACADEMIC"
    
    # 3. Heuristic: câu quá ngắn (<10 ký tự) thường là chào
    if len(text) < 10:
        return "CASUAL"
    
    # 4. Mặc định: ACADEMIC (để ReAct xử lý, không phải cũng OK)
    return "ACADEMIC"
