let runtime = null;

export function configureAdminPages(nextRuntime) {
  runtime = nextRuntime;
}

function useRuntime() {
  if (!runtime) {
    throw new Error("Admin pages runtime is not configured.");
  }
  return runtime;
}

function renderAdminFrame(content) {
  return `
    <div class="admin-frame admin-surface">
      ${content}
    </div>
  `;
}

function renderAdminTopbar(title, description, metrics = []) {
  const { escapeHtml } = useRuntime();
  return `
    <section class="admin-topbar">
      <div class="admin-topbar__content">
        <span class="admin-topbar__eyebrow">Admin Workspace</span>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(description)}</p>
      </div>
      ${
        metrics.length
          ? `
            <div class="admin-topbar__metrics">
              ${metrics
                .map(
                  (metric) => `
                    <article class="admin-topbar__metric">
                      <span>${escapeHtml(metric.label)}</span>
                      <strong>${escapeHtml(metric.value)}</strong>
                    </article>
                  `
                )
                .join("")}
            </div>
          `
          : ""
      }
    </section>
  `;
}

function renderAdminAuthRail(session = {}) {
  const { escapeHtml } = useRuntime();
  const securityCards = [
    {
      label: "검색엔진 차단",
      value: "활성",
      description: "robots.txt와 X-Robots-Tag로 /admin 경로를 차단합니다.",
    },
    {
      label: "세션 보안",
      value: "Strict",
      description: "HttpOnly + SameSite 쿠키 기반으로 관리자 세션을 유지합니다.",
    },
    {
      label: "민감정보 보호",
      value: "마스킹",
      description: "공급사 키와 고객 정보는 기본 화면에서 노출되지 않습니다.",
    },
  ];

  return `
    <div class="admin-rail-card admin-rail-card--auth">
      <div class="admin-rail-card__top">
        <span class="admin-rail-card__eyebrow">Security Gate</span>
        <strong>관리자 전용 데스크톱 진입</strong>
        <p>운영 메뉴가 계속 늘어나더라도 PC에서 빠르게 탐색할 수 있도록 관리자 화면을 별도 워크스페이스로 운용합니다.</p>
      </div>
      <div class="admin-auth-rail-grid">
        ${securityCards
          .map(
            (item) => `
              <article class="admin-auth-rail-card">
                <span>${escapeHtml(item.label)}</span>
                <strong>${escapeHtml(item.value)}</strong>
                <p>${escapeHtml(item.description)}</p>
              </article>
            `
          )
          .join("")}
      </div>
      <div class="admin-rail-card__foot">
        <span class="admin-badge ${session.configured ? "is-success" : "is-warning"}">${session.configured ? "보안 설정 완료" : "보안 설정 필요"}</span>
        <span class="admin-badge is-neutral">PC 최적화 콘솔</span>
      </div>
    </div>
  `;
}

export function renderAdminAuth() {
  const { state } = useRuntime();
  const session = state.adminSession || { configured: false, authenticated: false };
  const topbar = renderAdminTopbar("보안 인증 워크스페이스", "관리자 로그인 전에도 보안 상태와 접근 정책을 한눈에 볼 수 있도록 데스크톱형 진입 화면으로 재구성했습니다.", [
    { label: "관리자 계정", value: session.configured ? "준비됨" : "미설정" },
    { label: "봇 차단", value: "ON" },
    { label: "민감정보", value: "보호중" },
  ]);

  return renderAdminFrame(`
    <div class="admin-workspace admin-workspace--auth">
      <aside class="admin-rail">
        ${renderAdminAuthRail(session)}
      </aside>

      <div class="admin-content">
        ${topbar}
        <div class="admin-auth-layout">
          <section class="admin-hero admin-hero--auth">
            <div>
              <p class="admin-hero__eyebrow">Security Gate</p>
              <h1>관리자 보안 인증</h1>
              <p>공급사 API 키, 고객 상세 정보, 운영 제어 메뉴는 로그인된 관리자 세션에서만 접근할 수 있도록 잠금 처리되었습니다.</p>
            </div>
          </section>

          <section class="admin-card admin-auth-card">
            ${
              session.configured
                ? `
                  <div class="section-head section-head--compact">
                    <h2>관리자 로그인</h2>
                    <p>인증 후에만 고객 상세 정보와 공급사 키 수정 기능이 활성화됩니다.</p>
                  </div>
                  <form class="admin-form" data-admin-login-form>
                    <label class="form-field">
                      <span class="field-label">관리자 계정</span>
                      <div class="field-shell">
                        <input class="field-input" type="text" name="username" value="admin" autocomplete="username" />
                      </div>
                    </label>
                    <label class="form-field">
                      <span class="field-label">관리자 비밀번호</span>
                      <div class="field-shell">
                        <input class="field-input" type="password" name="password" autocomplete="current-password" />
                      </div>
                    </label>
                    <button class="admin-primary-button" type="submit">로그인</button>
                  </form>
                `
                : `
                  <div class="section-head section-head--compact">
                    <h2>보안 설정 필요</h2>
                    <p>서버 시작 시 관리자 비밀번호를 설정해야 관리자 화면이 열립니다.</p>
                  </div>
                  <div class="admin-security-note">
                    <strong>실행 예시</strong>
                    <code>export SMM_PANEL_ADMIN_PASSWORD="강한비밀번호"</code>
                    <code>python3 smm_panel/server.py --host 127.0.0.1 --port 8024</code>
                  </div>
                `
            }
          </section>
        </div>
      </div>
    </div>
  `);
}

