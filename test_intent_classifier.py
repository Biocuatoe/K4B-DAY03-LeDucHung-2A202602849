"""
Quick test cho Intent Classifier.
Chạy: python test_intent_classifier.py
"""
import sys
from pathlib import Path

# Đảm bảo import được src.intent_classifier
sys.path.insert(0, str(Path(__file__).parent / "src"))

from intent_classifier import classify_intent  # noqa: E402

# (input, expected_intent) — 14 cases từ acceptance criteria
TEST_CASES = [
    # ===== ACADEMIC (7 cases) =====
    ("Tra cứu SV2026001", "ACADEMIC"),
    ("Tôi muốn đặt lịch với cố vấn", "ACADEMIC"),
    ("Sinh viên Nguyễn Văn A có điểm môn Toán bao nhiêu?", "ACADEMIC"),
    ("Học phí kỳ này là bao nhiêu?", "ACADEMIC"),
    ("Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?", "ACADEMIC"),
    ("Hãy tra cứu thông tin học vụ của sinh viên SV2026001", "ACADEMIC"),
    ("Đặt lịch hẹn tư vấn cho SV2026001 vào 14:00 ngày 15/09/2026", "ACADEMIC"),
    # ===== CASUAL (7 cases) =====
    ("Hôm nay là thứ mấy?", "CASUAL"),
    ("Xin chào bạn", "CASUAL"),
    ("Bạn tên gì?", "CASUAL"),
    ("Thời tiết Hà Nội hôm nay thế nào?", "CASUAL"),
    ("Cảm ơn bạn", "CASUAL"),
    ("Hi", "CASUAL"),
    ("Hello", "CASUAL"),
]


def main():
    """Chạy tất cả test cases và in kết quả."""
    print("=" * 72)
    print("TEST INTENT CLASSIFIER — Trợ lý Học vụ VinUni")
    print("=" * 72)

    passed = 0
    failed = 0

    for text, expected in TEST_CASES:
        actual = classify_intent(text)
        is_pass = actual == expected
        status = "[PASS]" if is_pass else "[FAIL]"
        if is_pass:
            passed += 1
        else:
            failed += 1
        print(f"{status} '{text}' -> {actual} (expected: {expected})")

    print("=" * 72)
    total = passed + failed
    accuracy = (passed / total) * 100 if total else 0
    print(f"Kết quả: {passed}/{total} passed ({accuracy:.1f}%)")
    print("=" * 72)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
