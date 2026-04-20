import { evaluatePublicPasswordStrength } from "./auth-state.js";

const DEFAULT_LIGHT_BRAND_LOGO_URL = "/static/assets/instamart-logo-light-bg.png";

function enabledProviders(authConfig) {
  return (authConfig?.oauthProviders || []).filter((provider) => provider.enabled);
}

function brandMarkup(siteSettings, escapeHtml) {
  const siteName = escapeHtml(siteSettings?.siteName || "인스타마트");
  const logoUrl = String(DEFAULT_LIGHT_BRAND_LOGO_URL || siteSettings?.headerLogoUrl || "").trim();
  return `
    <div class="auth-brand">
      ${
        logoUrl
          ? `<img class="auth-brand__image" src="${escapeHtml(logoUrl)}" alt="${siteName}" loading="lazy" />`
          : `<span class="auth-brand__mark" aria-hidden="true">IM</span>`
      }
      <div class="auth-brand__text">
        <strong>${siteName}</strong>
      </div>
    </div>
  `;
}

function socialButtonsMarkup(authConfig, escapeHtml) {
  const providers = enabledProviders(authConfig);
  if (!providers.length) return "";
  return `
    <div class="auth-social">
      <span class="auth-social__label">간편 로그인</span>
      <div class="auth-social__row">
        ${providers
          .map(
            (provider) => `
              <button
                class="auth-social__button"
                type="button"
                data-oauth-provider="${provider.provider}"
              >
                ${escapeHtml(provider.label)}
              </button>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function loginFormMarkup({ authConfig, escapeHtml }) {
  return `
    <div class="auth-shell__body">
      <div class="auth-shell__copy">
        <h1>로그인하고 바로 이용하세요</h1>
        <p>충전, 주문, 내역은 로그인 후 이용할 수 있어요.</p>
      </div>
      <form class="auth-form" data-public-login-form>
        <label class="form-field">
          <span class="field-label">이메일</span>
          <div class="field-shell">
            <input class="field-input" type="email" name="email" placeholder="you@example.com" autocomplete="email" />
          </div>
        </label>
        <label class="form-field">
          <span class="field-label">비밀번호</span>
          <div class="field-shell field-shell--password">
            <input class="field-input" type="password" name="password" placeholder="비밀번호 입력" autocomplete="current-password" />
            <button class="password-toggle" type="button" data-password-toggle aria-label="비밀번호 보기">보기</button>
          </div>
        </label>
        <div class="auth-inline-row">
          <label class="auth-check">
            <input type="checkbox" name="rememberMe" />
            <span>로그인 유지</span>
          </label>
          <button class="auth-link" type="button" data-route="/help#guide">비밀번호 찾기</button>
        </div>
        <button class="full-width-cta auth-form__submit" type="submit">로그인</button>
      </form>
      ${socialButtonsMarkup(authConfig, escapeHtml)}
      <div class="auth-fast-start">
        <div class="auth-fast-start__copy">
          <strong>3초 만에 시작하기</strong>
          <span>처음이라면 빠르게 가입하고 바로 이용하세요.</span>
        </div>
        <button class="auth-fast-start__button" type="button" data-route="/auth/signup">회원가입</button>
      </div>
    </div>
  `;
}

function signupStepperMarkup(step) {
  const steps = [
    { key: "email", label: "이메일" },
    { key: "verify", label: "인증 확인" },
    { key: "account", label: "계정 만들기" },
  ];
  const stepIndex = Math.max(
    0,
    steps.findIndex((item) => item.key === step)
  );
  return `
    <ol class="signup-stepper" aria-label="회원가입 단계">
      ${steps
        .map((item, index) => {
          const state = index < stepIndex ? "is-done" : index === stepIndex ? "is-active" : "";
          return `<li class="signup-step ${state}"><span>${index + 1}</span><strong>${item.label}</strong></li>`;
        })
        .join("")}
    </ol>
  `;
}

function signupEmailStepMarkup(signupState, escapeHtml) {
  return `
    <form class="auth-form" data-public-signup-send-code-form>
      <label class="form-field">
        <span class="field-label">이메일</span>
        <div class="field-shell">
          <input
            class="field-input"
            type="email"
            name="email"
            placeholder="you@example.com"
            autocomplete="email"
            value="${escapeHtml(signupState.email ? signupState.email : "")}"
            data-signup-email-input
          />
        </div>
      </label>
      <button class="full-width-cta auth-form__submit" type="submit">인증코드 받기</button>
      <p class="auth-inline-note">입력한 이메일로 인증코드를 보내드립니다.</p>
    </form>
  `;
}

function signupVerifyStepMarkup(signupState, escapeHtml) {
  const expiresAt = String(signupState.expiresAt || "").trim();
  const resendAvailableAt = String(signupState.resendAvailableAt || "").trim();
  return `
    <div class="signup-verify">
      <div class="auth-status-card auth-status-card--success">
        <strong>${escapeHtml(signupState.email)}</strong>
        <span>인증코드를 확인한 뒤 다음 단계로 진행하세요.</span>
      </div>
      <form class="auth-form" data-public-signup-verify-form>
        <label class="form-field">
          <span class="field-label">인증코드</span>
          <div class="field-shell">
            <input
              class="field-input field-input--code"
              type="text"
              inputmode="numeric"
              name="code"
              placeholder="6자리 숫자"
              maxlength="6"
              autocomplete="one-time-code"
            />
          </div>
        </label>
        <div class="auth-inline-row auth-inline-row--split">
          <button class="ghost-secondary-button" type="button" data-public-signup-change-email>이메일 변경</button>
          <button class="ghost-secondary-button" type="button" data-public-signup-resend>인증코드 재전송</button>
        </div>
        <button class="full-width-cta auth-form__submit" type="submit">인증 확인</button>
      </form>
      <div class="auth-code-meta">
        ${expiresAt ? `<span>코드 만료: ${escapeHtml(expiresAt)}</span>` : ""}
        ${resendAvailableAt ? `<span>재전송 가능: ${escapeHtml(resendAvailableAt)}</span>` : ""}
      </div>
      ${
        signupState.previewCode
          ? `<div class="auth-dev-preview"><strong>개발용 코드</strong><span>${escapeHtml(signupState.previewCode)}</span></div>`
          : ""
      }
    </div>
  `;
}

function signupAccountStepMarkup({ signupState, legalDocuments, authConfig, escapeHtml }) {
  const passwordPolicy = authConfig?.passwordPolicy || {};
  const strength = evaluatePublicPasswordStrength("", { email: signupState.email, name: "" });
  return `
    <div class="signup-account">
      <div class="auth-status-card auth-status-card--verified">
        <strong>${escapeHtml(signupState.email)}</strong>
        <span>이메일 확인이 완료되었습니다. 계정 정보를 입력해 주세요.</span>
      </div>
      <form class="auth-form" data-public-signup-complete-form>
        <label class="form-field">
          <span class="field-label">이름 또는 닉네임</span>
          <div class="field-shell">
            <input class="field-input" type="text" name="name" placeholder="브랜드명 또는 닉네임" autocomplete="nickname" data-signup-name-input />
          </div>
        </label>
        <label class="form-field">
          <span class="field-label">비밀번호</span>
          <div class="field-shell field-shell--password">
            <input
              class="field-input"
              type="password"
              name="password"
              placeholder="${escapeHtml(`${passwordPolicy.minimumLength || 10}자 이상`)}"
              autocomplete="new-password"
              data-signup-password-input
            />
            <button class="password-toggle" type="button" data-password-toggle aria-label="비밀번호 보기">보기</button>
          </div>
        </label>
        <div class="password-strength" data-password-strength data-tone="${strength.tone}">
          <div class="password-strength__bar"><span style="width:${(strength.score / 4) * 100}%"></span></div>
          <div class="password-strength__meta">
            <strong data-password-strength-label>${strength.label}</strong>
            <span data-password-strength-guidance>${strength.guidance}</span>
          </div>
          <ul class="password-strength__warnings" data-password-strength-warnings></ul>
        </div>
        <label class="form-field">
          <span class="field-label">비밀번호 확인</span>
          <div class="field-shell field-shell--password">
            <input class="field-input" type="password" name="passwordConfirmation" placeholder="비밀번호를 다시 입력" autocomplete="new-password" />
            <button class="password-toggle" type="button" data-password-toggle aria-label="비밀번호 보기">보기</button>
          </div>
        </label>
        <div class="auth-consent-list">
          <label class="auth-consent-item"><input type="checkbox" name="termsAgreed" /> <span>이용약관 동의 (필수)</span></label>
          <label class="auth-consent-item"><input type="checkbox" name="privacyAgreed" /> <span>개인정보처리방침 동의 (필수)</span></label>
          <label class="auth-consent-item"><input type="checkbox" name="ageConfirmed" /> <span>만 14세 이상 확인 (필수)</span></label>
          <label class="auth-consent-item"><input type="checkbox" name="marketingAgreed" /> <span>마케팅 정보 수신 동의 (선택)</span></label>
        </div>
        <div class="auth-legal-links">
          ${legalDocuments
            .map((doc) => `<button class="auth-link" type="button" data-route="/legal/${doc.key}">${escapeHtml(doc.title)}</button>`)
            .join("")}
        </div>
        <button class="full-width-cta auth-form__submit" type="submit">가입 완료</button>
      </form>
    </div>
  `;
}

function signupFlowMarkup({ authConfig, legalDocuments, authState, escapeHtml }) {
  const signupState = authState?.signup || {};
  const currentStep = signupState.step || "email";
  return `
    <div class="auth-shell__body">
      <div class="auth-shell__copy">
        <h1>간편 가입하고 바로 이용하세요</h1>
        <p>이메일 확인 후 계정을 활성화합니다.</p>
      </div>
      ${signupStepperMarkup(currentStep)}
      ${
        currentStep === "verify"
          ? signupVerifyStepMarkup(signupState, escapeHtml)
          : currentStep === "account"
            ? signupAccountStepMarkup({ signupState, legalDocuments, authConfig, escapeHtml })
            : signupEmailStepMarkup(signupState, escapeHtml)
      }
      ${socialButtonsMarkup(authConfig, escapeHtml)}
      <div class="auth-switch">
        <span>이미 계정이 있나요?</span>
        <button class="auth-link" type="button" data-route="/auth">로그인</button>
      </div>
    </div>
  `;
}

function authShellMarkup({ mode, modal, authConfig, legalDocuments, authState, siteSettings, escapeHtml, includeClose }) {
  const bodyMarkup =
    mode === "signup"
      ? signupFlowMarkup({ authConfig, legalDocuments, authState, escapeHtml })
      : loginFormMarkup({ authConfig, escapeHtml });
  return `
    <section class="auth-shell ${modal ? "auth-shell--modal" : "auth-shell--page"}">
      <div class="auth-shell__surface">
        <div class="auth-shell__header">
          ${brandMarkup(siteSettings, escapeHtml)}
          ${includeClose ? `<button class="auth-shell__close" type="button" data-public-login-close aria-label="닫기">✕</button>` : ""}
        </div>
        ${bodyMarkup}
      </div>
    </section>
  `;
}

export function renderAuthModalMarkup({
  isOpen,
  isLoggedIn,
  authConfig,
  authState,
  siteSettings,
  escapeHtml,
}) {
  if (!isOpen || isLoggedIn) return "";
  return `
    <div class="auth-modal-layer">
      <button class="auth-modal-layer__backdrop" type="button" aria-label="로그인 닫기" data-public-login-close></button>
      ${authShellMarkup({
        mode: "login",
        modal: true,
        authConfig,
        legalDocuments: [],
        authState,
        siteSettings,
        escapeHtml,
        includeClose: true,
      })}
    </div>
  `;
}

export function renderAuthPageMarkup({
  mode,
  authConfig,
  authState,
  legalDocuments,
  siteSettings,
  escapeHtml,
}) {
  return authShellMarkup({
    mode,
    modal: false,
    authConfig,
    legalDocuments,
    authState,
    siteSettings,
    escapeHtml,
    includeClose: false,
  });
}