function renderAdminErpHeader(stats = {}, popup = null) {
  const { state, escapeHtml, getAdminSiteSettings, DEFAULT_SITE_NAME, brandMonogram, getAdminSectionConfig } = useRuntime();
  const username = state.adminSession?.username || "admin";
  const siteName = getAdminSiteSettings()?.siteName || state.bootstrap?.siteSettings?.siteName || DEFAULT_SITE_NAME;
  const activeSection = getAdminSectionConfig();
  const snapshotCards = [
    { label: "주문", value: `${Number(stats.orderCount || 0)}건` },
    { label: "고객", value: `${Number(stats.customerCount || 0)}명` },
    { label: "공급사", value: `${Number(stats.supplierCount || 0)}곳` },
    { label: "팝업", value: popup?.isActive ? "노출중" : "비노출" },
  ];

  return `
    <header class="admin-console-header">
      <div class="admin-console-header__main">
        <div class="admin-erp-brand">
          <div class="admin-erp-brand__mark">${escapeHtml(brandMonogram(siteName))}</div>
          <div class="admin-erp-brand__text">
            <strong>${escapeHtml(siteName)} ERP</strong>
            <span>Operations Console</span>
          </div>
        </div>

        <div class="admin-console-header__context">
          <span class="admin-console-header__eyebrow">현재 모듈</span>
          <strong>${escapeHtml(activeSection.label)}</strong>
          <p>${escapeHtml(activeSection.summary)}</p>
        </div>
      </div>

      <div class="admin-console-header__snapshot">
        ${snapshotCards
          .map(
            (card) => `
              <article class="admin-console-header__snapshot-card">
                <span>${escapeHtml(card.label)}</span>
                <strong>${escapeHtml(card.value)}</strong>
              </article>
            `
          )
          .join("")}
      </div>

      <div class="admin-console-header__actions">
        <div class="admin-erp-user">
          <span class="admin-erp-user__avatar">${escapeHtml(username.slice(0, 1).toUpperCase())}</span>
          <div>
            <strong>${escapeHtml(username)}</strong>
            <span>관리자 세션 진행 중</span>
          </div>
        </div>
        <div class="admin-console-header__button-row">
          <button class="admin-erp-utility" type="button" data-route="/">사이트 보기</button>
          <button class="admin-erp-utility" type="button" data-admin-refresh>새로고침</button>
          <button class="admin-erp-utility is-primary" type="button" data-admin-logout>로그아웃</button>
        </div>
      </div>
    </header>
  `;
}

