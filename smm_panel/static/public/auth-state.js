const COMMON_PASSWORD_PATTERNS = [
  "12345678",
  "123456789",
  "1234567890",
  "11111111",
  "00000000",
  "password",
  "password1",
  "qwer1234",
  "qwerty123",
  "abc12345",
  "letmein",
  "welcome123",
  "admin1234",
  "instamart",
  "인스타마트",
];

const KEYBOARD_SEQUENCE_PATTERNS = [
  "0123456789",
  "abcdefghijklmnopqrstuvwxyz",
  "qwertyuiop",
  "asdfghjkl",
  "zxcvbnm",
];

export function blankSignupState() {
  return {
    step: "email",
    email: "",
    challengeId: "",
    resendAvailableAt: "",
    expiresAt: "",
    previewCode: "",
    verificationToken: "",
    verifiedAt: "",
    completeBy: "",
  };
}

export function blankPublicAuthState() {
  return {
    signup: blankSignupState(),
  };
}

function tokenFragments(value = "") {
  return String(value || "")
    .trim()
    .toLowerCase()
    .split(/[^0-9a-zA-Z가-힣]+/)
    .filter((item) => item.length >= 3);
}

function hasSequence(password = "") {
  const normalized = String(password || "").toLowerCase();
  return KEYBOARD_SEQUENCE_PATTERNS.some((pattern) => {
    for (let index = 0; index <= pattern.length - 4; index += 1) {
      const slice = pattern.slice(index, index + 4);
      if (normalized.includes(slice) || normalized.includes([...slice].reverse().join(""))) {
        return true;
      }
    }
    return false;
  });
}

function hasRepeatedPattern(password = "") {
  return /(.)\1{3,}/i.test(String(password || ""));
}

export function evaluatePublicPasswordStrength(password, { email = "", name = "" } = {}) {
  const raw = String(password || "");
  const normalized = raw.toLowerCase();
  const emailLocal = String(email || "").split("@", 1)[0].trim().toLowerCase();
  const personalTokens = [...tokenFragments(emailLocal), ...tokenFragments(name)];
  const warnings = [];
  let score = 0;

  if (raw.length >= 10) score += 1;
  if (raw.length >= 12) score += 1;
  if (raw.length >= 14) score += 1;
  if (new Set(raw).size >= Math.min(10, Math.max(4, Math.floor(raw.length / 2)))) score += 1;
  if ((/[A-Za-z]/.test(raw) && /\d/.test(raw)) || /[^A-Za-z0-9\s]/.test(raw)) score += 1;

  const commonHit =
    COMMON_PASSWORD_PATTERNS.includes(normalized) ||
    COMMON_PASSWORD_PATTERNS.some((item) => item && normalized.includes(item));
  const containsPersonal = personalTokens.some((token) => token && normalized.includes(token));
  const repeatedPattern = hasRepeatedPattern(raw);
  const sequencePattern = hasSequence(raw);

  if (raw.length < 10) warnings.push("10자 이상으로 입력해 주세요.");
  if (containsPersonal) warnings.push("이메일이나 이름이 들어간 비밀번호는 사용할 수 없어요.");
  if (commonHit) warnings.push("너무 흔한 비밀번호는 사용할 수 없어요.");
  if (sequencePattern) warnings.push("연속된 문자나 키보드 패턴은 피해주세요.");
  if (repeatedPattern) warnings.push("같은 문자 반복은 피해주세요.");

  if (commonHit) score -= 3;
  if (containsPersonal) score -= 3;
  if (sequencePattern) score -= 2;
  if (repeatedPattern) score -= 2;
  score = Math.max(0, Math.min(score, 4));

  let label = "약함";
  let tone = "weak";
  let guidance = "길고 예측 어려운 비밀번호를 추천해요.";
  if (score === 2) {
    label = "보통";
    tone = "fair";
    guidance = "12자 이상으로 늘리면 더 안전해집니다.";
  } else if (score === 3) {
    label = "안전";
    tone = "good";
    guidance = "좋습니다. 숫자나 기호를 섞으면 더 안정적입니다.";
  } else if (score >= 4) {
    label = "매우 안전";
    tone = "strong";
    guidance = "현재 기준으로 충분히 강한 비밀번호입니다.";
  }

  return {
    score,
    label,
    tone,
    guidance,
    warnings,
    isValid: raw.length >= 10 && !containsPersonal && !commonHit && !sequencePattern && !repeatedPattern,
  };
}
