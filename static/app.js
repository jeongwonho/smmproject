import {
  configurePublicPages,
  renderAuthPage,
  renderHome,
  renderProducts,
  renderDetail,
  renderCharge,
  renderOrders,
  renderMy,
  renderHelp,
  renderLegalPage,
  renderFrame,
} from "./public/pages.js";
import {
  configureAdminPages,
  renderAdminAuth,
  renderAdmin,
} from "./admin/pages.js";
import { parseRoute } from "./shared/routes.js";
import { createRuntimeConfig } from "./shared/runtime.js";
import { blankPublicAuthState, blankSignupState, evaluatePublicPasswordStrength } from "./public/auth-state.js";

const DEFAULT_LIGHT_BRAND_LOGO_URL = "/static/assets/instamart-logo-light-bg.png";

const app = document.querySelector("#app");
const toast = document.querySelector("#toast");

const state = {
  bootstrap: null,
  publicCsrfToken: "",
  publicAuth: blankPublicAuthState(),
  catalog: [],
  categoryCache: {},
  orders: [],
  orderCounts: { all: 0, queued: 0, in_progress: 0, completed: 0 },
  transactions: [],
  wallet: null,
  walletLedger: [],
  chargeOrders: [],
  chargeDraft: null,
  adminBootstrap: null,
  adminSession: null,
  adminCsrfToken: "",
  adminSupplierServices: {},
  adminCustomerDetails: {},
  adminSiteSettingsDraft: null,
  adminPopupDraft: null,
  adminHomeBannerDraft: null,
  adminPlatformSectionDraft: null,
  adminSupplierDraft: null,
  adminConnectionResult: null,
  adminCustomerDraft: null,
  adminCategoryDraft: null,
  adminProductDraft: null,
  productSelections: {},
  linkPreviews: {},
  ui: {
    search: "",
    activePlatform: "",
    orderFilter: "all",
    chargeTab: "create",
    chargeHistoryMode: "chargeOrders",
    chargeStatusFilter: "all",
    chargeMethodFilter: "all",
    chargePeriodFilter: "all",
    chargeDetailKind: "",
    chargeDetailId: "",
    chargeDetailOpen: false,
    bannerIndex: 0,
    homeFooterExpanded: false,
    loginModalOpen: false,
    authTab: "login",
    loginRedirect: "",
    adminActiveSection: "overview",
    adminAnalyticsTab: "dashboard",
    adminAnalyticsRange: "30d",
    adminCustomerFilter: "all",
    adminCustomerSearch: "",
    adminSupplierMode: "edit",
    adminSelectedPlatformSectionId: "",
    adminSelectedSupplierId: "",
    adminSelectedProductId: "",
    adminSelectedSupplierServiceId: "",
    adminServiceSearch: "",
    adminCustomerMode: "edit",
    adminSelectedCustomerId: "",
    adminSelectedHomeBannerId: "",
    adminCategoryMode: "edit",
    adminSelectedCategoryId: "",
    adminProductMode: "edit",
    adminSelectedManageProductId: "",
    adminOrderFilter: "all",
    adminOrderSearch: "",
    closedPopups: {},
  },
};

let bannerIntervalId = null;
let previewSequence = 0;
let adminSectionObserver = null;
let lastTrackedPublicPath = "";
let previousPublicPath = "";
let fallbackVisitorId = "";
let fallbackSessionId = "";
const previewTimers = {};

const runtimeConfig = createRuntimeConfig(document, window);

const statusMap = {
  queued: { label: "접수 대기", className: "is-queued" },
  in_progress: { label: "진행 중", className: "is-progress" },
  completed: { label: "완료", className: "is-complete" },
};

const navItems = [
  { route: "/", key: "home", label: "홈", icon: "⌂" },
  { route: "/products", key: "products", label: "주문", icon: "▦" },
  { route: "/charge", key: "charge", label: "충전", icon: "₩" },
  { route: "/orders", key: "orders", label: "내역", icon: "◎" },
  { route: "/my", key: "my", label: "마이", icon: "☻" },
];

const DEFAULT_HOME_BANNER_ASSETS = {
  banner_launch: "/static/assets/home-banner-launch.jpg",
  banner_safe: "/static/assets/home-banner-safe.jpg",
  banner_consult: "/static/assets/home-banner-consult.jpg",
};
const DEFAULT_SITE_NAME = "인스타마트";

const adminSectionBlueprints = [
  { id: "overview", label: "대시보드", icon: "⌂", description: "운영 요약과 핵심 지표", title: "운영 대시보드", summary: "전체 운영 현황과 빠른 실행 메뉴를 한 곳에서 확인합니다." },
  { id: "analytics", label: "통계", icon: "▥", description: "매출, 방문, 유입, 재구매", title: "통계 분석 센터", summary: "매출, 방문자, 유입 경로, 재구매 흐름을 하나의 워크스페이스에서 분석합니다." },
  { id: "settings", label: "기본 설정", icon: "⚙", description: "사이트명, 메타, 파비콘", title: "사이트 기본 설정", summary: "사이트 이름, 설명, 메일·SMS 표기, 파비콘, 대표 이미지를 실제 사이트에 반영합니다." },
  { id: "popup", label: "팝업/노출", icon: "▣", description: "메인 팝업 노출 관리", title: "홈 노출 관리", summary: "메인 팝업과 홈 프로모션 노출을 관리합니다." },
  { id: "suppliers", label: "공급사", icon: "⇄", description: "API 연결과 서비스 동기화", title: "공급사 연동 센터", summary: "공급사 API 연결, 서비스 동기화, 상품 매핑을 운영합니다." },
  { id: "customers", label: "회원정보", icon: "☻", description: "계정, 잔액, 운영 메모", title: "고객/계정 관리", summary: "회원 계정, 등급, 잔액, 내부 운영 메모를 관리합니다." },
  { id: "catalog", label: "상품관리", icon: "▤", description: "카테고리와 상품 편집", title: "카탈로그 관리", summary: "카테고리와 상품 편집, 정렬, 판매 노출 상태를 관리합니다." },
  { id: "orders", label: "주문통제", icon: "◎", description: "상태 변경과 처리 메모", title: "주문 운영 센터", summary: "주문 상태 변경과 운영 메모를 기록하고 처리 현황을 추적합니다." },
];
const adminSectionIdSet = new Set(adminSectionBlueprints.map((section) => section.id));
const analyticsTabBlueprints = [
  { id: "dashboard", label: "전체 대시보드", description: "핵심 KPI와 종합 추이" },
  { id: "sales", label: "매출 분석", description: "매출, 객단가, 상품/플랫폼별 분석" },
  { id: "visitors", label: "방문자 분석", description: "방문자, 페이지뷰, 디바이스 분석" },
  { id: "sources", label: "유입/경로", description: "유입 사이트, 검색어, 이동 경로 분석" },
  { id: "repurchase", label: "재구매 분석", description: "반복 구매율과 충성 고객 분석" },
];
const advancedOrderFieldBlueprints = {
  runs: { label: "반복 횟수", description: "드립피드/반복 실행 서비스용" },
  interval: { label: "실행 간격", description: "반복 간격(분) 입력" },
  delay: { label: "지연 시간", description: "시작 지연 또는 게시 간격" },
  expiry: { label: "종료일", description: "구독/기간형 서비스 종료일" },
  min: { label: "최소 수량", description: "구독형 최소 목표 수량" },
  max: { label: "최대 수량", description: "구독형 최대 목표 수량" },
  posts: { label: "게시물 수", description: "대상 게시물 개수" },
  oldPosts: { label: "기존 게시물 수", description: "과거 게시물 기준 옵션" },
  comments: { label: "댓글 목록", description: "커스텀 댓글 한 줄씩 입력" },
  answerNumber: { label: "투표 답변 번호", description: "Poll 서비스 응답 번호" },
  country: { label: "국가 코드", description: "지역/국가 타겟 설정" },
  device: { label: "디바이스", description: "Mobile, Desktop 등" },
  typeOfTraffic: { label: "트래픽 타입", description: "유입/트래픽 유형 지정" },
  googleKeyword: { label: "검색 키워드", description: "검색 노출/트래픽 키워드" },
};
const advancedOrderFieldKeys = Object.keys(advancedOrderFieldBlueprints);

function normalizeAdminSectionId(sectionId) {
  const normalized = String(sectionId || "").trim().toLowerCase();
  return adminSectionIdSet.has(normalized) ? normalized : "overview";
}

function adminSectionPath(sectionId = "overview") {
  const normalized = normalizeAdminSectionId(sectionId);
  return normalized === "overview" ? "/admin" : `/admin/${encodeURIComponent(normalized)}`;
}
const analyticsRangeBlueprints = [
  { id: "7d", label: "최근 7일", days: 7 },
  { id: "30d", label: "최근 30일", days: 30 },
  { id: "90d", label: "최근 90일", days: 90 },
];

function blankChargeDraft(chargeConfig = state.bootstrap?.chargeConfig || {}) {
  const defaultMethod =
    (chargeConfig.methods || []).find((method) => method.id === "bank_transfer" && method.enabled)?.id ||
    (chargeConfig.methods || []).find((method) => method.enabled)?.id ||
    "card";
  return {
    amountInput: "",
    amount: 0,
    paymentChannel: defaultMethod,
    paymentMethodDetail: "general_card",
    depositorName: "",
    receiptType: "none",
    receiptPayload: {
      phoneNumber: "",
      businessNumber: "",
      purpose: "personal",
      businessName: "",
      recipientEmail: "",
      contactName: "",
    },
    agreementChecked: false,
    submitting: false,
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function ensureMetaTag(name) {
  let meta = document.querySelector(`meta[name="${name}"]`);
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute("name", name);
    document.head.appendChild(meta);
  }
  return meta;
}

function ensurePropertyMetaTag(property) {
  let meta = document.querySelector(`meta[property="${property}"]`);
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute("property", property);
    document.head.appendChild(meta);
  }
  return meta;
}

function ensureManagedLinkTag(key, rel) {
  let link = document.querySelector(`link[data-managed-head="${key}"]`);
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("data-managed-head", key);
    document.head.appendChild(link);
  }
  link.setAttribute("rel", rel);
  return link;
}

function clearManagedHeadTag(selector) {
  document.querySelectorAll(selector).forEach((node) => node.remove());
}

function formatMoney(value) {
  return `${Number(value || 0).toLocaleString("ko-KR")}원`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function formatCompactNumber(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) return "0";
  if (Math.abs(numeric) >= 100000000) return `${(numeric / 100000000).toFixed(1).replace(/\.0$/, "")}억`;
  if (Math.abs(numeric) >= 10000) return `${(numeric / 10000).toFixed(1).replace(/\.0$/, "")}만`;
  return formatNumber(numeric);
}

function formatPercent(value, digits = 1) {
  return `${Number(value || 0).toFixed(digits)}%`;
}

function parseCurrencyInput(rawValue) {
  const normalized = String(rawValue || "").replace(/[^\d]/g, "");
  return normalized ? Number(normalized) : 0;
}

function formatCurrencyInput(rawValue) {
  const amount = parseCurrencyInput(rawValue);
  return amount ? Number(amount).toLocaleString("ko-KR") : "";
}

function ensureChargeDraft() {
  if (!state.chargeDraft) {
    state.chargeDraft = blankChargeDraft();
  }
  return state.chargeDraft;
}

function chargeMethodConfig(methodId) {
  return (state.bootstrap?.chargeConfig?.methods || []).find((method) => method.id === methodId) || null;
}

function chargeAmountSummary(amount) {
  const normalized = Math.max(0, parseCurrencyInput(amount));
  const vat = Math.floor(normalized / 10);
  const total = normalized + vat;
  const current = Number(state.wallet?.availableBalance || state.bootstrap?.user?.balance || 0);
  return {
    amount: normalized,
    vat,
    total,
    expectedBalance: current + normalized,
  };
}

function filteredChargeOrders() {
  const range = state.ui.chargePeriodFilter;
  const status = state.ui.chargeStatusFilter;
  const method = state.ui.chargeMethodFilter;
  const now = new Date();
  const minimumTime = (() => {
    if (range === "7d") return now.getTime() - 7 * 24 * 60 * 60 * 1000;
    if (range === "30d") return now.getTime() - 30 * 24 * 60 * 60 * 1000;
    if (range === "90d") return now.getTime() - 90 * 24 * 60 * 60 * 1000;
    return 0;
  })();
  return (state.chargeOrders || []).filter((item) => {
    if (status !== "all" && item.status !== status) return false;
    if (method !== "all" && item.paymentChannel !== method) return false;
    if (minimumTime) {
      const createdAt = Date.parse(item.createdAt || "");
      if (Number.isFinite(createdAt) && createdAt < minimumTime) return false;
    }
    return true;
  });
}

function filteredWalletEntries() {
  const range = state.ui.chargePeriodFilter;
  const method = state.ui.chargeMethodFilter;
  const now = new Date();
  const minimumTime = (() => {
    if (range === "7d") return now.getTime() - 7 * 24 * 60 * 60 * 1000;
    if (range === "30d") return now.getTime() - 30 * 24 * 60 * 60 * 1000;
    if (range === "90d") return now.getTime() - 90 * 24 * 60 * 60 * 1000;
    return 0;
  })();
  return (state.walletLedger || []).filter((item) => {
    if (method !== "all" && item.paymentChannel !== method) return false;
    if (minimumTime) {
      const createdAt = Date.parse(item.createdAt || "");
      if (Number.isFinite(createdAt) && createdAt < minimumTime) return false;
    }
    return true;
  });
}

function openChargeDetail(kind, id) {
  state.ui.chargeDetailKind = kind;
  state.ui.chargeDetailId = id;
  state.ui.chargeDetailOpen = Boolean(kind && id);
}

function closeChargeDetail() {
  state.ui.chargeDetailKind = "";
  state.ui.chargeDetailId = "";
  state.ui.chargeDetailOpen = false;
}

function analyticsRangeDays(rangeId = state.ui.adminAnalyticsRange) {
  return analyticsRangeBlueprints.find((item) => item.id === rangeId)?.days || 30;
}

function analyticsWindow() {
  return getAdminAnalytics()?.windows?.[state.ui.adminAnalyticsRange] || null;
}

function analyticsDailySeries() {
  const analytics = getAdminAnalytics();
  const days = analyticsRangeDays();
  return (analytics?.dailyOverview || []).slice(-days);
}

function adminSectionItems(stats = {}, popup = null) {
  const siteSettings = state.adminBootstrap?.siteSettings || state.bootstrap?.siteSettings || null;
  return adminSectionBlueprints.map((section) => {
    let stat = "";
    if (section.id === "overview") stat = `${Number(stats.orderCount || 0)}건`;
    if (section.id === "analytics") stat = `${formatCompactNumber(stats.visitorCount || 0)}명`;
    if (section.id === "settings") stat = siteSettings?.siteName || "설정";
    if (section.id === "popup") stat = popup?.isActive ? "노출중" : "꺼짐";
    if (section.id === "suppliers") stat = `${Number(stats.supplierCount || 0)}개`;
    if (section.id === "customers") stat = `${Number(stats.customerCount || 0)}명`;
    if (section.id === "catalog") stat = `${Number(stats.productCount || 0)}개`;
    if (section.id === "orders") stat = `${Number(stats.orderCount || 0)}건`;
    return { ...section, stat };
  });
}

function getAdminSectionConfig(sectionId = state.ui.adminActiveSection) {
  return adminSectionBlueprints.find((section) => section.id === sectionId) || adminSectionBlueprints[0];
}

function blankSupplierDraft() {
  return {
    id: "",
    name: "",
    apiUrl: "",
    integrationType: "classic",
    apiKey: "",
    hasApiKey: false,
    apiKeyMasked: "",
    bearerToken: "",
    hasBearerToken: false,
    bearerTokenMasked: "",
    supportsBalanceCheck: true,
    supportsAutoDispatch: true,
    notes: "",
    isActive: true,
  };
}

function blankPopupDraft() {
  return {
    id: "",
    name: "홈 프로모션 팝업",
    badgeText: "",
    title: "",
    description: "",
    imageUrl: "",
    imageName: "",
    imageUrlInput: "",
    route: "/products/cat_youtube_views",
    theme: "coral",
    isActive: false,
  };
}

function blankSiteSettingsDraft() {
  return {
    siteName: "",
    siteDescription: "",
    useMailSmsSiteName: false,
    mailSmsSiteName: "",
    headerLogoUrl: "",
    headerLogoName: "",
    headerLogoUrlInput: "",
    faviconUrl: "",
    faviconName: "",
    faviconUrlInput: "",
    shareImageUrl: "",
    shareImageName: "",
    shareImageUrlInput: "",
  };
}

function blankHomeBannerDraft() {
  return {
    id: "",
    title: "",
    subtitle: "",
    ctaLabel: "바로 보기",
    route: "/products",
    imageUrl: "",
    imageName: "",
    imageUrlInput: "",
    theme: "blue",
    isActive: true,
    sortOrder: 0,
  };
}

function blankPlatformSectionDraft() {
  return {
    id: "",
    slug: "",
    displayName: "",
    description: "",
    icon: "●",
    logoImageUrl: "",
    logoImageName: "",
    logoImageUrlInput: "",
    accentColor: "#4c76ff",
    sortOrder: 0,
  };
}

function siteSettingsToDraft(siteSettings) {
  if (!siteSettings) return blankSiteSettingsDraft();
  const headerLogoUrl = siteSettings.headerLogoUrl || "";
  const faviconUrl = siteSettings.faviconUrl || "";
  const shareImageUrl = siteSettings.shareImageUrl || "";
  return {
    siteName: siteSettings.siteName || "",
    siteDescription: siteSettings.siteDescription || "",
    useMailSmsSiteName: Boolean(siteSettings.useMailSmsSiteName),
    mailSmsSiteName: siteSettings.mailSmsSiteName || "",
    headerLogoUrl,
    headerLogoName: "",
    headerLogoUrlInput: headerLogoUrl && !String(headerLogoUrl).startsWith("data:image/") ? headerLogoUrl : "",
    faviconUrl,
    faviconName: "",
    faviconUrlInput: faviconUrl && !String(faviconUrl).startsWith("data:image/") ? faviconUrl : "",
    shareImageUrl,
    shareImageName: "",
    shareImageUrlInput: shareImageUrl && !String(shareImageUrl).startsWith("data:image/") ? shareImageUrl : "",
  };
}

function getEffectiveMailSmsSiteName(siteSettings) {
  const siteName = String(siteSettings?.siteName || "").trim();
  const customName = String(siteSettings?.mailSmsSiteName || "").trim();
  if (siteSettings?.useMailSmsSiteName && customName) return customName;
  return siteName;
}

function siteSettingsPreviewPayload(siteSettings) {
  const draft = siteSettings || blankSiteSettingsDraft();
  return {
    siteName: draft.siteName || "사이트 이름",
    siteDescription: draft.siteDescription || "사이트를 대표하는 설명을 입력하면 브라우저 탭과 공유 미리보기에 반영됩니다.",
    useMailSmsSiteName: Boolean(draft.useMailSmsSiteName),
    mailSmsSiteName: draft.mailSmsSiteName || "",
    effectiveMailSmsSiteName: getEffectiveMailSmsSiteName(draft) || "사이트 이름",
    headerLogoUrl: draft.headerLogoUrl || "",
    faviconUrl: draft.faviconUrl || "",
    shareImageUrl: draft.shareImageUrl || "",
  };
}

function popupToDraft(popup) {
  if (!popup) return blankPopupDraft();
  return {
    id: popup.id || "",
    name: popup.name || "홈 프로모션 팝업",
    badgeText: popup.badgeText || "",
    title: popup.title || "",
    description: popup.description || "",
    imageUrl: popup.imageUrl || "",
    imageName: "",
    imageUrlInput: popup.imageUrl && !String(popup.imageUrl).startsWith("data:image/") ? popup.imageUrl : "",
    route: popup.route || "/",
    theme: popup.theme || "coral",
    isActive: Boolean(popup.isActive),
  };
}

function homeBannerToDraft(banner) {
  if (!banner) return blankHomeBannerDraft();
  return {
    id: banner.id || "",
    title: banner.title || "",
    subtitle: banner.subtitle || "",
    ctaLabel: banner.ctaLabel || "바로 보기",
    route: banner.route || "/",
    imageUrl: banner.imageUrl || "",
    imageName: "",
    imageUrlInput: banner.imageUrl && !String(banner.imageUrl).startsWith("data:image/") ? banner.imageUrl : "",
    theme: banner.theme || "blue",
    isActive: Boolean(banner.isActive),
    sortOrder: Number(banner.sortOrder || 0),
  };
}

function platformSectionToDraft(platformSection) {
  if (!platformSection) return blankPlatformSectionDraft();
  const logoImageUrl = platformSection.logoImageUrl || "";
  return {
    id: platformSection.id || "",
    slug: platformSection.slug || "",
    displayName: platformSection.displayName || "",
    description: platformSection.description || "",
    icon: platformSection.icon || "●",
    logoImageUrl,
    logoImageName: "",
    logoImageUrlInput: logoImageUrl && !String(logoImageUrl).startsWith("data:image/") ? logoImageUrl : "",
    accentColor: platformSection.accentColor || "#4c76ff",
    sortOrder: Number(platformSection.sortOrder || 0),
  };
}

function popupPreviewPayload(popup) {
  return {
    id: popup?.id || "preview",
    badgeText: popup?.badgeText || "",
    title: popup?.title || "유튜브 상위노출\n서비스 출시!",
    description: popup?.description || "",
    imageUrl: popup?.imageUrl || "",
    route: popup?.route || "/",
    theme: popup?.theme || "coral",
    isActive: Boolean(popup?.isActive),
  };
}