function renderAdminErpSidebar(stats = {}, popup = null) {
  const { state, escapeHtml, adminSectionItems, getAdminSectionConfig, getAdminSiteSettings, DEFAULT_SITE_NAME } = useRuntime();
  const sections = adminSectionItems(stats, popup);
  const activeSection = getAdminSectionConfig();
  const siteSettings = getAdminSiteSettings() || state.bootstrap?.siteSettings || null;
  const controlItems = [
    {
      label: "즉시 확인 필요",
      value: `${Number(stats.orderCount || 0)}건`,
      description: "주문 운영에서 대기/진행 주문과 전송 실패 상태를 먼저 점검",
    },
    {
      label: "공급사 상태",
      value: `${Number(stats.activeSupplierCount || 0)}/${Number(stats.supplierCount || 0)} 활성`,
      description: "연결 확인과 서비스 동기화 이력을 기준으로 관리",
    },
    {
      label: "브랜드/노출",
      value: siteSettings?.siteName || DEFAULT_SITE_NAME,
      description: popup?.isActive ? `팝업 노출중 · ${popup.route || "경로 미설정"}` : "팝업 비노출 · 기본 설정 확인 필요",
    },
  ];
  const quickActions = [
    { label: "새 공급사", action: "data-admin-supplier-new" },
    { label: "새 고객", action: "data-admin-customer-new" },
    { label: "새 상품", action: "data-admin-product-new" },
  ];

  return `
    <aside class="admin-erp-sidebar admin-console-sidebar">
      <section class="admin-console-sidebar__active">
        <span class="admin-erp-sidebar__eyebrow">현재 작업</span>
        <strong class="admin-erp-sidebar__title">${escapeHtml(activeSection.title)}</strong>
        <p class="admin-erp-sidebar__copy">${escapeHtml(activeSection.summary)}</p>
        <div class="admin-console-sidebar__quick-row">
          ${quickActions
            .map((item) => `<button class="admin-console-sidebar__quick" type="button" ${item.action}>${escapeHtml(item.label)}</button>`)
            .join("")}
        </div>
      </section>

      <section class="admin-erp-sidebar__section">
        <span class="admin-erp-sidebar__eyebrow">Workspace Menu</span>
        <div class="admin-erp-sidebar__menu">
          ${sections
            .map(
              (section) => `
                <button
                  class="admin-erp-sidebar__item ${state.ui.adminActiveSection === section.id ? "is-active" : ""}"
                  type="button"
                  data-admin-scroll-section="${section.id}"
                >
                  <span class="admin-erp-sidebar__item-icon">${escapeHtml(section.icon || "•")}</span>
                  <div>
                    <strong>${escapeHtml(section.label)}</strong>
                    <small>${escapeHtml(section.description)}</small>
                  </div>
                  <span class="admin-erp-sidebar__item-stat">${escapeHtml(section.stat || "")}</span>
                </button>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="admin-erp-sidebar__section">
        <span class="admin-erp-sidebar__eyebrow">Operation Snapshot</span>
        <div class="admin-erp-sidebar__stack">
          ${controlItems
            .map(
              (item) => `
                <article class="admin-erp-sidebar__card">
                  <span>${escapeHtml(item.label)}</span>
                  <strong>${escapeHtml(item.value)}</strong>
                  <p>${escapeHtml(item.description)}</p>
                </article>
              `
            )
            .join("")}
        </div>
      </section>
    </aside>
  `;
}

function renderAdminModuleHeader(sectionId) {
  const { state, escapeHtml, getAdminSectionConfig } = useRuntime();
  const section = getAdminSectionConfig(sectionId);
  const categorySelected = Boolean(state.ui.adminSelectedCategoryId);

  let actions = `
    <button class="admin-secondary-button" type="button" data-admin-refresh>새로고침</button>
  `;

  if (sectionId === "overview") {
    actions = `
      <button class="admin-secondary-button" type="button" data-route="/">사용자 패널 열기</button>
      <button class="admin-primary-button" type="button" data-admin-refresh>운영 데이터 갱신</button>
    `;
  } else if (sectionId === "analytics") {
    actions = `
      <button class="admin-secondary-button" type="button" data-route="/">사이트 열기</button>
      <button class="admin-primary-button" type="button" data-admin-refresh>통계 새로고침</button>
    `;
  } else if (sectionId === "settings") {
    actions = `
      <button class="admin-secondary-button" type="button" data-route="/">사이트 확인</button>
      <button class="admin-primary-button" type="button" data-admin-refresh>설정 다시 불러오기</button>
    `;
  } else if (sectionId === "popup") {
    actions = `
      <button class="admin-secondary-button" type="button" data-route="/">홈 미리보기</button>
      <button class="admin-primary-button" type="button" data-admin-refresh>노출 데이터 갱신</button>
    `;
  } else if (sectionId === "suppliers") {
    actions = `
      <button class="admin-secondary-button" type="button" data-admin-refresh>연동 현황 갱신</button>
      <button class="admin-primary-button" type="button" data-admin-supplier-new>새 공급사</button>
    `;
  } else if (sectionId === "customers") {
    actions = `
      <button class="admin-secondary-button" type="button" data-admin-refresh>회원 목록 갱신</button>
      <button class="admin-primary-button" type="button" data-admin-customer-new>새 고객</button>
    `;
  } else if (sectionId === "catalog") {
    actions = `
      <button class="admin-secondary-button" type="button" data-admin-category-new>새 카테고리</button>
      <button class="admin-primary-button" type="button" data-admin-product-new ${categorySelected ? "" : "disabled"}>새 상품</button>
    `;
  }

  return `
    <section class="admin-module-header">
      <div class="admin-module-header__breadcrumb">관리자 / ${escapeHtml(section.label)}</div>
      <div class="admin-module-header__row">
        <div>
          <h1>${escapeHtml(section.title)}</h1>
          <p>${escapeHtml(section.summary)}</p>
        </div>
        <div class="admin-module-header__actions">
          ${actions}
        </div>
      </div>
    </section>
  `;
}

function renderAdminActiveSection(sectionId, context) {
  const {
    renderAnalyticsAdminSection,
    renderSiteSettingsAdminSection,
    renderPopupAdminSection,
    renderSupplierAdminSection,
    renderCustomerAdminSection,
    renderCatalogAdminSection,
    renderAdminOrdersSection,
    renderAdminOverviewSection,
  } = useRuntime();
  if (sectionId === "analytics") return renderAnalyticsAdminSection();
  if (sectionId === "settings") return renderSiteSettingsAdminSection();
  if (sectionId === "popup") return renderPopupAdminSection();
  if (sectionId === "suppliers") return renderSupplierAdminSection(context);
  if (sectionId === "customers") return renderCustomerAdminSection();
  if (sectionId === "catalog") return renderCatalogAdminSection();
  if (sectionId === "orders") return renderAdminOrdersSection();
  return renderAdminOverviewSection(context.stats, context.popup);
}

export function renderAdmin() {
  const {
    state,
    getAdminSuppliers,
    getAdminProducts,
    getAdminPopup,
    getSelectedAdminSupplier,
    getSelectedAdminProduct,
    blankSupplierDraft,
    getAdminSectionConfig,
  } = useRuntime();
  const suppliers = getAdminSuppliers();
  const products = getAdminProducts();
  const stats = state.adminBootstrap?.stats || {};
  const popup = getAdminPopup();
  const selectedSupplier = getSelectedAdminSupplier();
  const selectedProduct = getSelectedAdminProduct();
  const draft = state.adminSupplierDraft || blankSupplierDraft();
  const serviceData = selectedSupplier ? state.adminSupplierServices[selectedSupplier.id] : null;
  const allServices = serviceData?.services || [];
  const serviceSearch = state.ui.adminServiceSearch.trim().toLowerCase();
  const filteredServices = allServices.filter((service) => {
    if (!serviceSearch) return true;
    const haystack = `${service.name} ${service.category} ${service.externalServiceId}`.toLowerCase();
    return haystack.includes(serviceSearch);
  });
  const selectedService =
    allServices.find((service) => service.id === state.ui.adminSelectedSupplierServiceId) ||
    filteredServices.find((service) => service.id === state.ui.adminSelectedSupplierServiceId) ||
    null;
  const connectionResult = state.adminConnectionResult;
  const activeConnection = connectionResult || selectedSupplier;
  const activeSection = getAdminSectionConfig();
  const context = {
    suppliers,
    products,
    stats,
    popup,
    selectedSupplier,
    selectedProduct,
    draft,
    allServices,
    filteredServices,
    selectedService,
    activeConnection,
  };

  return renderAdminFrame(`
    <div class="admin-erp-shell">
      ${renderAdminErpHeader(stats, popup)}
      <div class="admin-erp-body">
        ${renderAdminErpSidebar(stats, popup)}
        <main class="admin-erp-main">
          ${renderAdminModuleHeader(activeSection.id)}
          <div class="admin-erp-stage">
            ${renderAdminActiveSection(activeSection.id, context)}
          </div>
        </main>
      </div>
    </div>
  `);
}
