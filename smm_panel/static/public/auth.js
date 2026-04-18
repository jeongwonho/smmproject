function renderAuthFormMarkup({ loginTabActive, legalDocuments, authConfig, escapeHtml }) {
  return `
    <div class="auth-modal__tabs">
      <button class="auth-tab ${loginTabActive ? "is-active" : ""}" type="button" data-auth-tab="login">로그인</button>
      <button class="auth-tab ${loginTabActive ? "" : "is-active"}" type="button" data-auth-tab="signup">회원가입</button>
    </div>
    ${
      loginTabActive
        ? `
          <form class="auth-modal__form" data-public-login-form>
            <label class="form-field">
              <span class="field-label">이메일</span>
              <div class="field-shell">
                <input class="field-input" type="email" name="email" placeholder="you@example.com" autocomplete="email" />
              </div>
            </label>
            <label class="form-field">
              <span class="field-label">비밀번호</span>
              <div class="field-shell">
                <input class="field-input" type="password" name="password" placeholder="비밀번호 입력" autocomplete="current-password" />
              </div>
            </label>
            <button class="full-width-cta auth-modal__submit" type="submit">로그인</button>
          </form>
        `
        : `
          <form class="auth-modal__form" data-public-signup-form>
            <label class="form-field">
              <span class="field-label">이메일</span>
              <div class="field-shell">
                <input class="field-input" type="email" name="email" placeholder="you@example.com" autocomplete="email" />
              </div>
            </label>
            <label class="form-field">
              <span class="field-label">이름 또는 닉네임</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="name" placeholder="홍길동 또는 브랜드명" autocomplete="nickname" />
              </div>
            </label>
            <label class="form-field">
              <span class="field-label">비밀번호</span>
              <div class="field-shell">
                <input class="field-input" type="password" name="password" placeholder="8자 이상 입력" autocomplete="new-password" />
              </div>
            </label>
            <label class="form-field">
              <span class="field-label">비밀번호 확인</span>
              <div class="field-shell">
                <input class="field-input" type="password" name="passwordConfirmation" placeholder="비밀번호를 다시 입력" autocomplete="new-password" />
              </div>
            </label>
            <div class="auth-consent-list">
              <label class="auth-consent-item"><input type="checkbox" name="termsAgreed" /> <span>이용약관 동의(필수)</span></label>
              <label class="auth-consent-item"><input type="checkbox" name="privacyAgreed" /> <span>개인정보처리방침 동의(필수)</span></label>
              <label class="auth-consent-item"><input type="checkbox" name="ageConfirmed" /> <span>만 14세 이상 또는 법정대리인 동의 확인(필수)</span></label>
              <label class="auth-consent-item"><input type="checkbox" name="marketingAgreed" /> <span>마케팅 정보 수신 동의(선택)</span></label>
            </div>
            <div class="auth-legal-links">
              ${legalDocuments
                .map((doc) => `<button class="ghost-secondary-button" type="button" data-route="/legal/${doc.key}">${escapeHtml(doc.title)} 보기</button>`)
                .join("")}
            </div>
            <button class="full-width-cta auth-modal__submit" type="submit">회원가입</button>
          </form>
        `
    }
    <div class="auth-social-list">
      ${authConfig.oauthProviders
        .map(
          (provider) => `
            <button
              class="ghost-secondary-button auth-social-button ${provider.enabled ? "" : "is-disabled"}"
              type="button"
              data-oauth-provider="${provider.provider}"
            >
              ${escapeHtml(provider.label)} ${provider.enabled ? "" : "(준비 중)"}
            </button>
          `
        )
        .join("")}
    </div>
  `;
}

export function renderAuthModalMarkup({
  isOpen,
  isLoggedIn,
  authTab,
  authConfig,
  legalDocuments,
  escapeHtml,
}) {
  if (!isOpen || isLoggedIn) return "";
  const loginTabActive = authTab !== "signup";
  return `
    <div class="auth-modal-layer">
      <button class="auth-modal-layer__backdrop" type="button" aria-label="로그인 닫기" data-public-login-close></button>
      <div class="auth-modal">
        <div class="auth-modal__head">
          <span class="auth-modal__eyebrow">Customer Account</span>
          <strong>${loginTabActive ? "로그인 후 주문을 이어갈 수 있어요" : "회원가입 후 바로 주문할 수 있어요"}</strong>
          <p>상품 탐색은 자유롭게, 주문·충전·내역 확인은 고객 계정에서 안전하게 진행됩니다.</p>
        </div>
        ${renderAuthFormMarkup({ loginTabActive, legalDocuments, authConfig, escapeHtml })}
        <button class="auth-modal__close" type="button" data-public-login-close>닫기</button>
      </div>
    </div>
  `;
}

export function renderAuthPageMarkup({
  authTab,
  authConfig,
  legalDocuments,
  escapeHtml,
}) {
  const loginTabActive = authTab !== "signup";
  return `
    <section class="content-section">
      <div class="auth-page-card">
        <div class="auth-modal__head auth-modal__head--page">
          <span class="auth-modal__eyebrow">Customer Account</span>
          <strong>${loginTabActive ? "로그인 후 주문과 충전을 진행하세요" : "회원가입 후 바로 주문을 시작하세요"}</strong>
          <p>탐색은 자유롭게 가능하고, 실제 주문·충전·내역 조회는 고객 계정에서 안전하게 관리됩니다.</p>
        </div>
        ${renderAuthFormMarkup({ loginTabActive, legalDocuments, authConfig, escapeHtml })}
      </div>
    </section>
  `;
}
