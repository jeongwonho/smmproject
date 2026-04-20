import { renderAuthModalMarkup, renderAuthPageMarkup } from "./auth.js";
import { renderChargePage } from "./charge.js";
import { renderHelpMarkup, renderLegalPageMarkup } from "./help.js";

let runtime = null;

export function configurePublicPages(nextRuntime) {
  runtime = nextRuntime;
}

function useRuntime() {
  if (!runtime) {
    throw new Error("Public pages runtime is not configured.");
  }
  return runtime;
}

function renderBottomNav(activeKey) {
  const { navItems } = useRuntime();
  return `
    <nav class="bottom-nav public-bottom-nav">
      ${navItems
        .map(
          (item) => `
          <button class="bottom-nav__item ${activeKey === item.key ? "is-active" : ""}" type="button" data-route="${item.route}">
            <span class="bottom-nav__icon">${item.icon}</span>
            <span class="bottom-nav__label">${item.label}</span>
          </button>
        `
        )
        .join("")}
    </nav>
  `;
}

export function renderPublicLoginModal() {
  const { state, isLoggedIn, escapeHtml } = useRuntime();
  return renderAuthModalMarkup({
    isOpen: state.ui.loginModalOpen,
    isLoggedIn: isLoggedIn(),
    authConfig: state.bootstrap?.authConfig || { oauthProviders: [] },
    authState: state.publicAuth || {},
    siteSettings: state.bootstrap?.siteSettings || {},
    escapeHtml,
  });
}

export function renderFrame(content, activeKey, extraSticky = "") {
  return `
    <div class="phone-frame public-frame public-surface">
      ${content}
      ${extraSticky}
      ${renderBottomNav(activeKey)}
      ${renderPublicLoginModal()}
    </div>
  `;
}

function renderHomeFooter(data) {
  const { state, escapeHtml, siteNameOrDefault, renderSiteBrandLogoMarkup } = useRuntime();
  const siteSettings = data?.siteSettings || {};
  const siteName = siteNameOrDefault(siteSettings.siteName || data?.company?.name);
  const expanded = Boolean(state.ui.homeFooterExpanded);
  const currentYear = new Date().getFullYear();
  const detailRows = [
    ["서비스명", siteName],
    ["운영자", data?.company?.representative || "운영 관리자"],
    ["문의", data?.company?.contact || "support@example.com"],
    ["운영시간", data?.company?.hours || "평일 10:00 - 19:00"],
  ];

  return `
    <section class="content-section footer-section footer-section--home">
      <div class="footer-fold ${expanded ? "is-expanded" : ""}">
        <button
          class="footer-fold__toggle"
          type="button"
          data-home-footer-toggle
          aria-expanded="${expanded ? "true" : "false"}"
        >
          <span class="footer-fold__brand">
            ${renderSiteBrandLogoMarkup(siteSettings, "footer-fold__brand-mark", { surface: "light" })}
            <strong class="footer-fold__brand-name">${escapeHtml(siteName)}</strong>
          </span>
          <span class="footer-fold__chevron" aria-hidden="true">${expanded ? "⌃" : "⌄"}</span>
        </button>
        <div class="footer-fold__divider"></div>
        ${
          expanded
            ? `
              <dl class="footer-fold__details">
                ${detailRows
                  .map(
                    ([label, value]) => `
                      <div class="footer-fold__detail-row">
                        <dt>${escapeHtml(label)}</dt>
                        <dd>${escapeHtml(value)}</dd>
                      </div>
                    `
                  )
                  .join("")}
              </dl>
              <div class="footer-fold__divider"></div>
            `
            : ""
        }
        <p class="footer-fold__copyright">Copyright ${currentYear}. ${escapeHtml(siteName)}. All rights reserved.</p>
        <div class="footer-fold__links" role="navigation" aria-label="푸터 링크">
          <button class="footer-fold__link" type="button" data-route="/legal/terms">이용약관</button>
          <span class="footer-fold__sep" aria-hidden="true">|</span>
          <button class="footer-fold__link" type="button" data-route="/legal/privacy">개인정보 처리방침</button>
          <span class="footer-fold__sep" aria-hidden="true">|</span>
          <button class="footer-fold__link" type="button" data-route="/help">서비스 이용가이드</button>
        </div>
      </div>
    </section>
  `;
}