function svgToDataUrl(svgMarkup) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svgMarkup)}`;
}

function defaultHomeBannerImageUrl(bannerId = "", theme = "blue") {
  const explicit = DEFAULT_HOME_BANNER_ASSETS[String(bannerId || "").trim()];
  if (explicit) return explicit;
  const fallbackByTheme = {
    blue: DEFAULT_HOME_BANNER_ASSETS.banner_launch,
    mint: DEFAULT_HOME_BANNER_ASSETS.banner_safe,
    dark: DEFAULT_HOME_BANNER_ASSETS.banner_consult,
  };
  return fallbackByTheme[String(theme || "blue").trim().toLowerCase()] || DEFAULT_HOME_BANNER_ASSETS.banner_launch;
}

function resolveHomeBannerImageUrl(banner) {
  const explicitUrl = String(banner?.imageUrl || "").trim();
  if (explicitUrl) return explicitUrl;
  return defaultHomeBannerImageUrl(banner?.id, banner?.theme);
}

function renderPlatformLogoMarkup(platform, className) {
  const accentColor = escapeHtml(platform?.accentColor || "#4c76ff");
  const logoImageUrl = String(platform?.logoImageUrl || "").trim();
  if (logoImageUrl) {
    return `
      <span class="${className} is-image" style="--platform-accent:${accentColor}">
        <img src="${escapeHtml(logoImageUrl)}" alt="${escapeHtml(platform?.displayName || "")}" loading="lazy" />
      </span>
    `;
  }
  return `<span class="${className}" style="--platform-accent:${accentColor}">${escapeHtml(platform?.icon || "●")}</span>`;
}

function getActiveHomeBanners() {
  return (state.bootstrap?.banners || []).filter((banner) => banner.isActive !== false);
}

function setHomeBannerIndex(nextIndex, { render = false } = {}) {
  const banners = getActiveHomeBanners();
  if (!banners.length) {
    state.ui.bannerIndex = 0;
    return;
  }
  const total = banners.length;
  const normalized = ((Number(nextIndex) || 0) % total + total) % total;
  state.ui.bannerIndex = normalized;

  if (render || getRoute().name !== "home") {
    renderRoute();
    return;
  }

  const track = document.querySelector("[data-home-banner-track]");
  if (track) {
    track.style.transform = `translateX(-${normalized * 100}%)`;
  }
  document.querySelectorAll("[data-banner-index]").forEach((button, index) => {
    button.classList.toggle("is-active", index === normalized);
  });
}

function updateHomePlatformScrollerState(scroller = document.querySelector("[data-home-platform-scroller]")) {
  if (!scroller) return;
  const stack = scroller.closest("[data-home-platform-stack]");
  const fade = stack?.querySelector("[data-home-platform-fade]");
  const hint = stack?.querySelector("[data-home-platform-hint]");
  const remaining = Math.max(0, scroller.scrollHeight - scroller.clientHeight - scroller.scrollTop);
  const isScrollable = scroller.scrollHeight - scroller.clientHeight > 12;
  const isEnd = remaining <= 6;
  scroller.classList.toggle("is-scrollable", isScrollable);
  scroller.classList.toggle("is-end", isEnd);
  if (fade) fade.hidden = !isScrollable || isEnd;
  if (hint) hint.hidden = !isScrollable || isEnd;
}

function getHomePlatformScroller(target) {
  if (!(target instanceof Element)) return null;
  return target.closest("[data-home-platform-scroller]");
}

function homePlatformScrollerAtBoundary(scroller, deltaY) {
  if (!scroller || !deltaY) return false;
  const maxScrollTop = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
  if (deltaY > 0) {
    return scroller.scrollTop >= maxScrollTop - 2;
  }
  return scroller.scrollTop <= 2;
}

function relayHomePlatformScroll(scroller, deltaY) {
  const pageScroller = document.scrollingElement || document.documentElement;
  if (!pageScroller || !deltaY) return;
  pageScroller.scrollTop += deltaY;
  updateHomePlatformScrollerState(scroller);
}

const homePlatformTouchState = {
  scroller: null,
  lastY: 0,
};

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("이미지 파일을 읽지 못했습니다."));
    reader.readAsDataURL(file);
  });
}

function supplierToDraft(supplier) {
  if (!supplier) return blankSupplierDraft();
  return {
    id: supplier.id || "",
    name: supplier.name || "",
    apiUrl: supplier.apiUrl || "",
    integrationType: supplier.integrationType || "classic",
    apiKey: "",
    hasApiKey: Boolean(supplier.hasApiKey),
    apiKeyMasked: supplier.apiKeyMasked || "",
    bearerToken: "",
    hasBearerToken: Boolean(supplier.hasBearerToken),
    bearerTokenMasked: supplier.bearerTokenMasked || "",
    supportsBalanceCheck: supplier.supportsBalanceCheck !== false,
    supportsAutoDispatch: supplier.supportsAutoDispatch !== false,
    notes: supplier.notes || "",
    isActive: Boolean(supplier.isActive),
  };
}

function supplierApiKeyLabel(integrationType) {
  return integrationType === "mkt24" ? "x-api-key" : "API Key";
}

function supplierApiKeyPlaceholder(integrationType, hasId) {
  if (hasId) {
    return integrationType === "mkt24" ? "새 x-api-key 입력 시에만 변경됩니다." : "새 키 입력 시에만 변경됩니다.";
  }
  return integrationType === "mkt24" ? "공급사 x-api-key" : "공급사 API Key";
}

function supplierUrlPlaceholder(integrationType) {
  return integrationType === "mkt24" ? "https://api.mkt24.co.kr/v3 또는 전체 products/sns URL" : "https://example.com/api/v2";
}

function supplierConnectionGuide(integrationType) {
  if (integrationType === "mkt24") {
    return {
      status: "서비스 목록 조회가 성공하면 연결된 것으로 처리됩니다.",
      balance: "이 연동 방식은 잔액 API가 문서화되지 않아 서비스 수만 확인합니다.",
      dispatch: "현재는 서비스 동기화까지만 지원하고, 자동 발주는 주문 API 문서가 들어오면 연결합니다.",
    };
  }
  return {
    status: "잔액 조회와 서비스 목록 조회가 모두 성공해야 연결 확인으로 처리됩니다.",
    balance: "공급사 응답의 balance / currency 값을 그대로 표시합니다.",
    dispatch: "",
  };
}

function formPresetLabel(preset) {
  const labels = {
    account_quantity: "계정 ID + 수량",
    url_quantity: "URL + 수량",
    keyword_url: "키워드 + URL + 수량",
    package: "계정 패키지형",
    url_package: "URL 패키지형",
    custom: "맞춤 문의형",
  };
  return labels[preset] || preset || "-";
}

function supplierGuideFieldDefinitions(recommendation = {}) {
  const fields = [];
  const preset = String(recommendation.formPreset || "").trim();
  const targetPlaceholder = recommendation.targetPlaceholder || "";
  const quantityLabel = recommendation.quantityLabel || "수량";
  const unitLabel = recommendation.unitLabel || "개";

  const pushField = (key, label, placeholder = "", detail = "", required = true) => {
    fields.push({ key, label, placeholder, detail, required });
  };

  if (preset === "keyword_url") {
    pushField("targetKeyword", "키워드", "예: 강남 필라테스", "검색/유입형 서비스용", true);
    pushField("targetUrl", recommendation.targetLabel || "랜딩 URL", targetPlaceholder, "유입을 보낼 최종 페이지", true);
  } else if (preset === "account_quantity" || preset === "package") {
    pushField("targetValue", recommendation.targetLabel || "계정(ID)", targetPlaceholder, "계정 아이디 또는 채널명", true);
  } else if (preset === "url_quantity" || preset === "url_package") {
    pushField("targetUrl", recommendation.targetLabel || "링크", targetPlaceholder, "게시물/영상/프로필 링크", true);
  } else if (preset === "custom") {
    pushField("targetValue", recommendation.targetLabel || "희망 채널", targetPlaceholder || "예: 스레드, 블로그, 기타 SNS", "운영자가 수동 검토할 입력값", true);
  }

  if (preset === "account_quantity" || preset === "url_quantity") {
    pushField("orderedCount", quantityLabel, `${recommendation.minAmount || 1}`, `${quantityLabel} · ${formatNumber(recommendation.minAmount || 1)}~${formatNumber(recommendation.maxAmount || recommendation.minAmount || 1)} ${unitLabel}`, true);
  }
  if (preset === "keyword_url") {
    pushField("orderedCount", quantityLabel, `${recommendation.minAmount || 1}`, `${quantityLabel} · ${formatNumber(recommendation.minAmount || 1)}~${formatNumber(recommendation.maxAmount || recommendation.minAmount || 1)} ${unitLabel}`, true);
  }

  if (["account_quantity", "url_quantity", "package", "url_package", "custom"].includes(preset)) {
    pushField("contactPhone", "연락처", "01012345678", "고객 확인 또는 운영 연락용", false);
  }

  (recommendation.advancedFieldKeys || []).forEach((fieldKey) => {
    const blueprint = advancedOrderFieldBlueprints[fieldKey];
    if (!blueprint) return;
    pushField(fieldKey, blueprint.label, "", blueprint.description, false);
  });

  return fields;
}

function blankCustomerDraft() {
  return {
    id: "",
    name: "",
    email: "",
    password: "",
    phone: "",
    tier: "STANDARD",
    role: "customer",
    notes: "",
    isActive: true,
  };
}

function customerToDraft(customer) {
  if (!customer) return blankCustomerDraft();
  return {
    id: customer.id || "",
    name: customer.name || "",
    email: customer.email || "",
    password: "",
    phone: customer.phone || "",
    tier: customer.tier || "STANDARD",
    role: customer.role || "customer",
    notes: customer.notes || "",
    isActive: Boolean(customer.isActive),
  };
}

function blankCategoryDraft(groupId = "") {
  return {
    id: "",
    groupId,
    name: "",
    description: "",
    optionLabelName: "",
    heroTitle: "",
    heroSubtitle: "",
    serviceDescriptionHtml: "",
    cautionText: "비공개 계정 또는 잘못된 URL 입력 시 작업이 지연될 수 있어요.",
    refundText: "작업이 시작된 이후에는 취소 및 환불이 제한될 수 있어요.",
    isActive: true,
    sortOrder: 0,
  };
}

function categoryToDraft(category) {
  if (!category) return blankCategoryDraft();
  return {
    id: category.id || "",
    groupId: category.groupId || "",
    name: category.name || "",
    description: category.description || "",
    optionLabelName: category.optionLabelName || "",
    heroTitle: category.heroTitle || "",
    heroSubtitle: category.heroSubtitle || "",
    serviceDescriptionHtml: category.serviceDescriptionHtml || "",
    cautionText: category.cautionText || "",
    refundText: category.refundText || "",
    isActive: Boolean(category.isActive),
    sortOrder: Number(category.sortOrder || 0),
  };
}

function blankProductDraft(categoryId = "") {
  return {
    id: "",
    categoryId,
    name: "",
    menuName: "",
    optionName: "",
    productCode: "",
    price: 1000,
    minAmount: 1,
    maxAmount: 100,
    stepAmount: 1,
    priceStrategy: "unit",
    unitLabel: "개",
    badge: "",
    isDiscounted: false,
    estimatedTurnaround: "5분~2시간",
    isActive: true,
    sortOrder: 0,
    formPreset: "account_quantity",
    targetLabel: "계정(ID)",
    targetPlaceholder: "예: pulse24_official",
    quantityLabel: "수량",
    memoLabel: "운영 메모",
    advancedFieldKeys: [],
  };
}

function productToDraft(product) {
  if (!product) return blankProductDraft();
  const formConfig = product.formConfig || {};
  return {
    id: product.id || "",
    categoryId: product.categoryId || "",
    name: product.name || "",
    menuName: product.menuName || product.name || "",
    optionName: product.optionName || "",
    productCode: product.productCode || "",
    price: Number(product.price || 0),
    minAmount: Number(product.minAmount || 1),
    maxAmount: Number(product.maxAmount || 1),
    stepAmount: Number(product.stepAmount || 1),
    priceStrategy: product.priceStrategy || "unit",
    unitLabel: product.unitLabel || "개",
    badge: product.badge || "",
    isDiscounted: Boolean(product.isDiscounted),
    estimatedTurnaround: product.estimatedTurnaround || "",
    isActive: Boolean(product.isActive),
    sortOrder: Number(product.sortOrder || 0),
    formPreset: formConfig.preset || "account_quantity",
    targetLabel: formConfig.targetLabel || "계정(ID)",
    targetPlaceholder: formConfig.targetPlaceholder || "",
    quantityLabel: formConfig.quantityLabel || "수량",
    memoLabel: formConfig.memoLabel || "운영 메모",
    advancedFieldKeys: Array.isArray(formConfig.advancedFieldKeys) ? formConfig.advancedFieldKeys : [],
  };
}

function getAdminSuppliers() {
  return state.adminBootstrap?.suppliers || [];
}

function getAdminProducts() {
  return state.adminBootstrap?.internalProducts || [];
}

function getAdminCustomers() {
  return state.adminBootstrap?.customers || [];
}

function getAdminCategories() {
  return state.adminBootstrap?.categories || [];
}

function getAdminPlatformGroups() {
  return state.adminBootstrap?.platformGroups || [];
}

function getSelectedAdminSupplierService() {
  const selectedSupplier = getSelectedAdminSupplier();
  if (!selectedSupplier?.id) return null;
  const services = state.adminSupplierServices[selectedSupplier.id]?.services || [];
  return services.find((service) => service.id === state.ui.adminSelectedSupplierServiceId) || null;
}

function formatAdvancedFieldLabel(fieldKey) {
  return advancedOrderFieldBlueprints[fieldKey]?.label || fieldKey;
}

function renderAdvancedFieldBadges(fieldKeys = []) {
  if (!fieldKeys.length) return `<span class="admin-badge is-neutral">추가 옵션 없음</span>`;
  return fieldKeys
    .map((fieldKey) => `<span class="admin-badge is-neutral">${escapeHtml(formatAdvancedFieldLabel(fieldKey))}</span>`)
    .join("");
}

function applySupplierRecommendationToProductDraft(service, { product = null } = {}) {
  const recommendation = service?.requestGuide?.formRecommendation;
  if (!recommendation) return false;

  const seedDraft = product
    ? productToDraft(product)
    : state.adminProductDraft || blankProductDraft(state.ui.adminSelectedCategoryId);
  const nextDraft = {
    ...seedDraft,
    formPreset: recommendation.formPreset || seedDraft.formPreset,
    targetLabel: recommendation.targetLabel || seedDraft.targetLabel,
    targetPlaceholder: recommendation.targetPlaceholder || seedDraft.targetPlaceholder,
    quantityLabel: recommendation.quantityLabel || seedDraft.quantityLabel,
    unitLabel: recommendation.unitLabel || seedDraft.unitLabel,
    minAmount: Number(recommendation.minAmount || seedDraft.minAmount || 1),
    maxAmount: Number(recommendation.maxAmount || seedDraft.maxAmount || 1),
    stepAmount: Number(recommendation.stepAmount || seedDraft.stepAmount || 1),
    priceStrategy: recommendation.priceStrategy || seedDraft.priceStrategy,
    advancedFieldKeys: Array.isArray(recommendation.advancedFieldKeys) ? [...recommendation.advancedFieldKeys] : [],
  };
  if (!nextDraft.name) nextDraft.name = service.name || "";
  if (!nextDraft.menuName) nextDraft.menuName = service.name || "";
  if (!nextDraft.optionName) nextDraft.optionName = service.type || "";
  if (!nextDraft.productCode) nextDraft.productCode = service.externalServiceId || "";

  if (product?.id) {
    state.ui.adminProductMode = "edit";
    state.ui.adminSelectedManageProductId = product.id;
    state.ui.adminSelectedCategoryId = product.categoryId || state.ui.adminSelectedCategoryId;
  } else if (!nextDraft.categoryId) {
    nextDraft.categoryId = state.ui.adminSelectedCategoryId;
  }
  state.adminProductDraft = nextDraft;
  state.ui.adminActiveSection = "catalog";
  window.history.pushState({}, "", adminSectionPath("catalog"));
  return true;
}

function renderSupplierRequestGuide(service, { applyLabel = "" } = {}) {
  const guide = service?.requestGuide;
  if (!guide) return "";
  const recommendation = guide.formRecommendation || {};
  const recommendedFields = supplierGuideFieldDefinitions(recommendation);
  const example = guide.callExamplePayload ? JSON.stringify(guide.callExamplePayload, null, 2) : "";
  return `
    <div class="admin-guide-stack">
      <div class="admin-mini-card admin-guide-card">
        <span>추천 내부 상품 양식</span>
        <strong>${escapeHtml(formPresetLabel(recommendation.formPreset || ""))}</strong>
        <p>${escapeHtml(`${recommendation.targetLabel || "-"} · ${recommendation.priceStrategy === "fixed" ? "고정가 권장" : "수량형 권장"}`)}</p>
        <div class="admin-guide-metrics">
          <article>
            <span>가격 방식</span>
            <strong>${escapeHtml(recommendation.priceStrategy === "fixed" ? "고정가" : "수량형")}</strong>
          </article>
          <article>
            <span>수량 범위</span>
            <strong>${escapeHtml(`${formatNumber(recommendation.minAmount || 1)} ~ ${formatNumber(recommendation.maxAmount || recommendation.minAmount || 1)} ${recommendation.unitLabel || "개"}`)}</strong>
          </article>
          <article>
            <span>대표 입력</span>
            <strong>${escapeHtml(recommendation.targetLabel || "-")}</strong>
          </article>
        </div>
        <div class="admin-chip-row">
          ${renderAdvancedFieldBadges(recommendation.advancedFieldKeys || [])}
        </div>
        ${
          recommendedFields.length
            ? `
              <div class="admin-guide-field-grid">
                ${recommendedFields
                  .map(
                    (field) => `
                      <article class="admin-guide-field">
                        <div class="admin-guide-field__head">
                          <strong>${escapeHtml(field.label)}</strong>
                          <span>${field.required ? "필수" : "선택"}</span>
                        </div>
                        ${field.placeholder ? `<code>${escapeHtml(field.placeholder)}</code>` : ""}
                        ${field.detail ? `<p>${escapeHtml(field.detail)}</p>` : ""}
                      </article>
                    `
                  )
                  .join("")}
              </div>
            `
            : ""
        }
        ${
          applyLabel
            ? `<div class="admin-action-row admin-action-row--top"><button class="admin-secondary-button" type="button" data-apply-service-recommendation>${escapeHtml(applyLabel)}</button></div>`
            : ""
        }
      </div>
      <div class="admin-mini-card admin-guide-card">
        <span>${escapeHtml(guide.callExampleTitle || "호출 예시")}</span>
        <strong>${guide.callExampleIsEstimated ? "추정 예시" : "예시 Payload"}</strong>
        <pre class="admin-code-block">${escapeHtml(example || "{}")}</pre>
      </div>
      ${
        Array.isArray(guide.notes) && guide.notes.length
          ? `
            <div class="admin-mini-card admin-guide-card">
              <span>운영 메모</span>
              <div class="admin-guide-notes">
                ${guide.notes.map((note) => `<p>${escapeHtml(note)}</p>`).join("")}
              </div>
            </div>
          `
          : ""
      }
    </div>
  `;
}

function getAdminPopup() {
  return state.adminBootstrap?.popup || null;
}

function getAdminSiteSettings() {
  return state.adminBootstrap?.siteSettings || null;
}

function getAdminHomeBanners() {
  return state.adminBootstrap?.homeBanners || [];
}

function getAdminPlatformSections() {
  return state.adminBootstrap?.platformSections || [];
}

function getAdminAnalytics() {
  return state.adminBootstrap?.analytics || null;
}

function currentViewer() {
  return state.bootstrap?.viewer || { authenticated: false, csrfToken: "", user: null };
}

function isLoggedIn() {
  return Boolean(currentViewer().authenticated && state.bootstrap?.user);
}

function getSelectedAdminSupplier() {
  return getAdminSuppliers().find((supplier) => supplier.id === state.ui.adminSelectedSupplierId) || null;
}

function getSelectedAdminProduct() {
  return getAdminProducts().find((product) => product.id === state.ui.adminSelectedProductId) || null;
}

function getSelectedAdminCustomer() {
  const customerId = state.ui.adminSelectedCustomerId;
  return state.adminCustomerDetails[customerId] || getAdminCustomers().find((customer) => customer.id === customerId) || null;
}

function getSelectedAdminHomeBanner() {
  return getAdminHomeBanners().find((banner) => banner.id === state.ui.adminSelectedHomeBannerId) || null;
}

function getSelectedAdminPlatformSection() {
  return getAdminPlatformSections().find((platform) => platform.id === state.ui.adminSelectedPlatformSectionId) || null;
}

function getSelectedAdminCategory() {
  return getAdminCategories().find((category) => category.id === state.ui.adminSelectedCategoryId) || null;
}

function getManageProducts(categoryId = state.ui.adminSelectedCategoryId) {
  return getAdminProducts().filter((product) => product.categoryId === categoryId);
}

function getSelectedManageProduct() {
  return getManageProducts().find((product) => product.id === state.ui.adminSelectedManageProductId) || null;
}

function syncAdminSelections({ preserveDraft = true } = {}) {
  const suppliers = getAdminSuppliers();
  const products = getAdminProducts();
  const customers = getAdminCustomers();
  const categories = getAdminCategories();
  const groups = getAdminPlatformGroups();
  const popup = getAdminPopup();
  const homeBanners = getAdminHomeBanners();
  const platformSections = getAdminPlatformSections();
  const siteSettings = getAdminSiteSettings();

  if (!preserveDraft || !state.adminSiteSettingsDraft) {
    state.adminSiteSettingsDraft = siteSettingsToDraft(siteSettings);
  }

  if (!preserveDraft || !state.adminPopupDraft || state.adminPopupDraft.id !== (popup?.id || "")) {
    state.adminPopupDraft = popupToDraft(popup);
  }

  if (
    state.ui.adminSelectedHomeBannerId &&
    !homeBanners.some((banner) => banner.id === state.ui.adminSelectedHomeBannerId)
  ) {
    state.ui.adminSelectedHomeBannerId = "";
  }
  if (!state.ui.adminSelectedHomeBannerId && homeBanners.length) {
    state.ui.adminSelectedHomeBannerId = homeBanners[0].id;
  }
  const selectedBanner = getSelectedAdminHomeBanner();
  if (!preserveDraft || !state.adminHomeBannerDraft) {
    state.adminHomeBannerDraft = homeBannerToDraft(selectedBanner);
  } else if (state.adminHomeBannerDraft.id) {
    const matchingBanner = homeBanners.find((banner) => banner.id === state.adminHomeBannerDraft.id);
    if (matchingBanner) {
      state.adminHomeBannerDraft = homeBannerToDraft(matchingBanner);
    }
  }

  if (
    state.ui.adminSelectedPlatformSectionId &&
    !platformSections.some((platform) => platform.id === state.ui.adminSelectedPlatformSectionId)
  ) {
    state.ui.adminSelectedPlatformSectionId = "";
  }
  if (!state.ui.adminSelectedPlatformSectionId && platformSections.length) {
    state.ui.adminSelectedPlatformSectionId = platformSections[0].id;
  }
  const selectedPlatformSection = getSelectedAdminPlatformSection();
  if (!preserveDraft || !state.adminPlatformSectionDraft) {
    state.adminPlatformSectionDraft = platformSectionToDraft(selectedPlatformSection);
  } else if (state.adminPlatformSectionDraft.id) {
    const matchingPlatformSection = platformSections.find((platform) => platform.id === state.adminPlatformSectionDraft.id);
    if (matchingPlatformSection) {
      state.adminPlatformSectionDraft = platformSectionToDraft(matchingPlatformSection);
    }
  }

  if (state.ui.adminSupplierMode !== "new") {
    if (
      state.ui.adminSelectedSupplierId &&
      !suppliers.some((supplier) => supplier.id === state.ui.adminSelectedSupplierId)
    ) {
      state.ui.adminSelectedSupplierId = "";
    }
    if (!state.ui.adminSelectedSupplierId && suppliers.length) {
      state.ui.adminSelectedSupplierId = suppliers[0].id;
    }
  }

  if (
    state.ui.adminSelectedProductId &&
    !products.some((product) => product.id === state.ui.adminSelectedProductId)
  ) {
    state.ui.adminSelectedProductId = "";
  }
  if (!state.ui.adminSelectedProductId && products.length) {
    const preferred = products.find((product) => !product.mapping) || products[0];
    state.ui.adminSelectedProductId = preferred.id;
  }

  if (state.ui.adminCustomerMode !== "new") {
    if (
      state.ui.adminSelectedCustomerId &&
      !customers.some((customer) => customer.id === state.ui.adminSelectedCustomerId)
    ) {
      state.ui.adminSelectedCustomerId = "";
    }
    if (!state.ui.adminSelectedCustomerId && customers.length) {
      const preferredCustomer = customers.find((customer) => customer.role === "customer") || customers[0];
      state.ui.adminSelectedCustomerId = preferredCustomer.id;
    }
  }

  if (state.ui.adminCategoryMode !== "new") {
    if (
      state.ui.adminSelectedCategoryId &&
      !categories.some((category) => category.id === state.ui.adminSelectedCategoryId)
    ) {
      state.ui.adminSelectedCategoryId = "";
    }
    if (!state.ui.adminSelectedCategoryId && categories.length) {
      const preferredCategory = categories.find((category) => category.isActive) || categories[0];
      state.ui.adminSelectedCategoryId = preferredCategory.id;
    }
  }

  const manageProducts = getManageProducts(state.ui.adminSelectedCategoryId);
  if (state.ui.adminProductMode !== "new") {
    if (
      state.ui.adminSelectedManageProductId &&
      !manageProducts.some((product) => product.id === state.ui.adminSelectedManageProductId)
    ) {
      state.ui.adminSelectedManageProductId = "";
    }
    if (!state.ui.adminSelectedManageProductId && manageProducts.length) {
      const preferredProduct = manageProducts.find((product) => product.isActive) || manageProducts[0];
      state.ui.adminSelectedManageProductId = preferredProduct.id;
    }
  }

  if (state.ui.adminSupplierMode === "new") {
    if (!preserveDraft || !state.adminSupplierDraft) {
      state.adminSupplierDraft = blankSupplierDraft();
    }
  } else {
    const selectedSupplier = getSelectedAdminSupplier();
    if (!preserveDraft || !state.adminSupplierDraft) {
      state.adminSupplierDraft = supplierToDraft(selectedSupplier);
    } else if (state.adminSupplierDraft.id) {
      const matching = suppliers.find((supplier) => supplier.id === state.adminSupplierDraft.id);
      if (matching) {
        state.adminSupplierDraft = supplierToDraft(matching);
      }
    } else if (!state.adminSupplierDraft.id && selectedSupplier && !state.adminSupplierDraft.name && !state.adminSupplierDraft.apiUrl) {
      state.adminSupplierDraft = supplierToDraft(selectedSupplier);
    }
  }

  const selectedSupplier = getSelectedAdminSupplier();
  const services = selectedSupplier ? state.adminSupplierServices[selectedSupplier.id]?.services || [] : [];
  if (
    state.ui.adminSelectedSupplierServiceId &&
    !services.some((service) => service.id === state.ui.adminSelectedSupplierServiceId)
  ) {
    state.ui.adminSelectedSupplierServiceId = "";
  }

  const selectedProduct = getSelectedAdminProduct();
  if (
    selectedProduct?.mapping &&
    selectedProduct.mapping.supplierId === state.ui.adminSelectedSupplierId &&
    !state.ui.adminSelectedSupplierServiceId
  ) {
    state.ui.adminSelectedSupplierServiceId = selectedProduct.mapping.supplierServiceId;
  }

  if (state.ui.adminCustomerMode === "new") {
    if (!preserveDraft || !state.adminCustomerDraft) {
      state.adminCustomerDraft = blankCustomerDraft();
    }
  } else {
    const selectedCustomer = getSelectedAdminCustomer();
    if (!preserveDraft || !state.adminCustomerDraft) {
      state.adminCustomerDraft = customerToDraft(selectedCustomer);
    } else if (state.adminCustomerDraft.id) {
      const matchingCustomer =
        state.adminCustomerDetails[state.adminCustomerDraft.id] ||
        customers.find((customer) => customer.id === state.adminCustomerDraft.id);
      if (matchingCustomer) {
        state.adminCustomerDraft = customerToDraft(matchingCustomer);
      }
    }
  }

  if (state.ui.adminCategoryMode === "new") {
    if (!preserveDraft || !state.adminCategoryDraft) {
      state.adminCategoryDraft = blankCategoryDraft(groups[0]?.id || "");
    }
  } else {
    const selectedCategory = getSelectedAdminCategory();
    if (!preserveDraft || !state.adminCategoryDraft) {
      state.adminCategoryDraft = categoryToDraft(selectedCategory);
    } else if (state.adminCategoryDraft.id) {
      const matchingCategory = categories.find((category) => category.id === state.adminCategoryDraft.id);
      if (matchingCategory) {
        state.adminCategoryDraft = categoryToDraft(matchingCategory);
      }
    }
  }

  if (state.ui.adminProductMode === "new") {
    if (!preserveDraft || !state.adminProductDraft) {
      state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    } else if (!state.adminProductDraft.categoryId) {
      state.adminProductDraft.categoryId = state.ui.adminSelectedCategoryId;
    }
  } else {
    const selectedManageProduct = getSelectedManageProduct();
    if (!preserveDraft || !state.adminProductDraft) {
      state.adminProductDraft = productToDraft(selectedManageProduct);
    } else if (state.adminProductDraft.id) {
      const matchingProduct = products.find((product) => product.id === state.adminProductDraft.id);
      if (matchingProduct) {
        state.adminProductDraft = productToDraft(matchingProduct);
      }
    }
  }
}

function resetAdminState({ preserveSession = false } = {}) {
  state.adminBootstrap = null;
  state.adminSupplierServices = {};
  state.adminCustomerDetails = {};
  state.adminSiteSettingsDraft = null;
  state.adminPopupDraft = null;
  state.adminHomeBannerDraft = null;
  state.adminSupplierDraft = null;
  state.adminConnectionResult = null;
  state.adminCustomerDraft = null;
  state.adminCategoryDraft = null;
  state.adminProductDraft = null;
  state.ui.adminActiveSection = "overview";
  state.ui.adminAnalyticsTab = "dashboard";
  state.ui.adminAnalyticsRange = "30d";
  state.ui.adminCustomerFilter = "all";
  state.ui.adminCustomerSearch = "";
  state.ui.adminSupplierMode = "edit";
  state.ui.adminSelectedSupplierId = "";
  state.ui.adminSelectedProductId = "";
  state.ui.adminSelectedSupplierServiceId = "";
  state.ui.adminServiceSearch = "";
  state.ui.adminCustomerMode = "edit";
  state.ui.adminSelectedCustomerId = "";
  state.ui.adminSelectedHomeBannerId = "";
  state.ui.adminCategoryMode = "edit";
  state.ui.adminSelectedCategoryId = "";
  state.ui.adminProductMode = "edit";
  state.ui.adminSelectedManageProductId = "";
  state.ui.adminOrderFilter = "all";
  state.ui.adminOrderSearch = "";
  if (!preserveSession) {
    state.adminSession = null;
    state.adminCsrfToken = "";
  }
}

async function loadAdminSession({ force = false } = {}) {
  if (!force && state.adminSession) return state.adminSession;
  const data = await apiGet("/api/admin/session");
  state.adminSession = data;
  state.adminCsrfToken = data.csrfToken || "";
  setAdminAnalyticsExclusion(Boolean(data.authenticated));
  return data;
}

async function refreshAdminData({ preserveDraft = true } = {}) {
  const data = await apiGet("/api/admin/bootstrap");
  state.adminBootstrap = data;
  const validCustomerIds = new Set((data.customers || []).map((customer) => customer.id));
  Object.keys(state.adminCustomerDetails).forEach((customerId) => {
    if (!validCustomerIds.has(customerId)) {
      delete state.adminCustomerDetails[customerId];
    }
  });
  syncAdminSelections({ preserveDraft });
  return data;
}

async function ensureAdminSupplierServices(supplierId, { force = false } = {}) {
  if (!supplierId) return null;
  if (force || !state.adminSupplierServices[supplierId]) {
    const data = await apiGet(`/api/admin/suppliers/${encodeURIComponent(supplierId)}/services`);
    state.adminSupplierServices[supplierId] = data;
  }
  syncAdminSelections({ preserveDraft: true });
  return state.adminSupplierServices[supplierId];
}

async function ensureAdminCustomerDetail(customerId, { force = false } = {}) {
  if (!customerId) return null;
  if (force || !state.adminCustomerDetails[customerId]) {
    const data = await apiGet(`/api/admin/customers/${encodeURIComponent(customerId)}`);
    state.adminCustomerDetails[customerId] = data.customer;
  }
  syncAdminSelections({ preserveDraft: true });
  return state.adminCustomerDetails[customerId];
}

function syncShellMode(route) {
  const deviceShell = document.querySelector(".device-shell");
  const appRoot = document.getElementById("app");
  const isAdmin = route.name === "admin";
  if (deviceShell) {
    deviceShell.dataset.routeSurface = isAdmin ? "admin" : "public";
  }
  if (appRoot) {
    appRoot.dataset.routeSurface = isAdmin ? "admin" : "public";
  }
  document.body.dataset.routeSurface = isAdmin ? "admin" : "public";
  applySitePresentation(route);
}

function applySitePresentation(route) {
  const isAdmin = route.name === "admin";
  const siteSettings = state.adminBootstrap?.siteSettings || state.bootstrap?.siteSettings || {};
  const siteName = String(siteSettings.siteName || DEFAULT_SITE_NAME).trim() || DEFAULT_SITE_NAME;
  const siteDescription = String(siteSettings.siteDescription || "").trim();
  const faviconUrl = String(siteSettings.faviconUrl || "").trim();
  const shareImageUrl = String(siteSettings.shareImageUrl || "").trim();
  document.title = isAdmin ? `${siteName} Admin Console` : siteName;

  const robots = ensureMetaTag("robots");
  const googlebot = ensureMetaTag("googlebot");
  if (isAdmin) {
    robots.setAttribute("content", "noindex, nofollow, noarchive, nosnippet, noimageindex");
    googlebot.setAttribute("content", "noindex, nofollow, noarchive, nosnippet, noimageindex");
  } else {
    robots.remove();
    googlebot.remove();
  }

  const descriptionMeta = ensureMetaTag("description");
  const twitterTitle = ensureMetaTag("twitter:title");
  const twitterDescription = ensureMetaTag("twitter:description");
  const twitterCard = ensureMetaTag("twitter:card");
  const ogTitle = ensurePropertyMetaTag("og:title");
  const ogDescription = ensurePropertyMetaTag("og:description");
  const ogType = ensurePropertyMetaTag("og:type");
  const ogImage = ensurePropertyMetaTag("og:image");
  const twitterImage = ensureMetaTag("twitter:image");

  if (isAdmin) {
    descriptionMeta.remove();
    twitterTitle.remove();
    twitterDescription.remove();
    twitterCard.remove();
    ogTitle.remove();
    ogDescription.remove();
    ogType.remove();
    ogImage.remove();
    twitterImage.remove();
  } else {
    descriptionMeta.setAttribute("content", siteDescription);
    twitterTitle.setAttribute("content", siteName);
    twitterDescription.setAttribute("content", siteDescription);
    ogTitle.setAttribute("content", siteName);
    ogDescription.setAttribute("content", siteDescription);
    ogType.setAttribute("content", "website");
    if (shareImageUrl) {
      ogImage.setAttribute("content", shareImageUrl);
      twitterImage.setAttribute("content", shareImageUrl);
      twitterCard.setAttribute("content", "summary_large_image");
    } else {
      ogImage.remove();
      twitterImage.remove();
      twitterCard.setAttribute("content", "summary");
    }
  }

  if (faviconUrl) {
    ensureManagedLinkTag("site-favicon", "icon").setAttribute("href", faviconUrl);
    ensureManagedLinkTag("site-shortcut-icon", "shortcut icon").setAttribute("href", faviconUrl);
    ensureManagedLinkTag("site-apple-touch-icon", "apple-touch-icon").setAttribute("href", faviconUrl);
  } else {
    clearManagedHeadTag('link[data-managed-head="site-favicon"]');
    clearManagedHeadTag('link[data-managed-head="site-shortcut-icon"]');
    clearManagedHeadTag('link[data-managed-head="site-apple-touch-icon"]');
  }
}

function apiUrl(path) {
  if (!path.startsWith("/")) return path;
  return runtimeConfig.apiBaseUrl ? `${runtimeConfig.apiBaseUrl}${path}` : path;
}

function isAdminApiPath(path) {
  return path.startsWith("/api/admin/");
}

function requestCredentials(path) {
  return path.startsWith("/api/") ? "include" : "same-origin";
}

function clearAdminSessionState(configured = true) {
  state.adminSession = { configured, authenticated: false, username: "", csrfToken: "" };
  state.adminCsrfToken = "";
  resetAdminState({ preserveSession: true });
}

function clearPublicSessionState() {
  state.publicCsrfToken = "";
  if (state.bootstrap) {
    state.bootstrap.viewer = { authenticated: false, csrfToken: "", user: null };
    state.bootstrap.user = null;
  }
  state.orders = [];
  state.transactions = [];
  state.wallet = null;
  state.walletLedger = [];
  state.chargeOrders = [];
  state.chargeDraft = null;
  state.orderCounts = { all: 0, queued: 0, in_progress: 0, completed: 0 };
}

async function parseApiResponse(response) {
  try {
    return await response.json();
  } catch (_) {
    return { ok: false, error: "API 응답을 해석하지 못했습니다." };
  }
}

async function apiGet(path) {
  const response = await fetch(apiUrl(path), {
    headers: { Accept: "application/json" },
    credentials: requestCredentials(path),
  });
  const data = await parseApiResponse(response);
  if (!isAdminApiPath(path) && response.status === 401) {
    clearPublicSessionState();
  }
  if (isAdminApiPath(path) && response.status === 401) {
    clearAdminSessionState(true);
  }
  if (isAdminApiPath(path) && response.status === 503) {
    clearAdminSessionState(false);
  }
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || "요청 처리 중 오류가 발생했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

async function apiPost(path, payload) {
  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  if (
    (["/api/orders", "/api/charge", "/api/charge-orders", "/api/logout"].includes(path) ||
      path.startsWith("/api/charge-orders/")) &&
    state.publicCsrfToken
  ) {
    headers["X-SMM-CSRF-Token"] = state.publicCsrfToken;
  }
  if (isAdminApiPath(path) && path !== "/api/admin/login" && state.adminCsrfToken) {
    headers["X-SMM-CSRF-Token"] = state.adminCsrfToken;
  }
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    credentials: requestCredentials(path),
  });
  const data = await parseApiResponse(response);
  if (!isAdminApiPath(path) && response.status === 401) {
    clearPublicSessionState();
  }
  if (isAdminApiPath(path) && response.status === 401) {
    clearAdminSessionState(true);
  }
  if (isAdminApiPath(path) && response.status === 503) {
    clearAdminSessionState(false);
  }
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || "요청 처리 중 오류가 발생했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

function getRoute() {
  return parseRoute(window.location.pathname, normalizeAdminSectionId);
}

function showLoading(message = "패널을 불러오는 중...") {
  app.innerHTML = `
    <div class="loading-screen">
      <div class="loading-card">
        <div class="loading-spinner"></div>
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
}

function showToast(message, variant = "default") {
  toast.textContent = message;
  toast.className = `toast is-visible ${variant === "error" ? "is-error" : ""}`;
  window.clearTimeout(showToast._timer);
  showToast._timer = window.setTimeout(() => {
    toast.className = "toast";
  }, 2600);
}

async function refreshCoreData() {
  const bootstrapData = await apiGet("/api/bootstrap");
  state.bootstrap = bootstrapData;
  state.publicCsrfToken = bootstrapData.viewer?.csrfToken || "";
  if (bootstrapData.viewer?.authenticated) {
    const [ordersData, walletData, walletLedgerData, chargeOrdersData] = await Promise.all([
      apiGet("/api/orders"),
      apiGet("/api/wallet"),
      apiGet("/api/wallet/ledger?limit=100"),
      apiGet("/api/charge-orders?limit=100"),
    ]);
    state.orders = ordersData.orders;
    state.orderCounts = ordersData.counts;
    state.wallet = walletData.wallet;
    state.walletLedger = walletLedgerData.entries || [];
    state.chargeOrders = chargeOrdersData.chargeOrders || [];
    state.transactions = state.walletLedger;
    if (!state.chargeDraft) {
      state.chargeDraft = blankChargeDraft(bootstrapData.chargeConfig);
    }
  } else {
    state.orders = [];
    state.orderCounts = { all: 0, queued: 0, in_progress: 0, completed: 0 };
    state.transactions = [];
    state.wallet = null;
  state.walletLedger = [];
  state.chargeOrders = [];
  state.chargeDraft = null;
}

function resetSignupFlow() {
  state.publicAuth.signup = blankSignupState();
}

function currentSignupState() {
  if (!state.publicAuth) {
    state.publicAuth = blankPublicAuthState();
  }
  if (!state.publicAuth.signup) {
    state.publicAuth.signup = blankSignupState();
  }
  return state.publicAuth.signup;
}

function updateSignupPasswordFeedback(scope) {
  const container = scope || document;
  const form = container.querySelector("[data-public-signup-complete-form]");
  if (!(form instanceof HTMLElement)) return;
  const passwordInput = form.querySelector("[data-signup-password-input]");
  const nameInput = form.querySelector("[data-signup-name-input]");
  if (!(passwordInput instanceof HTMLInputElement)) return;
  const rawPassword = passwordInput.value || "";
  const feedback = evaluatePublicPasswordStrength(rawPassword, {
    email: currentSignupState().email || "",
    name: nameInput instanceof HTMLInputElement ? nameInput.value : "",
  });
  const root = form.querySelector("[data-password-strength]");
  const label = form.querySelector("[data-password-strength-label]");
  const guidance = form.querySelector("[data-password-strength-guidance]");
  const warnings = form.querySelector("[data-password-strength-warnings]");
  const bar = form.querySelector(".password-strength__bar span");
  if (root instanceof HTMLElement) {
    root.setAttribute("data-tone", feedback.tone);
  }
  if (label instanceof HTMLElement) {
    label.textContent = rawPassword ? feedback.label : "안내";
  }
  if (guidance instanceof HTMLElement) {
    guidance.textContent = rawPassword ? feedback.guidance : "문장처럼 길게 만들면 더 안전해요.";
  }
  if (warnings instanceof HTMLElement) {
    warnings.innerHTML = rawPassword ? feedback.warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("") : "";
  }
  if (bar instanceof HTMLElement) {
    bar.style.width = rawPassword ? `${Math.max(0, Math.min(feedback.score, 4)) * 25}%` : "0%";
  }
}
  if (!state.ui.activePlatform && bootstrapData.platforms.length) {
    state.ui.activePlatform = bootstrapData.platforms[0].id;
  }
}

async function loadCatalog() {
  const data = await apiGet("/api/products");
  state.catalog = data.platforms;
  if (!state.ui.activePlatform && state.catalog.length) {
    state.ui.activePlatform = state.catalog[0].id;
  }
}

async function ensureCategory(categoryId) {
  if (!state.categoryCache[categoryId]) {
    const data = await apiGet(`/api/product-categories/${encodeURIComponent(categoryId)}`);
    state.categoryCache[categoryId] = data.category;
  }
  return state.categoryCache[categoryId];
}

function filteredCatalog() {
  const search = state.ui.search.trim().toLowerCase();
  if (!search) return state.catalog;
  return state.catalog
    .map((platform) => {
      const groups = platform.groups
        .map((group) => {
          const productCategories = group.productCategories.filter((category) => {
            const haystack = [
              platform.displayName,
              group.name,
              category.name,
              category.description,
              category.heroSubtitle,
            ]
              .join(" ")
              .toLowerCase();
            return haystack.includes(search);
          });
          return { ...group, productCategories };
        })
        .filter((group) => group.productCategories.length);
      return { ...platform, groups };
    })
    .filter((platform) => platform.groups.length);
}

function getCurrentPlatform(platforms) {
  const found = platforms.find((platform) => platform.id === state.ui.activePlatform);
  return found || platforms[0] || null;
}

function ensureSelection(detail) {
  if (!detail || !detail.products.length) return null;
  const cached = state.productSelections[detail.id] || {
    productId: detail.products[0].id,
    fields: {},
  };
  const selectedProduct = detail.products.find((item) => item.id === cached.productId) || detail.products[0];
  cached.productId = selectedProduct.id;
  if (selectedProduct.priceStrategy === "unit") {
    const numeric = Number(cached.fields.orderedCount || 0);
    if (!numeric || numeric < selectedProduct.minAmount) {
      cached.fields.orderedCount = String(selectedProduct.minAmount);
    }
  } else {
    delete cached.fields.orderedCount;
  }
  state.productSelections[detail.id] = cached;
  return cached;
}

function getSelectedProduct(detail) {
  const selection = ensureSelection(detail);
  if (!selection) return null;
  return detail.products.find((product) => product.id === selection.productId) || detail.products[0];
}

function calculateSummary(detail) {
  const selection = ensureSelection(detail);
  const product = getSelectedProduct(detail);
  if (!selection || !product) return null;

  let quantity = product.priceStrategy === "fixed" ? 1 : Number(selection.fields.orderedCount || product.minAmount);
  if (!Number.isFinite(quantity) || quantity < product.minAmount) {
    quantity = product.minAmount;
  }
  if (product.priceStrategy === "unit") {
    if (quantity > product.maxAmount) quantity = product.maxAmount;
    if (product.stepAmount > 1) {
      quantity = Math.floor(quantity / product.stepAmount) * product.stepAmount;
      if (quantity < product.minAmount) quantity = product.minAmount;
    }
  }

  const total = product.priceStrategy === "fixed" ? product.price : product.price * quantity;
  return { product, selection, quantity, total };
}

function previewPlatformHint(detail, product) {
  const lowered = `${detail?.platform?.slug || ""} ${product?.productCode || ""}`.toLowerCase();
  for (const [keyword, resolved] of [
    ["instagram", "instagram"],
    ["youtube", "youtube"],
    ["tiktok", "tiktok"],
    ["threads", "threads"],
    ["facebook", "facebook"],
    ["naver", "nportal"],
    ["blog", "nportal"],
  ]) {
    if (lowered.includes(keyword)) return resolved;
  }
  return detail?.platform?.slug || "";
}

