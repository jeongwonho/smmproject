from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Any, Dict, List


AUTH_VERIFICATION_CODE_LENGTH = 6
PUBLIC_PASSWORD_MIN_LENGTH = 10
PUBLIC_PASSWORD_RECOMMENDED_LENGTH = 12
PUBLIC_PASSWORD_VERY_STRONG_LENGTH = 14
PASSWORD_HASH_ITERATIONS = 260_000
COMMON_PASSWORD_PATTERNS = {
    "12345678",
    "123456789",
    "1234567890",
    "password",
    "qwer1234",
    "qwerty",
    "11111111",
    "00000000",
    "iloveyou",
    "admin1234",
    "instamart",
    "인스타마트",
}
KEYBOARD_SEQUENCE_PATTERNS = (
    "0123456789",
    "abcdefghijklmnopqrstuvwxyz",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
)


def hash_token_value(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def generate_email_verification_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(AUTH_VERIFICATION_CODE_LENGTH))


def password_contains_sequence(password: str) -> bool:
    normalized = str(password or "").lower()
    for pattern in KEYBOARD_SEQUENCE_PATTERNS:
        for index in range(len(pattern) - 3):
            token = pattern[index : index + 4]
            if token in normalized or token[::-1] in normalized:
                return True
    return False


def password_contains_repeated_pattern(password: str) -> bool:
    normalized = str(password or "").lower()
    return bool(re.search(r"(.)\1{3,}", normalized))


def _name_like_tokens(value: str) -> List[str]:
    raw = str(value or "").strip().lower()
    pieces = re.split(r"[^0-9a-zA-Z가-힣]+", raw)
    return [piece for piece in pieces if len(piece) >= 3]


def assess_public_password_strength(password: str, *, email: str = "", name: str = "") -> Dict[str, Any]:
    raw = str(password or "")
    normalized = raw.lower()
    email_local = str(email or "").split("@", 1)[0].strip().lower()
    email_tokens = _name_like_tokens(email_local)
    name_tokens = _name_like_tokens(name)
    warnings: List[str] = []
    score = 0

    if len(raw) >= PUBLIC_PASSWORD_MIN_LENGTH:
        score += 1
    if len(raw) >= PUBLIC_PASSWORD_RECOMMENDED_LENGTH:
        score += 1
    if len(raw) >= PUBLIC_PASSWORD_VERY_STRONG_LENGTH:
        score += 1
    if len(set(raw)) >= min(10, max(4, len(raw) // 2)):
        score += 1
    if re.search(r"[A-Za-z]", raw) and re.search(r"\d", raw):
        score += 1
    elif re.search(r"[^A-Za-z0-9\s]", raw):
        score += 1

    common_hit = normalized in COMMON_PASSWORD_PATTERNS or any(
        pattern and pattern in normalized for pattern in COMMON_PASSWORD_PATTERNS
    )
    if common_hit:
        warnings.append("너무 흔한 비밀번호는 사용할 수 없어요.")
        score = max(0, score - 3)
    if password_contains_sequence(raw):
        warnings.append("연속된 문자나 키보드 패턴은 피해주세요.")
        score = max(0, score - 2)
    if password_contains_repeated_pattern(raw):
        warnings.append("같은 문자 반복은 피해주세요.")
        score = max(0, score - 2)
    if any(token and token in normalized for token in email_tokens + name_tokens):
        warnings.append("이메일이나 이름이 들어간 비밀번호는 사용할 수 없어요.")
        score = max(0, score - 3)

    if len(raw) < PUBLIC_PASSWORD_MIN_LENGTH:
        warnings.append(f"{PUBLIC_PASSWORD_MIN_LENGTH}자 이상으로 입력해 주세요.")

    if score <= 1:
        label = "약함"
        tone = "weak"
        guidance = "길고 예측 어려운 비밀번호를 추천해요."
    elif score == 2:
        label = "보통"
        tone = "fair"
        guidance = "12자 이상으로 늘리면 더 안전해집니다."
    elif score == 3:
        label = "안전"
        tone = "good"
        guidance = "좋습니다. 숫자나 기호를 섞으면 더 안정적입니다."
    else:
        label = "매우 안전"
        tone = "strong"
        guidance = "현재 기준으로 충분히 강한 비밀번호입니다."

    is_valid = (
        len(raw) >= PUBLIC_PASSWORD_MIN_LENGTH
        and not common_hit
        and not password_contains_sequence(raw)
        and not password_contains_repeated_pattern(raw)
        and not any(token and token in normalized for token in email_tokens + name_tokens)
    )

    return {
        "label": label,
        "tone": tone,
        "score": max(0, min(score, 4)),
        "guidance": guidance,
        "warnings": warnings,
        "isValid": is_valid,
    }


def hash_password(password: str) -> str:
    raw = str(password or "")
    if not raw:
        return ""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${derived.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    raw_password = str(password or "")
    stored = str(encoded_hash or "").strip()
    if not raw_password or not stored:
        return False
    parts = stored.split("$", 3)
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    _, iteration_text, salt, digest = parts
    try:
        iterations = int(iteration_text)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(candidate.hex(), digest)