function renderHomePlatformDock(data) {
  const { escapeHtml, siteNameOrDefault, renderSiteBrandLogoMarkup, renderPlatformLogoMarkup } = useRuntime();
  const siteSettings = data?.siteSettings || {};
  return `
    <section class="content-section content-section--tight home-platform-dock-section">
      <div class="home-platform-dock">
        <div class="home-platform-dock__brand" aria-label="${escapeHtml(siteNameOrDefault(siteSettings.siteName))}">
          ${renderSiteBrandLogoMarkup(siteSettings, "home-platform-dock__brand-mark", { surface: "light" })}
        </div>
        <div class="home-platform-dock__scroller" aria-label="서비스 플랫폼 빠른 선택">
          ${data.platforms
            .map(
              (platform) => `
                <button
                  class="home-platform-chip"
                  type="button"
                  data-route="/products"
                  data-platform-id="${platform.id}"
                >
                  ${renderPlatformLogoMarkup(platform, "home-platform-chip__icon")}
                  <span>${escapeHtml(platform.displayName)}</span>
                </button>
              `
            )
            .join("")}
        </div>
      </div>
    </section>
  `;
}

function renderHomeHeroStats(items) {
  const { escapeHtml } = useRuntime();
  if (!items?.length) return "";
  return `
    <div class="home-hero-stats">
      ${items
        .map(
          (item) => `
            <article class="home-hero-stat">
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function buildHomeHeroStats(formatNumber) {
  const now = new Date();
  const base = 12485321;
  const dayStart = new Date(2026, 0, 1);
  const dayOffset = Math.max(0, Math.floor((now.getTime() - dayStart.getTime()) / 86400000));
  const purchasedCount = base + dayOffset * 173;
  const latestCheck = now.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return [
    { label: "이만큼 구매했어요", value: formatNumber(purchasedCount) },
    { label: "점검 상태", value: `최신 점검 ${latestCheck}` },
  ];
}

function renderInterestTags(tags = []) {
  const { escapeHtml } = useRuntime();
  if (!tags.length) return "";
  return `
    <div class="home-interest-row">
      ${tags
        .map(
          (tag) => `
            <button class="interest-tag" type="button" data-route="${escapeHtml(tag.route)}">${escapeHtml(tag.title)}</button>
          `
        )
        .join("")}
    </div>
  `;
}

export function renderAuthPage() {
  const { getRoute, state, escapeHtml } = useRuntime();
  const route = getRoute();
  const mode = route.name === "auth" ? route.mode || "login" : "login";
  return renderFrame(
    `
      <div class="page page-auth">
        <header class="topbar">
          <button class="icon-button" type="button" data-route="/">‹</button>
          <strong class="topbar-title">${mode === "signup" ? "회원가입" : "로그인"}</strong>
          <button class="icon-button" type="button" data-route="/help">?</button>
        </header>
        <div class="topbar-spacer"></div>
        ${renderAuthPageMarkup({
          mode,
          authConfig: state.bootstrap?.authConfig || { oauthProviders: [] },
          authState: state.publicAuth || {},
          legalDocuments: state.bootstrap?.legalDocuments || [],
          siteSettings: state.bootstrap?.siteSettings || {},
          escapeHtml,
        })}
      </div>
    `,
    "my"
  );
}

export function renderHome() {
  const {
    state,
    isLoggedIn,
    escapeHtml,
    formatNumber,
    getActiveHomeBanners,
    renderHomeBannerCard,
    renderSiteBrandLogoMarkup,
    renderPlatformLogoMarkup,
    renderHomePopupOverlay,
  } = useRuntime();
  const data = state.bootstrap;
  if (!data) return "";
  const authenticated = isLoggedIn();
  const user = data.user;
  const siteSettings = data.siteSettings || {};
  const activeBanners = getActiveHomeBanners();
  const safeBannerIndex = activeBanners.length ? state.ui.bannerIndex % activeBanners.length : 0;
  if (safeBannerIndex !== state.ui.bannerIndex) {
    state.ui.bannerIndex = safeBannerIndex;
  }
  const topBanner = activeBanners[0] || null;
  const quickLinks = data.topLinks?.length ? data.topLinks : [{ label: "서비스 소개서", route: "/products" }, { label: "이용 가이드", route: "/help" }];
  const noticePreview = data.notices?.[0] || null;
  const compactPlatforms = (data.platforms || []).slice(0, 10);
  const featuredServices = (data.featuredServices || []).slice(0, 6);
  const supportLinks = (data.supportLinks || []).slice(0, 3);
  const heroStats = buildHomeHeroStats(formatNumber);

  return renderFrame(
    `
      <div class="page page-home page-home--renewed">
        <section class="home-hero home-hero--compact">
          <div class="home-hero__header">
            <div class="home-hero__brandblock">
              ${renderSiteBrandLogoMarkup(siteSettings, "home-hero__brandmark")}
            </div>
            <div class="home-hero__quicklinks">
              ${quickLinks
                .map(
                  (link) => `
                    <button class="home-hero__quicklink" type="button" data-route="${escapeHtml(link.route)}">
                      ${escapeHtml(link.label)}
                    </button>
                  `
                )
                .join("")}
            </div>
          </div>

          <div class="home-hero__body">
            <button
              class="home-login-card ${authenticated ? "is-authenticated" : ""}"
              type="button"
              ${authenticated ? 'data-route="/my"' : 'data-route="/auth"'}
            >
              <div class="home-login-card__copy">
                <strong>${escapeHtml(authenticated ? `${user.name}님, 바로 주문할까요?` : "지금 필요한 서비스를 바로 찾으세요")}</strong>
                <span>${escapeHtml(authenticated ? `보유 캐시 ${user.balanceLabel} · 누적 주문 ${formatNumber(state.orderCounts.all || 0)}건` : "플랫폼을 고르고 상품을 확인한 뒤 바로 주문까지 이어갈 수 있습니다.")}</span>
              </div>
              <span class="home-login-card__arrow">›</span>
            </button>
          </div>

          ${renderHomeHeroStats(heroStats)}
        </section>

        ${
          topBanner
            ? `
              <section class="content-section content-section--tight">
                ${renderHomeBannerCard(topBanner, { compact: true })}
              </section>
            `
            : ""
        }

        <section class="content-section content-section--tight home-discovery-section">
          <div class="home-search">
            <input
              class="home-search__input"
              type="text"
              placeholder="어떤 서비스를 찾으세요?"
              value="${escapeHtml(state.ui.search)}"
              data-home-search-input
            />
            <button class="home-search__submit" type="button" aria-label="서비스 검색" data-home-search-submit>⌕</button>
          </div>
          <div class="home-discovery-meta">
            <strong>대표 플랫폼</strong>
            <button class="home-discovery-meta__action" type="button" data-route="/products">전체 상품 보기</button>
          </div>
          <div class="home-platform-grid home-platform-grid--compact">
            ${compactPlatforms
              .map(
                (platform) => `
                  <button
                    class="home-platform-card home-platform-card--compact"
                    type="button"
                    data-route="/products"
                    data-platform-id="${platform.id}"
                  >
                    ${renderPlatformLogoMarkup(platform, "home-platform-card__icon")}
                    <strong>${escapeHtml(platform.displayName)}</strong>
                  </button>
                `
              )
              .join("")}
          </div>
          <div class="home-sales-strip">
            <span class="mini-badge">빠른 선택</span>
            <p>자주 찾는 플랫폼부터 바로 들어가고, 상세에서 가격과 정책을 확인한 뒤 주문하세요.</p>
          </div>
        </section>

        ${renderHomePlatformDock(data)}

        ${
          activeBanners.length
            ? `
              <section class="content-section">
                <div class="banner-carousel banner-carousel--media">
                  <div class="banner-track" data-home-banner-track style="transform: translateX(-${safeBannerIndex * 100}%);">
                    ${activeBanners
                      .map((banner, index) => renderHomeBannerCard(banner, { compact: false, index, total: activeBanners.length }))
                      .join("")}
                  </div>
                </div>
                ${
                  activeBanners.length > 1
                    ? `
                      <div class="banner-dots banner-dots--home">
                        ${activeBanners
                          .map(
                            (_, index) => `
                              <button
                                class="banner-dot ${index === safeBannerIndex ? "is-active" : ""}"
                                type="button"
                                data-banner-index="${index}"
                                aria-label="배너 ${index + 1}"
                              ></button>
                            `
                          )
                          .join("")}
                      </div>
                    `
                    : ""
                }
              </section>
            `
            : ""
        }

        <section class="content-section content-section--tight">
          <div class="section-head section-head--compact public-section-head">
            <h2>바로 선택하기</h2>
            <p>자주 찾는 서비스를 먼저 열어보고 상세에서 가격과 정책을 확인할 수 있습니다.</p>
          </div>
          <div class="spotlight-list spotlight-list--compact">
            ${featuredServices
              .map(
                (item) => `
                  <button class="spotlight-card spotlight-card--compact" type="button" data-route="${item.route}">
                    <span class="spotlight-card__icon">${escapeHtml(item.icon)}</span>
                    <div class="spotlight-card__copy">
                      <strong>${escapeHtml(item.title)}</strong>
                      <p>${escapeHtml(item.subtitle)}</p>
                    </div>
                    <span class="spotlight-card__arrow">›</span>
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section content-section--tight">
          <div class="home-help-inline">
            <div class="home-help-inline__links">
              ${supportLinks
                .map(
                  (item) => `
                    <button class="home-help-link" type="button" data-route="${item.route}">
                      <span>${escapeHtml(item.icon)}</span>
                      <strong>${escapeHtml(item.title)}</strong>
                    </button>
                  `
                )
                .join("")}
            </div>
            ${
              noticePreview
                ? `
                  <article class="notice-card home-notice-card home-notice-card--compact">
                    <div class="notice-card__top">
                      <span class="mini-badge">${escapeHtml(noticePreview.tag)}</span>
                      <span>${escapeHtml(noticePreview.publishedLabel)}</span>
                    </div>
                    <strong>${escapeHtml(noticePreview.title)}</strong>
                    <p>${escapeHtml(noticePreview.body)}</p>
                  </article>
                `
                : `
                  <button class="home-help-inline__cta" type="button" data-route="/help">FAQ · 공지 · 정책 보기</button>
                `
            }
          </div>
        </section>

        ${renderHomeFooter(data)}
      </div>
    `,
    "home",
    renderHomePopupOverlay()
  );
}

export function renderProducts() {
  const { state, escapeHtml, filteredCatalog, getCurrentPlatform, renderPlatformLogoMarkup } = useRuntime();
  const platforms = filteredCatalog();
  const activePlatform = getCurrentPlatform(platforms);
  const activeProductCount = activePlatform ? activePlatform.groups.reduce((total, group) => total + group.productCategories.length, 0) : 0;

  return renderFrame(
    `
      <div class="page page-products">
        <header class="topbar topbar--search">
          <button class="icon-button" type="button" data-route="/">‹</button>
          <div class="search-shell">
            <input
              class="search-input"
              type="text"
              name="search"
              placeholder="상품명, 플랫폼, 설명 검색"
              value="${escapeHtml(state.ui.search)}"
              data-search-input="catalog"
            />
          </div>
          <button class="icon-button" type="button" data-route="/charge">₩</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="content-section">
          <div class="catalog-toolbar-card">
            <div class="section-head section-head--compact public-section-head">
              <h2>상품 목록</h2>
              <p>${escapeHtml(activePlatform ? `${activePlatform.displayName} 카테고리 ${activeProductCount}개` : "검색어에 맞는 플랫폼과 상품을 찾지 못했습니다.")}</p>
            </div>
            <aside class="platform-rail public-platform-rail">
              ${platforms
                .map(
                  (platform) => `
                    <button
                      class="platform-rail__item ${activePlatform && platform.id === activePlatform.id ? "is-active" : ""}"
                      type="button"
                      data-platform-select="${platform.id}"
                    >
                      ${renderPlatformLogoMarkup(platform, "platform-rail__icon")}
                      <strong>${escapeHtml(platform.displayName)}</strong>
                    </button>
                  `
                )
                .join("")}
            </aside>
          </div>
        </section>

        <div class="catalog-layout public-catalog-layout">
          <section class="catalog-main">
            ${
              activePlatform
                ? `
                  <div class="catalog-hero catalog-hero--public">
                    <span class="catalog-hero__eyebrow">${escapeHtml(activePlatform.displayName)}</span>
                    <h2>${escapeHtml(activePlatform.description)}</h2>
                    <div class="catalog-hero__summary">
                      <span class="meta-chip">${escapeHtml(String(activePlatform.groups.length))}개 그룹</span>
                      <span class="meta-chip">${escapeHtml(String(activeProductCount))}개 카테고리</span>
                      <button class="meta-chip meta-chip--button" type="button" data-route="/help">이용 가이드</button>
                    </div>
                  </div>
                  ${activePlatform.groups
                    .map(
                      (group) => `
                        <section class="catalog-group">
                          <div class="section-head section-head--compact">
                            <h3>${escapeHtml(group.name)}</h3>
                            <p>${escapeHtml(group.description)}</p>
                            <div class="catalog-group__summary">
                              <span class="meta-chip">${escapeHtml(String(group.productCategories.length))}개 상품</span>
                            </div>
                          </div>
                          <div class="catalog-card-list">
                            ${group.productCategories
                              .map(
                                (category) => `
                                  <button class="catalog-card" type="button" data-route="/products/${category.id}">
                                    <div class="catalog-card__copy">
                                      <div class="catalog-card__title">
                                        <strong>${escapeHtml(category.name)}</strong>
                                        ${category.badge ? `<span class="mini-badge">${escapeHtml(category.badge)}</span>` : ""}
                                      </div>
                                      <p>${escapeHtml(category.description)}</p>
                                      <div class="catalog-card__meta">
                                        <span>${escapeHtml(category.startingPriceLabel)}부터</span>
                                        <span>${escapeHtml(String(category.optionCount))}개 옵션</span>
                                      </div>
                                    </div>
                                    <span class="catalog-card__arrow">›</span>
                                  </button>
                                `
                              )
                              .join("")}
                          </div>
                        </section>
                      `
                    )
                    .join("")}
                `
                : `
                  <div class="empty-card">
                    <span class="empty-card__eyebrow">NO RESULT</span>
                    <strong>검색 결과가 없습니다.</strong>
                    <p>다른 키워드로 다시 검색해 주세요.</p>
                    <button class="ghost-secondary-button" type="button" data-route="/help">상품 찾는 방법 보기</button>
                  </div>
                `
            }
          </section>
        </div>
      </div>
    `,
    "products"
  );
}

export function renderDetail(detail) {
  const {
    escapeHtml,
    formatMoney,
    formatNumber,
    ensureSelection,
    calculateSummary,
    getPreviewSource,
    getOrderValidationState,
    renderField,
    renderPreviewPanel,
    isLoggedIn,
  } = useRuntime();
  const summary = calculateSummary(detail);
  const selection = ensureSelection(detail);
  const selectedProduct = summary?.product;
  const values = selection?.fields || {};
  const template = selectedProduct?.formStructure?.template || {};
  const rules = selectedProduct?.formStructure?.schema || {};
  const previewSource = getPreviewSource(detail, selectedProduct);
  const orderValidation = getOrderValidationState(detail, selectedProduct);
  const loggedIn = isLoggedIn();

  return renderFrame(
    `
      <div class="page page-detail">
        <header class="topbar">
          <button class="icon-button" type="button" data-route="/products">‹</button>
          <strong class="topbar-title">${escapeHtml(detail.platform.displayName)}</strong>
          <button class="icon-button" type="button" data-route="/charge">₩</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="detail-hero-card">
          <div class="detail-hero-card__eyebrow">${escapeHtml(detail.group.name)}</div>
          <h1>${escapeHtml(detail.heroTitle)}</h1>
          <p>${escapeHtml(detail.heroSubtitle)}</p>
          <div class="detail-meta-row">
            <span class="meta-chip">${escapeHtml(detail.platform.displayName)}</span>
            ${
              selectedProduct?.badge
                ? `<span class="meta-chip meta-chip--accent">${escapeHtml(selectedProduct.badge)}</span>`
                : ""
            }
            <span class="meta-chip">${escapeHtml(selectedProduct?.estimatedTurnaround || "")}</span>
          </div>
          <div class="detail-hero-card__facts">
            <article class="detail-hero-card__fact">
              <span>판매가</span>
              <strong>${escapeHtml(selectedProduct?.priceLabel || "0원")}</strong>
            </article>
            <article class="detail-hero-card__fact">
              <span>예상 시작</span>
              <strong>${escapeHtml(selectedProduct?.estimatedTurnaround || "상품별 상이")}</strong>
            </article>
            <article class="detail-hero-card__fact">
              <span>정책 요약</span>
              <strong>${escapeHtml(detail.refundNotice?.[0] || "상품 정책 기준 적용")}</strong>
            </article>
          </div>
        </section>

        ${
          !loggedIn
            ? `
              <section class="content-section">
                <div class="detail-login-gate">
                  <div class="detail-login-gate__copy">
                    <strong>상품 확인 후 로그인하면 바로 주문을 이어갈 수 있습니다</strong>
                    <p>주문·충전·내역 확인은 고객 계정에서만 관리됩니다. 상품 탐색과 정책 확인은 로그인 없이 가능합니다.</p>
                  </div>
                  <button class="full-width-cta" type="button" data-route="/auth">로그인 / 회원가입</button>
                </div>
              </section>
            `
            : ""
        }

        ${
          detail.products.length > 1
            ? `
              <section class="content-section">
                <div class="section-head section-head--compact">
                  <h2>${escapeHtml(detail.optionLabelName || "옵션 선택")}</h2>
                  <p>레퍼런스의 옵션 칩 UI를 참고해 한 화면에서 바로 비교할 수 있게 구성했습니다.</p>
                </div>
                <div class="option-chip-row">
                  ${detail.products
                    .map(
                      (product) => `
                        <button
                          class="option-chip ${selectedProduct && product.id === selectedProduct.id ? "is-active" : ""}"
                          type="button"
                          data-option-select="${product.id}"
                          data-category-id="${detail.id}"
                        >
                          <strong>${escapeHtml(product.optionName || product.name)}</strong>
                          <span>${escapeHtml(product.priceLabel)}</span>
                        </button>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
            : ""
        }

        <section class="content-section">
          <div class="detail-trust-row">
            <article class="info-card">
              <strong>판매가</strong>
              <p>${escapeHtml(selectedProduct?.priceLabel || "0원")} ${selectedProduct?.priceStrategy === "fixed" ? "패키지" : `· 최소 ${formatNumber(selectedProduct?.minAmount || 0)}${escapeHtml(selectedProduct?.unitLabel || "개")}`}</p>
            </article>
            <article class="info-card">
              <strong>예상 소요시간</strong>
              <p>${escapeHtml(selectedProduct?.estimatedTurnaround || "상품별 상이 · 주문 후 순차 진행")}</p>
            </article>
            <article class="info-card">
              <strong>핵심 정책</strong>
              <p>${escapeHtml(detail.refundNotice?.[0] || "작업 시작 후 환불·취소 기준은 상품 정책을 따릅니다.")}</p>
            </article>
          </div>
        </section>

        <section class="content-section">
          <div class="section-head section-head--compact">
            <h2>주문 폼</h2>
            <p>${escapeHtml(detail.description)}</p>
          </div>
          <div class="detail-order-meta">
            <span class="meta-chip">${escapeHtml(selectedProduct?.priceStrategy === "fixed" ? "패키지형 상품" : "수량형 상품")}</span>
            <span class="meta-chip">${escapeHtml(selectedProduct?.estimatedTurnaround || "작업 시작 시점 상이")}</span>
            <button class="meta-chip meta-chip--button" type="button" data-route="/help">환불·정책 보기</button>
          </div>
          <form class="detail-form-card" id="order-form" data-order-form="${detail.id}">
            <div class="detail-form-layout ${previewSource ? "has-preview" : ""}">
              <div class="detail-form-layout__fields">
                <div class="guide-card detail-form-guide">
                  <strong>입력 전 확인</strong>
                  <p>링크 또는 계정 정보는 주문 직후 검수됩니다. 비공개 계정, 잘못된 URL, 삭제된 게시물은 작업이 지연되거나 반려될 수 있습니다.</p>
                </div>
                ${Object.entries(template)
                  .map(([key, entry]) => renderField(key, entry, rules[key], values))
                  .join("")}

                <div class="order-summary">
                  <div>
                    <span>예상 수량</span>
                    <strong id="summary-quantity">${escapeHtml(
                      selectedProduct?.priceStrategy === "fixed"
                        ? "패키지 1건"
                        : `${summary?.quantity || 0}${selectedProduct?.unitLabel || ""}`
                    )}</strong>
                  </div>
                  <div>
                    <span>예상 결제금액</span>
                    <strong id="summary-total">${escapeHtml(summary ? formatMoney(summary.total) : "0원")}</strong>
                  </div>
                </div>
                <p class="order-validation-note ${orderValidation.blocked ? "is-blocked" : ""}" data-order-validation-note ${orderValidation.reason ? "" : "hidden"}>
                  ${escapeHtml(orderValidation.blocked ? `현재 주문이 막힌 이유: ${orderValidation.reason || ""}` : orderValidation.reason || "")}
                </p>
              </div>

              ${
                previewSource
                  ? `<aside class="detail-form-layout__preview" data-preview-panel>${renderPreviewPanel(detail, selectedProduct)}</aside>`
                  : ""
              }
            </div>
          </form>
        </section>

        <section class="content-section two-column-mobile">
          <article class="info-card">
            <div class="section-head section-head--compact">
              <h2>주의사항</h2>
            </div>
            <ul class="bullet-list">
              ${detail.caution.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
            </ul>
          </article>
          <article class="info-card">
            <div class="section-head section-head--compact">
              <h2>환불 안내</h2>
            </div>
            <ul class="bullet-list">
              ${detail.refundNotice.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
            </ul>
          </article>
        </section>

        <section class="content-section">
          <div class="detail-support-card">
            <div>
              <strong>주문 전 확인이 더 필요하면 도움말 허브를 먼저 확인하세요</strong>
              <p>환불 기준, 충전 방식, 작업 지연 사유, 공지사항을 로그인 없이 볼 수 있습니다.</p>
            </div>
            <button class="ghost-secondary-button detail-support-card__button" type="button" data-route="/help">도움말 허브</button>
          </div>
        </section>

        <section class="content-section">
          <div class="section-head section-head--compact">
            <h2>서비스 설명</h2>
            <p>HTML 상세 설명 영역도 로컬 DB에서 읽어와 동일한 흐름으로 붙였습니다.</p>
          </div>
          <article class="html-card">${detail.serviceDescriptionHtml}</article>
        </section>

        ${
          detail.relatedCategories.length
            ? `
              <section class="content-section">
                <div class="section-head section-head--compact">
                  <h2>같은 그룹의 다른 상품</h2>
                </div>
                <div class="related-list">
                  ${detail.relatedCategories
                    .map(
                      (category) => `
                        <button class="related-card" type="button" data-route="/products/${category.id}">
                          <strong>${escapeHtml(category.name)}</strong>
                          <p>${escapeHtml(category.description)}</p>
                        </button>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
            : ""
        }
      </div>
    `,
    "products",
    `
      <div class="sticky-order-bar">
        <div class="sticky-order-bar__price">
          <span>총 결제금액</span>
          <strong id="sticky-total">${escapeHtml(summary ? formatMoney(summary.total) : "0원")}</strong>
        </div>
        <button class="sticky-order-bar__button" type="submit" form="order-form" data-order-submit-button ${orderValidation.blocked ? "disabled" : ""}>
          ${orderValidation.blocked ? "주문 불가" : loggedIn ? "주문하기" : "로그인 후 주문"}
        </button>
      </div>
    `
  );
}

export function renderCharge() {
  return renderChargePage(useRuntime(), renderFrame);
}

export function renderOrders() {
  const { state, escapeHtml, statusMap } = useRuntime();
  const activeFilter = state.ui.orderFilter;
  const visibleOrders =
    activeFilter === "all" ? state.orders : state.orders.filter((order) => order.status === activeFilter);

  return renderFrame(
    `
      <div class="page page-orders">
        <header class="topbar">
          <button class="icon-button" type="button" data-route="/">‹</button>
          <strong class="topbar-title">주문 내역</strong>
          <button class="icon-button" type="button" data-route="/products">＋</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="content-section">
          <div class="section-head">
            <h2>상태별 주문</h2>
            <p>접수, 진행, 완료 흐름이 한눈에 보이도록 카드형으로 정리했습니다.</p>
          </div>
          <div class="orders-summary-grid">
            <article class="info-card">
              <strong>전체 주문</strong>
              <p>${escapeHtml(String(state.orderCounts.all || 0))}건</p>
            </article>
            <article class="info-card">
              <strong>진행 중</strong>
              <p>${escapeHtml(String((state.orderCounts.queued || 0) + (state.orderCounts.in_progress || 0)))}건</p>
            </article>
          </div>
          <div class="filter-row">
            ${[
              ["all", `전체 ${state.orderCounts.all}`],
              ["queued", `대기 ${state.orderCounts.queued}`],
              ["in_progress", `진행 ${state.orderCounts.in_progress}`],
              ["completed", `완료 ${state.orderCounts.completed}`],
            ]
              .map(
                ([key, label]) => `
                  <button class="filter-chip ${activeFilter === key ? "is-active" : ""}" type="button" data-order-filter="${key}">
                    ${escapeHtml(label)}
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="order-list">
            ${visibleOrders.length
              ? visibleOrders
                  .map((order) => {
                    const status = statusMap[order.status] || statusMap.queued;
                    return `
                      <article class="order-card">
                        <div class="order-card__top">
                          <div>
                            <span class="order-card__platform">${escapeHtml(order.platformIcon)} ${escapeHtml(order.platformName)}</span>
                            <strong>${escapeHtml(order.productName)}</strong>
                          </div>
                          <span class="status-pill ${status.className}">${escapeHtml(status.label)}</span>
                        </div>
                        <p class="order-card__target">${escapeHtml(order.targetValue || "입력 정보 없음")}</p>
                        <div class="order-card__meta">
                          <span>${escapeHtml(order.optionName || "기본 옵션")}</span>
                          <span>${escapeHtml(order.totalPriceLabel)}</span>
                          <span>${escapeHtml(order.createdLabel)}</span>
                        </div>
                        ${
                          order.notes.memo
                            ? `<div class="order-card__note">요청 메모: ${escapeHtml(order.notes.memo)}</div>`
                            : ""
                        }
                      </article>
                    `;
                  })
                  .join("")
              : `
                <article class="empty-card">
                  <strong>${activeFilter === "all" ? "주문 내역이 아직 없습니다." : "이 상태의 주문이 없습니다."}</strong>
                  <p>서비스를 탐색한 뒤 첫 주문을 생성하거나, 필터를 바꿔 다른 상태의 주문을 확인해 주세요.</p>
                  <button class="full-width-cta" type="button" data-route="/products">서비스 둘러보기</button>
                </article>
              `}
          </div>
        </section>
      </div>
    `,
    "orders"
  );
}

export function renderMy() {
  const { state, escapeHtml, formatNumber } = useRuntime();
  const data = state.bootstrap;
  return renderFrame(
    `
      <div class="page page-my">
        <header class="topbar">
          <button class="icon-button" type="button" data-route="/">‹</button>
          <strong class="topbar-title">마이</strong>
          <button class="icon-button" type="button" data-public-logout>⇥</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="profile-card">
          <div class="profile-card__avatar">${escapeHtml(data.user.avatarLabel)}</div>
          <div class="profile-card__copy">
            <strong>${escapeHtml(data.user.name)}</strong>
            <p>${escapeHtml(data.user.emailMasked || "이메일 비공개")}</p>
            <span>${escapeHtml(data.user.tier)} · 보유 캐시 ${escapeHtml(data.user.balanceLabel)}</span>
          </div>
        </section>

        <section class="content-section">
          <div class="my-summary-grid">
            <article class="info-card">
              <strong>보유 잔액</strong>
              <p>${escapeHtml(data.user.balanceLabel)}</p>
            </article>
            <article class="info-card">
              <strong>누적 주문</strong>
              <p>${escapeHtml(formatNumber(state.orderCounts.all || 0))}건</p>
            </article>
            <article class="info-card">
              <strong>회원 등급</strong>
              <p>${escapeHtml(data.user.tier)}</p>
            </article>
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>바로가기</h2>
            <p>주문과 계정 관리에 필요한 메뉴만 모았습니다.</p>
          </div>
          <div class="support-grid support-grid--account">
            <article class="support-card">
              <span class="support-card__icon">₩</span>
              <strong>보유 잔액</strong>
              <p>${escapeHtml(data.user.balanceLabel)}</p>
            </article>
            <article class="support-card">
              <span class="support-card__icon">◎</span>
              <strong>누적 주문</strong>
              <p>${escapeHtml(formatNumber(state.orderCounts.all || 0))}건</p>
            </article>
            <button class="support-card" type="button" data-route="/orders">
              <span class="support-card__icon">→</span>
              <strong>주문 내역 보기</strong>
              <p>진행 상태, 주문 메모, 결제 금액을 확인합니다.</p>
            </button>
            <button class="support-card" type="button" data-route="/help">
              <span class="support-card__icon">?</span>
              <strong>도움말 허브</strong>
              <p>FAQ, 공지, 이용 가이드, 상담 안내로 이동합니다.</p>
            </button>
          </div>
        </section>

        <section class="content-section footer-section">
          <button class="full-width-cta" type="button" data-route="/help">도움말 허브로 이동</button>
        </section>
      </div>
    `,
    "my"
  );
}

export function renderHelp() {
  const { state, escapeHtml } = useRuntime();
  return renderFrame(renderHelpMarkup({ data: state.bootstrap, escapeHtml }), "home");
}

export function renderLegalPage(documentKey) {
  const { state, escapeHtml, renderNotFound } = useRuntime();
  const documentItem = (state.bootstrap?.legalDocuments || []).find((item) => item.key === documentKey);
  if (!documentItem) {
    return renderNotFound("약관 또는 정책 문서를 찾지 못했습니다.");
  }
  return renderFrame(renderLegalPageMarkup({ documentItem, escapeHtml }), "home");
}