function platformSupportsAccountFormat(platformHint) {
  return ["instagram", "threads", "youtube", "tiktok", "facebook"].includes(platformHint);
}

function looksLikeLinkInput(raw) {
  const candidate = String(raw || "").trim();
  return /^(https?:\/\/|www\.)/i.test(candidate) || /^[\w.-]+\.[a-z]{2,}/i.test(candidate);
}

function normalizeCandidateUrl(raw) {
  const candidate = String(raw || "").trim();
  if (!candidate) return "";
  try {
    const normalized = /^(https?:)?\/\//i.test(candidate) ? candidate : `https://${candidate}`;
    const parsed = new URL(normalized);
    return parsed.hostname ? parsed.toString() : "";
  } catch (_) {
    return "";
  }
}

function platformTargetUrlMatches(platformHint, rawUrl) {
  const normalized = normalizeCandidateUrl(rawUrl);
  if (!normalized) return false;
  try {
    const parsed = new URL(normalized);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname || "/";
    const hostIs = (domain) => host === domain || host.endsWith(`.${domain}`);

    if (platformHint === "instagram") return hostIs("instagram.com") && path.replace(/\//g, "") !== "";
    if (platformHint === "youtube") return host === "youtu.be" || hostIs("youtube.com");
    if (platformHint === "tiktok") return hostIs("tiktok.com");
    if (platformHint === "facebook") return hostIs("facebook.com");
    if (platformHint === "threads") return hostIs("threads.net");
    if (platformHint === "nportal") return hostIs("naver.com");
    return true;
  } catch (_) {
    return false;
  }
}

function accountPreviewUrlForPlatform(accountValue, platformHint) {
  const cleaned = String(accountValue || "").trim().replace(/^@/, "").replace(/\//g, "").replace(/\s+/g, "");
  if (!cleaned || !/^[\w.-]+$/i.test(cleaned)) return "";
  if (platformHint === "instagram") return `https://www.instagram.com/${cleaned}/`;
  if (platformHint === "threads") return `https://www.threads.net/@${cleaned}`;
  if (platformHint === "youtube") return `https://www.youtube.com/@${cleaned}`;
  if (platformHint === "tiktok") return `https://www.tiktok.com/@${cleaned}`;
  if (platformHint === "facebook") return `https://www.facebook.com/${cleaned}`;
  return "";
}

function getPreviewSource(detail, product) {
  if (!product) return null;
  if (previewPlatformHint(detail, product) !== "instagram") return null;
  const template = product.formStructure?.template || {};
  for (const key of ["targetUrl", "targetValue"]) {
    const entry = template[key];
    if (!entry) continue;
    const options = entry.templateOptions || {};
    const label = options.label || options.labelProps?.label || key;
    return {
      key,
      label,
      type: options.type || options.formProps?.inputType || "text",
    };
  }
  return null;
}

function resolveOrderTarget(detail, product, fields) {
  const template = product?.formStructure?.template || {};
  const platformHint = previewPlatformHint(detail, product);

  for (const key of ["targetUrl", "targetValue"]) {
    if (!template[key]) continue;
    const rawInput = String(fields?.[key] || "").trim();
    if (!rawInput) continue;
    const options = template[key]?.templateOptions || {};
    const sourceLabel = options.label || options.labelProps?.label || key;

    if (looksLikeLinkInput(rawInput)) {
      return {
        fieldKey: key,
        rawInput,
        url: normalizeCandidateUrl(rawInput),
        sourceLabel,
        platformHint,
      };
    }

    if (key === "targetValue") {
      return {
        fieldKey: key,
        rawInput,
        url: accountPreviewUrlForPlatform(rawInput, platformHint),
        sourceLabel,
        platformHint,
      };
    }

    return { fieldKey: key, rawInput, url: "", sourceLabel, platformHint };
  }

  return { fieldKey: "", rawInput: "", url: "", sourceLabel: "", platformHint };
}

function platformTargetErrorMessage(platformHint) {
  const labels = {
    instagram: "인스타그램",
    youtube: "유튜브",
    tiktok: "틱톡",
    facebook: "페이스북",
    threads: "스레드",
    nportal: "네이버",
  };
  return `${labels[platformHint] || "해당 플랫폼"} 형식에 맞는 링크 또는 계정을 입력해 주세요.`;
}

function getOrderValidationState(detail, product) {
  if (!detail || !product) {
    return { blocked: true, reason: "상품을 다시 선택해 주세요." };
  }

  const selection = ensureSelection(detail);
  const fields = selection?.fields || {};
  const resolved = resolveOrderTarget(detail, product, fields);
  const hasTargetField = Boolean(product.formStructure?.template?.targetUrl || product.formStructure?.template?.targetValue);

  if (!hasTargetField) {
    return { blocked: false, reason: "" };
  }
  if (!resolved.rawInput) {
    return { blocked: true, reason: `${resolved.sourceLabel || "링크"} 입력 후 주문할 수 있습니다.` };
  }

  if (resolved.fieldKey === "targetUrl") {
    if (!resolved.url || !platformTargetUrlMatches(resolved.platformHint, resolved.url)) {
      return { blocked: true, reason: platformTargetErrorMessage(resolved.platformHint) };
    }
  } else if (resolved.fieldKey === "targetValue") {
    if (looksLikeLinkInput(resolved.rawInput)) {
      if (!resolved.url || !platformTargetUrlMatches(resolved.platformHint, resolved.url)) {
        return { blocked: true, reason: platformTargetErrorMessage(resolved.platformHint) };
      }
    } else if (platformSupportsAccountFormat(resolved.platformHint) && !resolved.url) {
      return { blocked: true, reason: platformTargetErrorMessage(resolved.platformHint) };
    }
  }

  if (resolved.platformHint === "instagram") {
    const preview = getPreviewState(detail, product);
    if (preview.state === "loading") {
      return { blocked: true, reason: "인스타그램 링크를 확인하는 중입니다." };
    }
    if (!(preview.state === "found" && preview.found)) {
      return { blocked: true, reason: "인스타그램 링크가 확인되어야 주문할 수 있습니다." };
    }
  }

  return { blocked: false, reason: "" };
}

function previewStateKey(detailId, productId) {
  return `${detailId}:${productId}`;
}

function defaultPreviewState() {
  return {
    state: "idle",
    found: false,
    title: "",
    imageUrl: "",
    resolvedUrl: "",
    displayInput: "",
    sourceLabel: "",
    message: "링크나 계정 ID를 입력하면 미리보기가 표시됩니다.",
  };
}

function getPreviewState(detail, product) {
  if (!detail || !product) return defaultPreviewState();
  return state.linkPreviews[previewStateKey(detail.id, product.id)] || defaultPreviewState();
}

function renderPreviewPanel(detail, product) {
  const preview = getPreviewState(detail, product);
  const previewSource = getPreviewSource(detail, product);

  if (!previewSource) {
    return "";
  }

  if (preview.state === "loading") {
    return `
      <div class="preview-card is-loading">
        <div class="preview-card__image preview-card__image--skeleton"></div>
        <div class="preview-card__body">
          <span class="preview-card__eyebrow">${escapeHtml(previewSource.label)}</span>
          <strong>링크 확인 중...</strong>
          <p>입력하신 값이 실제로 열리는지 확인하고 있습니다.</p>
        </div>
      </div>
    `;
  }

  if (preview.state === "found" && preview.found) {
    return `
      <div class="preview-card is-valid is-thumbnail-only">
        <div class="preview-card__image-wrap">
          <img class="preview-card__image" src="${escapeHtml(preview.imageUrl)}" alt="링크 썸네일 미리보기" />
          <span class="preview-card__badge">확인됨</span>
        </div>
      </div>
    `;
  }

  if (preview.state === "missing") {
    return `
      <div class="preview-card is-invalid">
        <div class="preview-card__empty">!</div>
        <div class="preview-card__body">
          <span class="preview-card__eyebrow">${escapeHtml(preview.sourceLabel || previewSource.label)}</span>
          <strong>링크가 확인되지 않습니다.</strong>
          <p>${escapeHtml(preview.displayInput || "입력한 주소를 다시 확인해 주세요.")}</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="preview-card">
      <div class="preview-card__empty">⌁</div>
      <div class="preview-card__body">
        <span class="preview-card__eyebrow">${escapeHtml(previewSource.label)}</span>
        <strong>입력값 확인용 썸네일</strong>
        <p>링크 주소나 계정 ID를 입력하면 오른쪽에 미리보기가 표시됩니다.</p>
      </div>
    </div>
  `;
}

function updatePreviewPanel(detail) {
  const product = getSelectedProduct(detail);
  const panel = document.querySelector("[data-preview-panel]");
  if (!panel || !product) return;
  panel.innerHTML = renderPreviewPanel(detail, product);
  updateOrderValidation(detail);
}

async function requestLinkPreview(detail, { immediate = false } = {}) {
  const summary = calculateSummary(detail);
  if (!summary) return;
  const previewSource = getPreviewSource(detail, summary.product);
  if (!previewSource) return;

  const previewInput = String(summary.selection.fields[previewSource.key] || "").trim();
  const key = previewStateKey(detail.id, summary.product.id);

  if (!previewInput) {
    state.linkPreviews[key] = defaultPreviewState();
    updatePreviewPanel(detail);
    return;
  }

  const existing = state.linkPreviews[key];
  if (
    !immediate &&
    existing &&
    existing.displayInput === previewInput &&
    (existing.state === "found" || existing.state === "missing")
  ) {
    updatePreviewPanel(detail);
    return;
  }

  const requestId = ++previewSequence;
  state.linkPreviews[key] = {
    ...defaultPreviewState(),
    state: "loading",
    displayInput: previewInput,
    sourceLabel: previewSource.label,
    requestId,
  };
  updatePreviewPanel(detail);

  try {
    const data = await apiPost("/api/link-preview", {
      productId: summary.product.id,
      fields: summary.selection.fields,
    });
    const latest = state.linkPreviews[key];
    if (!latest || latest.requestId !== requestId) return;
    state.linkPreviews[key] = {
      ...defaultPreviewState(),
      ...data.preview,
      requestId,
    };
    updatePreviewPanel(detail);
  } catch (error) {
    const latest = state.linkPreviews[key];
    if (!latest || latest.requestId !== requestId) return;
    state.linkPreviews[key] = {
      ...defaultPreviewState(),
      state: "missing",
      displayInput: previewInput,
      sourceLabel: previewSource.label,
      message: error.message || "링크가 확인되지 않습니다.",
    };
    updatePreviewPanel(detail);
  }
}

function scheduleLinkPreview(detail, { immediate = false } = {}) {
  if (!detail) return;
  window.clearTimeout(previewTimers[detail.id]);
  if (immediate) {
    requestLinkPreview(detail, { immediate: true });
    return;
  }
  previewTimers[detail.id] = window.setTimeout(() => {
    requestLinkPreview(detail);
  }, 450);
}

function updateOrderValidation(detail) {
  const product = getSelectedProduct(detail);
  const validation = getOrderValidationState(detail, product);
  const loggedIn = isLoggedIn();
  const note = document.querySelector("[data-order-validation-note]");
  if (note) {
    note.textContent = validation.reason || "";
    note.hidden = !validation.reason;
    note.classList.toggle("is-blocked", validation.blocked);
    note.classList.toggle("is-ready", !validation.blocked && Boolean(validation.reason));
  }
  document.querySelectorAll("[data-order-submit-button]").forEach((button) => {
    button.disabled = Boolean(validation.blocked);
    button.textContent = validation.blocked ? "주문 불가" : loggedIn ? "주문하기" : "로그인 후 주문";
  });
}

function syncAdminSectionNavState() {
  document.querySelectorAll("[data-admin-scroll-section]").forEach((button) => {
    button.classList.toggle("is-active", button.getAttribute("data-admin-scroll-section") === state.ui.adminActiveSection);
  });
}

function setActiveAdminSection(sectionId) {
  if (!sectionId) return;
  state.ui.adminActiveSection = sectionId;
  syncAdminSectionNavState();
}

function installAdminSectionObserver() {
  if (adminSectionObserver) {
    adminSectionObserver.disconnect();
    adminSectionObserver = null;
  }
  const anchors = Array.from(document.querySelectorAll("[data-admin-section-anchor]"));
  if (!anchors.length) return;
  if (typeof window.IntersectionObserver !== "function") {
    setActiveAdminSection(anchors[0].getAttribute("data-admin-section-anchor") || "overview");
    return;
  }
  adminSectionObserver = new window.IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
      if (!visible.length) return;
      setActiveAdminSection(visible[0].target.getAttribute("data-admin-section-anchor") || "overview");
    },
    {
      root: null,
      threshold: [0.2, 0.45, 0.7],
      rootMargin: "-12% 0px -58% 0px",
    }
  );
  anchors.forEach((anchor) => adminSectionObserver.observe(anchor));
  setActiveAdminSection(state.ui.adminActiveSection || anchors[0].getAttribute("data-admin-section-anchor") || "overview");
}

function renderAdminHealthBadge(status) {
  const normalized = String(status || "never").toLowerCase();
  let label = "미확인";
  let className = "is-neutral";

  if (normalized === "success" || normalized === "submitted" || normalized === "accepted") {
    label = "정상";
    className = "is-success";
  } else if (normalized === "failed" || normalized === "fail" || normalized === "error") {
    label = "실패";
    className = "is-error";
  } else if (normalized === "pending" || normalized === "syncing") {
    label = "진행 중";
    className = "is-warn";
  }

  return `<span class="admin-badge ${className}">${escapeHtml(label)}</span>`;
}

function renderMultilineText(value) {
  return escapeHtml(value || "").replace(/\n/g, "<br />");
}

function renderPromoPopupCard(popup, { preview = false } = {}) {
  if (!popup) return "";
  const theme = escapeHtml(popup.theme || "coral");
  const imageUrl = String(popup.imageUrl || "").trim();
  const hasImage = Boolean(imageUrl);
  return `
    <div class="promo-popup-card promo-popup-card--${theme} ${hasImage ? "has-image" : ""} ${preview ? "is-preview" : ""}">
      ${
        hasImage
          ? `
            <div class="promo-popup-card__media" aria-hidden="true">
              <img class="promo-popup-card__media-image" src="${escapeHtml(imageUrl)}" alt="" />
            </div>
            <div class="promo-popup-card__overlay" aria-hidden="true"></div>
          `
          : ""
      }
      <div class="promo-popup-card__body">
        <div class="promo-popup-card__copy">
          ${popup.badgeText ? `<span class="promo-popup-card__badge">${escapeHtml(popup.badgeText)}</span>` : ""}
          <strong class="promo-popup-card__title">${renderMultilineText(popup.title)}</strong>
          ${popup.description ? `<p class="promo-popup-card__description">${escapeHtml(popup.description)}</p>` : ""}
        </div>
        ${
          hasImage
            ? ""
            : `
              <div class="promo-popup-card__visual" aria-hidden="true">
                <span class="promo-popup-card__spark promo-popup-card__spark--one"></span>
                <span class="promo-popup-card__spark promo-popup-card__spark--two"></span>
                <span class="promo-popup-card__spark promo-popup-card__spark--three"></span>
                <div class="promo-popup-card__stacks"></div>
                <div class="promo-popup-card__device">
                  <div class="promo-popup-card__play"></div>
                </div>
              </div>
            `
        }
      </div>
    </div>
  `;
}

function updateAdminPopupPreview() {
  const previewHost = document.querySelector("[data-admin-popup-preview]");
  const statusHost = document.querySelector("[data-admin-popup-status]");
  const imageMeta = document.querySelector("[data-admin-popup-image-meta]");
  const clearButton = document.querySelector("[data-admin-popup-image-clear]");
  const draft = state.adminPopupDraft || blankPopupDraft();
  if (previewHost) {
    previewHost.innerHTML = renderPopupPreviewMarkup(popupPreviewPayload(draft));
  }
  if (statusHost) {
    statusHost.className = `admin-badge ${draft.isActive ? "is-success" : "is-neutral"}`;
    statusHost.textContent = draft.isActive ? "노출 중" : "비노출";
  }
  if (imageMeta) {
    imageMeta.textContent = draft.imageName || (draft.imageUrl ? "저장된 이미지 연결됨" : "이미지 없음");
  }
  if (clearButton) {
    clearButton.disabled = !draft.imageUrl;
  }
}

function updateAdminHomeBannerPreview() {
  const draft = state.adminHomeBannerDraft || homeBannerToDraft(getSelectedAdminHomeBanner());
  const previewHost = document.querySelector("[data-admin-home-banner-preview]");
  const clearButton = document.querySelector("[data-admin-home-banner-image-clear]");
  if (previewHost) {
    previewHost.innerHTML = renderHomeBannerPreviewMarkup(draft);
  }
  if (clearButton) {
    clearButton.disabled = !draft.imageUrl || draft.imageUrl === defaultHomeBannerImageUrl(draft.id, draft.theme);
  }
}

function renderPlatformLogoPreviewMarkup(platform) {
  const preview = platformSectionToDraft(platform);
  return `
    <div class="admin-platform-logo-preview-card">
      ${renderPlatformLogoMarkup(preview, "admin-platform-logo-preview-card__visual")}
      <div class="admin-platform-logo-preview-card__copy">
        <strong>${escapeHtml(preview.displayName || "플랫폼 이름")}</strong>
        <p>${escapeHtml(preview.description || "홈 서비스 그리드와 상품 플랫폼 탭에 같은 로고가 노출됩니다.")}</p>
      </div>
    </div>
  `;
}

function updateAdminPlatformSectionPreview() {
  const draft = state.adminPlatformSectionDraft || platformSectionToDraft(getSelectedAdminPlatformSection());
  const previewHost = document.querySelector("[data-admin-platform-section-preview]");
  const clearButton = document.querySelector("[data-admin-platform-section-image-clear]");
  const imageMeta = document.querySelector("[data-admin-platform-section-image-meta]");
  if (previewHost) {
    previewHost.innerHTML = renderPlatformLogoPreviewMarkup(draft);
  }
  if (clearButton) {
    clearButton.disabled = !draft.logoImageUrl;
  }
  if (imageMeta) {
    imageMeta.textContent = draft.logoImageName || (draft.logoImageUrl ? "저장된 로고 이미지 연결됨" : "텍스트 아이콘 사용 중");
  }
}

function renderSiteSettingsPreviewMarkup(siteSettings) {
  const preview = siteSettingsPreviewPayload(siteSettings);
  const origin = window.location.origin || "https://your-site.example";
  return `
    <div class="admin-site-preview-stack">
      <article class="admin-site-preview-note">
        <span>상단 로고</span>
        <strong>${escapeHtml(preview.siteName)}</strong>
        <div class="admin-site-preview-logo">
          ${renderSiteBrandLogoMarkup(preview, "admin-site-preview-logo__mark", { surface: "light" })}
        </div>
      </article>

      <div class="admin-site-preview-browser">
        <div class="admin-site-preview-browser__tab">
          <span class="admin-site-preview-browser__favicon">
            ${
              preview.faviconUrl
                ? `<img src="${escapeHtml(preview.faviconUrl)}" alt="" />`
                : `<span class="admin-site-preview-browser__favicon-fallback">⌂</span>`
            }
          </span>
          <strong>${escapeHtml(preview.siteName)}</strong>
        </div>
        <div class="admin-site-preview-browser__bar">
          <span class="admin-site-preview-browser__dot"></span>
          <span class="admin-site-preview-browser__dot"></span>
          <span class="admin-site-preview-browser__dot"></span>
          <div class="admin-site-preview-browser__address">${escapeHtml(origin.replace(/^https?:\/\//, ""))}</div>
        </div>
      </div>

      <article class="admin-site-preview-note">
        <span>메일·SMS 전용 표기</span>
        <strong>${escapeHtml(preview.effectiveMailSmsSiteName)}</strong>
        <p>${preview.useMailSmsSiteName && preview.mailSmsSiteName ? "알림 메시지용 별도 이름이 활성화되어 있습니다." : "별도 이름을 켜지 않으면 사이트 이름이 그대로 사용됩니다."}</p>
      </article>

      <article class="admin-site-preview-share">
        <div class="admin-site-preview-share__image">
          ${
            preview.shareImageUrl
              ? `<img src="${escapeHtml(preview.shareImageUrl)}" alt="" />`
              : `<div class="admin-site-preview-share__placeholder">
                  <span>대표 이미지 미리보기</span>
                  <strong>${escapeHtml(preview.siteName)}</strong>
                </div>`
          }
        </div>
        <div class="admin-site-preview-share__body">
          <strong>${escapeHtml(preview.siteName)}</strong>
          <p>${escapeHtml(preview.siteDescription)}</p>
          <span>${escapeHtml(origin)}</span>
        </div>
      </article>
    </div>
  `;
}

function updateAdminSiteSettingsPreview() {
  const draft = state.adminSiteSettingsDraft || blankSiteSettingsDraft();
  const previewHost = document.querySelector("[data-admin-site-settings-preview]");
  const nameCount = document.querySelector("[data-admin-site-settings-name-count]");
  const descriptionCount = document.querySelector("[data-admin-site-settings-description-count]");
  const mailCount = document.querySelector("[data-admin-site-settings-mail-count]");
  const headerLogoMeta = document.querySelector("[data-admin-site-settings-header-logo-meta]");
  const faviconMeta = document.querySelector("[data-admin-site-settings-favicon-meta]");
  const shareMeta = document.querySelector("[data-admin-site-settings-share-meta]");
  const headerLogoClear = document.querySelector("[data-admin-site-settings-header-logo-clear]");
  const faviconClear = document.querySelector("[data-admin-site-settings-favicon-clear]");
  const shareClear = document.querySelector("[data-admin-site-settings-share-clear]");
  if (previewHost) {
    previewHost.innerHTML = renderSiteSettingsPreviewMarkup(draft);
  }
  if (nameCount) {
    nameCount.textContent = `${String(draft.siteName || "").length}/80`;
  }
  if (descriptionCount) {
    descriptionCount.textContent = `${String(draft.siteDescription || "").length}/240`;
  }
  if (mailCount) {
    mailCount.textContent = `${String(draft.mailSmsSiteName || "").length}/60`;
  }
  if (headerLogoMeta) {
    headerLogoMeta.textContent = draft.headerLogoName || (draft.headerLogoUrl ? "저장된 상단 로고 연결됨" : "상단 로고 없음");
  }
  if (faviconMeta) {
    faviconMeta.textContent = draft.faviconName || (draft.faviconUrl ? "저장된 파비콘 연결됨" : "파비콘 없음");
  }
  if (shareMeta) {
    shareMeta.textContent = draft.shareImageName || (draft.shareImageUrl ? "저장된 대표 이미지 연결됨" : "대표 이미지 없음");
  }
  if (headerLogoClear) {
    headerLogoClear.disabled = !draft.headerLogoUrl;
  }
  if (faviconClear) {
    faviconClear.disabled = !draft.faviconUrl;
  }
  if (shareClear) {
    shareClear.disabled = !draft.shareImageUrl;
  }
}

function renderSiteSettingsAdminSection() {
  const draft = state.adminSiteSettingsDraft || blankSiteSettingsDraft();

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>기본 설정</h2>
        <p>사이트 이름, 검색 설명, 메일·SMS 표기, 파비콘, 대표 이미지를 수정하면 공개 사이트와 공유 미리보기에 실제로 반영됩니다.</p>
      </div>

      <div class="admin-management-layout admin-management-layout--site-settings">
        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>사이트 기본 정보</strong>
            <span class="admin-badge is-success">실시간 적용 가능</span>
          </div>

          <form class="admin-form" data-admin-site-settings-form>
            <section class="admin-settings-section">
              <div class="admin-settings-section__head">
                <h3>사이트 기본 정보</h3>
                <p>브라우저 탭, 검색 결과, 공유 카드에 노출되는 핵심 문구를 관리합니다.</p>
              </div>

              <label class="form-field">
                <span class="field-label field-label-row">
                  <span>사이트 이름</span>
                  <span class="field-counter" data-admin-site-settings-name-count>${escapeHtml(String(draft.siteName || "").length)}/80</span>
                </span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="siteName" value="${escapeHtml(draft.siteName)}" placeholder="예: 인스타 관리, 인스타그램 관리대행 그로우잇" data-admin-site-settings-field="siteName" />
                </div>
                <p class="admin-inline-note">브라우저 탭과 공유 카드 제목에 가장 먼저 노출되는 이름입니다.</p>
              </label>

              <label class="form-field">
                <span class="field-label field-label-row">
                  <span>사이트 설명</span>
                  <span class="field-counter" data-admin-site-settings-description-count>${escapeHtml(String(draft.siteDescription || "").length)}/240</span>
                </span>
                <textarea class="field-textarea" name="siteDescription" rows="4" placeholder="사이트를 대표하는 설명과 핵심 키워드를 입력해 주세요." data-admin-site-settings-field="siteDescription">${escapeHtml(draft.siteDescription)}</textarea>
                <p class="admin-inline-note">검색엔진 설명과 SNS 공유 미리보기에 함께 사용됩니다.</p>
              </label>

              <label class="admin-toggle">
                <input type="checkbox" name="useMailSmsSiteName" ${draft.useMailSmsSiteName ? "checked" : ""} data-admin-site-settings-field="useMailSmsSiteName" />
                <span>메일·SMS 전용 사이트 이름 사용</span>
              </label>

              <label class="form-field">
                <span class="field-label field-label-row">
                  <span>메일·SMS 전용 사이트 이름</span>
                  <span class="field-counter" data-admin-site-settings-mail-count>${escapeHtml(String(draft.mailSmsSiteName || "").length)}/60</span>
                </span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="mailSmsSiteName" value="${escapeHtml(draft.mailSmsSiteName)}" placeholder="예: 그로우잇" ${draft.useMailSmsSiteName ? "" : "disabled"} data-admin-site-settings-field="mailSmsSiteName" />
                </div>
                <p class="admin-inline-note">알림 메시지용 별도 표기가 필요할 때만 켜고 입력하세요. 비워두면 사이트 이름이 그대로 사용됩니다.</p>
              </label>
            </section>

            <section class="admin-settings-section">
              <div class="admin-settings-section__head">
                <h3>사이트 표시 이미지</h3>
                <p>상단 로고, 파비콘, 공유 대표 이미지는 저장 즉시 공개 화면과 미리보기에 반영됩니다.</p>
              </div>

              <div class="admin-popup-upload">
                <div class="admin-popup-upload__head">
                  <div>
                    <strong>상단 로고</strong>
                    <p>권장 사이즈: 가로형 PNG/WebP/SVG, 400 x 120px 이상, 2MB 이하. 홈 상단과 고정 서비스 바에 사용됩니다.</p>
                  </div>
                  <span class="admin-badge is-neutral" data-admin-site-settings-header-logo-meta>${escapeHtml(draft.headerLogoName || (draft.headerLogoUrl ? "저장된 상단 로고 연결됨" : "상단 로고 없음"))}</span>
                </div>
                <div class="admin-popup-upload__controls">
                  <label class="admin-secondary-button admin-secondary-button--file" for="admin-site-settings-header-logo-upload">상단 로고 업로드</label>
                  <input class="admin-popup-upload__input" id="admin-site-settings-header-logo-upload" type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" data-admin-site-settings-image-upload="headerLogo" />
                  <button class="admin-secondary-button" type="button" data-admin-site-settings-header-logo-clear ${draft.headerLogoUrl ? "" : "disabled"}>상단 로고 제거</button>
                </div>
                <label class="form-field">
                  <span class="field-label">상단 로고 URL</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="headerLogoUrlInput" value="${escapeHtml(draft.headerLogoUrlInput || "")}" placeholder="https://example.com/header-logo.png" data-admin-site-settings-field="headerLogoUrlInput" />
                  </div>
                </label>
              </div>

              <div class="admin-popup-upload">
                <div class="admin-popup-upload__head">
                  <div>
                    <strong>파비콘</strong>
                    <p>권장 사이즈: 정사각 64 x 64px 이상, PNG/ICO/SVG, 1MB 이하. 최소 16 x 16px 이상을 권장합니다.</p>
                  </div>
                  <span class="admin-badge is-neutral" data-admin-site-settings-favicon-meta>${escapeHtml(draft.faviconName || (draft.faviconUrl ? "저장된 파비콘 연결됨" : "파비콘 없음"))}</span>
                </div>
                <div class="admin-popup-upload__controls">
                  <label class="admin-secondary-button admin-secondary-button--file" for="admin-site-settings-favicon-upload">파비콘 업로드</label>
                  <input class="admin-popup-upload__input" id="admin-site-settings-favicon-upload" type="file" accept="image/png,image/x-icon,image/vnd.microsoft.icon,image/svg+xml" data-admin-site-settings-image-upload="favicon" />
                  <button class="admin-secondary-button" type="button" data-admin-site-settings-favicon-clear ${draft.faviconUrl ? "" : "disabled"}>파비콘 제거</button>
                </div>
                <label class="form-field">
                  <span class="field-label">파비콘 URL</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="faviconUrlInput" value="${escapeHtml(draft.faviconUrlInput || "")}" placeholder="https://example.com/favicon.png" data-admin-site-settings-field="faviconUrlInput" />
                  </div>
                </label>
              </div>

              <div class="admin-popup-upload">
                <div class="admin-popup-upload__head">
                  <div>
                    <strong>대표 이미지</strong>
                    <p>권장 사이즈: 1200 x 630px 이상, JPG/PNG/WebP, 5MB 이하. 카카오톡, 페이스북, X 공유 카드에 사용됩니다.</p>
                  </div>
                  <span class="admin-badge is-neutral" data-admin-site-settings-share-meta>${escapeHtml(draft.shareImageName || (draft.shareImageUrl ? "저장된 대표 이미지 연결됨" : "대표 이미지 없음"))}</span>
                </div>
                <div class="admin-popup-upload__controls">
                  <label class="admin-secondary-button admin-secondary-button--file" for="admin-site-settings-share-upload">대표 이미지 업로드</label>
                  <input class="admin-popup-upload__input" id="admin-site-settings-share-upload" type="file" accept="image/png,image/jpeg,image/webp" data-admin-site-settings-image-upload="share" />
                  <button class="admin-secondary-button" type="button" data-admin-site-settings-share-clear ${draft.shareImageUrl ? "" : "disabled"}>대표 이미지 제거</button>
                </div>
                <label class="form-field">
                  <span class="field-label">대표 이미지 URL</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="shareImageUrlInput" value="${escapeHtml(draft.shareImageUrlInput || "")}" placeholder="https://example.com/share-card.jpg" data-admin-site-settings-field="shareImageUrlInput" />
                  </div>
                </label>
              </div>
            </section>

            <div class="admin-action-row">
              <button class="admin-primary-button" type="submit">기본 설정 저장</button>
            </div>
          </form>
        </div>

        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>실시간 미리보기</strong>
            <span class="admin-badge is-neutral">브라우저 탭 / 공유 카드</span>
          </div>
          <div class="admin-site-preview" data-admin-site-settings-preview>
            ${renderSiteSettingsPreviewMarkup(draft)}
          </div>
        </div>
      </div>
    </section>
    ${renderPlatformLogoAdminSection()}
  `;
}

function renderHomePopupOverlay() {
  const popup = state.bootstrap?.popup;
  if (!popup || !shouldShowHomePopup()) return "";
  return `
    <div class="promo-popup-layer">
      <button class="promo-popup-layer__backdrop" type="button" aria-label="팝업 닫기" data-popup-close="${escapeHtml(popup.id)}"></button>
      <div class="promo-popup-layer__sheet">
        <button class="promo-popup-layer__card" type="button" data-route="${escapeHtml(popup.route)}">
          ${renderPromoPopupCard(popup)}
        </button>
        <div class="promo-popup-layer__actions">
          <button class="promo-popup-layer__action" type="button" data-popup-dismiss-today="${escapeHtml(popup.id)}">오늘 그만보기</button>
          <button class="promo-popup-layer__action" type="button" data-popup-close="${escapeHtml(popup.id)}">닫기</button>
        </div>
      </div>
    </div>
  `;
}

function renderPopupPreviewMarkup(popup) {
  return `
    ${renderPromoPopupCard(popup, { preview: true })}
    <div class="promo-popup-layer__actions promo-popup-layer__actions--preview">
      <span class="promo-popup-layer__action is-static">오늘 그만보기</span>
      <span class="promo-popup-layer__action is-static">닫기</span>
    </div>
  `;
}

function renderHomeBannerPreviewMarkup(banner) {
  return renderHomeBannerCard(banner, { compact: false, index: 0, total: 1, interactive: false });
}

function renderPlatformLogoAdminSection() {
  const platforms = getAdminPlatformSections();
  const draft = state.adminPlatformSectionDraft || platformSectionToDraft(platforms[0]);
  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>플랫폼 로고 관리</h2>
        <p>홈 서비스 그리드와 주문 페이지 플랫폼 탭에 노출되는 로고 이미지를 수정합니다. 이미지가 없으면 대체 텍스트 아이콘이 사용됩니다.</p>
      </div>

      <div class="admin-banner-list">
        ${platforms
          .map(
            (platform) => `
              <button
                class="admin-banner-list__item ${platform.id === state.ui.adminSelectedPlatformSectionId ? "is-active" : ""}"
                type="button"
                data-admin-platform-section-select="${platform.id}"
              >
                <span>${escapeHtml(platform.displayName)}</span>
                <strong>${escapeHtml(String(platform.productCount || 0))}개</strong>
              </button>
            `
          )
          .join("")}
      </div>

      <div class="admin-management-layout admin-management-layout--popup">
        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>플랫폼 로고 편집</strong>
          </div>
          <form class="admin-form" data-admin-platform-section-form>
            <label class="form-field">
              <span class="field-label">플랫폼 이름</span>
              <div class="field-shell">
                <input class="field-input" type="text" value="${escapeHtml(draft.displayName)}" disabled />
              </div>
            </label>
            <div class="admin-popup-upload">
              <div class="admin-popup-upload__head">
                <div>
                  <strong>플랫폼 로고 이미지</strong>
                  <p>권장 사이즈: 정사각 256 x 256px 이상, JPG/PNG/WebP, 2MB 이하. 비율은 고정 슬롯에서 자동으로 맞춰집니다.</p>
                </div>
                <span class="admin-badge is-neutral" data-admin-platform-section-image-meta>${escapeHtml(draft.logoImageName || (draft.logoImageUrl ? "저장된 로고 이미지 연결됨" : "텍스트 아이콘 사용 중"))}</span>
              </div>
              <div class="admin-popup-upload__controls">
                <label class="admin-secondary-button admin-secondary-button--file" for="admin-platform-section-image-upload">로고 업로드</label>
                <input class="admin-popup-upload__input" id="admin-platform-section-image-upload" type="file" accept="image/png,image/jpeg,image/webp" data-admin-platform-section-image-upload />
                <button class="admin-secondary-button" type="button" data-admin-platform-section-image-clear ${draft.logoImageUrl ? "" : "disabled"}>로고 제거</button>
              </div>
              <label class="form-field">
                <span class="field-label">로고 이미지 URL</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="logoImageUrlInput" value="${escapeHtml(draft.logoImageUrlInput || "")}" placeholder="https://example.com/platform-logo.jpg" data-admin-platform-section-field="logoImageUrlInput" />
                </div>
              </label>
            </div>
            <div class="admin-two-column">
              <label class="form-field">
                <span class="field-label">대체 텍스트 아이콘</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="icon" value="${escapeHtml(draft.icon)}" maxlength="6" data-admin-platform-section-field="icon" />
                </div>
              </label>
              <label class="form-field">
                <span class="field-label">강조 색상</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="accentColor" value="${escapeHtml(draft.accentColor)}" placeholder="#4c76ff" data-admin-platform-section-field="accentColor" />
                </div>
              </label>
            </div>
            <button class="admin-primary-button" type="submit">플랫폼 로고 저장</button>
          </form>
        </div>

        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>플랫폼 미리보기</strong>
            <span class="admin-badge is-neutral">${escapeHtml(draft.slug || "")}</span>
          </div>
          <div class="admin-home-banner-preview" data-admin-platform-section-preview>
            ${renderPlatformLogoPreviewMarkup(draft)}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderHomeBannerAdminSection() {
  const banners = getAdminHomeBanners();
  const draft = state.adminHomeBannerDraft || homeBannerToDraft(banners[0]);
  const imageMeta = draft.imageName || (draft.imageUrl ? "저장된 배너 이미지 연결됨" : "기본 이미지 자동 적용 중");

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>메인 배너 관리</h2>
        <p>홈 상단 스트립과 메인 캐러셀에 노출되는 배너 이미지를 수정합니다. 첫 번째 배너는 상단 얇은 스트립에도 함께 사용됩니다.</p>
      </div>

      <div class="admin-banner-list">
        ${banners
          .map(
            (banner) => `
              <button
                class="admin-banner-list__item ${banner.id === state.ui.adminSelectedHomeBannerId ? "is-active" : ""}"
                type="button"
                data-admin-home-banner-select="${banner.id}"
              >
                <span>${escapeHtml(banner.title)}</span>
                <strong>${escapeHtml(String(banner.sortOrder || 0))}번</strong>
              </button>
            `
          )
          .join("")}
      </div>

      <div class="admin-management-layout admin-management-layout--popup">
        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>배너 슬롯 편집</strong>
          </div>
          <form class="admin-form" data-admin-home-banner-form>
            <label class="form-field">
              <span class="field-label">배너 이름(관리용)</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="title" value="${escapeHtml(draft.title)}" data-admin-home-banner-field="title" />
              </div>
            </label>
            <div class="admin-popup-upload">
              <div class="admin-popup-upload__head">
                <div>
                  <strong>배너 이미지</strong>
                  <p>권장 사이즈: 1600 x 720px 이상, JPG/PNG/WebP, 5MB 이하. 홈 상단 배너 영역은 고정 크기로 노출되며 이미지는 자동 크롭됩니다.</p>
                </div>
                <span class="admin-badge is-neutral">${escapeHtml(imageMeta)}</span>
              </div>
              <div class="admin-popup-upload__controls">
                <label class="admin-secondary-button admin-secondary-button--file" for="admin-home-banner-image-upload">이미지 업로드</label>
                <input class="admin-popup-upload__input" id="admin-home-banner-image-upload" type="file" accept="image/png,image/jpeg,image/webp" data-admin-home-banner-image-upload />
                <button class="admin-secondary-button" type="button" data-admin-home-banner-image-clear ${draft.imageUrl && draft.imageUrl !== defaultHomeBannerImageUrl(draft.id, draft.theme) ? "" : "disabled"}>기본 이미지 복원</button>
              </div>
              <label class="form-field">
                <span class="field-label">이미지 URL</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="imageUrlInput" value="${escapeHtml(draft.imageUrlInput || "")}" placeholder="https://example.com/banner.jpg" data-admin-home-banner-field="imageUrlInput" />
                </div>
              </label>
            </div>
            <div class="admin-two-column">
              <label class="form-field">
                <span class="field-label">이동 경로 / URL</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="route" value="${escapeHtml(draft.route)}" data-admin-home-banner-field="route" />
                </div>
              </label>
            </div>
            <div class="admin-two-column">
              <label class="form-field">
                <span class="field-label">정렬 순서</span>
                <div class="field-shell">
                  <input class="field-input" type="number" name="sortOrder" value="${escapeHtml(String(draft.sortOrder || 0))}" data-admin-home-banner-field="sortOrder" />
                </div>
              </label>
              <div class="form-field">
                <span class="field-label">노출 방식</span>
                <p class="admin-inline-note">배너 슬롯은 이미지 전용으로 고정되며 텍스트 UI를 별도로 그리지 않습니다.</p>
              </div>
            </div>
            <label class="admin-toggle">
              <input type="checkbox" name="isActive" ${draft.isActive ? "checked" : ""} data-admin-home-banner-field="isActive" />
              <span>홈 배너 노출</span>
            </label>
            <button class="admin-primary-button" type="submit">배너 저장</button>
          </form>
        </div>

        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>배너 미리보기</strong>
            <span class="admin-badge ${draft.isActive ? "is-success" : "is-neutral"}">${draft.isActive ? "노출 중" : "비노출"}</span>
          </div>
          <div class="admin-home-banner-preview" data-admin-home-banner-preview>
            ${renderHomeBannerPreviewMarkup(draft)}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderPopupAdminSection() {
  const draft = state.adminPopupDraft || blankPopupDraft();
  const previewPopup = popupPreviewPayload(draft);
  const imageMeta = draft.imageName || (draft.imageUrl ? "저장된 이미지 연결됨" : "이미지 없음");

  return `
    <div class="admin-section-stack">
      <section class="admin-card">
        <div class="section-head section-head--compact">
          <h2>홈 팝업 관리</h2>
          <p>홈 첫 진입 시 띄우는 프로모션 팝업을 켜고 끄거나, 이미지와 문구, 이동 경로를 직접 수정할 수 있습니다.</p>
        </div>

        <div class="admin-management-layout admin-management-layout--popup">
          <div class="admin-card admin-subcard">
            <div class="admin-subcard__head">
              <strong>팝업 편집</strong>
            </div>
            <form class="admin-form" data-admin-popup-form>
              <label class="form-field">
                <span class="field-label">관리용 이름</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="name" value="${escapeHtml(draft.name)}" data-admin-popup-field="name" />
                </div>
              </label>
              <label class="form-field">
                <span class="field-label">뱃지 문구</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="badgeText" value="${escapeHtml(draft.badgeText)}" placeholder="예: 상단(1~5위) 노출 보장!" data-admin-popup-field="badgeText" />
                </div>
              </label>
              <label class="form-field">
                <span class="field-label">메인 제목</span>
                <textarea class="field-textarea" name="title" rows="3" data-admin-popup-field="title">${escapeHtml(draft.title)}</textarea>
              </label>
              <label class="form-field">
                <span class="field-label">보조 설명</span>
                <textarea class="field-textarea" name="description" rows="3" data-admin-popup-field="description">${escapeHtml(draft.description)}</textarea>
              </label>
              <div class="admin-popup-upload">
                <div class="admin-popup-upload__head">
                  <div>
                    <strong>배너 이미지</strong>
                    <p>권장 사이즈: 1200 x 800px 이상, JPG/PNG/WebP, 5MB 이하. 너무 세로로 긴 이미지는 상하가 잘릴 수 있습니다.</p>
                  </div>
                  <span class="admin-badge is-neutral" data-admin-popup-image-meta>${escapeHtml(imageMeta)}</span>
                </div>
                <div class="admin-popup-upload__controls">
                  <label class="admin-secondary-button admin-secondary-button--file" for="admin-popup-image-upload">이미지 업로드</label>
                  <input class="admin-popup-upload__input" id="admin-popup-image-upload" type="file" accept="image/png,image/jpeg,image/webp" data-admin-popup-image-upload />
                  <button class="admin-secondary-button" type="button" data-admin-popup-image-clear ${draft.imageUrl ? "" : "disabled"}>이미지 제거</button>
                </div>
                <label class="form-field">
                  <span class="field-label">이미지 URL</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="imageUrlInput" value="${escapeHtml(draft.imageUrlInput || "")}" placeholder="https://example.com/popup-banner.jpg" data-admin-popup-field="imageUrlInput" />
                  </div>
                </label>
                <p class="admin-inline-note">업로드한 이미지가 있으면 우선 사용되며, URL 입력으로도 교체할 수 있습니다. 중요한 텍스트는 좌측 영역에 배치하는 것을 권장합니다.</p>
              </div>
              <div class="admin-two-column">
                <label class="form-field">
                  <span class="field-label">이동 경로 / URL</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="route" value="${escapeHtml(draft.route)}" placeholder="/products/cat_youtube_views 또는 https://example.com" data-admin-popup-field="route" />
                  </div>
                </label>
                <label class="form-field">
                  <span class="field-label">컬러 테마</span>
                  <div class="field-shell">
                    <select class="field-select" name="theme" data-admin-popup-field="theme">
                      ${[
                        ["coral", "Coral Launch"],
                        ["midnight", "Midnight Motion"],
                        ["blue", "Blue Impact"],
                      ]
                        .map(([value, label]) => `<option value="${value}" ${draft.theme === value ? "selected" : ""}>${label}</option>`)
                        .join("")}
                    </select>
                  </div>
                </label>
              </div>
              <label class="admin-toggle">
                <input type="checkbox" name="isActive" ${draft.isActive ? "checked" : ""} data-admin-popup-field="isActive" />
                <span>홈에서 팝업 노출</span>
              </label>
              <p class="admin-inline-note">팝업 카드를 누르면 위 경로로 이동합니다. 내부 경로와 외부 URL 모두 입력할 수 있습니다.</p>
              <button class="admin-primary-button" type="submit">팝업 저장</button>
            </form>
          </div>

          <div class="admin-card admin-subcard">
            <div class="admin-subcard__head">
              <strong>실시간 미리보기</strong>
              <span class="admin-badge ${draft.isActive ? "is-success" : "is-neutral"}" data-admin-popup-status>${draft.isActive ? "노출 중" : "비노출"}</span>
            </div>
            <div class="admin-popup-preview" data-admin-popup-preview>
              ${renderPopupPreviewMarkup(previewPopup)}
            </div>
          </div>
        </div>
      </section>
      ${renderHomeBannerAdminSection()}
    </div>
  `;
}

function renderAdminInsightStrip(items, className = "") {
  return `
    <div class="admin-insight-grid ${className}">
      ${items
        .map(
          (item) => `
            <article class="admin-insight-card ${item.tone ? `is-${item.tone}` : ""}">
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
              <p>${escapeHtml(item.description || "")}</p>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderAdminFormSection(title, description, content, { open = true } = {}) {
  return `
    <details class="admin-form-section" ${open ? "open" : ""}>
      <summary>
        <div>
          <strong>${escapeHtml(title)}</strong>
          <p>${escapeHtml(description)}</p>
        </div>
        <span>${open ? "열림" : "선택"}</span>
      </summary>
      <div class="admin-form-section__body">
        ${content}
      </div>
    </details>
  `;
}

function isSupplierDispatchIssue(order) {
  const text = `${order?.supplierDispatchLabel || ""} ${order?.supplierStatus || ""}`.toLowerCase();
  return /(실패|오류|failed|cancel|취소|blocked|error)/.test(text);
}

function renderCustomerAdminSection() {
  const customers = getAdminCustomers();
  const selectedCustomer = getSelectedAdminCustomer();
  const draft = state.adminCustomerDraft || blankCustomerDraft();
  const activeFilter = state.ui.adminCustomerFilter;
  const search = state.ui.adminCustomerSearch.trim().toLowerCase();
  const filteredCustomers = customers.filter((customer) => {
    if (activeFilter === "inactive" && customer.isActive) return false;
    if (activeFilter !== "all" && activeFilter !== "inactive" && customer.role !== activeFilter) return false;
    if (!search) return true;
    return String(customer.searchText || "").includes(search);
  });
  const activeCustomers = customers.filter((customer) => customer.isActive).length;
  const marketingOptInCount = customers.filter((customer) => customer.marketingOptIn).length;
  const selectedIdentitySummary = Array.isArray(selectedCustomer?.socialIdentities) && selectedCustomer.socialIdentities.length
    ? `
      <div class="admin-detail-pill-row">
        ${selectedCustomer.socialIdentities
          .map((identity) => `<span class="admin-detail-pill">${escapeHtml(identity.providerLabel || identity.provider)}</span>`)
          .join("")}
      </div>
    `
    : `<p class="admin-inline-note">연결된 소셜 계정이 없습니다.</p>`;
  const selectedConsentSummary = Array.isArray(selectedCustomer?.consents) && selectedCustomer.consents.length
    ? `
      <div class="admin-detail-list">
        ${selectedCustomer.consents
          .map(
            (consent) => `
              <article>
                <strong>${escapeHtml(consent.consentLabel || consent.consentType)}</strong>
                <span>${consent.isAgreed ? "동의" : "미동의"} · ${escapeHtml(consent.agreedAt || "-")} · v${escapeHtml(consent.consentVersion || "")}</span>
              </article>
            `
          )
          .join("")}
      </div>
    `
    : `<p class="admin-inline-note">저장된 동의 이력이 없습니다.</p>`;

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>고객/계정 관리</h2>
        <p>고객 계정을 생성하고 등급, 역할, 활성 상태, 잔액을 관리할 수 있습니다.</p>
      </div>

      ${renderAdminInsightStrip(
        [
          { label: "전체 고객", value: `${customers.length}명`, description: "검색과 역할 필터 기준의 전체 회원 수" },
          { label: "활성 계정", value: `${activeCustomers}명`, description: "현재 로그인 가능 상태로 운영 중인 계정" },
          { label: "마케팅 동의", value: `${marketingOptInCount}명`, description: "마케팅 수신 동의가 저장된 고객" },
          { label: "현재 결과", value: `${filteredCustomers.length}명`, description: "현재 필터와 검색 조건에 맞는 고객" },
        ],
        "admin-insight-grid--compact"
      )}

      <div class="admin-customer-shell">
        <div class="admin-card admin-subcard admin-pane">
          <div class="admin-subcard__head">
            <strong>고객 목록</strong>
            <button class="admin-secondary-button" type="button" data-admin-customer-new>새 고객</button>
          </div>
          <div class="admin-toolbar admin-toolbar--stack">
            <div class="search-shell">
                <input
                  class="search-input"
                  type="text"
                  value="${escapeHtml(state.ui.adminCustomerSearch)}"
                  placeholder="이름, 이메일, 연락처, 메모 검색"
                  data-admin-customer-search
                />
            </div>
            <div class="filter-row">
              ${[
                ["all", `전체 ${customers.length}`],
                ["customer", `고객 ${customers.filter((customer) => customer.role === "customer").length}`],
                ["operator", `운영 ${customers.filter((customer) => customer.role === "operator").length}`],
                ["admin", `관리자 ${customers.filter((customer) => customer.role === "admin").length}`],
                ["inactive", `비활성 ${customers.filter((customer) => !customer.isActive).length}`],
              ]
                .map(
                  ([key, label]) => `
                    <button class="filter-chip ${activeFilter === key ? "is-active" : ""}" type="button" data-admin-customer-filter="${key}">
                      ${escapeHtml(label)}
                    </button>
                `
                )
                .join("")}
            </div>
          </div>
          <div class="admin-customer-list">
            ${filteredCustomers.length
              ? filteredCustomers
                  .map(
                (customer) => `
                  <button
                    class="admin-record-row admin-record-row--customer ${state.ui.adminSelectedCustomerId === customer.id && state.ui.adminCustomerMode !== "new" ? "is-active" : ""}"
                    type="button"
                    data-admin-select-customer="${customer.id}"
                  >
                    <div class="admin-record-row__main">
                      <strong>${escapeHtml(customer.name)}</strong>
                      <p>${escapeHtml(customer.emailMasked || "이메일 비공개")} · ${escapeHtml(customer.phoneMasked || "연락처 비공개")}</p>
                    </div>
                    <div class="admin-record-row__meta">
                      <span>${escapeHtml(customer.role)}</span>
                      <span>${escapeHtml(customer.tier)}</span>
                      <span>${customer.hasPassword ? "로그인 가능" : "비밀번호 없음"}</span>
                    </div>
                    <div class="admin-record-row__stats">
                      <strong>${escapeHtml(customer.balanceLabel)}</strong>
                      <small>주문 ${escapeHtml(String(customer.orderCount || 0))} · 누적 ${escapeHtml(customer.totalSpentLabel || "0원")}</small>
                    </div>
                    <div class="admin-record-row__status">
                      <span class="admin-badge ${customer.isActive ? "is-success" : "is-neutral"}">${customer.isActive ? "활성" : "비활성"}</span>
                      <small>${escapeHtml(customer.lastLoginAt || customer.lastOrderLabel || "활동 기록 없음")}</small>
                    </div>
                  </button>
                `
              )
                  .join("")
              : `<div class="admin-empty-card"><strong>조건에 맞는 고객이 없습니다.</strong><p>필터나 검색어를 바꿔 다시 확인해 주세요.</p></div>`}
          </div>
        </div>

        <div class="admin-customer-main">
          <div class="admin-card admin-subcard admin-pane">
            <div class="admin-subcard__head">
              <strong>선택 고객 상세</strong>
              ${selectedCustomer ? `<span class="admin-badge ${selectedCustomer.isActive ? "is-success" : "is-neutral"}">${escapeHtml(selectedCustomer.accountStatus || (selectedCustomer.isActive ? "active" : "suspended"))}</span>` : ""}
            </div>
            ${
              selectedCustomer
                ? `
                  <div class="admin-customer-detail-card">
                    <div class="admin-customer-detail-card__row">
                      <strong>${escapeHtml(selectedCustomer.name)}</strong>
                      <span class="admin-inline-note">${escapeHtml(selectedCustomer.role)} · ${escapeHtml(selectedCustomer.tier)}</span>
                    </div>
                    <div class="admin-customer-detail-card__grid">
                      <article><span>이메일</span><strong>${escapeHtml(selectedCustomer.email || selectedCustomer.emailMasked || "-")}</strong></article>
                      <article><span>연락처</span><strong>${escapeHtml(selectedCustomer.phone || selectedCustomer.phoneMasked || "-")}</strong></article>
                      <article><span>최근 로그인</span><strong>${escapeHtml(selectedCustomer.lastLoginAt || "기록 없음")}</strong></article>
                      <article><span>마케팅 동의</span><strong>${selectedCustomer.marketingOptIn ? "동의" : "미동의"}</strong></article>
                      <article><span>누적 주문</span><strong>${escapeHtml(String(selectedCustomer.orderCount || 0))}건</strong></article>
                      <article><span>총 결제</span><strong>${escapeHtml(selectedCustomer.totalSpentLabel || "0원")}</strong></article>
                    </div>
                    ${selectedIdentitySummary}
                    ${selectedConsentSummary}
                  </div>

                  <form class="admin-form admin-balance-form" data-admin-balance-form>
                    <div class="admin-subcard__head">
                      <strong>잔액 조정</strong>
                    </div>
                    <input type="hidden" name="customerId" value="${escapeHtml(selectedCustomer.id)}" />
                    <div class="admin-two-column">
                      <label class="form-field">
                        <span class="field-label">조정 금액</span>
                        <div class="field-shell">
                          <input class="field-input" type="number" name="amount" placeholder="예: 10000 또는 -5000" />
                        </div>
                      </label>
                      <label class="form-field">
                        <span class="field-label">현재 잔액</span>
                        <div class="field-shell">
                          <input class="field-input" type="text" value="${escapeHtml(selectedCustomer.balanceLabel)}" disabled />
                        </div>
                      </label>
                    </div>
                    <label class="form-field">
                      <span class="field-label">사유</span>
                      <div class="field-shell">
                        <input class="field-input" type="text" name="memo" placeholder="예: 수동 충전, 정산 조정" />
                      </div>
                    </label>
                    <button class="admin-secondary-button" type="submit">잔액 반영</button>
                  </form>
                `
                : `<div class="admin-empty-card"><strong>선택된 고객이 없습니다.</strong><p>왼쪽 목록에서 계정을 선택하면 상세 정보와 운영 액션이 표시됩니다.</p></div>`
            }
          </div>

          <div class="admin-card admin-subcard admin-pane">
            <div class="admin-subcard__head">
              <strong>${draft.id ? "계정 수정" : "새 계정 생성"}</strong>
            </div>
            <form class="admin-form" data-admin-customer-form>
              <div class="admin-two-column">
                <label class="form-field">
                  <span class="field-label">이름</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="name" value="${escapeHtml(draft.name)}" data-admin-customer-field="name" />
                  </div>
                </label>
                <label class="form-field">
                  <span class="field-label">이메일</span>
                  <div class="field-shell">
                    <input class="field-input" type="email" name="email" value="${escapeHtml(draft.email)}" data-admin-customer-field="email" />
                  </div>
                </label>
              </div>
              <div class="admin-two-column">
                <label class="form-field">
                  <span class="field-label">연락처</span>
                  <div class="field-shell">
                    <input class="field-input" type="text" name="phone" value="${escapeHtml(draft.phone)}" data-admin-customer-field="phone" />
                  </div>
                </label>
                <label class="form-field">
                  <span class="field-label">고객 로그인 비밀번호</span>
                  <div class="field-shell">
                    <input class="field-input" type="password" name="password" value="" placeholder="${draft.id ? "변경 시에만 입력" : "8자 이상 입력"}" data-admin-customer-field="password" />
                  </div>
                </label>
              </div>
              <p class="admin-inline-note">고객 로그인은 일반 고객 역할 계정에서만 사용됩니다. 수정 시 비밀번호를 비워두면 기존 비밀번호를 유지합니다.</p>
              <div class="admin-two-column">
                <label class="form-field">
                  <span class="field-label">등급</span>
                  <div class="field-shell">
                    <select class="field-select" name="tier" data-admin-customer-field="tier">
                      ${["STANDARD", "BUSINESS", "PRO"]
                        .map((tier) => `<option value="${tier}" ${draft.tier === tier ? "selected" : ""}>${tier}</option>`)
                        .join("")}
                    </select>
                  </div>
                </label>
                <label class="form-field">
                  <span class="field-label">역할</span>
                  <div class="field-shell">
                    <select class="field-select" name="role" data-admin-customer-field="role">
                      ${[
                        ["customer", "고객"],
                        ["operator", "운영자"],
                        ["admin", "관리자"],
                      ]
                        .map(([value, label]) => `<option value="${value}" ${draft.role === value ? "selected" : ""}>${label}</option>`)
                        .join("")}
                    </select>
                  </div>
                </label>
              </div>
              <label class="form-field">
                <span class="field-label">메모</span>
                <textarea class="field-textarea" name="notes" rows="4" data-admin-customer-field="notes">${escapeHtml(draft.notes)}</textarea>
              </label>
              <label class="admin-toggle">
                <input type="checkbox" name="isActive" ${draft.isActive ? "checked" : ""} data-admin-customer-field="isActive" />
                <span>활성 계정으로 운영</span>
              </label>
              <div class="admin-action-row">
                <button class="admin-primary-button" type="submit">${draft.id ? "고객 저장" : "고객 생성"}</button>
                ${selectedCustomer && selectedCustomer.id !== "user_demo" ? `<button class="admin-secondary-button" type="button" data-admin-delete-customer="${selectedCustomer.id}">삭제/비활성</button>` : ""}
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderCatalogAdminSection() {
  const groups = getAdminPlatformGroups();
  const categories = getAdminCategories();
  const selectedCategory = getSelectedAdminCategory();
  const selectedSupplierService = getSelectedAdminSupplierService();
  const categoryDraft = state.adminCategoryDraft || blankCategoryDraft(groups[0]?.id || "");
  const categoryProducts = getManageProducts(selectedCategory?.id || state.ui.adminSelectedCategoryId);
  const selectedManageProduct = getSelectedManageProduct();
  const productDraft = state.adminProductDraft || blankProductDraft(selectedCategory?.id || "");
  const categoryName = selectedCategory?.name || "카테고리 미선택";

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>상품 관리</h2>
        <p>카테고리 생성/편집과 상품 생성/편집/삭제를 통해 사용자 패널 노출 상품을 직접 관리할 수 있습니다.</p>
      </div>

      ${renderAdminInsightStrip(
        [
          { label: "카테고리", value: `${categories.length}개`, description: "운영 중인 전체 카테고리 수" },
          { label: "선택 카테고리", value: categoryName, description: `${categoryProducts.length}개 상품 연결` },
          { label: "최근 공급사 추천", value: selectedSupplierService ? selectedSupplierService.externalServiceId : "-", description: selectedSupplierService ? selectedSupplierService.name : "선택된 공급사 서비스 없음" },
          { label: "상품 편집 상태", value: productDraft.id ? "수정 중" : "신규 작성", description: productDraft.id ? productDraft.name : "새 상품 작성 폼" },
        ],
        "admin-insight-grid--compact"
      )}

      <div class="admin-management-layout admin-management-layout--catalog-top">
        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>카테고리</strong>
            <button class="admin-secondary-button" type="button" data-admin-category-new>새 카테고리</button>
          </div>
          <div class="admin-product-list">
            ${categories
              .map(
                (category) => `
                  <button
                    class="admin-product-card ${state.ui.adminSelectedCategoryId === category.id && state.ui.adminCategoryMode !== "new" ? "is-active" : ""}"
                    type="button"
                    data-admin-category-select="${category.id}"
                  >
                    <div class="admin-product-card__top">
                      <strong>${escapeHtml(category.name)}</strong>
                      <span class="admin-badge ${category.isActive ? "is-success" : "is-neutral"}">${category.isActive ? "노출" : "숨김"}</span>
                    </div>
                    <p>${escapeHtml(category.platformName)} · ${escapeHtml(category.groupName)}</p>
                    <div class="admin-product-card__meta">
                      <span>상품 ${escapeHtml(String(category.productCount || 0))}</span>
                      <span>활성 ${escapeHtml(String(category.activeProductCount || 0))}</span>
                    </div>
                  </button>
                `
              )
              .join("")}
          </div>
        </div>

        <div class="admin-card admin-subcard admin-pane">
          <div class="admin-subcard__head">
            <strong>${categoryDraft.id ? "카테고리 수정" : "카테고리 생성"}</strong>
          </div>
          <form class="admin-form" data-admin-category-form>
            ${renderAdminFormSection(
              "기본 정보",
              "플랫폼 그룹과 공개 카테고리명을 먼저 정의합니다.",
              `
                <label class="form-field">
                  <span class="field-label">플랫폼 그룹</span>
                  <div class="field-shell">
                    <select class="field-select" name="groupId" data-admin-category-field="groupId">
                      ${groups
                        .map(
                          (group) => `
                            <option value="${escapeHtml(group.id)}" ${categoryDraft.groupId === group.id ? "selected" : ""}>
                              ${escapeHtml(group.platformName)} · ${escapeHtml(group.name)}
                            </option>
                          `
                        )
                        .join("")}
                    </select>
                  </div>
                </label>
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">카테고리명</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="name" value="${escapeHtml(categoryDraft.name)}" data-admin-category-field="name" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">옵션 라벨</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="optionLabelName" value="${escapeHtml(categoryDraft.optionLabelName)}" data-admin-category-field="optionLabelName" />
                    </div>
                  </label>
                </div>
                <label class="form-field">
                  <span class="field-label">설명</span>
                  <textarea class="field-textarea" name="description" rows="3" data-admin-category-field="description">${escapeHtml(categoryDraft.description)}</textarea>
                </label>
              `
            )}
            ${renderAdminFormSection(
              "노출 카피",
              "목록/상세 상단에 노출할 제목과 설명 문구를 구성합니다.",
              `
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">히어로 제목</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="heroTitle" value="${escapeHtml(categoryDraft.heroTitle)}" data-admin-category-field="heroTitle" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">히어로 부제</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="heroSubtitle" value="${escapeHtml(categoryDraft.heroSubtitle)}" data-admin-category-field="heroSubtitle" />
                    </div>
                  </label>
                </div>
                <label class="form-field">
                  <span class="field-label">상세 설명 HTML</span>
                  <textarea class="field-textarea" name="serviceDescriptionHtml" rows="4" data-admin-category-field="serviceDescriptionHtml">${escapeHtml(categoryDraft.serviceDescriptionHtml)}</textarea>
                </label>
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">주의사항</span>
                    <textarea class="field-textarea" name="cautionText" rows="4" data-admin-category-field="cautionText">${escapeHtml(categoryDraft.cautionText)}</textarea>
                  </label>
                  <label class="form-field">
                    <span class="field-label">환불 안내</span>
                    <textarea class="field-textarea" name="refundText" rows="4" data-admin-category-field="refundText">${escapeHtml(categoryDraft.refundText)}</textarea>
                  </label>
                </div>
              `
            )}
            ${renderAdminFormSection(
              "노출 상태",
              "정렬과 공개 여부를 마지막에 확정합니다.",
              `
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">정렬 순서</span>
                    <div class="field-shell">
                      <input class="field-input" type="number" name="sortOrder" value="${escapeHtml(String(categoryDraft.sortOrder || 0))}" data-admin-category-field="sortOrder" />
                    </div>
                  </label>
                  <label class="admin-toggle">
                    <input type="checkbox" name="isActive" ${categoryDraft.isActive ? "checked" : ""} data-admin-category-field="isActive" />
                    <span>카테고리 노출</span>
                  </label>
                </div>
              `,
              { open: false }
            )}
            <div class="admin-action-row">
              <button class="admin-primary-button" type="submit">${categoryDraft.id ? "카테고리 저장" : "카테고리 생성"}</button>
              ${state.ui.adminCategoryMode !== "new" && selectedCategory ? `<button class="admin-secondary-button" type="button" data-admin-delete-category="${selectedCategory.id}">삭제/숨김</button>` : ""}
            </div>
          </form>
        </div>
      </div>

      <div class="admin-management-layout admin-management-layout--products">
        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>${escapeHtml(selectedCategory?.name || "상품")}</strong>
            <button class="admin-secondary-button" type="button" data-admin-product-new>새 상품</button>
          </div>
          <div class="admin-product-list">
            ${categoryProducts.length
              ? categoryProducts
                  .map(
                    (product) => `
                      <button
                        class="admin-product-card ${state.ui.adminSelectedManageProductId === product.id && state.ui.adminProductMode !== "new" ? "is-active" : ""}"
                        type="button"
                        data-admin-manage-product-select="${product.id}"
                      >
                        <div class="admin-product-card__top">
                          <strong>${escapeHtml(product.name)}</strong>
                          <span class="admin-badge ${product.isActive ? "is-success" : "is-neutral"}">${product.isActive ? "판매중" : "숨김"}</span>
                        </div>
                        <p>${escapeHtml(product.optionName || "기본 옵션")} · ${escapeHtml(product.priceLabel)}</p>
                        <div class="admin-product-card__meta">
                          <span>${escapeHtml(product.productCode)}</span>
                          <span>${escapeHtml(product.priceStrategy)}</span>
                          <span>${escapeHtml(product.formConfig?.preset || "")}</span>
                        </div>
                      </button>
                    `
                  )
                  .join("")
              : `<div class="admin-empty-card"><strong>등록된 상품이 없습니다.</strong><p>이 카테고리에서 바로 새 상품을 만들 수 있습니다.</p></div>`}
          </div>
        </div>

        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>${productDraft.id ? "상품 수정" : "상품 생성"}</strong>
          </div>
          ${
            selectedSupplierService
              ? `
                <div class="admin-inline-note">
                  최근 선택한 공급사 서비스: ${escapeHtml(selectedSupplierService.name)} (#${escapeHtml(selectedSupplierService.externalServiceId)})
                </div>
                ${renderSupplierRequestGuide(selectedSupplierService, { applyLabel: productDraft.id ? "이 상품 폼에 추천 적용" : "새 상품 폼에 추천 적용" })}
              `
              : ""
          }
          <form class="admin-form" data-admin-product-form>
            ${renderAdminFormSection(
              "1) 기본 정보",
              "카테고리, 상품명, 메뉴명, 옵션명, 내부 코드와 기본 배지를 설정합니다.",
              `
                <label class="form-field">
                  <span class="field-label">카테고리</span>
                  <div class="field-shell">
                    <select class="field-select" name="categoryId" data-admin-product-field="categoryId">
                      ${categories
                        .map((category) => `<option value="${escapeHtml(category.id)}" ${productDraft.categoryId === category.id ? "selected" : ""}>${escapeHtml(category.platformName)} · ${escapeHtml(category.name)}</option>`)
                        .join("")}
                    </select>
                  </div>
                </label>
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">상품명</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="name" value="${escapeHtml(productDraft.name)}" data-admin-product-field="name" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">메뉴명</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="menuName" value="${escapeHtml(productDraft.menuName)}" data-admin-product-field="menuName" />
                    </div>
                  </label>
                </div>
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">옵션명</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="optionName" value="${escapeHtml(productDraft.optionName)}" data-admin-product-field="optionName" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">상품 코드</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="productCode" value="${escapeHtml(productDraft.productCode)}" data-admin-product-field="productCode" />
                    </div>
                  </label>
                </div>
              `
            )}
            ${renderAdminFormSection(
              "2) 가격/수량 정책",
              "판매 가격과 최소/최대/증가 단위를 같은 섹션에서 조정합니다.",
              `
                <div class="admin-three-column">
                  <label class="form-field">
                    <span class="field-label">가격</span>
                    <div class="field-shell">
                      <input class="field-input" type="number" name="price" value="${escapeHtml(String(productDraft.price || 0))}" data-admin-product-field="price" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">가격 방식</span>
                    <div class="field-shell">
                      <select class="field-select" name="priceStrategy" data-admin-product-field="priceStrategy">
                        <option value="unit" ${productDraft.priceStrategy === "unit" ? "selected" : ""}>수량형</option>
                        <option value="fixed" ${productDraft.priceStrategy === "fixed" ? "selected" : ""}>패키지형</option>
                      </select>
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">단위</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="unitLabel" value="${escapeHtml(productDraft.unitLabel)}" data-admin-product-field="unitLabel" />
                    </div>
                  </label>
                </div>
                <div class="admin-three-column">
                  <label class="form-field">
                    <span class="field-label">최소</span>
                    <div class="field-shell">
                      <input class="field-input" type="number" name="minAmount" value="${escapeHtml(String(productDraft.minAmount || 1))}" data-admin-product-field="minAmount" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">최대</span>
                    <div class="field-shell">
                      <input class="field-input" type="number" name="maxAmount" value="${escapeHtml(String(productDraft.maxAmount || 1))}" data-admin-product-field="maxAmount" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">증가 단위</span>
                    <div class="field-shell">
                      <input class="field-input" type="number" name="stepAmount" value="${escapeHtml(String(productDraft.stepAmount || 1))}" data-admin-product-field="stepAmount" />
                    </div>
                  </label>
                </div>
              `
            )}
            ${renderAdminFormSection(
              "3) 주문 폼 구성",
              "사용자가 보게 될 입력 라벨과 예상 시작 시간을 설정합니다.",
              `
                <div class="admin-three-column">
                  <label class="form-field">
                    <span class="field-label">폼 프리셋</span>
                    <div class="field-shell">
                      <select class="field-select" name="formPreset" data-admin-product-field="formPreset">
                        ${[
                          ["account_quantity", "계정 ID + 수량"],
                          ["url_quantity", "URL + 수량"],
                          ["keyword_url", "키워드 + URL + 수량"],
                          ["package", "계정 패키지형"],
                          ["url_package", "URL 패키지형"],
                          ["custom", "맞춤 문의형"],
                        ]
                          .map(([value, label]) => `<option value="${value}" ${productDraft.formPreset === value ? "selected" : ""}>${label}</option>`)
                          .join("")}
                      </select>
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">입력 라벨</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="targetLabel" value="${escapeHtml(productDraft.targetLabel)}" data-admin-product-field="targetLabel" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">입력 플레이스홀더</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="targetPlaceholder" value="${escapeHtml(productDraft.targetPlaceholder)}" data-admin-product-field="targetPlaceholder" />
                    </div>
                  </label>
                </div>
                <div class="admin-three-column">
                  <label class="form-field">
                    <span class="field-label">수량 라벨</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="quantityLabel" value="${escapeHtml(productDraft.quantityLabel)}" data-admin-product-field="quantityLabel" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">메모 라벨</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="memoLabel" value="${escapeHtml(productDraft.memoLabel)}" data-admin-product-field="memoLabel" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">예상 시작 시간</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="estimatedTurnaround" value="${escapeHtml(productDraft.estimatedTurnaround)}" data-admin-product-field="estimatedTurnaround" />
                    </div>
                  </label>
                </div>
              `
            )}
            ${renderAdminFormSection(
              "4) 노출/배지",
              "배지, 할인 노출, 판매 상태, 정렬 순서를 같이 관리합니다.",
              `
                <div class="admin-two-column">
                  <label class="form-field">
                    <span class="field-label">배지</span>
                    <div class="field-shell">
                      <input class="field-input" type="text" name="badge" value="${escapeHtml(productDraft.badge)}" data-admin-product-field="badge" />
                    </div>
                  </label>
                  <label class="form-field">
                    <span class="field-label">정렬 순서</span>
                    <div class="field-shell">
                      <input class="field-input" type="number" name="sortOrder" value="${escapeHtml(String(productDraft.sortOrder || 0))}" data-admin-product-field="sortOrder" />
                    </div>
                  </label>
                </div>
                <div class="admin-two-column">
                  <label class="admin-toggle">
                    <input type="checkbox" name="isDiscounted" ${productDraft.isDiscounted ? "checked" : ""} data-admin-product-field="isDiscounted" />
                    <span>할인 상품으로 표시</span>
                  </label>
                  <label class="admin-toggle">
                    <input type="checkbox" name="isActive" ${productDraft.isActive ? "checked" : ""} data-admin-product-field="isActive" />
                    <span>판매 상태로 노출</span>
                  </label>
                </div>
              `
            )}
            ${renderAdminFormSection(
              "5) 고급 옵션",
              "드립/트래픽/반복형 상품에 필요한 추가 주문 필드를 선택합니다.",
              `
                <div class="form-field">
                  <span class="field-label">추가 주문 옵션</span>
                  <div class="admin-advanced-field-grid">
                    ${advancedOrderFieldKeys
                      .map((fieldKey) => {
                        const field = advancedOrderFieldBlueprints[fieldKey];
                        const active = Array.isArray(productDraft.advancedFieldKeys) && productDraft.advancedFieldKeys.includes(fieldKey);
                        return `
                          <label class="admin-check-card ${active ? "is-active" : ""}">
                            <input type="checkbox" ${active ? "checked" : ""} data-admin-product-advanced-field="${fieldKey}" />
                            <strong>${escapeHtml(field.label)}</strong>
                            <span>${escapeHtml(field.description)}</span>
                          </label>
                        `;
                      })
                      .join("")}
                  </div>
                </div>
              `,
              { open: false }
            )}
            <div class="admin-action-row">
              <button class="admin-primary-button" type="submit">${productDraft.id ? "상품 저장" : "상품 생성"}</button>
              ${state.ui.adminProductMode !== "new" && selectedManageProduct ? `<button class="admin-secondary-button" type="button" data-admin-delete-product="${selectedManageProduct.id}">삭제/숨김</button>` : ""}
            </div>
          </form>
        </div>
      </div>
    </section>
  `;
}

function renderAdminOrdersSection() {
  const adminOrders = state.adminBootstrap?.adminOrders || [];
  const activeFilter = state.ui.adminOrderFilter;
  const search = state.ui.adminOrderSearch.trim().toLowerCase();
  const filteredOrders = activeFilter === "all" ? adminOrders : adminOrders.filter((order) => order.status === activeFilter);
  const visibleOrders = filteredOrders.filter((order) => {
    if (!search) return true;
    return String(order.searchText || "").includes(search);
  });
  const queuedCount = adminOrders.filter((order) => order.status === "queued").length;
  const inProgressCount = adminOrders.filter((order) => order.status === "in_progress").length;
  const completedCount = adminOrders.filter((order) => order.status === "completed").length;
  const dispatchIssueCount = adminOrders.filter((order) => isSupplierDispatchIssue(order)).length;

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>주문 운영</h2>
        <p>최근 주문을 확인하고 상태를 수동으로 업데이트할 수 있습니다.</p>
      </div>

      ${renderAdminInsightStrip(
        [
          { label: "대기", value: `${queuedCount}건`, description: "아직 작업이 시작되지 않은 주문" },
          { label: "진행", value: `${inProgressCount}건`, description: "공급사 처리 또는 내부 확인이 필요한 주문" },
          { label: "완료", value: `${completedCount}건`, description: "완료 처리된 주문" },
          { label: "전송 이슈", value: `${dispatchIssueCount}건`, description: "공급사 전송 실패/오류가 감지된 주문" },
        ],
        "admin-insight-grid--compact"
      )}

      <div class="filter-row admin-filter-row">
        ${[
          ["all", `전체 ${adminOrders.length}`],
          ["queued", `대기 ${adminOrders.filter((order) => order.status === "queued").length}`],
          ["in_progress", `진행 ${adminOrders.filter((order) => order.status === "in_progress").length}`],
          ["completed", `완료 ${adminOrders.filter((order) => order.status === "completed").length}`],
        ]
          .map(
            ([key, label]) => `
              <button class="filter-chip ${activeFilter === key ? "is-active" : ""}" type="button" data-admin-order-filter="${key}">
                ${escapeHtml(label)}
              </button>
            `
          )
          .join("")}
      </div>

      <div class="admin-toolbar admin-toolbar--stack">
        <div class="search-shell">
          <input
            class="search-input"
            type="text"
            value="${escapeHtml(state.ui.adminOrderSearch)}"
            placeholder="주문번호, 고객명, 상품명, 입력값, 공급사 검색"
            data-admin-order-search
          />
        </div>
        <p class="admin-inline-note">현재 표시: ${escapeHtml(String(visibleOrders.length))}건</p>
      </div>

      <div class="admin-order-list">
        ${visibleOrders.length
          ? visibleOrders
              .map((order) => {
            const status = statusMap[order.status] || statusMap.queued;
            const hasDispatchIssue = isSupplierDispatchIssue(order);
            const supplierDispatchLabel = order.supplierDispatchLabel || order.supplierStatus || "공급사 미연결";
            return `
              <article class="admin-order-card ${hasDispatchIssue ? "is-risk" : ""}">
                <div class="admin-order-card__top">
                  <div>
                    <span class="order-card__platform">${escapeHtml(order.platformIcon)} ${escapeHtml(order.platformName)}</span>
                    <strong>${escapeHtml(order.productName)}</strong>
                    <p>${escapeHtml(order.customerName)} · ${escapeHtml(order.customerEmailMasked || "비공개")}</p>
                  </div>
                  <div class="admin-order-card__statusbox">
                    <span class="admin-order-card__number">${escapeHtml(order.orderNumber)}</span>
                    <span class="status-pill ${status.className}">${escapeHtml(status.label)}</span>
                  </div>
                </div>
                <div class="admin-order-card__fact-grid">
                  <article><span>결제 금액</span><strong>${escapeHtml(order.totalPriceLabel)}</strong></article>
                  <article><span>접수 시각</span><strong>${escapeHtml(order.createdLabel)}</strong></article>
                  <article><span>공급사</span><strong>${escapeHtml(order.supplierName || "미연결")}</strong></article>
                  <article><span>전송 상태</span><strong>${escapeHtml(supplierDispatchLabel)}</strong></article>
                </div>
                <p class="order-card__target">${escapeHtml(order.targetValue || "입력값 없음")}</p>
                <div class="admin-order-callout-grid">
                  <article class="admin-mini-card ${hasDispatchIssue ? "is-risk" : ""}">
                    <span>공급사 전송</span>
                    <strong>${escapeHtml(supplierDispatchLabel)}</strong>
                    <p>${escapeHtml(order.supplierExternalOrderId || order.supplierStatus || "외부 주문번호 없음")}</p>
                  </article>
                  <article class="admin-mini-card">
                    <span>고객 요청 메모</span>
                    <strong>${escapeHtml(order.notes?.memo || "없음")}</strong>
                    <p>${escapeHtml(order.optionName || "기본 옵션")}</p>
                  </article>
                </div>
                <form class="admin-order-form" data-admin-order-status-form>
                  <input type="hidden" name="orderId" value="${escapeHtml(order.id)}" />
                  <div class="admin-three-column">
                    <label class="form-field">
                      <span class="field-label">상태</span>
                      <div class="field-shell">
                        <select class="field-select" name="status">
                          ${[
                            ["queued", "접수 대기"],
                            ["in_progress", "진행 중"],
                            ["completed", "완료"],
                          ]
                            .map(([value, label]) => `<option value="${value}" ${order.status === value ? "selected" : ""}>${label}</option>`)
                            .join("")}
                        </select>
                      </div>
                    </label>
                    <label class="form-field admin-order-form__memo">
                      <span class="field-label">운영 메모</span>
                      <div class="field-shell">
                        <input class="field-input" type="text" name="adminMemo" value="${escapeHtml(order.notes?.adminMemo || "")}" placeholder="내부 처리 메모" />
                      </div>
                    </label>
                    <div class="admin-order-form__submit">
                      <button class="admin-secondary-button" type="submit">상태 저장</button>
                    </div>
                  </div>
                </form>
              </article>
            `;
          })
              .join("")
          : `<div class="admin-empty-card"><strong>조건에 맞는 주문이 없습니다.</strong><p>상태 필터나 검색어를 바꿔 다시 확인해 주세요.</p></div>`}
      </div>
    </section>
  `;
}

function renderAdminOverviewSection(stats = {}, popup = null) {
  const sectionCards = adminSectionItems(stats, popup).filter((section) => section.id !== "overview");
  const siteSettings = getAdminSiteSettings() || state.bootstrap?.siteSettings || null;
  const operationsBoard = [
    { label: "사이트명", value: siteSettings?.siteName || "미설정", detail: siteSettings?.siteDescription || "사이트 설명 미설정" },
    { label: "팝업 노출", value: popup?.isActive ? "ON" : "OFF", detail: popup?.route || "이동 경로 미설정" },
    { label: "공급사", value: `${Number(stats.supplierCount || 0)}개`, detail: `동기화 서비스 ${Number(stats.syncedServiceCount || 0)}개` },
    { label: "회원", value: `${Number(stats.customerCount || 0)}명`, detail: `활성 회원 ${Number(stats.activeCustomerCount || 0)}명` },
    { label: "상품", value: `${Number(stats.productCount || 0)}개`, detail: `매핑 완료 ${Number(stats.mappedProductCount || 0)}개` },
    { label: "주문", value: `${Number(stats.orderCount || 0)}건`, detail: "주문 운영 모듈에서 상태 변경 가능" },
  ];

  return `
    <div class="admin-page">
      <section class="admin-stats-grid">
        <article class="admin-stat-card">
          <span>등록 공급사</span>
          <strong>${escapeHtml(String(stats.supplierCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>활성 공급사</span>
          <strong>${escapeHtml(String(stats.activeSupplierCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>동기화 서비스</span>
          <strong>${escapeHtml(String(stats.syncedServiceCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>매핑 완료 상품</span>
          <strong>${escapeHtml(String(stats.mappedProductCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>고객 계정</span>
          <strong>${escapeHtml(String(stats.customerCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>활성 상품</span>
          <strong>${escapeHtml(String(stats.activeProductCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>최근 주문</span>
          <strong>${escapeHtml(String(stats.orderCount || 0))}</strong>
        </article>
        <article class="admin-stat-card">
          <span>활성 고객</span>
          <strong>${escapeHtml(String(stats.activeCustomerCount || 0))}</strong>
        </article>
      </section>

      <div class="admin-erp-grid">
        <section class="admin-card admin-erp-panel">
          <div class="section-head section-head--compact">
            <h2>빠른 이동</h2>
            <p>확장되는 기능을 모듈 단위로 바로 열 수 있도록 ERP형 바로가기를 구성했습니다.</p>
          </div>
          <div class="admin-erp-shortcuts">
            ${sectionCards
              .map(
                (section) => `
                  <button class="admin-erp-shortcut" type="button" data-admin-scroll-section="${section.id}">
                    <span>${escapeHtml(section.icon || "•")}</span>
                    <strong>${escapeHtml(section.label)}</strong>
                    <small>${escapeHtml(section.description)}</small>
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="admin-card admin-erp-panel">
          <div class="section-head section-head--compact">
            <h2>운영 상태판</h2>
            <p>현재 운영 상태를 표처럼 빠르게 훑을 수 있도록 핵심 정보를 정리했습니다.</p>
          </div>
          <div class="admin-erp-board">
            ${operationsBoard
              .map(
                (item) => `
                  <div class="admin-erp-board__row">
                    <strong>${escapeHtml(item.label)}</strong>
                    <span>${escapeHtml(item.value)}</span>
                    <small>${escapeHtml(item.detail)}</small>
                  </div>
                `
              )
              .join("")}
          </div>
        </section>
      </div>
    </div>
  `;
}

function analyticsLinePath(points) {
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
}

function analyticsAreaPath(points, height, paddingBottom) {
  if (!points.length) return "";
  const first = points[0];
  const last = points[points.length - 1];
  return `M ${first.x.toFixed(1)} ${(height - paddingBottom).toFixed(1)} L ${analyticsLinePath(points).slice(2)} L ${last.x.toFixed(1)} ${(height - paddingBottom).toFixed(1)} Z`;
}

function formatAnalyticsTooltipValue(value, format = "number") {
  if (format === "money") return formatMoney(value);
  if (format === "percent") return formatPercent(value, 2);
  return formatNumber(value);
}

function analyticsChartPayload(series, metrics) {
  return series.map((item) => ({
    label: item.label,
    date: item.date || "",
    values: metrics.map((metric) => ({
      label: metric.label,
      value: Number(item[metric.key] || 0),
      format: metric.format || "number",
      color: metric.color,
    })),
  }));
}

function renderAnalyticsTrendChart(series, metrics, title) {
  if (!series.length) {
    return `
      <div class="admin-analytics-chart admin-analytics-chart--empty">
        <strong>데이터가 아직 없습니다.</strong>
        <p>${escapeHtml(title)} 데이터가 누적되면 이 영역에 추이가 표시됩니다.</p>
      </div>
    `;
  }

  const width = 760;
  const height = 260;
  const paddingX = 28;
  const paddingTop = 18;
  const paddingBottom = 42;
  const usableHeight = height - paddingTop - paddingBottom;
  const allValues = series.flatMap((item) => metrics.map((metric) => Number(item[metric.key] || 0)));
  const maxValue = Math.max(...allValues, 1);
  const stepX = series.length > 1 ? (width - paddingX * 2) / (series.length - 1) : 0;
  const labelEvery = Math.max(1, Math.ceil(series.length / 7));
  const tooltipPayload = analyticsChartPayload(series, metrics);

  const pointSets = metrics.map((metric) => {
    const points = series.map((item, index) => {
      const value = Number(item[metric.key] || 0);
      return {
        label: item.label,
        value,
        x: paddingX + stepX * index,
        y: height - paddingBottom - (value / maxValue) * usableHeight,
      };
    });
    return { ...metric, points };
  });

  return `
    <div class="admin-analytics-chart" data-analytics-chart="${escapeHtml(title)}" data-analytics-chart-points="${escapeHtml(JSON.stringify(tooltipPayload))}">
      <div class="admin-analytics-legend">
        ${metrics
          .map(
            (metric) => `
              <span>
                <i style="--legend-color:${escapeHtml(metric.color)}"></i>
                ${escapeHtml(metric.label)}
              </span>
            `
          )
          .join("")}
      </div>
      <div class="admin-analytics-chart__tooltip" data-analytics-chart-tooltip hidden></div>
      <div class="admin-analytics-chart__cursor" data-analytics-chart-cursor hidden></div>
      <svg class="admin-analytics-chart__svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)}">
        ${[0, 1, 2, 3, 4]
          .map((step) => {
            const y = paddingTop + (usableHeight / 4) * step;
            return `<line x1="${paddingX}" y1="${y.toFixed(1)}" x2="${width - paddingX}" y2="${y.toFixed(1)}"></line>`;
          })
          .join("")}
        ${pointSets[0]?.fill
          ? `<path class="analytics-area" fill="${escapeHtml(pointSets[0].fill)}" d="${analyticsAreaPath(pointSets[0].points, height, paddingBottom)}"></path>`
          : ""}
        ${pointSets
          .map(
            (metric) => `
              <path class="analytics-line" stroke="${escapeHtml(metric.color)}" d="${analyticsLinePath(metric.points)}"></path>
              ${metric.points
                .map(
                  (point) => `
                    <circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="4" fill="${escapeHtml(metric.color)}"></circle>
                  `
                )
                .join("")}
            `
          )
          .join("")}
        ${series
          .map((item, index) => {
            if (index !== series.length - 1 && index % labelEvery !== 0) return "";
            const x = paddingX + stepX * index;
            return `<text x="${x.toFixed(1)}" y="${height - 12}" text-anchor="middle">${escapeHtml(item.label)}</text>`;
          })
          .join("")}
      </svg>
      <div class="admin-analytics-chart__foot">
        <span>최대 ${escapeHtml(formatCompactNumber(maxValue))}</span>
        <span>${escapeHtml(series[0].label)} - ${escapeHtml(series[series.length - 1].label)}</span>
      </div>
    </div>
  `;
}

function renderAnalyticsTable(headers, rows, emptyMessage = "표시할 데이터가 없습니다.") {
  if (!rows.length) {
    return `<div class="admin-empty-card"><strong>데이터가 비어 있습니다.</strong><p>${escapeHtml(emptyMessage)}</p></div>`;
  }
  return `
    <div class="admin-analytics-table-wrap">
      <table class="admin-analytics-table">
        <thead>
          <tr>
            ${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAnalyticsOverviewCards(cards) {
  return `
    <section class="admin-analytics-kpi-grid">
      ${cards
        .map(
          (card) => `
            <article class="admin-card admin-analytics-kpi">
              <span>${escapeHtml(card.label)}</span>
              <strong>${escapeHtml(card.value)}</strong>
              <p>${escapeHtml(card.detail)}</p>
            </article>
          `
        )
        .join("")}
    </section>
  `;
}

function renderAnalyticsDashboardTab(windowData, daily) {
  const overview = windowData?.overview || {};
  const topPages = windowData?.topPages || [];
  const sources = windowData?.sourceDomains || [];
  const paths = windowData?.pathTransitions || [];
  const repurchase = windowData?.repurchaseSummary || {};
  return `
    <div class="admin-analytics-stack">
      ${renderAnalyticsOverviewCards([
        { label: "순매출", value: formatMoney(overview.sales), detail: `${formatNumber(overview.orders)}건 주문 · 객단가 ${formatMoney(overview.avgOrderValue)}` },
        { label: "방문자", value: `${formatNumber(overview.uniqueVisitors)}명`, detail: `페이지뷰 ${formatCompactNumber(overview.pageViews)} · 세션 ${formatNumber(overview.sessions)}` },
        { label: "전환율", value: formatPercent(overview.conversionRate, 2), detail: `주문 ${formatNumber(overview.orders)}건 / 방문자 ${formatNumber(overview.uniqueVisitors)}명` },
        { label: "재구매율", value: formatPercent(repurchase.repeatRate, 2), detail: `재구매 고객 ${formatNumber(repurchase.repeatCustomers)}명` },
        { label: "신규 방문자", value: `${formatNumber(overview.newVisitors)}명`, detail: `재방문 ${formatNumber(overview.returningVisitors)}명` },
        { label: "평균 구매주기", value: `${Number(repurchase.avgGapDays || 0).toFixed(1)}일`, detail: "재구매 고객 기준 주문 간격" },
      ])}

      <div class="admin-analytics-grid">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>전체 통계 대시보드</h2>
              <p>방문자와 페이지뷰 추이를 함께 보며 운영 변동을 빠르게 파악합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTrendChart(daily, [
            { key: "pageViews", label: "페이지뷰", color: "#84c5ff", fill: "rgba(132, 197, 255, 0.18)" },
            { key: "visitors", label: "방문자", color: "#2563eb" },
          ], "방문자 추이")}
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>매출 스냅샷</h2>
              <p>선택한 기간의 일별 매출과 주문 변화를 바로 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTrendChart(daily, [
            { key: "sales", label: "매출", color: "#1f5cff", fill: "rgba(31, 92, 255, 0.16)", format: "money" },
          ], "매출 추이")}
          <div class="admin-analytics-note">
            <strong>${escapeHtml(formatMoney(overview.sales))}</strong>
            <p>현재 선택 기간의 총매출입니다. 환불/할인 정책이 추가되면 순매출 로직도 이 영역에 함께 반영할 수 있습니다.</p>
          </div>
        </section>
      </div>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>많이 방문한 페이지</h2>
              <p>콘텐츠 성과가 높은 랜딩 페이지를 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["페이지", "경로", "조회", "방문자"],
            topPages.map((item) => [
              escapeHtml(item.pageLabel),
              `<code>${escapeHtml(item.route)}</code>`,
              escapeHtml(formatNumber(item.views)),
              escapeHtml(formatNumber(item.visitors)),
            ]),
            "방문 로그가 더 쌓이면 상위 페이지가 표시됩니다."
          )}
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>상위 유입 사이트</h2>
              <p>직접 방문을 포함해 외부 유입 비중을 빠르게 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["유입원", "유형", "방문", "세션"],
            sources.map((item) => [
              escapeHtml(item.label || item.domain),
              `<span class="admin-badge is-neutral">${escapeHtml(item.sourceType)}</span>`,
              escapeHtml(formatNumber(item.visits)),
              escapeHtml(formatNumber(item.sessions)),
            ]),
            "유입 사이트 데이터가 아직 없습니다."
          )}
        </section>
      </div>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>재구매 요약</h2>
              <p>반복 구매 고객 기반으로 충성도를 빠르게 확인합니다.</p>
            </div>
          </div>
          <div class="admin-analytics-band-grid">
            <article class="admin-analytics-band">
              <span>주문 고객</span>
              <strong>${escapeHtml(formatNumber(repurchase.customersWithOrders || 0))}명</strong>
            </article>
            <article class="admin-analytics-band">
              <span>재구매 고객</span>
              <strong>${escapeHtml(formatNumber(repurchase.repeatCustomers || 0))}명</strong>
            </article>
            <article class="admin-analytics-band">
              <span>재구매율</span>
              <strong>${escapeHtml(formatPercent(repurchase.repeatRate, 2))}</strong>
            </article>
            <article class="admin-analytics-band">
              <span>평균 간격</span>
              <strong>${escapeHtml(Number(repurchase.avgGapDays || 0).toFixed(1))}일</strong>
            </article>
          </div>
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>주요 이동 경로</h2>
              <p>홈에서 어떤 상세 페이지로 이동하는지 흐름을 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["출발", "도착", "횟수"],
            paths.map((item) => [
              `<code>${escapeHtml(item.fromRoute)}</code>`,
              `<code>${escapeHtml(item.toRoute)}</code>`,
              escapeHtml(formatNumber(item.hits)),
            ]),
            "경로 이동 데이터가 아직 없습니다."
          )}
        </section>
      </div>
    </div>
  `;
}

function renderAnalyticsSalesTab(windowData, daily) {
  const overview = windowData?.overview || {};
  const salesByPlatform = windowData?.salesByPlatform || [];
  const salesByProduct = windowData?.salesByProduct || [];
  return `
    <div class="admin-analytics-stack">
      ${renderAnalyticsOverviewCards([
        { label: "총매출", value: formatMoney(overview.sales), detail: `주문 ${formatNumber(overview.orders)}건` },
        { label: "구매 고객", value: `${formatNumber(overview.uniqueCustomers)}명`, detail: `고객당 평균 ${Number(overview.avgOrdersPerCustomer || 0).toFixed(2)}건` },
        { label: "객단가", value: formatMoney(overview.avgOrderValue), detail: "선택 기간 평균" },
        { label: "전환율", value: formatPercent(overview.conversionRate, 2), detail: "방문 대비 주문 비율" },
      ])}

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>매출 분석 탭</h2>
            <p>선택 기간의 일별 매출과 주문량을 확인합니다.</p>
          </div>
        </div>
        ${renderAnalyticsTrendChart(daily, [
          { key: "sales", label: "일 매출", color: "#1f5cff", fill: "rgba(31, 92, 255, 0.18)", format: "money" },
        ], "매출 분석")}
      </section>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>플랫폼별 매출</h2>
              <p>어느 플랫폼이 매출 기여가 큰지 정리합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["플랫폼", "주문", "고객", "매출"],
            salesByPlatform.map((item) => [
              escapeHtml(item.name),
              escapeHtml(formatNumber(item.orders)),
              escapeHtml(formatNumber(item.customers)),
              escapeHtml(formatMoney(item.sales)),
            ]),
            "플랫폼별 매출 데이터가 없습니다."
          )}
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>상품별 매출</h2>
              <p>매출 상위 상품을 빠르게 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["상품", "주문", "고객", "매출"],
            salesByProduct.map((item) => [
              escapeHtml(item.productName),
              escapeHtml(formatNumber(item.orders)),
              escapeHtml(formatNumber(item.customers)),
              escapeHtml(formatMoney(item.sales)),
            ]),
            "상품별 매출 데이터가 없습니다."
          )}
        </section>
      </div>

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>일자별 매출표</h2>
            <p>회계/정산 기초 확인용으로 날짜별 주문과 매출을 나란히 봅니다.</p>
          </div>
        </div>
        ${renderAnalyticsTable(
          ["날짜", "주문건수", "구매고객", "판매수량", "매출", "객단가"],
          daily
            .slice()
            .reverse()
            .map((item) => [
              escapeHtml(item.date),
              escapeHtml(formatNumber(item.orders)),
              escapeHtml(formatNumber(item.customers)),
              escapeHtml(formatNumber(item.quantity)),
              escapeHtml(formatMoney(item.sales)),
              escapeHtml(formatMoney(item.avgOrderValue)),
            ]),
          "선택한 기간의 매출 데이터가 없습니다."
        )}
      </section>
    </div>
  `;
}

function renderAnalyticsVisitorsTab(windowData, daily) {
  const overview = windowData?.overview || {};
  const devices = windowData?.deviceBreakdown || [];
  const topPages = windowData?.topPages || [];
  return `
    <div class="admin-analytics-stack">
      ${renderAnalyticsOverviewCards([
        { label: "페이지뷰", value: formatCompactNumber(overview.pageViews), detail: `세션 ${formatNumber(overview.sessions)}회` },
        { label: "순방문자", value: `${formatNumber(overview.uniqueVisitors)}명`, detail: `신규 ${formatNumber(overview.newVisitors)}명 / 재방문 ${formatNumber(overview.returningVisitors)}명` },
        { label: "재방문율", value: formatPercent(overview.returningVisitorRate, 2), detail: "기간 내 유니크 방문자 기준" },
        { label: "전환율", value: formatPercent(overview.conversionRate, 2), detail: "방문 대비 주문 비율" },
      ])}

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>방문자 분석 탭</h2>
            <p>페이지뷰와 순방문자를 같이 보며 유입 변화를 체크합니다.</p>
          </div>
        </div>
        ${renderAnalyticsTrendChart(daily, [
          { key: "pageViews", label: "페이지뷰", color: "#84c5ff", fill: "rgba(132, 197, 255, 0.18)" },
          { key: "visitors", label: "방문자", color: "#1d4ed8" },
        ], "방문자 분석")}
      </section>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>디바이스 분포</h2>
              <p>모바일 중심 운영인지 데스크톱 유입이 강한지 확인합니다.</p>
            </div>
          </div>
          <div class="admin-analytics-pill-row">
            ${devices
              .map(
                (item) => `
                  <article class="admin-analytics-pill">
                    <strong>${escapeHtml(item.label)}</strong>
                    <span>${escapeHtml(formatNumber(item.visits))}회 · ${escapeHtml(formatPercent(item.sharePercent, 1))}</span>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>상위 방문 페이지</h2>
              <p>가장 많이 도달한 페이지를 다시 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["페이지", "조회", "방문자"],
            topPages.map((item) => [
              escapeHtml(item.pageLabel),
              escapeHtml(formatNumber(item.views)),
              escapeHtml(formatNumber(item.visitors)),
            ]),
            "방문 페이지 데이터가 없습니다."
          )}
        </section>
      </div>

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>기간별 방문표</h2>
            <p>일자별 페이지뷰, 방문자, 신규/재방문, 전환율을 한 번에 봅니다.</p>
          </div>
        </div>
        ${renderAnalyticsTable(
          ["날짜", "페이지뷰", "방문자", "세션", "신규", "재방문", "전환율"],
          daily
            .slice()
            .reverse()
            .map((item) => [
              escapeHtml(item.date),
              escapeHtml(formatNumber(item.pageViews)),
              escapeHtml(formatNumber(item.visitors)),
              escapeHtml(formatNumber(item.sessions)),
              escapeHtml(formatNumber(item.newVisitors)),
              escapeHtml(formatNumber(item.returningVisitors)),
              escapeHtml(formatPercent(item.conversionRate, 2)),
            ]),
          "방문 추이 데이터가 없습니다."
        )}
      </section>
    </div>
  `;
}

function renderAnalyticsSourcesTab(windowData) {
  const sources = windowData?.sourceDomains || [];
  const sourceTypes = windowData?.sourceTypes || [];
  const entryPages = (windowData?.entryPages || []).slice().sort((a, b) => (b.sessions || 0) - (a.sessions || 0));
  const searchKeywords = windowData?.searchKeywords || [];
  const paths = windowData?.pathTransitions || [];
  return `
    <div class="admin-analytics-stack">
      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>유입 사이트 분석</h2>
              <p>직접 방문, 검색, SNS, 추천 유입을 도메인 단위로 봅니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["유입원", "유형", "방문", "방문자", "세션"],
            sources.map((item) => [
              escapeHtml(item.label),
              `<span class="admin-badge is-neutral">${escapeHtml(item.sourceType)}</span>`,
              escapeHtml(formatNumber(item.visits)),
              escapeHtml(formatNumber(item.visitors)),
              escapeHtml(formatNumber(item.sessions)),
            ]),
            "외부 유입 데이터가 아직 없습니다."
          )}
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>유입 유형 비중</h2>
              <p>검색/SNS/직접/추천/내부 이동 비중을 간단히 확인합니다.</p>
            </div>
          </div>
          <div class="admin-analytics-pill-row">
            ${sourceTypes
              .map(
                (item) => `
                  <article class="admin-analytics-pill">
                    <strong>${escapeHtml(item.label)}</strong>
                    <span>${escapeHtml(formatNumber(item.visits))}회</span>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      </div>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>랜딩 페이지</h2>
              <p>세션이 처음 시작된 페이지를 기준으로 랜딩 성과를 봅니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["페이지", "경로", "세션"],
            entryPages.map((item) => [
              escapeHtml(item.pageLabel),
              `<code>${escapeHtml(item.route)}</code>`,
              escapeHtml(formatNumber(item.sessions)),
            ]),
            "랜딩 페이지 데이터가 없습니다."
          )}
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>유입 검색어</h2>
              <p>검색 엔진에서 실제로 들어온 핵심 키워드를 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["검색어", "유입수"],
            searchKeywords.map((item) => [
              escapeHtml(item.keyword),
              escapeHtml(formatNumber(item.visits)),
            ]),
            "검색어 데이터가 아직 없습니다."
          )}
        </section>
      </div>

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>경로 분석</h2>
            <p>어떤 페이지에서 어떤 페이지로 이동했는지 주요 흐름을 확인합니다.</p>
          </div>
        </div>
        ${renderAnalyticsTable(
          ["출발 경로", "도착 경로", "이동 횟수"],
          paths.map((item) => [
            `<code>${escapeHtml(item.fromRoute)}</code>`,
            `<code>${escapeHtml(item.toRoute)}</code>`,
            escapeHtml(formatNumber(item.hits)),
          ]),
          "경로 이동 데이터가 없습니다."
        )}
      </section>
    </div>
  `;
}

function renderAnalyticsRepurchaseTab(windowData) {
  const summary = windowData?.repurchaseSummary || {};
  const customers = windowData?.repurchaseCustomers || [];
  const bands = windowData?.repurchaseBands || [];
  const products = windowData?.repurchaseProducts || [];
  return `
    <div class="admin-analytics-stack">
      ${renderAnalyticsOverviewCards([
        { label: "재구매율", value: formatPercent(summary.repeatRate, 2), detail: `재구매 고객 ${formatNumber(summary.repeatCustomers || 0)}명` },
        { label: "주문 고객", value: `${formatNumber(summary.customersWithOrders || 0)}명`, detail: "기간 내 1회 이상 주문 고객" },
        { label: "평균 구매횟수", value: `${Number(summary.avgOrdersPerCustomer || 0).toFixed(2)}회`, detail: "주문 고객 1인당 평균" },
        { label: "평균 구매간격", value: `${Number(summary.avgGapDays || 0).toFixed(1)}일`, detail: "재구매 고객 기준" },
      ])}

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>재구매 구간 분석</h2>
              <p>1회 구매와 반복 구매 고객 구간을 나눠서 확인합니다.</p>
            </div>
          </div>
          <div class="admin-analytics-band-grid">
            ${bands
              .map(
                (item) => `
                  <article class="admin-analytics-band">
                    <span>${escapeHtml(item.label)}</span>
                    <strong>${escapeHtml(formatNumber(item.customers))}명</strong>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>반복 구매 상품</h2>
              <p>재구매 고객이 다시 찾는 상품을 확인합니다.</p>
            </div>
          </div>
          ${renderAnalyticsTable(
            ["상품", "반복 주문", "고객수", "매출"],
            products.map((item) => [
              escapeHtml(item.productName),
              escapeHtml(formatNumber(item.repeatOrders)),
              escapeHtml(formatNumber(item.repeatCustomers)),
              escapeHtml(formatMoney(item.sales)),
            ]),
            "반복 구매 상품 데이터가 없습니다."
          )}
        </section>
      </div>

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>재구매 고객 리스트</h2>
            <p>반복 주문 고객을 우선순위대로 확인하고 운영 액션을 연결할 수 있습니다.</p>
          </div>
        </div>
        ${renderAnalyticsTable(
          ["고객", "구매횟수", "누적매출", "평균객단가", "평균간격", "마지막 주문"],
          customers.map((item) => [
            `${escapeHtml(item.customerName)} ${item.isRepeat ? '<span class="admin-badge is-success">재구매</span>' : '<span class="admin-badge is-neutral">1회</span>'}`,
            escapeHtml(formatNumber(item.orders)),
            escapeHtml(formatMoney(item.sales)),
            escapeHtml(formatMoney(item.avgOrderValue)),
            escapeHtml(`${Number(item.avgGapDays || 0).toFixed(1)}일`),
            escapeHtml(item.lastOrderAt ? item.lastOrderAt.slice(0, 10) : "-"),
          ]),
          "주문 고객 데이터가 없습니다."
        )}
      </section>
    </div>
  `;
}

function renderAnalyticsAdminSection() {
  const analytics = getAdminAnalytics();
  const windowData = analyticsWindow();
  const daily = analyticsDailySeries();
  const activeTab = state.ui.adminAnalyticsTab;

  if (!analytics || !windowData) {
    return `<div class="admin-empty-card"><strong>통계 데이터가 아직 준비되지 않았습니다.</strong><p>방문 이벤트와 주문 데이터가 누적되면 이 모듈에 자동으로 집계됩니다.</p></div>`;
  }

  let body = renderAnalyticsDashboardTab(windowData, daily);
  if (activeTab === "sales") body = renderAnalyticsSalesTab(windowData, daily);
  if (activeTab === "visitors") body = renderAnalyticsVisitorsTab(windowData, daily);
  if (activeTab === "sources") body = renderAnalyticsSourcesTab(windowData);
  if (activeTab === "repurchase") body = renderAnalyticsRepurchaseTab(windowData);

  return `
    <div class="admin-analytics-shell">
      <section class="admin-card admin-analytics-toolbar">
        <div>
          <span class="admin-module-header__breadcrumb">최근 ${escapeHtml(String(windowData.rangeDays || analyticsRangeDays()))}일 기준</span>
          <h2>통계 탭</h2>
          <p>실시간 방문 추적과 주문 데이터를 결합해 운영 성과를 같은 화면에서 분석합니다.</p>
        </div>
        <div class="admin-analytics-toolbar__actions">
          ${analyticsRangeBlueprints
            .map(
              (item) => `
                <button class="filter-chip ${state.ui.adminAnalyticsRange === item.id ? "is-active" : ""}" type="button" data-admin-analytics-range="${item.id}">
                  ${escapeHtml(item.label)}
                </button>
              `
            )
            .join("")}
        </div>
      </section>

      <nav class="admin-analytics-subnav">
        ${analyticsTabBlueprints
          .map(
            (tab) => `
              <button class="admin-analytics-subnav__item ${activeTab === tab.id ? "is-active" : ""}" type="button" data-admin-analytics-tab="${tab.id}">
                <strong>${escapeHtml(tab.label)}</strong>
                <small>${escapeHtml(tab.description)}</small>
              </button>
            `
          )
          .join("")}
      </nav>

      ${body}
    </div>
  `;
}

function renderSupplierAdminSection({
  suppliers,
  draft,
  selectedSupplier,
  selectedProduct,
  selectedService,
  allServices,
  filteredServices,
  activeConnection,
  products,
}) {
  const integrationType = draft.integrationType || selectedSupplier?.integrationType || "classic";
  const integrationGuide = supplierConnectionGuide(integrationType);
  const apiKeyLabel = supplierApiKeyLabel(integrationType);
  const visibleServices = filteredServices.slice(0, 160);
  const savedSecretSummary = integrationType === "mkt24"
    ? `x-api-key ${draft.hasApiKey ? draft.apiKeyMasked || "설정됨" : "미설정"} · Bearer ${draft.hasBearerToken ? draft.bearerTokenMasked || "설정됨" : "미설정"}`
    : draft.hasApiKey
      ? draft.apiKeyMasked || "설정됨"
      : "미설정";
  const connectionState = activeConnection?.status || activeConnection?.lastTestStatus || "never";
  const currentIssue = connectionState === "success"
    ? "오류 없음"
    : activeConnection?.message || activeConnection?.lastTestMessage || "연결 확인을 아직 실행하지 않았습니다.";
  const nextAction = !selectedSupplier
    ? "공급사를 선택해 연결 확인을 시작하세요."
    : !activeConnection?.resolvedApiUrl && !selectedSupplier?.lastCheckedAt
      ? "연결 확인을 먼저 실행하세요."
      : !allServices.length
        ? "서비스 동기화를 실행하세요."
        : !selectedService
          ? "서비스 목록에서 하나를 선택하세요."
          : !selectedProduct
            ? "내부 상품을 선택해 매핑을 준비하세요."
            : "현재 선택값으로 매핑을 저장하세요.";
  return `
    <div class="admin-layout">
      <aside class="admin-sidebar">
        <section class="admin-card">
          <div class="section-head section-head--compact">
            <h2>공급사 목록</h2>
            <p>공급사별 연결 상태와 동기화 현황을 빠르게 확인할 수 있습니다.</p>
          </div>
          <div class="admin-supplier-list">
            ${suppliers.length
              ? suppliers
                  .map(
                    (supplier) => `
                      <button
                        class="admin-supplier-card ${state.ui.adminSelectedSupplierId === supplier.id && state.ui.adminSupplierMode !== "new" ? "is-active" : ""}"
                        type="button"
                        data-admin-select-supplier="${supplier.id}"
                      >
                        <div class="admin-supplier-card__top">
                          <strong>${escapeHtml(supplier.name)}</strong>
                          ${renderAdminHealthBadge(supplier.lastTestStatus)}
                        </div>
                        <p class="admin-inline-note">${escapeHtml(supplier.integrationType === "mkt24" ? "MKT24 Bearer 연동" : "기존 SMM API 연동")}</p>
                        <p>${escapeHtml(supplier.apiUrl)}</p>
                        <div class="admin-supplier-card__meta">
                          <span>서비스 ${escapeHtml(String(supplier.serviceCount || 0))}</span>
                          <span>매핑 ${escapeHtml(String(supplier.mappingCount || 0))}</span>
                          <span>${supplier.isActive ? "활성" : "비활성"}</span>
                        </div>
                      </button>
                    `
                  )
                  .join("")
              : `<div class="admin-empty-card"><strong>등록된 공급사가 없습니다.</strong><p>새 공급사를 추가한 뒤 연결 확인과 동기화를 진행해 주세요.</p></div>`}
          </div>
        </section>

        <section class="admin-card">
          <div class="section-head section-head--compact">
            <h2>${draft.id ? "공급사 수정" : "공급사 등록"}</h2>
            <p>${escapeHtml(integrationType === "mkt24" ? "MKT24는 /v3 또는 전체 products/sns URL을 입력하면 백엔드에서 자동 보정합니다." : "/api, /api/v2 형태를 모두 시도하도록 백엔드에서 자동 보정합니다.")}</p>
          </div>
          <form class="admin-form" data-admin-supplier-form>
            <label class="form-field">
              <span class="field-label">연동 방식</span>
              <div class="field-shell">
                <select class="field-select" name="integrationType" data-admin-supplier-field="integrationType">
                  <option value="classic" ${integrationType === "classic" ? "selected" : ""}>기존 SMM API</option>
                  <option value="mkt24" ${integrationType === "mkt24" ? "selected" : ""}>MKT24 Bearer API</option>
                </select>
              </div>
            </label>

            <label class="form-field">
              <span class="field-label">공급사 이름</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="name" value="${escapeHtml(draft.name)}" data-admin-supplier-field="name" />
              </div>
            </label>

            <label class="form-field">
              <span class="field-label">API URL</span>
              <div class="field-shell">
                <input class="field-input" type="url" name="apiUrl" value="${escapeHtml(draft.apiUrl)}" placeholder="${escapeHtml(supplierUrlPlaceholder(integrationType))}" data-admin-supplier-field="apiUrl" />
              </div>
            </label>

            <label class="form-field">
              <span class="field-label">${escapeHtml(apiKeyLabel)}</span>
              <div class="field-shell">
                <input class="field-input" type="password" name="apiKey" value="${escapeHtml(draft.apiKey)}" placeholder="${escapeHtml(supplierApiKeyPlaceholder(integrationType, Boolean(draft.id)))}" data-admin-supplier-field="apiKey" />
              </div>
            </label>
            ${integrationType === "mkt24"
              ? `
                <label class="form-field">
                  <span class="field-label">Bearer Token</span>
                  <div class="field-shell">
                    <textarea class="field-textarea" name="bearerToken" rows="3" placeholder="${draft.id ? "새 토큰 입력 시에만 변경됩니다." : "Bearer Token"}" data-admin-supplier-field="bearerToken">${escapeHtml(draft.bearerToken)}</textarea>
                  </div>
                </label>
              `
              : ""}
            <p class="admin-inline-note">저장된 시크릿 상태: ${escapeHtml(savedSecretSummary)} · 기존 원문은 브라우저로 다시 내려오지 않습니다.</p>

            <label class="form-field">
              <span class="field-label">메모</span>
              <textarea class="field-textarea" name="notes" rows="4" data-admin-supplier-field="notes">${escapeHtml(draft.notes)}</textarea>
            </label>

            <label class="admin-toggle">
              <input type="checkbox" name="isActive" ${draft.isActive ? "checked" : ""} data-admin-supplier-field="isActive" />
              <span>이 공급사를 활성 상태로 운영</span>
            </label>

            <div class="admin-action-row">
              <button class="admin-primary-button" type="submit">${draft.id ? "저장하기" : "등록하기"}</button>
              <button class="admin-secondary-button" type="button" data-admin-test-connection>연결 확인</button>
            </div>
          </form>
        </section>
      </aside>

      <main class="admin-main">
        <section class="admin-card">
          <div class="admin-step-strip">
            ${[
              ["1. 연결 확인", Boolean(activeConnection?.resolvedApiUrl || selectedSupplier?.lastCheckedAt), "공급사 인증 정보와 응답 상태를 먼저 검증합니다."],
              ["2. 서비스 동기화", Boolean(allServices.length), "실제 공급사 서비스 목록을 불러와 내부에서 검색 가능하게 만듭니다."],
              ["3. 서비스 선택", Boolean(selectedService), "연동할 공급사 서비스를 선택하고 호출 예시를 검토합니다."],
              ["4. 내부 상품 매핑", Boolean(selectedProduct?.mapping), "실제 판매 상품과 공급사 서비스를 연결해 주문 발주를 준비합니다."],
            ]
              .map(
                ([label, done, description]) => `
                  <article class="admin-step-card ${done ? "is-complete" : ""}">
                    <strong>${escapeHtml(String(label))}</strong>
                    <p>${escapeHtml(String(description))}</p>
                    <span>${done ? "완료" : "대기"}</span>
                  </article>
                `
              )
            .join("")}
          </div>
        </section>

        <section class="admin-card">
          <div class="section-head section-head--compact">
            <h2>API 연결 상태</h2>
            <p>${escapeHtml(integrationGuide.status)}</p>
          </div>

          ${renderAdminInsightStrip(
            [
              {
                label: "현재 문제",
                value: currentIssue,
                description: connectionState === "success" ? "최근 연결 확인에서 오류가 감지되지 않았습니다." : "API URL, 인증 정보, 공급사 응답 메시지를 먼저 점검하세요.",
                tone: connectionState === "success" ? "success" : "warning",
              },
              {
                label: "마지막 확인",
                value: activeConnection?.checkedAt || selectedSupplier?.lastCheckedAt || "기록 없음",
                description: activeConnection?.resolvedApiUrl || selectedSupplier?.apiUrl || draft.apiUrl || "확인된 URL 없음",
              },
              {
                label: "다음 액션",
                value: nextAction,
                description: "연결 확인 → 서비스 동기화 → 서비스 선택 → 내부 상품 매핑 순서를 유지합니다.",
              },
              {
                label: "사용 가능 서비스",
                value: `${String(activeConnection?.serviceCount || selectedSupplier?.lastServiceCount || selectedSupplier?.serviceCount || 0)}개`,
                description: activeConnection?.balance ? `잔액 ${`${activeConnection.balance} ${activeConnection.currency || ""}`.trim()}` : integrationGuide.balance,
              },
            ],
            "admin-insight-grid--compact"
          )}

          ${integrationGuide.dispatch ? `<p class="admin-inline-note">${escapeHtml(integrationGuide.dispatch)}</p>` : ""}

          <div class="admin-action-row admin-action-row--top">
            <button class="admin-secondary-button" type="button" data-admin-test-connection>API 연결 재확인</button>
            <button class="admin-primary-button" type="button" data-admin-sync-services ${selectedSupplier?.id ? "" : "disabled"}>
              서비스 동기화
            </button>
          </div>
        </section>

        <section class="admin-card">
          <div class="section-head section-head--compact">
            <h2>공급사 서비스 목록</h2>
            <p>${escapeHtml(selectedSupplier ? `${selectedSupplier.name}에서 불러온 서비스입니다.` : "공급사를 선택하면 서비스 목록이 표시됩니다.")}</p>
          </div>

          <div class="admin-supplier-explorer">
            <div class="admin-card admin-subcard admin-pane">
              <div class="admin-toolbar admin-toolbar--stack">
                <div class="search-shell">
                  <input
                    class="search-input"
                    type="text"
                    value="${escapeHtml(state.ui.adminServiceSearch)}"
                    placeholder="서비스명, 카테고리, ID 검색"
                    data-admin-service-search
                  />
                </div>
                <div class="admin-inline-note">
                  전체 ${escapeHtml(String(allServices.length))}개 / 검색 결과 ${escapeHtml(String(filteredServices.length))}개
                </div>
              </div>
              ${
                filteredServices.length
                  ? `
                    <div class="admin-service-browser">
                      ${visibleServices
                        .map(
                          (service) => `
                            <button
                              class="admin-service-row ${state.ui.adminSelectedSupplierServiceId === service.id ? "is-active" : ""}"
                              type="button"
                              data-admin-service-select="${service.id}"
                            >
                              <div>
                                <strong>${escapeHtml(service.name)}</strong>
                                <p>${escapeHtml(service.category || "분류 없음")} · #${escapeHtml(service.externalServiceId)} · ${escapeHtml(String(service.minAmount || 0))}~${escapeHtml(String(service.maxAmount || 0))}</p>
                              </div>
                              <span>${escapeHtml(service.rateLabel)}</span>
                            </button>
                          `
                        )
                        .join("")}
                    </div>
                    ${filteredServices.length > visibleServices.length ? `<p class="admin-inline-note">성능을 위해 상위 ${escapeHtml(String(visibleServices.length))}개만 먼저 보여줍니다. 검색어를 더 구체화해 서비스 범위를 좁히세요.</p>` : ""}
                  `
                  : `<div class="admin-empty-card"><strong>표시할 서비스가 없습니다.</strong><p>공급사를 저장하고 서비스 동기화를 먼저 실행하거나 검색어를 조정해 주세요.</p></div>`
              }
            </div>

            <div class="admin-card admin-subcard admin-pane">
              <div class="admin-subcard__head">
                <strong>선택 서비스 상세</strong>
                ${selectedService ? `<span class="admin-badge is-success">선택됨</span>` : `<span class="admin-badge is-neutral">미선택</span>`}
              </div>
              ${
                selectedService
                  ? `
                    <div class="admin-mini-card">
                      <span>선택 서비스</span>
                      <strong>${escapeHtml(selectedService.name)} (#${escapeHtml(selectedService.externalServiceId)})</strong>
                      <p>${escapeHtml(selectedService.category || "분류 없음")} · Rate ${escapeHtml(selectedService.rateLabel)} · ${escapeHtml(String(selectedService.minAmount || 0))} ~ ${escapeHtml(String(selectedService.maxAmount || 0))} · ${selectedService.refill ? "리필 가능" : "리필 없음"}</p>
                    </div>
                    ${renderSupplierRequestGuide(selectedService, { applyLabel: selectedProduct ? "선택한 상품 제작 폼에 추천 적용" : "새 상품 제작 폼에 추천 적용" })}
                  `
                  : `<div class="admin-empty-card"><strong>선택된 서비스가 없습니다.</strong><p>왼쪽 목록에서 공급사 서비스를 고르면 호출 예시와 추천 양식이 이곳에 표시됩니다.</p></div>`
              }
            </div>
          </div>
        </section>

        <section class="admin-card">
          <div class="section-head section-head--compact">
            <h2>내부 상품 매핑</h2>
            <p>패널 상품과 공급사 서비스를 연결해 주문 시 외부 API 발주가 가능하도록 설정합니다.</p>
          </div>

          <div class="admin-mapping-layout">
            <div class="admin-product-list">
              ${products
                .map(
                  (product) => `
                    <button
                      class="admin-product-card ${state.ui.adminSelectedProductId === product.id ? "is-active" : ""}"
                      type="button"
                      data-admin-product-select="${product.id}"
                    >
                      <div class="admin-product-card__top">
                        <strong>${escapeHtml(product.name)}</strong>
                        ${product.mapping ? `<span class="admin-badge is-success">매핑됨</span>` : `<span class="admin-badge is-neutral">미매핑</span>`}
                      </div>
                      <p>${escapeHtml(product.platformName)} · ${escapeHtml(product.categoryName)}</p>
                      <div class="admin-product-card__meta">
                        <span>${escapeHtml(product.optionName || "기본 옵션")}</span>
                        <span>${escapeHtml(product.priceLabel)}</span>
                      </div>
                    </button>
                  `
                )
                .join("")}
            </div>

            <div class="admin-mapping-editor">
              ${
                selectedProduct
                  ? `
                    <div class="admin-selected-summary">
                      <div>
                        <span>선택한 내부 상품</span>
                        <strong>${escapeHtml(selectedProduct.name)}</strong>
                        <p>${escapeHtml(selectedProduct.platformName)} · ${escapeHtml(selectedProduct.categoryName)} · ${escapeHtml(selectedProduct.optionName || "기본 옵션")}</p>
                      </div>
                      <div>
                        <span>현재 매핑</span>
                        <strong>${escapeHtml(selectedProduct.mapping ? `${selectedProduct.mapping.supplierName} / ${selectedProduct.mapping.supplierServiceName}` : "미설정")}</strong>
                        <p>${escapeHtml(selectedProduct.mapping ? `배율 ${selectedProduct.mapping.priceMultiplier} / 마크업 ${formatMoney(selectedProduct.mapping.fixedMarkup)}` : "아직 연결된 공급사 서비스가 없습니다.")}</p>
                      </div>
                    </div>

                    <form class="admin-form" data-admin-mapping-form>
                      <div class="admin-mapping-preview">
                        <article class="admin-mini-card">
                          <span>공급사</span>
                          <strong>${escapeHtml(selectedSupplier?.name || "선택 필요")}</strong>
                        </article>
                        <article class="admin-mini-card">
                          <span>공급사 서비스</span>
                          <strong>${escapeHtml(selectedService ? `${selectedService.name} (#${selectedService.externalServiceId})` : "선택 필요")}</strong>
                        </article>
                      </div>

                      <label class="form-field">
                        <span class="field-label">가격 정책</span>
                        <div class="field-shell">
                          <select class="field-select" name="pricingMode">
                            <option value="multiplier" ${selectedProduct.mapping?.pricingMode === "multiplier" ? "selected" : ""}>배율 적용</option>
                            <option value="markup" ${selectedProduct.mapping?.pricingMode === "markup" ? "selected" : ""}>고정 마크업</option>
                          </select>
                        </div>
                      </label>

                      <label class="form-field">
                        <span class="field-label">배율</span>
                        <div class="field-shell">
                          <input class="field-input" type="number" name="priceMultiplier" step="0.01" min="0" value="${escapeHtml(String(selectedProduct.mapping?.priceMultiplier || 1))}" />
                        </div>
                      </label>

                      <label class="form-field">
                        <span class="field-label">고정 마크업</span>
                        <div class="field-shell">
                          <input class="field-input" type="number" name="fixedMarkup" step="100" min="0" value="${escapeHtml(String(selectedProduct.mapping?.fixedMarkup || 0))}" />
                        </div>
                      </label>

                      <div class="admin-action-row">
                        <button class="admin-primary-button" type="submit" ${selectedSupplier?.id && selectedService?.id ? "" : "disabled"}>
                          매핑 저장
                        </button>
                        ${
                          selectedProduct.mapping
                            ? `
                              <button
                                class="admin-secondary-button"
                                type="button"
                                data-admin-delete-mapping="${selectedProduct.mapping.id}"
                              >
                                매핑 해제
                              </button>
                            `
                            : ""
                        }
                      </div>
                    </form>
                  `
                  : `<div class="admin-empty-card"><strong>매핑할 내부 상품이 없습니다.</strong><p>상품 데이터가 준비되면 이 영역에서 공급사 서비스와 연결할 수 있습니다.</p></div>`
              }
            </div>
          </div>
        </section>
      </main>
    </div>
  `;
}

function renderHomeBannerCard(banner, { compact = false, index = 0, total = 1, interactive = true } = {}) {
  const imageUrl = resolveHomeBannerImageUrl(banner);
  const title = banner?.title || "프로모션 배너";
  const route = banner?.route || "/";
  const tag = interactive ? "button" : "div";
  const routeAttr = interactive ? ` type="button" data-route="${escapeHtml(route)}"` : "";
  return `
    <${tag} class="home-banner-card home-banner-card--${compact ? "compact" : "feature"}" aria-label="${escapeHtml(title)}"${routeAttr}>
      <span class="home-banner-card__media">
        <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(title)}" loading="lazy" />
      </span>
      ${!compact && total > 1 ? `<span class="home-banner-card__slot">${escapeHtml(`${index + 1} / ${total}`)}</span>` : ""}
    </${tag}>
  `;
}

function siteNameOrDefault(siteName) {
  return String(siteName || "").trim() || DEFAULT_SITE_NAME;
}

function brandMonogram(siteName) {
  const normalized = siteNameOrDefault(siteName).replace(/\s+/g, "");
  const latin = normalized.replace(/[^A-Za-z0-9]/g, "");
  if (latin.length >= 2) {
    return latin.slice(0, 2).toUpperCase();
  }
  return Array.from(normalized)[0] || "인";
}

function renderSiteBrandLogoMarkup(siteSettings, className, options = {}) {
  const siteName = siteNameOrDefault(siteSettings?.siteName);
  const surface = options.surface === "light" ? "light" : "dark";
  const darkLogoImageUrl = String(siteSettings?.headerLogoUrl || "").trim();
  const logoImageUrl = surface === "light" ? DEFAULT_LIGHT_BRAND_LOGO_URL || darkLogoImageUrl : darkLogoImageUrl;
  if (logoImageUrl) {
    return `
      <span class="${escapeHtml(className)} is-image" aria-label="${escapeHtml(siteName)}">
        <img src="${escapeHtml(logoImageUrl)}" alt="${escapeHtml(siteName)}" loading="lazy" />
      </span>
    `;
  }
  return `<span class="${escapeHtml(className)}" aria-label="${escapeHtml(siteName)}">${escapeHtml(brandMonogram(siteName))}</span>`;
}

function renderLoginRequiredPage(title, description, activeKey = "home") {
  return renderFrame(
    `
      <div class="page page-login-required">
        <section class="empty-card empty-card--center empty-card--auth">
          <span class="empty-card__eyebrow">로그인 필요</span>
          <strong>${escapeHtml(title)}</strong>
          <p>${escapeHtml(description)}</p>
          <div class="guide-list">
            <article class="guide-card">
              <strong>로그인 후 가능</strong>
              <p>주문 내역, 잔액, 충전, 계정별 진행 현황을 한 화면에서 확인할 수 있습니다.</p>
            </article>
            <article class="guide-card">
              <strong>탐색은 로그인 없이 가능</strong>
              <p>상품 탐색, 상세 확인, FAQ, 공지, 정책 문서는 로그인 없이 열람할 수 있습니다.</p>
            </article>
          </div>
          <button class="full-width-cta" type="button" data-route="/auth">로그인 / 회원가입</button>
          <button class="ghost-secondary-button" type="button" data-route="/products">서비스 둘러보기</button>
        </section>
      </div>
    `,
    activeKey
  );
}

function renderField(key, templateEntry, rules, values) {
  const value = values[key] ?? "";
  const required = (rules || []).includes("STRING_REQUIRED") || (rules || []).includes("MIN_MAX");
  const variant = templateEntry.variant;
  const options = templateEntry.templateOptions || {};

  if (variant === "textarea") {
    const formProps = options.formProps || {};
    return `
      <label class="form-field">
        <span class="field-label">${escapeHtml(options.labelProps?.label || key)}${required ? " *" : ""}</span>
        <textarea
          class="field-textarea"
          name="${escapeHtml(formProps.name || key)}"
          rows="${Number(formProps.rows || 4)}"
          placeholder="${escapeHtml(formProps.placeholder || "")}"
          data-order-field="${escapeHtml(key)}"
        >${escapeHtml(value)}</textarea>
      </label>
    `;
  }

  if (variant === "select") {
    const formProps = options.formProps || {};
    return `
      <label class="form-field">
        <span class="field-label">${escapeHtml(options.labelProps?.label || key)}${required ? " *" : ""}</span>
        <div class="field-shell">
          <select class="field-select" name="${escapeHtml(formProps.name || key)}" data-order-field="${escapeHtml(key)}">
            ${(formProps.options || [])
              .map(
                (option) => `
                  <option value="${escapeHtml(option.value)}" ${String(value) === String(option.value) ? "selected" : ""}>
                    ${escapeHtml(option.label)}
                  </option>
                `
              )
              .join("")}
          </select>
        </div>
      </label>
    `;
  }

  if (variant === "input") {
    const formProps = options.formProps || {};
    return `
      <label class="form-field">
        <span class="field-label">${escapeHtml(options.labelProps?.label || key)}${required ? " *" : ""}</span>
        <div class="field-shell">
          <input
            class="field-input"
            type="${escapeHtml(formProps.inputType || "text")}"
            name="${escapeHtml(formProps.name || key)}"
            placeholder="${escapeHtml(formProps.placeholder || "")}"
            value="${escapeHtml(value)}"
            min="${formProps.min ?? ""}"
            max="${formProps.max ?? ""}"
            step="${formProps.step ?? ""}"
            data-order-field="${escapeHtml(key)}"
          />
          ${formProps.unit ? `<span class="field-unit">${escapeHtml(formProps.unit)}</span>` : ""}
        </div>
      </label>
    `;
  }

  return `
    <label class="form-field">
      <span class="field-label">${escapeHtml(options.label || key)}${required ? " *" : ""}</span>
      <div class="field-shell">
        <input
          class="field-input"
          type="${options.type === "tel" ? "tel" : options.type === "url" ? "url" : "text"}"
          name="${escapeHtml(key)}"
          placeholder="${escapeHtml(options.placeholder || "")}"
          value="${escapeHtml(value)}"
          data-order-field="${escapeHtml(key)}"
        />
      </div>
    </label>
  `;
}

function renderNotFound(message) {
  return renderFrame(
    `
      <div class="page">
        <section class="empty-card empty-card--center">
          <strong>페이지를 불러오지 못했습니다.</strong>
          <p>${escapeHtml(message)}</p>
          <button class="full-width-cta" type="button" data-route="/">홈으로 이동</button>
        </section>
      </div>
    `,
    "home"
  );
}

configurePublicPages({
  state,
  navItems,
  escapeHtml,
  formatNumber,
  formatMoney,
  isLoggedIn,
  getRoute,
  filteredCatalog,
  getCurrentPlatform,
  getActiveHomeBanners,
  renderHomeBannerCard,
  renderSiteBrandLogoMarkup,
  renderPlatformLogoMarkup,
  renderHomePopupOverlay,
  ensureSelection,
  calculateSummary,
  getPreviewSource,
  getOrderValidationState,
  renderField,
  renderPreviewPanel,
  ensureChargeDraft,
  chargeAmountSummary,
  chargeMethodConfig,
  filteredChargeOrders,
  filteredWalletEntries,
  parseCurrencyInput,
  formatCurrencyInput,
  siteNameOrDefault,
  brandMonogram,
  statusMap,
  renderNotFound,
});

configureAdminPages({
  state,
  escapeHtml,
  DEFAULT_SITE_NAME,
  brandMonogram,
  adminSectionItems,
  getAdminSectionConfig,
  getAdminSiteSettings,
  getAdminSuppliers,
  getAdminProducts,
  getAdminPopup,
  getSelectedAdminSupplier,
  getSelectedAdminProduct,
  blankSupplierDraft,
  renderAnalyticsAdminSection,
  renderSiteSettingsAdminSection,
  renderPopupAdminSection,
  renderSupplierAdminSection,
  renderCustomerAdminSection,
  renderCatalogAdminSection,
  renderAdminOrdersSection,
  renderAdminOverviewSection,
});

async function renderRoute() {
  const route = getRoute();
  syncShellMode(route);
  try {
    if (!state.bootstrap || !state.catalog.length) {
      showLoading();
      return;
    }
    if (route.name === "admin") {
      state.ui.adminActiveSection = normalizeAdminSectionId(route.section);
      const session = await loadAdminSession();
      if (!session.configured || !session.authenticated) {
        app.innerHTML = renderAdminAuth();
        return;
      }
      if (!state.adminBootstrap) {
        showLoading("관리자 페이지를 준비하는 중...");
        await refreshAdminData({ preserveDraft: false });
      } else {
        syncAdminSelections({ preserveDraft: true });
      }
      const selectedCustomerId = state.ui.adminSelectedCustomerId;
      if (selectedCustomerId && !state.adminCustomerDetails[selectedCustomerId]) {
        showLoading("고객 정보를 불러오는 중...");
        await ensureAdminCustomerDetail(selectedCustomerId);
      }
      const selectedSupplierId = state.ui.adminSelectedSupplierId;
      if (selectedSupplierId && !state.adminSupplierServices[selectedSupplierId]) {
        showLoading("공급사 서비스 목록을 불러오는 중...");
        await ensureAdminSupplierServices(selectedSupplierId);
      }
    }
    if (route.name === "detail") {
      if (!route.id) {
        app.innerHTML = renderNotFound("잘못된 상품 경로입니다.");
        return;
      }
      if (!state.categoryCache[route.id]) {
        showLoading("상품 상세를 불러오는 중...");
        await ensureCategory(route.id);
      }
    }
    if (isLoggedIn() && route.name === "auth") {
      navigate(state.ui.loginRedirect || "/my");
      return;
    }
    if (!isLoggedIn() && ["charge", "orders", "my"].includes(route.name)) {
      const descriptions = {
        charge: "충전과 거래 내역은 로그인된 고객 계정에서만 확인할 수 있습니다.",
        orders: "주문 내역은 로그인 후에만 확인할 수 있습니다.",
        my: "마이 페이지는 로그인된 고객 계정 정보를 기준으로 표시됩니다.",
      };
      app.innerHTML = renderLoginRequiredPage("로그인 후 이용할 수 있는 메뉴입니다.", descriptions[route.name] || "로그인이 필요합니다.", route.name === "orders" ? "orders" : route.name === "charge" ? "charge" : "my");
      return;
    }

    if (route.name === "home") {
      app.innerHTML = renderHome();
    } else if (route.name === "auth") {
      app.innerHTML = renderAuthPage();
    } else if (route.name === "admin") {
      app.innerHTML = renderAdmin();
    } else if (route.name === "help") {
      app.innerHTML = renderHelp();
    } else if (route.name === "legal") {
      app.innerHTML = renderLegalPage(route.documentKey);
    } else if (route.name === "products") {
      app.innerHTML = renderProducts();
    } else if (route.name === "detail") {
      const detail = state.categoryCache[route.id];
      if (!detail) {
        app.innerHTML = renderNotFound("상품을 찾지 못했습니다.");
        return;
      }
      app.innerHTML = renderDetail(detail);
    } else if (route.name === "charge") {
      ensureChargeDraft();
      app.innerHTML = renderCharge();
    } else if (route.name === "orders") {
      app.innerHTML = renderOrders();
    } else if (route.name === "my") {
      app.innerHTML = renderMy();
    } else {
      app.innerHTML = renderHome();
    }

    if (route.name !== "admin" && adminSectionObserver) {
      adminSectionObserver.disconnect();
      adminSectionObserver = null;
    }

    updateLiveSummary();
    if (route.name === "auth") {
      updateSignupPasswordFeedback(app);
    }
    scrollToActiveHash();
    if (route.name === "detail" && route.id && state.categoryCache[route.id]) {
      scheduleLinkPreview(state.categoryCache[route.id], { immediate: true });
    }
    if (route.name === "home") {
      requestAnimationFrame(() => updateHomePlatformScrollerState());
    }
    ensureBannerTimer();
    trackPublicRoute(route);
  } catch (error) {
    if (route.name === "admin" && (error.status === 401 || error.status === 503)) {
      try {
        await loadAdminSession({ force: true });
      } catch (_) {
        state.adminSession = { configured: false, authenticated: false, username: "", csrfToken: "" };
        state.adminCsrfToken = "";
      }
      app.innerHTML = renderAdminAuth();
      return;
    }
    app.innerHTML = renderNotFound(error.message || "데이터를 불러오는 중 오류가 발생했습니다.");
  }
}

function updateLiveSummary() {
  const route = getRoute();
  if (route.name !== "detail") return;
  const detail = state.categoryCache[route.id];
  if (!detail) return;
  const summary = calculateSummary(detail);
  if (!summary) return;
  const summaryQuantity = document.querySelector("#summary-quantity");
  const summaryTotal = document.querySelector("#summary-total");
  const stickyTotal = document.querySelector("#sticky-total");
  if (summaryQuantity) {
    summaryQuantity.textContent =
      summary.product.priceStrategy === "fixed"
        ? "패키지 1건"
        : `${summary.quantity}${summary.product.unitLabel}`;
  }
  if (summaryTotal) summaryTotal.textContent = formatMoney(summary.total);
  if (stickyTotal) stickyTotal.textContent = formatMoney(summary.total);
  updateOrderValidation(detail);
}

function isExternalTarget(path) {
  return /^https?:\/\//i.test(String(path || "").trim());
}

function popupVersionKey(popup) {
  return `${popup?.id || "popup"}:${popup?.updatedAt || "v1"}`;
}

function popupDismissStorageKey(popup) {
  return `pulse24_popup_dismiss:${popupVersionKey(popup)}`;
}

function currentLocalDayKey() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isPopupDismissedToday(popup) {
  if (!popup?.id) return false;
  try {
    return window.localStorage.getItem(popupDismissStorageKey(popup)) === currentLocalDayKey();
  } catch (_) {
    return false;
  }
}

function dismissPopupToday(popup) {
  if (!popup?.id) return;
  try {
    window.localStorage.setItem(popupDismissStorageKey(popup), currentLocalDayKey());
  } catch (_) {
    // Ignore storage failures and still close for the current session.
  }
}

function shouldShowHomePopup() {
  const popup = state.bootstrap?.popup;
  if (!popup?.id || !popup.isActive) return false;
  if (getRoute().name !== "home") return false;
  if (state.ui.closedPopups[popupVersionKey(popup)]) return false;
  return !isPopupDismissedToday(popup);
}

function closePopupForSession(popup) {
  if (!popup?.id) return;
  state.ui.closedPopups[popupVersionKey(popup)] = true;
}

function updateAnalyticsChartTooltip(chart, clientX) {
  if (!chart) return;
  const svg = chart.querySelector(".admin-analytics-chart__svg");
  const tooltip = chart.querySelector("[data-analytics-chart-tooltip]");
  const cursor = chart.querySelector("[data-analytics-chart-cursor]");
  if (!svg || !tooltip || !cursor) return;

  let points = chart._analyticsPoints;
  if (!points) {
    try {
      points = JSON.parse(chart.getAttribute("data-analytics-chart-points") || "[]");
      chart._analyticsPoints = points;
    } catch (_) {
      points = [];
    }
  }
  if (!points.length) return;

  const rect = svg.getBoundingClientRect();
  const relativeX = Math.min(Math.max(clientX - rect.left, 0), rect.width);
  const ratio = rect.width ? relativeX / rect.width : 0;
  const index = Math.min(points.length - 1, Math.max(0, Math.round(ratio * (points.length - 1))));
  const point = points[index];
  const markerLeft = rect.width * (points.length > 1 ? index / (points.length - 1) : 0);

  tooltip.innerHTML = `
    <strong>${escapeHtml(point.date || point.label)}</strong>
    ${point.values
      .map(
        (item) => `
          <span>
            <i style="--legend-color:${escapeHtml(item.color)}"></i>
            ${escapeHtml(item.label)} ${escapeHtml(formatAnalyticsTooltipValue(item.value, item.format))}
          </span>
        `
      )
      .join("")}
  `;
  tooltip.hidden = false;
  cursor.hidden = false;
  tooltip.style.left = `${Math.min(Math.max(markerLeft, 56), rect.width - 56)}px`;
  cursor.style.left = `${markerLeft}px`;
}

function hideAnalyticsChartTooltip(chart) {
  if (!chart) return;
  const tooltip = chart.querySelector("[data-analytics-chart-tooltip]");
  const cursor = chart.querySelector("[data-analytics-chart-cursor]");
  if (tooltip) tooltip.hidden = true;
  if (cursor) cursor.hidden = true;
}

function randomClientId(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
}

function setAdminAnalyticsExclusion(enabled) {
  try {
    if (enabled) {
      window.localStorage.setItem("pulse24_admin_exclude_analytics", "1");
    } else {
      window.localStorage.removeItem("pulse24_admin_exclude_analytics");
    }
  } catch (_) {
    // Ignore storage errors.
  }
}

function shouldExcludeCurrentVisitFromStats() {
  try {
    return window.localStorage.getItem("pulse24_admin_exclude_analytics") === "1";
  } catch (_) {
    return false;
  }
}

function getStoredAnalyticsId(storageKind, key, prefix) {
  try {
    const storage = storageKind === "local" ? window.localStorage : window.sessionStorage;
    const existing = storage.getItem(key);
    if (existing) return existing;
    const created = randomClientId(prefix);
    storage.setItem(key, created);
    return created;
  } catch (_) {
    if (storageKind === "local") {
      fallbackVisitorId = fallbackVisitorId || randomClientId(prefix);
      return fallbackVisitorId;
    }
    fallbackSessionId = fallbackSessionId || randomClientId(prefix);
    return fallbackSessionId;
  }
}

function analyticsVisitorId() {
  return getStoredAnalyticsId("local", "pulse24_visitor_id", "visitor");
}

function analyticsSessionId() {
  return getStoredAnalyticsId("session", "pulse24_session_id", "session");
}

function analyticsPageLabel(route) {
  if (route.name === "home") return "홈";
  if (route.name === "auth") return route.mode === "signup" ? "회원가입" : "로그인";
  if (route.name === "help") return "도움말 허브";
  if (route.name === "legal") return "약관/정책";
  if (route.name === "products") return "상품 목록";
  if (route.name === "charge") return "충전";
  if (route.name === "orders") return "주문 내역";
  if (route.name === "my") return "마이 페이지";
  if (route.name === "detail") {
    return state.categoryCache[route.id]?.name || "상품 상세";
  }
  return "";
}

function trackPublicRoute(route) {
  if (!route) return;
  if (route.name === "admin") {
    lastTrackedPublicPath = "";
    return;
  }
  const pathname = window.location.pathname.replace(/\/+$/, "") || "/";
  if (lastTrackedPublicPath === pathname) return;
  const payload = {
    visitorId: analyticsVisitorId(),
    sessionId: analyticsSessionId(),
    route: pathname,
    pageLabel: analyticsPageLabel(route),
    referrerUrl: document.referrer || "",
    previousRoute: previousPublicPath || "",
    excludeFromStats: shouldExcludeCurrentVisitFromStats(),
  };
  lastTrackedPublicPath = pathname;
  previousPublicPath = pathname;
  fetch(apiUrl("/api/analytics/track"), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}

function openLoginModal(redirectPath = "") {
  state.ui.loginRedirect = redirectPath || window.location.pathname || "/";
  state.ui.authTab = "login";
  state.ui.loginModalOpen = true;
  renderRoute();
}

function closeLoginModal({ preserveRedirect = false } = {}) {
  state.ui.loginModalOpen = false;
  state.ui.authTab = "login";
  if (!preserveRedirect) {
    state.ui.loginRedirect = "";
  }
}

function postAuthRedirectPath() {
  const candidate = state.ui.loginRedirect || "";
  if (candidate && candidate !== "/auth" && candidate !== "/auth/signup") return candidate;
  return "/";
}

function requiresUserAuthPath(path) {
  return ["/charge", "/orders", "/my"].includes(String(path || "").trim());
}

function navigate(path, { push = true } = {}) {
  if (isExternalTarget(path)) {
    window.open(path, "_blank", "noopener,noreferrer");
    return;
  }
  if (requiresUserAuthPath(path) && !isLoggedIn()) {
    state.ui.loginRedirect = path;
    const messages = {
      "/charge": "로그인 후 충전 내역과 주문 내역을 확인할 수 있어요",
      "/orders": "로그인 후 주문 내역을 확인할 수 있어요",
      "/my": "로그인 후 계정과 보유금액을 확인할 수 있어요",
    };
    showToast(messages[path] || "로그인이 필요합니다.");
    window.setTimeout(() => {
      if (!isLoggedIn()) {
        openLoginModal(path);
      }
    }, 420);
    return;
  }
  if (push) {
    window.history.pushState({}, "", path);
  }
  renderRoute();
}

function scrollToActiveHash() {
  const hash = String(window.location.hash || "").trim();
  if (!hash) return;
  const target = document.querySelector(hash);
  if (!(target instanceof HTMLElement)) return;
  window.requestAnimationFrame(() => {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function ensureBannerTimer() {
  if (bannerIntervalId || !getActiveHomeBanners().length) return;
  bannerIntervalId = window.setInterval(() => {
    if (getRoute().name !== "home" || state.ui.loginModalOpen) return;
    const activeElement = document.activeElement;
    if (activeElement && activeElement.closest(".auth-modal, .home-search")) return;
    setHomeBannerIndex(state.ui.bannerIndex + 1);
  }, 4500);
}

async function applyAdminSiteSettingsImage(kind, file) {
  if (!state.adminSiteSettingsDraft) {
    state.adminSiteSettingsDraft = blankSiteSettingsDraft();
  }
  const isFavicon = kind === "favicon";
  const isHeaderLogo = kind === "headerLogo";
  if (!file.type.startsWith("image/")) {
    throw new Error("이미지 파일만 업로드할 수 있습니다.");
  }
  if (isFavicon && file.size > 1024 * 1024) {
    throw new Error("파비콘 이미지는 1MB 이하로 업로드해 주세요.");
  }
  if (isHeaderLogo && file.size > 2 * 1024 * 1024) {
    throw new Error("상단 로고 이미지는 2MB 이하로 업로드해 주세요.");
  }
  if (!isFavicon && !isHeaderLogo && file.size > 5 * 1024 * 1024) {
    throw new Error("대표 이미지는 5MB 이하로 업로드해 주세요.");
  }
  const encoded = await readFileAsDataUrl(file);
  if (isHeaderLogo) {
    state.adminSiteSettingsDraft.headerLogoUrl = encoded;
    state.adminSiteSettingsDraft.headerLogoName = file.name;
    state.adminSiteSettingsDraft.headerLogoUrlInput = "";
  } else if (isFavicon) {
    state.adminSiteSettingsDraft.faviconUrl = encoded;
    state.adminSiteSettingsDraft.faviconName = file.name;
    state.adminSiteSettingsDraft.faviconUrlInput = "";
  } else {
    state.adminSiteSettingsDraft.shareImageUrl = encoded;
    state.adminSiteSettingsDraft.shareImageName = file.name;
    state.adminSiteSettingsDraft.shareImageUrlInput = "";
  }
  updateAdminSiteSettingsPreview();
}

document.addEventListener("click", async (event) => {
  const targetElement = event.target instanceof Element ? event.target : event.target?.parentElement;
  const closest = (selector) => targetElement?.closest(selector);

  const authTabButton = closest("[data-auth-tab]");
  if (authTabButton) {
    state.ui.authTab = authTabButton.getAttribute("data-auth-tab") || "login";
    renderRoute();
    return;
  }

  const oauthProviderButton = closest("[data-oauth-provider]");
  if (oauthProviderButton) {
    const provider = oauthProviderButton.getAttribute("data-oauth-provider") || "";
    const providerConfig = (state.bootstrap?.authConfig?.oauthProviders || []).find((item) => item.provider === provider);
    if (!providerConfig?.enabled) {
      showToast(`${providerConfig?.label || provider} 연동은 환경변수 설정 후 활성화됩니다.`, "error");
      return;
    }
    navigate(providerConfig.startPath);
    return;
  }

  const publicLoginOpenButton = closest("[data-public-login-open]");
  if (publicLoginOpenButton) {
    openLoginModal(window.location.pathname || "/");
    return;
  }

  const publicLoginCloseButton = closest("[data-public-login-close]");
  if (publicLoginCloseButton) {
    closeLoginModal();
    renderRoute();
    return;
  }

  const passwordToggleButton = closest("[data-password-toggle]");
  if (passwordToggleButton) {
    const shell = passwordToggleButton.closest(".field-shell--password");
    const input = shell?.querySelector("input");
    if (input instanceof HTMLInputElement) {
      input.type = input.type === "password" ? "text" : "password";
      passwordToggleButton.textContent = input.type === "password" ? "보기" : "숨기기";
    }
    return;
  }

  const signupChangeEmailButton = closest("[data-public-signup-change-email]");
  if (signupChangeEmailButton) {
    const nextState = currentSignupState();
    nextState.step = "email";
    nextState.verificationToken = "";
    nextState.previewCode = "";
    nextState.verifiedAt = "";
    nextState.completeBy = "";
    renderRoute();
    return;
  }

  const signupResendButton = closest("[data-public-signup-resend]");
  if (signupResendButton) {
    const signup = currentSignupState();
    if (!signup.email) {
      showToast("먼저 이메일을 입력해 주세요.", "error");
      return;
    }
    try {
      const result = await apiPost("/api/auth/email/send-code", { email: signup.email });
      Object.assign(signup, {
        step: "verify",
        challengeId: result.challengeId || "",
        resendAvailableAt: result.resendAvailableAt || "",
        expiresAt: result.expiresAt || "",
        previewCode: result.previewCode || "",
        verificationToken: "",
        verifiedAt: "",
        completeBy: "",
      });
      renderRoute();
      showToast("인증코드를 다시 보냈습니다.");
    } catch (error) {
      showToast(error.message || "인증코드 재전송에 실패했습니다.", "error");
    }
    return;
  }

  const publicLogoutButton = closest("[data-public-logout]");
  if (publicLogoutButton) {
    try {
      await apiPost("/api/logout", {});
    } catch (_) {
      // Ignore transport errors and still clear the local session state.
    }
    clearPublicSessionState();
    await refreshCoreData();
    showToast("로그아웃되었습니다.");
    navigate("/", { push: false });
    return;
  }

  const homeFooterToggleButton = closest("[data-home-footer-toggle]");
  if (homeFooterToggleButton) {
    state.ui.homeFooterExpanded = !state.ui.homeFooterExpanded;
    renderRoute();
    return;
  }

  const routeButton = closest("[data-route]");
  if (routeButton) {
    const path = routeButton.getAttribute("data-route");
    const platformId = routeButton.getAttribute("data-platform-id");
    if (state.ui.loginModalOpen) {
      closeLoginModal({ preserveRedirect: Boolean(path && path.startsWith("/auth")) });
    }
    if (platformId) {
      state.ui.activePlatform = platformId;
      state.ui.search = "";
    }
    navigate(path);
    return;
  }

  const homeSearchSubmitButton = closest("[data-home-search-submit]");
  if (homeSearchSubmitButton) {
    navigate("/products");
    return;
  }

  const popupDismissTodayButton = closest("[data-popup-dismiss-today]");
  if (popupDismissTodayButton) {
    const popup = state.bootstrap?.popup;
    dismissPopupToday(popup);
    closePopupForSession(popup);
    renderRoute();
    return;
  }

  const popupCloseButton = closest("[data-popup-close]");
  if (popupCloseButton) {
    closePopupForSession(state.bootstrap?.popup);
    renderRoute();
    return;
  }

  const clearPopupImageButton = closest("[data-admin-popup-image-clear]");
  if (clearPopupImageButton) {
    if (!state.adminPopupDraft) {
      state.adminPopupDraft = blankPopupDraft();
    }
    state.adminPopupDraft.imageUrl = "";
    state.adminPopupDraft.imageName = "";
    state.adminPopupDraft.imageUrlInput = "";
    updateAdminPopupPreview();
    renderRoute();
    return;
  }

  const selectHomeBannerButton = closest("[data-admin-home-banner-select]");
  if (selectHomeBannerButton) {
    state.ui.adminSelectedHomeBannerId = selectHomeBannerButton.getAttribute("data-admin-home-banner-select") || "";
    state.adminHomeBannerDraft = homeBannerToDraft(getSelectedAdminHomeBanner());
    renderRoute();
    return;
  }

  const clearHomeBannerImageButton = closest("[data-admin-home-banner-image-clear]");
  if (clearHomeBannerImageButton) {
    if (!state.adminHomeBannerDraft) {
      state.adminHomeBannerDraft = homeBannerToDraft(getSelectedAdminHomeBanner());
    }
    state.adminHomeBannerDraft.imageUrl = "";
    state.adminHomeBannerDraft.imageName = "";
    state.adminHomeBannerDraft.imageUrlInput = "";
    updateAdminHomeBannerPreview();
    return;
  }

  const selectPlatformSectionButton = closest("[data-admin-platform-section-select]");
  if (selectPlatformSectionButton) {
    state.ui.adminSelectedPlatformSectionId = selectPlatformSectionButton.getAttribute("data-admin-platform-section-select") || "";
    state.adminPlatformSectionDraft = platformSectionToDraft(getSelectedAdminPlatformSection());
    renderRoute();
    return;
  }

  const clearPlatformSectionImageButton = closest("[data-admin-platform-section-image-clear]");
  if (clearPlatformSectionImageButton) {
    if (!state.adminPlatformSectionDraft) {
      state.adminPlatformSectionDraft = platformSectionToDraft(getSelectedAdminPlatformSection());
    }
    state.adminPlatformSectionDraft.logoImageUrl = "";
    state.adminPlatformSectionDraft.logoImageName = "";
    state.adminPlatformSectionDraft.logoImageUrlInput = "";
    updateAdminPlatformSectionPreview();
    return;
  }

  const clearHeaderLogoButton = closest("[data-admin-site-settings-header-logo-clear]");
  if (clearHeaderLogoButton) {
    if (!state.adminSiteSettingsDraft) {
      state.adminSiteSettingsDraft = blankSiteSettingsDraft();
    }
    state.adminSiteSettingsDraft.headerLogoUrl = "";
    state.adminSiteSettingsDraft.headerLogoName = "";
    state.adminSiteSettingsDraft.headerLogoUrlInput = "";
    const headerLogoInput = document.querySelector('[data-admin-site-settings-field="headerLogoUrlInput"]');
    if (headerLogoInput) headerLogoInput.value = "";
    updateAdminSiteSettingsPreview();
    return;
  }

  const clearFaviconButton = closest("[data-admin-site-settings-favicon-clear]");
  if (clearFaviconButton) {
    if (!state.adminSiteSettingsDraft) {
      state.adminSiteSettingsDraft = blankSiteSettingsDraft();
    }
    state.adminSiteSettingsDraft.faviconUrl = "";
    state.adminSiteSettingsDraft.faviconName = "";
    state.adminSiteSettingsDraft.faviconUrlInput = "";
    const faviconInput = document.querySelector('[data-admin-site-settings-field="faviconUrlInput"]');
    if (faviconInput) faviconInput.value = "";
    updateAdminSiteSettingsPreview();
    return;
  }

  const clearShareImageButton = closest("[data-admin-site-settings-share-clear]");
  if (clearShareImageButton) {
    if (!state.adminSiteSettingsDraft) {
      state.adminSiteSettingsDraft = blankSiteSettingsDraft();
    }
    state.adminSiteSettingsDraft.shareImageUrl = "";
    state.adminSiteSettingsDraft.shareImageName = "";
    state.adminSiteSettingsDraft.shareImageUrlInput = "";
    const shareInput = document.querySelector('[data-admin-site-settings-field="shareImageUrlInput"]');
    if (shareInput) shareInput.value = "";
    updateAdminSiteSettingsPreview();
    return;
  }

  const adminSectionButton = closest("[data-admin-scroll-section]");
  if (adminSectionButton) {
    const sectionId = adminSectionButton.getAttribute("data-admin-scroll-section") || "overview";
    navigate(adminSectionPath(sectionId));
    return;
  }

  const analyticsTabButton = closest("[data-admin-analytics-tab]");
  if (analyticsTabButton) {
    state.ui.adminAnalyticsTab = analyticsTabButton.getAttribute("data-admin-analytics-tab") || "dashboard";
    renderRoute();
    return;
  }

  const analyticsRangeButton = closest("[data-admin-analytics-range]");
  if (analyticsRangeButton) {
    state.ui.adminAnalyticsRange = analyticsRangeButton.getAttribute("data-admin-analytics-range") || "30d";
    renderRoute();
    return;
  }

  const customerFilterButton = closest("[data-admin-customer-filter]");
  if (customerFilterButton) {
    state.ui.adminCustomerFilter = customerFilterButton.getAttribute("data-admin-customer-filter") || "all";
    renderRoute();
    return;
  }

  const adminRefreshButton = closest("[data-admin-refresh]");
  if (adminRefreshButton) {
    try {
      await refreshAdminData({ preserveDraft: false });
      if (state.ui.adminSelectedCustomerId) {
        await ensureAdminCustomerDetail(state.ui.adminSelectedCustomerId, { force: true });
      }
      if (state.ui.adminSelectedSupplierId) {
        await ensureAdminSupplierServices(state.ui.adminSelectedSupplierId, { force: true });
      }
      showToast("관리자 데이터를 새로고침했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "관리자 새로고침에 실패했습니다.", "error");
    }
    return;
  }

  const adminLogoutButton = closest("[data-admin-logout]");
  if (adminLogoutButton) {
    try {
      await apiPost("/api/admin/logout", {});
    } catch (_) {
      // Ignore logout transport errors; local state still needs to be cleared.
    }
    setAdminAnalyticsExclusion(false);
    state.adminSession = { configured: true, authenticated: false, username: "", csrfToken: "" };
    state.adminCsrfToken = "";
    resetAdminState({ preserveSession: true });
    renderRoute();
    return;
  }

  const newSupplierButton = closest("[data-admin-supplier-new]");
  if (newSupplierButton) {
    state.ui.adminSupplierMode = "new";
    state.ui.adminSelectedSupplierId = "";
    state.ui.adminSelectedSupplierServiceId = "";
    state.adminSupplierDraft = blankSupplierDraft();
    state.adminConnectionResult = null;
    renderRoute();
    return;
  }

  const supplierButton = closest("[data-admin-select-supplier]");
  if (supplierButton) {
    const supplierId = supplierButton.getAttribute("data-admin-select-supplier");
    const supplier = getAdminSuppliers().find((item) => item.id === supplierId) || null;
    state.ui.adminSupplierMode = "edit";
    state.ui.adminSelectedSupplierId = supplierId || "";
    state.ui.adminSelectedSupplierServiceId = "";
    state.ui.adminServiceSearch = "";
    state.adminSupplierDraft = supplierToDraft(supplier);
    state.adminConnectionResult = null;
    try {
      if (supplierId) {
        await ensureAdminSupplierServices(supplierId);
      }
      renderRoute();
    } catch (error) {
      showToast(error.message || "공급사 서비스 목록을 불러오지 못했습니다.", "error");
    }
    return;
  }

  const testConnectionButton = closest("[data-admin-test-connection]");
  if (testConnectionButton) {
    const draft = state.adminSupplierDraft || blankSupplierDraft();
    try {
      const result = await apiPost("/api/admin/suppliers/test", {
        id: draft.id,
        name: draft.name,
        apiUrl: draft.apiUrl,
        integrationType: draft.integrationType,
        apiKey: draft.apiKey,
        bearerToken: draft.bearerToken,
        notes: draft.notes,
        isActive: draft.isActive,
      });
      state.adminConnectionResult = result.result;
      if (draft.id) {
        await refreshAdminData({ preserveDraft: false });
        state.ui.adminSupplierMode = "edit";
        state.adminSupplierDraft = supplierToDraft(getSelectedAdminSupplier());
      }
      showToast(result.result.message || "API 연결이 확인되었습니다.");
      renderRoute();
    } catch (error) {
      state.adminConnectionResult = {
        status: "failed",
        message: error.message || "API 연결을 확인하지 못했습니다.",
      };
      showToast(error.message || "API 연결 확인에 실패했습니다.", "error");
      renderRoute();
    }
    return;
  }

  const syncServicesButton = closest("[data-admin-sync-services]");
  if (syncServicesButton) {
    const supplierId = state.ui.adminSelectedSupplierId;
    if (!supplierId) {
      showToast("먼저 저장된 공급사를 선택해 주세요.", "error");
      return;
    }
    try {
      const result = await apiPost(`/api/admin/suppliers/${encodeURIComponent(supplierId)}/sync-services`, {});
      await refreshAdminData({ preserveDraft: false });
      await ensureAdminSupplierServices(supplierId, { force: true });
      state.adminConnectionResult = {
        status: "success",
        message: `${result.serviceCount}개 서비스를 동기화했습니다.`,
        serviceCount: result.serviceCount,
        checkedAt: result.syncedAt,
        resolvedApiUrl: result.supplier?.apiUrl || "",
        balance: result.supplier?.lastBalance || "",
        currency: result.supplier?.lastCurrency || "",
      };
      showToast(`${result.serviceCount}개 서비스를 동기화했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "서비스 동기화에 실패했습니다.", "error");
    }
    return;
  }

  const serviceButton = closest("[data-admin-service-select]");
  if (serviceButton) {
    state.ui.adminSelectedSupplierServiceId = serviceButton.getAttribute("data-admin-service-select") || "";
    renderRoute();
    return;
  }

  const applyServiceRecommendationButton = closest("[data-apply-service-recommendation]");
  if (applyServiceRecommendationButton) {
    const service = getSelectedAdminSupplierService();
    const product = getSelectedAdminProduct() || getSelectedManageProduct() || null;
    if (!service?.requestGuide?.formRecommendation) {
      showToast("적용할 추천 양식이 없습니다.", "error");
      return;
    }
    applySupplierRecommendationToProductDraft(service, { product });
    showToast(product ? "선택한 상품 폼에 추천 양식을 반영했습니다." : "새 상품 제작 폼에 추천 양식을 반영했습니다.");
    renderRoute();
    return;
  }

  const productButton = closest("[data-admin-product-select]");
  if (productButton) {
    const productId = productButton.getAttribute("data-admin-product-select") || "";
    state.ui.adminSelectedProductId = productId;
    const selectedProduct = getAdminProducts().find((item) => item.id === productId);
    if (selectedProduct?.mapping && selectedProduct.mapping.supplierId === state.ui.adminSelectedSupplierId) {
      state.ui.adminSelectedSupplierServiceId = selectedProduct.mapping.supplierServiceId;
    }
    renderRoute();
    return;
  }

  const deleteMappingButton = closest("[data-admin-delete-mapping]");
  if (deleteMappingButton) {
    const mappingId = deleteMappingButton.getAttribute("data-admin-delete-mapping");
    if (!mappingId) return;
    try {
      await apiPost("/api/admin/mappings/delete", { mappingId });
      await refreshAdminData({ preserveDraft: true });
      showToast("상품 매핑을 해제했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "상품 매핑 해제에 실패했습니다.", "error");
    }
    return;
  }

  const newCustomerButton = closest("[data-admin-customer-new]");
  if (newCustomerButton) {
    state.ui.adminCustomerMode = "new";
    state.ui.adminSelectedCustomerId = "";
    state.adminCustomerDraft = blankCustomerDraft();
    renderRoute();
    return;
  }

  const selectCustomerButton = closest("[data-admin-select-customer]");
  if (selectCustomerButton) {
    const customerId = selectCustomerButton.getAttribute("data-admin-select-customer") || "";
    try {
      state.ui.adminCustomerMode = "edit";
      state.ui.adminSelectedCustomerId = customerId;
      await ensureAdminCustomerDetail(customerId);
      state.adminCustomerDraft = customerToDraft(getSelectedAdminCustomer());
      renderRoute();
    } catch (error) {
      showToast(error.message || "고객 상세 정보를 불러오지 못했습니다.", "error");
    }
    return;
  }

  const deleteCustomerButton = closest("[data-admin-delete-customer]");
  if (deleteCustomerButton) {
    const customerId = deleteCustomerButton.getAttribute("data-admin-delete-customer");
    try {
      await apiPost("/api/admin/customers/delete", { customerId });
      delete state.adminCustomerDetails[customerId];
      await refreshAdminData({ preserveDraft: false });
      showToast("고객 계정을 정리했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "고객 계정 정리에 실패했습니다.", "error");
    }
    return;
  }

  const newCategoryButton = closest("[data-admin-category-new]");
  if (newCategoryButton) {
    state.ui.adminCategoryMode = "new";
    state.adminCategoryDraft = blankCategoryDraft(getAdminPlatformGroups()[0]?.id || "");
    renderRoute();
    return;
  }

  const selectCategoryButton = closest("[data-admin-category-select]");
  if (selectCategoryButton) {
    const categoryId = selectCategoryButton.getAttribute("data-admin-category-select") || "";
    const category = getAdminCategories().find((item) => item.id === categoryId) || null;
    state.ui.adminCategoryMode = "edit";
    state.ui.adminSelectedCategoryId = categoryId;
    state.adminCategoryDraft = categoryToDraft(category);
    state.ui.adminProductMode = "edit";
    state.ui.adminSelectedManageProductId = "";
    renderRoute();
    return;
  }

  const deleteCategoryButton = closest("[data-admin-delete-category]");
  if (deleteCategoryButton) {
    const categoryId = deleteCategoryButton.getAttribute("data-admin-delete-category");
    try {
      await apiPost("/api/admin/categories/delete", { categoryId });
      await refreshAdminData({ preserveDraft: false });
      showToast("카테고리를 정리했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "카테고리 정리에 실패했습니다.", "error");
    }
    return;
  }

  const newProductButton = closest("[data-admin-product-new]");
  if (newProductButton) {
    state.ui.adminProductMode = "new";
    state.ui.adminSelectedManageProductId = "";
    state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    renderRoute();
    return;
  }

  const selectManageProductButton = closest("[data-admin-manage-product-select]");
  if (selectManageProductButton) {
    const productId = selectManageProductButton.getAttribute("data-admin-manage-product-select") || "";
    const product = getAdminProducts().find((item) => item.id === productId) || null;
    state.ui.adminProductMode = "edit";
    state.ui.adminSelectedManageProductId = productId;
    state.adminProductDraft = productToDraft(product);
    renderRoute();
    return;
  }

  const deleteProductButton = closest("[data-admin-delete-product]");
  if (deleteProductButton) {
    const productId = deleteProductButton.getAttribute("data-admin-delete-product");
    try {
      await apiPost("/api/admin/products/delete", { productId });
      await refreshAdminData({ preserveDraft: false });
      showToast("상품을 정리했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "상품 정리에 실패했습니다.", "error");
    }
    return;
  }

  const adminOrderFilterButton = closest("[data-admin-order-filter]");
  if (adminOrderFilterButton) {
    state.ui.adminOrderFilter = adminOrderFilterButton.getAttribute("data-admin-order-filter") || "all";
    renderRoute();
    return;
  }

  const platformButton = closest("[data-platform-select]");
  if (platformButton) {
    state.ui.activePlatform = platformButton.getAttribute("data-platform-select");
    renderRoute();
    return;
  }

  const bannerDot = closest("[data-banner-index]");
  if (bannerDot) {
    setHomeBannerIndex(Number(bannerDot.getAttribute("data-banner-index")) || 0);
    return;
  }

  const optionButton = closest("[data-option-select]");
  if (optionButton) {
    const route = getRoute();
    const categoryId = optionButton.getAttribute("data-category-id");
    const productId = optionButton.getAttribute("data-option-select");
    if (route.name === "detail" && categoryId && productId) {
      const selection = ensureSelection(state.categoryCache[categoryId]);
      selection.productId = productId;
      renderRoute();
    }
    return;
  }

  const filterButton = closest("[data-order-filter]");
  if (filterButton) {
    state.ui.orderFilter = filterButton.getAttribute("data-order-filter");
    renderRoute();
    return;
  }

  const chargeTabButton = closest("[data-charge-tab]");
  if (chargeTabButton) {
    state.ui.chargeTab = chargeTabButton.getAttribute("data-charge-tab") || "create";
    closeChargeDetail();
    renderRoute();
    return;
  }

  const chargeHistoryModeButton = closest("[data-charge-history-mode]");
  if (chargeHistoryModeButton) {
    state.ui.chargeHistoryMode = chargeHistoryModeButton.getAttribute("data-charge-history-mode") || "chargeOrders";
    closeChargeDetail();
    renderRoute();
    return;
  }

  const chargeQuickAmountButton = closest("[data-charge-quick-amount]");
  if (chargeQuickAmountButton) {
    const draft = ensureChargeDraft();
    const delta = Number(chargeQuickAmountButton.getAttribute("data-charge-quick-amount") || 0);
    const nextAmount = parseCurrencyInput(draft.amountInput) + delta;
    draft.amountInput = String(nextAmount);
    renderRoute();
    return;
  }

  const chargePaymentChannelButton = closest("[data-charge-payment-channel]");
  if (chargePaymentChannelButton) {
    const nextChannel = chargePaymentChannelButton.getAttribute("data-charge-payment-channel") || "card";
    const method = chargeMethodConfig(nextChannel);
    if (method && !method.enabled) {
      showToast(method.label === "카드/간편결제" ? "카드/간편결제는 준비 중입니다." : "계좌입금 설정이 필요합니다.", "error");
      return;
    }
    const draft = ensureChargeDraft();
    draft.paymentChannel = nextChannel;
    renderRoute();
    return;
  }

  const chargeSubmitButton = closest("[data-charge-submit]");
  if (chargeSubmitButton) {
    const form = document.querySelector("[data-charge-create-form]");
    if (form instanceof HTMLFormElement) {
      form.requestSubmit();
    }
    return;
  }

  const chargeDetailButton = closest("[data-charge-detail-open]");
  if (chargeDetailButton) {
    openChargeDetail(
      chargeDetailButton.getAttribute("data-charge-detail-kind") || "chargeOrders",
      chargeDetailButton.getAttribute("data-charge-detail-open") || "",
    );
    renderRoute();
    return;
  }

  const chargeDetailCloseButton = closest("[data-charge-detail-close]");
  if (chargeDetailCloseButton) {
    closeChargeDetail();
    renderRoute();
    return;
  }
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (target.matches("[data-signup-email-input]")) {
    currentSignupState().email = target.value;
    return;
  }
  if (target.matches("[data-signup-name-input], [data-signup-password-input]")) {
    updateSignupPasswordFeedback(target.closest("[data-public-signup-complete-form]"));
    return;
  }
  if (target.matches("[data-home-search-input]")) {
    state.ui.search = target.value;
    return;
  }
  if (target.matches("[data-search-input='catalog']")) {
    const cursor = target.selectionStart || target.value.length;
    state.ui.search = target.value;
    renderRoute().then(() => {
      const input = document.querySelector("[data-search-input='catalog']");
      if (input) {
        input.focus();
        input.setSelectionRange(cursor, cursor);
      }
    });
    return;
  }

  if (target.matches("[data-charge-amount-input]")) {
    const draft = ensureChargeDraft();
    const cursor = target.selectionStart || target.value.length;
    draft.amountInput = String(parseCurrencyInput(target.value) || "");
    renderRoute().then(() => {
      const input = document.querySelector("[data-charge-amount-input]");
      if (input) {
        input.focus();
        const formattedLength = input.value.length;
        input.setSelectionRange(formattedLength, formattedLength);
      }
    });
    return;
  }

  if (target.matches("[data-charge-draft-field]")) {
    const draft = ensureChargeDraft();
    const field = target.getAttribute("data-charge-draft-field") || "";
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    draft[field] = nextValue;
    if (field === "receiptType" && nextValue === "none") {
      draft.receiptPayload = {
        ...draft.receiptPayload,
        phoneNumber: "",
        businessNumber: "",
        businessName: "",
        recipientEmail: "",
        contactName: "",
      };
    }
    if (target.type === "checkbox" || target.type === "radio" || target.tagName === "SELECT") {
      renderRoute();
    }
    return;
  }

  if (target.matches("[data-charge-receipt-field]")) {
    const draft = ensureChargeDraft();
    const field = target.getAttribute("data-charge-receipt-field") || "";
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    draft.receiptPayload = { ...(draft.receiptPayload || {}), [field]: nextValue };
    if (target.type === "radio" || target.tagName === "SELECT") {
      renderRoute();
    }
    return;
  }

  if (target.matches("[data-charge-filter]")) {
    const field = target.getAttribute("data-charge-filter") || "";
    if (field === "status") state.ui.chargeStatusFilter = target.value || "all";
    if (field === "method") state.ui.chargeMethodFilter = target.value || "all";
    if (field === "period") state.ui.chargePeriodFilter = target.value || "all";
    closeChargeDetail();
    renderRoute();
    return;
  }

  if (target.matches("[data-admin-supplier-field]")) {
    const field = target.getAttribute("data-admin-supplier-field");
    if (!state.adminSupplierDraft) {
      state.adminSupplierDraft = blankSupplierDraft();
    }
    state.adminSupplierDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    if (field === "integrationType") {
      if (target.value !== "mkt24") {
        state.adminSupplierDraft.bearerToken = "";
      }
      renderRoute();
    }
    return;
  }

  if (target.matches("[data-admin-popup-field]")) {
    const field = target.getAttribute("data-admin-popup-field");
    if (!state.adminPopupDraft) {
      state.adminPopupDraft = blankPopupDraft();
    }
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    state.adminPopupDraft[field] = nextValue;
    if (field === "imageUrlInput") {
      state.adminPopupDraft.imageUrl = String(nextValue || "").trim();
      state.adminPopupDraft.imageName = "";
    }
    updateAdminPopupPreview();
    return;
  }

  if (target.matches("[data-admin-home-banner-field]")) {
    const field = target.getAttribute("data-admin-home-banner-field");
    if (!state.adminHomeBannerDraft) {
      state.adminHomeBannerDraft = homeBannerToDraft(getSelectedAdminHomeBanner());
    }
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    state.adminHomeBannerDraft[field] = field === "sortOrder" ? Number(nextValue || 0) : nextValue;
    if (field === "imageUrlInput") {
      state.adminHomeBannerDraft.imageUrl = String(nextValue || "").trim();
      state.adminHomeBannerDraft.imageName = "";
    }
    updateAdminHomeBannerPreview();
    return;
  }

  if (target.matches("[data-admin-platform-section-field]")) {
    const field = target.getAttribute("data-admin-platform-section-field");
    if (!state.adminPlatformSectionDraft) {
      state.adminPlatformSectionDraft = platformSectionToDraft(getSelectedAdminPlatformSection());
    }
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    state.adminPlatformSectionDraft[field] = nextValue;
    if (field === "logoImageUrlInput") {
      state.adminPlatformSectionDraft.logoImageUrl = String(nextValue || "").trim();
      state.adminPlatformSectionDraft.logoImageName = "";
    }
    updateAdminPlatformSectionPreview();
    return;
  }

  if (target.matches("[data-admin-site-settings-field]")) {
    const field = target.getAttribute("data-admin-site-settings-field");
    if (!state.adminSiteSettingsDraft) {
      state.adminSiteSettingsDraft = blankSiteSettingsDraft();
    }
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    state.adminSiteSettingsDraft[field] = nextValue;
    if (field === "headerLogoUrlInput") {
      state.adminSiteSettingsDraft.headerLogoUrl = String(nextValue || "").trim();
      state.adminSiteSettingsDraft.headerLogoName = "";
    }
    if (field === "faviconUrlInput") {
      state.adminSiteSettingsDraft.faviconUrl = String(nextValue || "").trim();
      state.adminSiteSettingsDraft.faviconName = "";
    }
    if (field === "shareImageUrlInput") {
      state.adminSiteSettingsDraft.shareImageUrl = String(nextValue || "").trim();
      state.adminSiteSettingsDraft.shareImageName = "";
    }
    if (field === "useMailSmsSiteName") {
      const mailInput = document.querySelector('[data-admin-site-settings-field="mailSmsSiteName"]');
      if (mailInput) {
        mailInput.disabled = !nextValue;
      }
    }
    updateAdminSiteSettingsPreview();
    return;
  }

  if (target.matches("[data-admin-service-search]")) {
    const cursor = target.selectionStart || target.value.length;
    state.ui.adminServiceSearch = target.value;
    renderRoute().then(() => {
      const input = document.querySelector("[data-admin-service-search]");
      if (input) {
        input.focus();
        input.setSelectionRange(cursor, cursor);
      }
    });
    return;
  }

  if (target.matches("[data-admin-customer-search]")) {
    const cursor = target.selectionStart || target.value.length;
    state.ui.adminCustomerSearch = target.value;
    renderRoute().then(() => {
      const input = document.querySelector("[data-admin-customer-search]");
      if (input) {
        input.focus();
        input.setSelectionRange(cursor, cursor);
      }
    });
    return;
  }

  if (target.matches("[data-admin-order-search]")) {
    const cursor = target.selectionStart || target.value.length;
    state.ui.adminOrderSearch = target.value;
    renderRoute().then(() => {
      const input = document.querySelector("[data-admin-order-search]");
      if (input) {
        input.focus();
        input.setSelectionRange(cursor, cursor);
      }
    });
    return;
  }

  if (target.matches("[data-admin-customer-field]")) {
    const field = target.getAttribute("data-admin-customer-field");
    if (!state.adminCustomerDraft) {
      state.adminCustomerDraft = blankCustomerDraft();
    }
    state.adminCustomerDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return;
  }

  if (target.matches("[data-admin-category-field]")) {
    const field = target.getAttribute("data-admin-category-field");
    if (!state.adminCategoryDraft) {
      state.adminCategoryDraft = blankCategoryDraft(getAdminPlatformGroups()[0]?.id || "");
    }
    state.adminCategoryDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return;
  }

  if (target.matches("[data-admin-product-field]")) {
    const field = target.getAttribute("data-admin-product-field");
    if (!state.adminProductDraft) {
      state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    }
    state.adminProductDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return;
  }

  if (target.matches("[data-order-field]")) {
    const route = getRoute();
    if (route.name !== "detail") return;
    const detail = state.categoryCache[route.id];
    if (!detail) return;
    const selection = ensureSelection(detail);
    selection.fields[target.name] = target.value;
    updateLiveSummary();
    const previewSource = getPreviewSource(detail, getSelectedProduct(detail));
    if (previewSource && previewSource.key === target.name) {
      scheduleLinkPreview(detail);
    }
  }
});

document.addEventListener("change", async (event) => {
  const target = event.target;
  if (target.matches("[data-charge-filter]")) {
    const field = target.getAttribute("data-charge-filter") || "";
    if (field === "status") state.ui.chargeStatusFilter = target.value || "all";
    if (field === "method") state.ui.chargeMethodFilter = target.value || "all";
    if (field === "period") state.ui.chargePeriodFilter = target.value || "all";
    closeChargeDetail();
    renderRoute();
    return;
  }
  if (target.matches("[data-admin-product-advanced-field]")) {
    if (!state.adminProductDraft) {
      state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    }
    const fieldKey = target.getAttribute("data-admin-product-advanced-field") || "";
    const current = Array.isArray(state.adminProductDraft.advancedFieldKeys) ? [...state.adminProductDraft.advancedFieldKeys] : [];
    state.adminProductDraft.advancedFieldKeys = target.checked
      ? [...new Set([...current, fieldKey])]
      : current.filter((item) => item !== fieldKey);
    renderRoute();
    return;
  }
  if (target.matches("[data-admin-service-select-box]")) {
    state.ui.adminSelectedSupplierServiceId = target.value || "";
    renderRoute();
    return;
  }
  if (target.matches("[data-admin-popup-image-upload]")) {
    const file = target.files && target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showToast("이미지 파일만 업로드할 수 있습니다.", "error");
      target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast("팝업 이미지는 5MB 이하로 업로드해 주세요.", "error");
      target.value = "";
      return;
    }
    if (!state.adminPopupDraft) {
      state.adminPopupDraft = blankPopupDraft();
    }
    try {
      state.adminPopupDraft.imageUrl = await readFileAsDataUrl(file);
      state.adminPopupDraft.imageName = file.name;
      state.adminPopupDraft.imageUrlInput = "";
      updateAdminPopupPreview();
      showToast("팝업 이미지가 적용되었습니다. 저장하면 실제 팝업에 반영됩니다.");
    } catch (error) {
      showToast(error.message || "이미지 업로드에 실패했습니다.", "error");
    } finally {
      target.value = "";
    }
    return;
  }

  if (target.matches("[data-admin-home-banner-image-upload]")) {
    const file = target.files && target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showToast("이미지 파일만 업로드할 수 있습니다.", "error");
      target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast("홈 배너 이미지는 5MB 이하로 업로드해 주세요.", "error");
      target.value = "";
      return;
    }
    if (!state.adminHomeBannerDraft) {
      state.adminHomeBannerDraft = homeBannerToDraft(getSelectedAdminHomeBanner());
    }
    try {
      state.adminHomeBannerDraft.imageUrl = await readFileAsDataUrl(file);
      state.adminHomeBannerDraft.imageName = file.name;
      state.adminHomeBannerDraft.imageUrlInput = "";
      showToast("배너 이미지가 적용되었습니다. 저장하면 홈에 반영됩니다.");
      updateAdminHomeBannerPreview();
    } catch (error) {
      showToast(error.message || "이미지 업로드에 실패했습니다.", "error");
    } finally {
      target.value = "";
    }
    return;
  }

  if (target.matches("[data-admin-platform-section-image-upload]")) {
    const file = target.files && target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showToast("이미지 파일만 업로드할 수 있습니다.", "error");
      target.value = "";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      showToast("플랫폼 로고 이미지는 2MB 이하로 업로드해 주세요.", "error");
      target.value = "";
      return;
    }
    if (!state.adminPlatformSectionDraft) {
      state.adminPlatformSectionDraft = platformSectionToDraft(getSelectedAdminPlatformSection());
    }
    try {
      state.adminPlatformSectionDraft.logoImageUrl = await readFileAsDataUrl(file);
      state.adminPlatformSectionDraft.logoImageName = file.name;
      state.adminPlatformSectionDraft.logoImageUrlInput = "";
      showToast("플랫폼 로고가 적용되었습니다. 저장하면 실제 서비스에 반영됩니다.");
      updateAdminPlatformSectionPreview();
    } catch (error) {
      showToast(error.message || "이미지 업로드에 실패했습니다.", "error");
    } finally {
      target.value = "";
    }
    return;
  }

  const siteImageType = target.getAttribute("data-admin-site-settings-image-upload");
  if (!siteImageType) return;
  const file = target.files && target.files[0];
  if (!file) return;
  try {
    await applyAdminSiteSettingsImage(siteImageType, file);
    if (siteImageType === "headerLogo") {
      showToast("상단 로고가 적용되었습니다. 저장하면 홈 상단과 고정 서비스 바에 반영됩니다.");
    } else if (siteImageType === "favicon") {
      showToast("파비콘이 적용되었습니다. 저장하면 실제 사이트에 반영됩니다.");
    } else {
      showToast("대표 이미지가 적용되었습니다. 저장하면 공유 미리보기에 반영됩니다.");
    }
  } catch (error) {
    showToast(error.message || "이미지 업로드에 실패했습니다.", "error");
  } finally {
    target.value = "";
  }
});

document.addEventListener("mousemove", (event) => {
  const svg = event.target.closest(".admin-analytics-chart__svg");
  if (!svg) {
    document.querySelectorAll(".admin-analytics-chart").forEach((chart) => hideAnalyticsChartTooltip(chart));
    return;
  }
  updateAnalyticsChartTooltip(svg.closest(".admin-analytics-chart"), event.clientX);
});

document.addEventListener("mouseleave", (event) => {
  const svg = event.target.closest(".admin-analytics-chart__svg");
  if (!svg) return;
  hideAnalyticsChartTooltip(svg.closest(".admin-analytics-chart"));
}, true);

document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (form.matches("[data-public-login-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const redirectPath = postAuthRedirectPath();
      const result = await apiPost("/api/login", {
        email: formData.get("email"),
        password: formData.get("password"),
        rememberMe: formData.get("rememberMe") === "on",
      });
      state.publicCsrfToken = result.csrfToken || "";
      closeLoginModal();
      await refreshCoreData();
      if (redirectPath && redirectPath !== window.location.pathname) {
        navigate(redirectPath);
        return;
      }
      renderRoute();
      showToast("로그인되었습니다.");
    } catch (error) {
      showToast(error.message || "로그인에 실패했습니다.", "error");
    }
    return;
  }
  if (form.matches("[data-public-signup-send-code-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/auth/email/send-code", {
        email: formData.get("email"),
      });
      Object.assign(currentSignupState(), {
        step: "verify",
        email: result.email || String(formData.get("email") || "").trim(),
        challengeId: result.challengeId || "",
        resendAvailableAt: result.resendAvailableAt || "",
        expiresAt: result.expiresAt || "",
        previewCode: result.previewCode || "",
        verificationToken: "",
        verifiedAt: "",
        completeBy: "",
      });
      renderRoute();
      showToast("인증코드를 보냈습니다.");
    } catch (error) {
      showToast(error.message || "인증코드 발송에 실패했습니다.", "error");
    }
    return;
  }
  if (form.matches("[data-public-signup-verify-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const signup = currentSignupState();
      const result = await apiPost("/api/auth/email/verify-code", {
        email: signup.email,
        code: formData.get("code"),
      });
      Object.assign(signup, {
        step: "account",
        verificationToken: result.verificationToken || "",
        verifiedAt: result.verifiedAt || "",
        completeBy: result.completeBy || "",
      });
      renderRoute();
      showToast("이메일 인증이 완료되었습니다.");
    } catch (error) {
      showToast(error.message || "인증 확인에 실패했습니다.", "error");
    }
    return;
  }
  if (form.matches("[data-public-signup-complete-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const redirectPath = postAuthRedirectPath();
      const signup = currentSignupState();
      const result = await apiPost("/api/signup", {
        email: signup.email,
        verificationToken: signup.verificationToken,
        name: formData.get("name"),
        password: formData.get("password"),
        passwordConfirmation: formData.get("passwordConfirmation"),
        termsAgreed: formData.get("termsAgreed") === "on",
        privacyAgreed: formData.get("privacyAgreed") === "on",
        ageConfirmed: formData.get("ageConfirmed") === "on",
        marketingAgreed: formData.get("marketingAgreed") === "on",
      });
      state.publicCsrfToken = result.csrfToken || "";
      resetSignupFlow();
      closeLoginModal();
      await refreshCoreData();
      if (redirectPath && redirectPath !== window.location.pathname) {
        navigate(redirectPath);
        return;
      }
      renderRoute();
      showToast("회원가입이 완료되었습니다.");
    } catch (error) {
      showToast(error.message || "회원가입에 실패했습니다.", "error");
    }
    return;
  }
  if (form.matches("[data-charge-create-form]")) {
    event.preventDefault();
    const draft = ensureChargeDraft();
    const chargeConfig = state.bootstrap?.chargeConfig || {};
    const amountSummary = chargeAmountSummary(draft.amountInput);
    const method = chargeMethodConfig(draft.paymentChannel);
    if (!draft.agreementChecked) {
      showToast("충전 유의사항과 환불 안내에 동의해 주세요.", "error");
      return;
    }
    if (amountSummary.amount < Number(chargeConfig.minimumAmount || 5000)) {
      showToast(`최소 충전 금액은 ${formatMoney(chargeConfig.minimumAmount || 5000)}입니다.`, "error");
      return;
    }
    if (!method?.enabled) {
      showToast("선택한 결제수단은 아직 사용할 수 없습니다.", "error");
      return;
    }
    const payload = {
      amount: amountSummary.amount,
      paymentChannel: draft.paymentChannel,
      paymentMethodDetail: draft.paymentMethodDetail,
      depositorName: draft.depositorName,
      receiptType: draft.receiptType,
      receiptPayload: draft.receiptPayload,
    };
    try {
      const created = await apiPost("/api/charge-orders", payload);
      let detailId = created.chargeOrder.id;
      if (draft.paymentChannel === "bank_transfer") {
        await apiPost(`/api/charge-orders/${encodeURIComponent(detailId)}/deposit-request`, payload);
        await refreshCoreData();
        state.ui.chargeTab = "history";
        state.ui.chargeHistoryMode = "chargeOrders";
        openChargeDetail("chargeOrders", detailId);
        state.chargeDraft = blankChargeDraft(state.bootstrap?.chargeConfig);
        showToast("입금 요청이 접수되었습니다. 입금 확인 후 보유금액이 반영됩니다.");
        renderRoute();
        return;
      }
      const started = await apiPost(`/api/charge-orders/${encodeURIComponent(detailId)}/start-payment`, {
        paymentMethodDetail: draft.paymentMethodDetail,
      });
      await refreshCoreData();
      state.ui.chargeTab = "history";
      state.ui.chargeHistoryMode = "chargeOrders";
      openChargeDetail("chargeOrders", detailId);
      state.chargeDraft = blankChargeDraft(state.bootstrap?.chargeConfig);
      renderRoute();
      if (started.paymentSession?.providerConfigured) {
        showToast("결제 세션이 준비되었습니다. PG SDK 연결 단계가 남아 있습니다.");
      } else {
        showToast("결제 준비에 실패했습니다.", "error");
      }
    } catch (error) {
      showToast(error.message || "충전 요청에 실패했습니다.", "error");
    }
    return;
  }
  if (form.matches("[data-admin-login-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/admin/login", {
        username: formData.get("username"),
        password: formData.get("password"),
      });
      setAdminAnalyticsExclusion(true);
      state.adminSession = {
        configured: true,
        authenticated: true,
        username: result.username || "admin",
        csrfToken: result.csrfToken || "",
      };
      state.adminCsrfToken = result.csrfToken || "";
      resetAdminState({ preserveSession: true });
      await refreshAdminData({ preserveDraft: false });
      if (state.ui.adminSelectedCustomerId) {
        await ensureAdminCustomerDetail(state.ui.adminSelectedCustomerId);
      }
      renderRoute();
    } catch (error) {
      showToast(error.message || "관리자 로그인에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-popup-form]")) {
    event.preventDefault();
    const draft = state.adminPopupDraft || blankPopupDraft();
    try {
      const result = await apiPost("/api/admin/popup", {
        id: draft.id,
        name: draft.name,
        badgeText: draft.badgeText,
        title: draft.title,
        description: draft.description,
        imageUrl: draft.imageUrl,
        route: draft.route,
        theme: draft.theme,
        isActive: draft.isActive,
      });
      state.adminPopupDraft = popupToDraft(result.popup);
      state.bootstrap = null;
      await refreshAdminData({ preserveDraft: false });
      showToast("홈 팝업 설정을 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "홈 팝업 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-home-banner-form]")) {
    event.preventDefault();
    const draft = state.adminHomeBannerDraft || homeBannerToDraft(getSelectedAdminHomeBanner());
    try {
      const result = await apiPost("/api/admin/home-banners", {
        id: draft.id,
        title: draft.title,
        subtitle: draft.subtitle,
        ctaLabel: draft.ctaLabel,
        route: draft.route,
        imageUrl: draft.imageUrl,
        theme: draft.theme,
        isActive: draft.isActive,
        sortOrder: draft.sortOrder,
      });
      state.adminHomeBannerDraft = homeBannerToDraft(result.banner);
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("홈 배너를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "홈 배너 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-platform-section-form]")) {
    event.preventDefault();
    const draft = state.adminPlatformSectionDraft || platformSectionToDraft(getSelectedAdminPlatformSection());
    try {
      const result = await apiPost("/api/admin/platform-sections", {
        id: draft.id,
        icon: draft.icon,
        logoImageUrl: draft.logoImageUrl,
        accentColor: draft.accentColor,
      });
      state.adminPlatformSectionDraft = platformSectionToDraft(result.platformSection);
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("플랫폼 로고를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "플랫폼 로고 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-site-settings-form]")) {
    event.preventDefault();
    const draft = state.adminSiteSettingsDraft || blankSiteSettingsDraft();
    try {
      const result = await apiPost("/api/admin/site-settings", {
        siteName: draft.siteName,
        siteDescription: draft.siteDescription,
        useMailSmsSiteName: draft.useMailSmsSiteName,
        mailSmsSiteName: draft.mailSmsSiteName,
        headerLogoUrl: draft.headerLogoUrl,
        faviconUrl: draft.faviconUrl,
        shareImageUrl: draft.shareImageUrl,
      });
      state.adminSiteSettingsDraft = siteSettingsToDraft(result.siteSettings);
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("사이트 기본 설정을 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "사이트 기본 설정 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-customer-form]")) {
    event.preventDefault();
    const draft = state.adminCustomerDraft || blankCustomerDraft();
    try {
      const result = await apiPost("/api/admin/customers", {
        id: draft.id,
        name: draft.name,
        email: draft.email,
        password: draft.password,
        phone: draft.phone,
        tier: draft.tier,
        role: draft.role,
        notes: draft.notes,
        isActive: draft.isActive,
      });
      state.ui.adminCustomerMode = "edit";
      state.ui.adminSelectedCustomerId = result.customer.id;
      state.adminCustomerDetails[result.customer.id] = result.customer;
      state.adminCustomerDraft = customerToDraft(result.customer);
      await refreshAdminData({ preserveDraft: false });
      await ensureAdminCustomerDetail(result.customer.id, { force: true });
      showToast(`${result.customer.name} 계정을 저장했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "고객 계정 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-balance-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/admin/customers/balance", {
        customerId: formData.get("customerId"),
        amount: formData.get("amount"),
        memo: formData.get("memo"),
      });
      state.adminCustomerDetails[result.customer.id] = result.customer;
      await refreshAdminData({ preserveDraft: false });
      await ensureAdminCustomerDetail(result.customer.id, { force: true });
      showToast(`잔액 조정 완료: ${result.balanceAfterLabel}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "잔액 조정에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-category-form]")) {
    event.preventDefault();
    const draft = state.adminCategoryDraft || blankCategoryDraft(getAdminPlatformGroups()[0]?.id || "");
    try {
      const result = await apiPost("/api/admin/categories", {
        id: draft.id,
        groupId: draft.groupId,
        name: draft.name,
        description: draft.description,
        optionLabelName: draft.optionLabelName,
        heroTitle: draft.heroTitle,
        heroSubtitle: draft.heroSubtitle,
        serviceDescriptionHtml: draft.serviceDescriptionHtml,
        cautionText: draft.cautionText,
        refundText: draft.refundText,
        isActive: draft.isActive,
        sortOrder: draft.sortOrder,
      });
      state.ui.adminCategoryMode = "edit";
      state.ui.adminSelectedCategoryId = result.category.id;
      state.adminCategoryDraft = categoryToDraft(result.category);
      await refreshAdminData({ preserveDraft: false });
      showToast(`${result.category.name} 카테고리를 저장했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "카테고리 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-product-form]")) {
    event.preventDefault();
    const draft = state.adminProductDraft || blankProductDraft(state.ui.adminSelectedCategoryId);
    try {
      const result = await apiPost("/api/admin/products", {
        id: draft.id,
        categoryId: draft.categoryId,
        name: draft.name,
        menuName: draft.menuName || draft.name,
        optionName: draft.optionName,
        productCode: draft.productCode,
        price: draft.price,
        minAmount: draft.minAmount,
        maxAmount: draft.maxAmount,
        stepAmount: draft.stepAmount,
        priceStrategy: draft.priceStrategy,
        unitLabel: draft.unitLabel,
        badge: draft.badge,
        isDiscounted: draft.isDiscounted,
        estimatedTurnaround: draft.estimatedTurnaround,
        isActive: draft.isActive,
        sortOrder: draft.sortOrder,
        formPreset: draft.formPreset,
        targetLabel: draft.targetLabel,
        targetPlaceholder: draft.targetPlaceholder,
        quantityLabel: draft.quantityLabel,
        memoLabel: draft.memoLabel,
        advancedFieldKeys: draft.advancedFieldKeys || [],
      });
      state.ui.adminProductMode = "edit";
      state.ui.adminSelectedManageProductId = result.product.id;
      state.ui.adminSelectedCategoryId = result.product.categoryId;
      state.adminProductDraft = productToDraft(result.product);
      await refreshAdminData({ preserveDraft: false });
      showToast(`${result.product.name} 상품을 저장했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "상품 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-order-status-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      await apiPost("/api/admin/orders/status", {
        orderId: formData.get("orderId"),
        status: formData.get("status"),
        adminMemo: formData.get("adminMemo"),
      });
      await refreshAdminData({ preserveDraft: true });
      showToast("주문 상태를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "주문 상태 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-supplier-form]")) {
    event.preventDefault();
    const draft = state.adminSupplierDraft || blankSupplierDraft();

    try {
      const result = await apiPost("/api/admin/suppliers", {
        id: draft.id,
        name: draft.name,
        apiUrl: draft.apiUrl,
        integrationType: draft.integrationType,
        apiKey: draft.apiKey,
        bearerToken: draft.bearerToken,
        notes: draft.notes,
        isActive: draft.isActive,
      });
      state.ui.adminSupplierMode = "edit";
      state.ui.adminSelectedSupplierId = result.supplier.id;
      state.adminSupplierDraft = supplierToDraft(result.supplier);
      state.adminConnectionResult = null;
      await refreshAdminData({ preserveDraft: false });
      await ensureAdminSupplierServices(result.supplier.id);
      showToast(`${result.supplier.name} 공급사를 저장했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "공급사 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-mapping-form]")) {
    event.preventDefault();
    const selectedSupplier = getSelectedAdminSupplier();
    const selectedProduct = getSelectedAdminProduct();
    const selectedService = selectedSupplier
      ? state.adminSupplierServices[selectedSupplier.id]?.services?.find(
          (service) => service.id === state.ui.adminSelectedSupplierServiceId
        ) || null
      : null;

    if (!selectedSupplier || !selectedProduct || !selectedService) {
      showToast("공급사와 서비스를 먼저 선택해 주세요.", "error");
      return;
    }

    const formData = new FormData(form);
    try {
      await apiPost("/api/admin/mappings", {
        productId: selectedProduct.id,
        supplierId: selectedSupplier.id,
        supplierServiceId: selectedService.id,
        pricingMode: formData.get("pricingMode") || "multiplier",
        priceMultiplier: formData.get("priceMultiplier") || "1",
        fixedMarkup: formData.get("fixedMarkup") || "0",
        isPrimary: true,
      });
      await refreshAdminData({ preserveDraft: true });
      showToast("상품 매핑을 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "상품 매핑 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (!form.matches("[data-order-form]")) return;
  event.preventDefault();

  const route = getRoute();
  if (route.name !== "detail") return;
  if (!isLoggedIn()) {
    state.ui.loginRedirect = window.location.pathname || "/products";
    navigate("/auth");
    showToast("주문하려면 먼저 로그인해 주세요.", "error");
    return;
  }
  const detail = state.categoryCache[route.id];
  if (!detail) return;

  const summary = calculateSummary(detail);
  if (!summary) return;
  const formData = new FormData(form);
  const fields = Object.fromEntries(formData.entries());
  state.productSelections[detail.id].fields = { ...state.productSelections[detail.id].fields, ...fields };
  const validation = getOrderValidationState(detail, summary.product);
  if (validation.blocked) {
    showToast(validation.reason || "주문 정보를 다시 확인해 주세요.", "error");
    return;
  }

  try {
    const result = await apiPost("/api/orders", {
      productId: summary.product.id,
      fields,
    });
    await refreshCoreData();
    showToast(`주문이 접수되었습니다. ${result.totalPriceLabel} 결제 완료`);
    navigate("/orders");
  } catch (error) {
    showToast(error.message || "주문 접수에 실패했습니다.", "error");
  }
});

document.addEventListener(
  "scroll",
  (event) => {
    const target = event.target;
    if (target instanceof HTMLElement && target.matches("[data-home-platform-scroller]")) {
      updateHomePlatformScrollerState(target);
    }
  },
  true
);

document.addEventListener(
  "wheel",
  (event) => {
    const scroller = getHomePlatformScroller(event.target);
    if (!scroller) return;
    if (!homePlatformScrollerAtBoundary(scroller, event.deltaY)) return;
    event.preventDefault();
    relayHomePlatformScroll(scroller, event.deltaY);
  },
  { passive: false }
);

document.addEventListener(
  "touchstart",
  (event) => {
    const scroller = getHomePlatformScroller(event.target);
    if (!scroller || event.touches.length !== 1) {
      homePlatformTouchState.scroller = null;
      return;
    }
    homePlatformTouchState.scroller = scroller;
    homePlatformTouchState.lastY = event.touches[0].clientY;
  },
  { passive: true }
);

document.addEventListener(
  "touchmove",
  (event) => {
    const scroller = homePlatformTouchState.scroller;
    if (!scroller || event.touches.length !== 1) return;
    const currentY = event.touches[0].clientY;
    const deltaY = homePlatformTouchState.lastY - currentY;
    homePlatformTouchState.lastY = currentY;
    if (!homePlatformScrollerAtBoundary(scroller, deltaY)) return;
    event.preventDefault();
    relayHomePlatformScroll(scroller, deltaY);
  },
  { passive: false }
);

document.addEventListener(
  "touchend",
  () => {
    homePlatformTouchState.scroller = null;
  },
  { passive: true }
);

document.addEventListener("keydown", (event) => {
  const target = event.target;
  if (target.matches("[data-home-search-input]") && event.key === "Enter") {
    event.preventDefault();
    navigate("/products");
  }
});

window.addEventListener("popstate", () => {
  renderRoute();
});

async function init() {
  showLoading();
  try {
    await Promise.all([refreshCoreData(), loadCatalog()]);
    await renderRoute();
  } catch (error) {
    app.innerHTML = renderNotFound(error.message || "패널 초기화에 실패했습니다.");
  }
}

init();
