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
import {
  configureAdminSections,
  formatAnalyticsTooltipValue,
  renderAnalyticsAdminSection,
  renderSiteSettingsAdminSection,
  renderPopupAdminSection,
  renderContentAdminSection,
  renderSupplierAdminSection,
  renderCustomerAdminSection,
  renderCatalogAdminSection,
  renderCafe24AdminSection,
  renderAdminChargesSection,
  renderAdminOrdersSection,
  renderAdminOverviewSection,
  renderHomePopupOverlay,
  updateAdminPopupPreview,
  updateAdminHomeBannerPreview,
  updateAdminPlatformSectionPreview,
  updateAdminSiteSettingsPreview,
} from "./admin/sections.js";
import {
  configureCafe24AdminActions,
  handleCafe24AdminChange,
  handleCafe24AdminClick,
  handleCafe24AdminSubmit,
} from "./admin/cafe24.js";
import { parseRoute } from "./shared/routes.js";
import { createRuntimeConfig } from "./shared/runtime.js";
import { blankPublicAuthState, blankSignupState, evaluatePublicPasswordStrength } from "./public/auth-state.js";

const DEFAULT_LIGHT_BRAND_LOGO_URL = "/static/assets/instamart-logo-light-bg.png";

const app = document.querySelector("#app");
const toast = document.querySelector("#toast");

const state = {
  bootstrap: null,
  bootstrapMode: "none",
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
  adminMkt24ProductSettings: {},
  adminCafe24ProductLookup: { products: [], detail: null, query: {}, warnings: [] },
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
    adminChargeFilter: "all",
    adminChargeSearch: "",
    adminSupplierMode: "edit",
    adminSelectedPlatformSectionId: "",
    adminSelectedSupplierId: "",
    adminCafe24SelectedSupplierId: "",
    adminCafe24Tab: "queue",
    adminCafe24PaymentFilter: "all",
    adminCafe24MappingFilter: "all",
    adminCafe24Search: "",
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
    adminContentTab: "notices",
    adminNoticeMode: "edit",
    adminSelectedNoticeId: "",
    adminFaqMode: "edit",
    adminSelectedFaqId: "",
    closedPopups: {},
  },
};

let bannerIntervalId = null;
let catalogLoadPromise = null;
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
  failed: { label: "실패", className: "is-failed" },
  cancelled: { label: "취소", className: "is-cancelled" },
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
  { id: "content", label: "콘텐츠", icon: "≡", description: "공지, FAQ, 운영 로그", title: "콘텐츠/운영 로그", summary: "공지사항, FAQ, 관리자 작업 로그를 관리합니다." },
  { id: "suppliers", label: "공급사", icon: "⇄", description: "API 연결과 서비스 동기화", title: "공급사 연동 센터", summary: "공급사 API 연결, 서비스 동기화, 상품 매핑을 운영합니다." },
  { id: "cafe24", label: "Cafe24", icon: "C24", description: "외부몰 주문 수집/매핑", title: "Cafe24 주문 연동", summary: "Cafe24 주문을 수집해 내부 표준 주문으로 정규화하고 공급사 처리 흐름에 연결합니다." },
  { id: "customers", label: "회원정보", icon: "☻", description: "계정, 잔액, 운영 메모", title: "고객/계정 관리", summary: "회원 계정, 등급, 잔액, 내부 운영 메모를 관리합니다." },
  { id: "charges", label: "충전관리", icon: "₩", description: "입금 확인과 결제 상태", title: "충전 운영 센터", summary: "충전 주문, 입금 확인, 실패/취소 상태를 관리합니다." },
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
    if (section.id === "content") stat = `${Number(state.adminBootstrap?.notices?.length || 0)}개 공지`;
    if (section.id === "suppliers") stat = `${Number(stats.supplierCount || 0)}개`;
    if (section.id === "cafe24") {
      stat = Number(stats.cafe24ReconnectRequiredCount || 0)
        ? `${Number(stats.cafe24ReconnectRequiredCount || 0)}재연결`
        : `${Number(stats.cafe24WaitingInputCount || 0)}확인`;
    }
    if (section.id === "customers") stat = `${Number(stats.customerCount || 0)}명`;
    if (section.id === "charges") stat = `${Number(stats.pendingChargeCount || 0)}대기`;
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
      dispatch: "상품 상세 주문 필드와 optionInfo 기본값을 저장하면 MKT24 주문 API로 발주합니다.",
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

function blankNoticeDraft() {
  return {
    id: "",
    title: "",
    body: "",
    tag: "공지",
    pinned: false,
    publishedAt: new Date().toISOString(),
  };
}

function noticeToDraft(notice) {
  if (!notice) return blankNoticeDraft();
  return {
    id: notice.id || "",
    title: notice.title || "",
    body: notice.body || "",
    tag: notice.tag || "공지",
    pinned: Boolean(notice.pinned),
    publishedAt: notice.publishedAt || new Date().toISOString(),
  };
}

function blankFaqDraft() {
  return {
    id: "",
    question: "",
    answer: "",
    sortOrder: 0,
  };
}

function faqToDraft(faq) {
  if (!faq) return blankFaqDraft();
  return {
    id: faq.id || "",
    question: faq.question || "",
    answer: faq.answer || "",
    sortOrder: Number(faq.sortOrder || 0),
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

function getAdminChargeOrders() {
  return state.adminBootstrap?.adminChargeOrders || [];
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

function getAdminNotices() {
  return state.adminBootstrap?.notices || [];
}

function getAdminFaqs() {
  return state.adminBootstrap?.faqs || [];
}

function getAdminAuditLogs() {
  return state.adminBootstrap?.auditLogs || [];
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

function getSelectedAdminNotice() {
  return getAdminNotices().find((notice) => notice.id === state.ui.adminSelectedNoticeId) || null;
}

function getSelectedAdminFaq() {
  return getAdminFaqs().find((faq) => faq.id === state.ui.adminSelectedFaqId) || null;
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
  const notices = getAdminNotices();
  const faqs = getAdminFaqs();

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

  if (state.ui.adminNoticeMode !== "new") {
    if (
      state.ui.adminSelectedNoticeId &&
      !notices.some((notice) => notice.id === state.ui.adminSelectedNoticeId)
    ) {
      state.ui.adminSelectedNoticeId = "";
    }
    if (!state.ui.adminSelectedNoticeId && notices.length) {
      state.ui.adminSelectedNoticeId = notices[0].id;
    }
  }
  if (state.ui.adminNoticeMode === "new") {
    if (!preserveDraft || !state.adminNoticeDraft) {
      state.adminNoticeDraft = blankNoticeDraft();
    }
  } else {
    const selectedNotice = getSelectedAdminNotice();
    if (!preserveDraft || !state.adminNoticeDraft) {
      state.adminNoticeDraft = noticeToDraft(selectedNotice);
    } else if (state.adminNoticeDraft.id) {
      const matchingNotice = notices.find((notice) => notice.id === state.adminNoticeDraft.id);
      if (matchingNotice) {
        state.adminNoticeDraft = noticeToDraft(matchingNotice);
      }
    }
  }

  if (state.ui.adminFaqMode !== "new") {
    if (state.ui.adminSelectedFaqId && !faqs.some((faq) => faq.id === state.ui.adminSelectedFaqId)) {
      state.ui.adminSelectedFaqId = "";
    }
    if (!state.ui.adminSelectedFaqId && faqs.length) {
      state.ui.adminSelectedFaqId = faqs[0].id;
    }
  }
  if (state.ui.adminFaqMode === "new") {
    if (!preserveDraft || !state.adminFaqDraft) {
      state.adminFaqDraft = blankFaqDraft();
    }
  } else {
    const selectedFaq = getSelectedAdminFaq();
    if (!preserveDraft || !state.adminFaqDraft) {
      state.adminFaqDraft = faqToDraft(selectedFaq);
    } else if (state.adminFaqDraft.id) {
      const matchingFaq = faqs.find((faq) => faq.id === state.adminFaqDraft.id);
      if (matchingFaq) {
        state.adminFaqDraft = faqToDraft(matchingFaq);
      }
    }
  }
}

function resetAdminState({ preserveSession = false } = {}) {
  state.adminBootstrap = null;
  state.adminSupplierServices = {};
  state.adminMkt24ProductSettings = {};
  state.adminCafe24ProductLookup = { products: [], detail: null, query: {}, warnings: [] };
  state.adminCustomerDetails = {};
  state.adminSiteSettingsDraft = null;
  state.adminPopupDraft = null;
  state.adminHomeBannerDraft = null;
  state.adminSupplierDraft = null;
  state.adminConnectionResult = null;
  state.adminCustomerDraft = null;
  state.adminCategoryDraft = null;
  state.adminProductDraft = null;
  state.adminNoticeDraft = null;
  state.adminFaqDraft = null;
  state.ui.adminActiveSection = "overview";
  state.ui.adminAnalyticsTab = "dashboard";
  state.ui.adminAnalyticsRange = "30d";
  state.ui.adminCustomerFilter = "all";
  state.ui.adminCustomerSearch = "";
  state.ui.adminSupplierMode = "edit";
  state.ui.adminSelectedSupplierId = "";
  state.ui.adminCafe24SelectedSupplierId = "";
  state.ui.adminCafe24Tab = "queue";
  state.ui.adminCafe24PaymentFilter = "all";
  state.ui.adminCafe24MappingFilter = "all";
  state.ui.adminCafe24Search = "";
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
  state.ui.adminContentTab = "notices";
  state.ui.adminNoticeMode = "edit";
  state.ui.adminSelectedNoticeId = "";
  state.ui.adminFaqMode = "edit";
  state.ui.adminSelectedFaqId = "";
  state.ui.adminChargeFilter = "all";
  state.ui.adminChargeSearch = "";
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

function mkt24ProductSettingKey(supplierId, productUuid) {
  return `${supplierId || ""}:${productUuid || ""}`;
}

function getAdminMkt24ProductSetting(supplierId, productUuid) {
  return state.adminMkt24ProductSettings[mkt24ProductSettingKey(supplierId, productUuid)] || null;
}

async function ensureAdminMkt24ProductSetting(supplierId, productUuid, { force = false } = {}) {
  if (!supplierId || !productUuid) return null;
  const key = mkt24ProductSettingKey(supplierId, productUuid);
  if (force || !state.adminMkt24ProductSettings[key]) {
    const query = force ? "?refresh=1" : "";
    const data = await apiGet(
      `/api/admin/suppliers/${encodeURIComponent(supplierId)}/mkt24-product-settings/${encodeURIComponent(productUuid)}${query}`
    );
    state.adminMkt24ProductSettings[key] = data.setting || {};
  }
  return state.adminMkt24ProductSettings[key];
}

async function ensureSelectedMkt24ProductSetting({ force = false } = {}) {
  const supplier = getSelectedAdminSupplier();
  const service = getSelectedAdminSupplierService();
  if (supplier?.integrationType !== "mkt24" || !service?.externalServiceId) return null;
  return ensureAdminMkt24ProductSetting(supplier.id, service.externalServiceId, { force });
}

function collectMkt24ProductSettingPayload(form) {
  const selectedSupplier = getSelectedAdminSupplier();
  const selectedService = getSelectedAdminSupplierService();
  if (!selectedSupplier || !selectedService) {
    throw new Error("MKT24 공급사와 서비스를 먼저 선택해 주세요.");
  }
  const fieldConfig = {};
  form.querySelectorAll("[data-mkt24-field-row]").forEach((row) => {
    const key = row.getAttribute("data-mkt24-field-row") || "";
    if (!key) return;
    const field = (suffix) => Array.from(row.querySelectorAll("[name]")).find((item) => item.name === `field_${key}_${suffix}`);
    const defaultValue = field("defaultValue")?.value || "";
    const config = {
      enabled: Boolean(field("enabled")?.checked),
      required: Boolean(field("required")?.checked),
      inputMode: field("inputMode")?.value || "user_input",
      defaultValue,
    };
    const minInput = field("min");
    const maxInput = field("max");
    const stepInput = field("step");
    if (minInput) config.min = minInput.value;
    if (maxInput) config.max = maxInput.value;
    if (stepInput) config.step = stepInput.value;
    fieldConfig[key] = config;
  });

  const optionDefaultsRaw = form.querySelector('[name="optionDefaultsJson"]')?.value || "{}";
  let optionDefaults = {};
  try {
    optionDefaults = optionDefaultsRaw.trim() ? JSON.parse(optionDefaultsRaw) : {};
  } catch (error) {
    throw new Error("optionInfo JSON 형식이 올바르지 않습니다.");
  }
  return {
    supplierId: selectedSupplier.id,
    supplierServiceId: selectedService.id,
    productUuid: selectedService.externalServiceId,
    isActive: Boolean(form.querySelector('[name="isActive"]')?.checked),
    fieldConfig,
    optionConfig: {
      enabled: Boolean(form.querySelector('[name="optionEnabled"]')?.checked),
      defaults: optionDefaults,
    },
  };
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

function readableApiErrorMessage(errorPayload, fallback = "요청 처리 중 오류가 발생했습니다.") {
  if (!errorPayload) return fallback;
  if (typeof errorPayload === "string") return errorPayload;
  if (typeof errorPayload === "object") {
    return (
      errorPayload.message ||
      errorPayload.detail ||
      errorPayload.reason ||
      errorPayload.error ||
      fallback
    );
  }
  return String(errorPayload);
}

function isTransientApiError(error) {
  const status = Number(error?.status || 0);
  return error?.name === "TypeError" || status === 0 || status === 408 || status === 429 || status >= 500;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
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
    const error = new Error(readableApiErrorMessage(data.error));
    error.status = response.status;
    throw error;
  }
  return data;
}

async function apiGetWithRetry(path, { retries = 1, retryDelay = 900 } = {}) {
  try {
    return await apiGet(path);
  } catch (error) {
    if (retries <= 0 || !isTransientApiError(error)) {
      throw error;
    }
    await delay(retryDelay);
    return apiGetWithRetry(path, { retries: retries - 1, retryDelay: Math.round(retryDelay * 1.5) });
  }
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
    const error = new Error(readableApiErrorMessage(data.error));
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

function consumeCafe24OAuthNotice() {
  const params = new URLSearchParams(window.location.search);
  const status = params.get("cafe24OAuth");
  if (!status) return;
  const message = params.get("message") || "";
  if (status === "success") {
    showToast("Cafe24 OAuth 토큰을 저장했습니다.");
  } else {
    showToast(message || "Cafe24 OAuth 연결에 실패했습니다.", "error");
  }
  window.history.replaceState({}, "", window.location.pathname);
}

function routeCanUsePublicShell(route) {
  if (!route) return true;
  return ["home", "products", "detail", "admin"].includes(route.name);
}

function routeNeedsFullBootstrap(route) {
  if (!route) return false;
  if (["help", "legal"].includes(route.name)) return true;
  return isLoggedIn() && ["charge", "orders", "my"].includes(route.name);
}

async function refreshCoreData({ shell = false } = {}) {
  const endpoint = shell ? "/api/public-shell" : "/api/bootstrap";
  const bootstrapData = await apiGetWithRetry(endpoint);
  state.bootstrap = bootstrapData;
  state.bootstrapMode = shell ? "shell" : "full";
  state.publicCsrfToken = bootstrapData.viewer?.csrfToken || "";
  if (bootstrapData.viewer?.authenticated && !shell) {
    const [ordersData, walletData, walletLedgerData, chargeOrdersData] = await Promise.all([
      apiGetWithRetry("/api/orders"),
      apiGetWithRetry("/api/wallet"),
      apiGetWithRetry("/api/wallet/ledger?limit=100"),
      apiGetWithRetry("/api/charge-orders?limit=100"),
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
  } else if (!bootstrapData.viewer?.authenticated) {
    state.orders = [];
    state.orderCounts = { all: 0, queued: 0, in_progress: 0, completed: 0 };
    state.transactions = [];
    state.wallet = null;
    state.walletLedger = [];
    state.chargeOrders = [];
    state.chargeDraft = null;
  }
  if (!state.ui.activePlatform && bootstrapData.platforms.length) {
    state.ui.activePlatform = bootstrapData.platforms[0].id;
  }
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

async function loadCatalog({ force = false } = {}) {
  if (state.catalog.length && !force) return state.catalog;
  if (catalogLoadPromise && !force) return catalogLoadPromise;
  catalogLoadPromise = apiGetWithRetry("/api/products")
    .then((data) => {
      state.catalog = data.platforms;
      if (!state.ui.activePlatform && state.catalog.length) {
        state.ui.activePlatform = state.catalog[0].id;
      }
      return state.catalog;
    })
    .finally(() => {
      catalogLoadPromise = null;
    });
  return catalogLoadPromise;
}

async function ensureCategory(categoryId) {
  if (!state.categoryCache[categoryId]) {
    const data = await apiGetWithRetry(`/api/product-categories/${encodeURIComponent(categoryId)}`);
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

function createOrderIdempotencyKey() {
  if (window.crypto?.randomUUID) {
    return `order:${window.crypto.randomUUID()}`;
  }
  return `order:${Date.now().toString(36)}:${Math.random().toString(36).slice(2, 12)}`;
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
  document.querySelectorAll("[data-order-sticky-hint]").forEach((hint) => {
    hint.textContent = validation.blocked
      ? validation.reason || "입력값을 확인해 주세요."
      : loggedIn
        ? "보유금액에서 차감 후 주문이 접수됩니다."
        : "로그인 후 주문과 내역 관리를 이어갑니다.";
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
  const logoImageUrl = surface === "light" ? darkLogoImageUrl || DEFAULT_LIGHT_BRAND_LOGO_URL : darkLogoImageUrl;
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
        <section class="empty-card empty-card--center empty-card--auth login-required-card">
          <span class="empty-card__eyebrow">로그인 필요</span>
          <strong>${escapeHtml(title)}</strong>
          <p>${escapeHtml(description)}</p>
          <div class="login-required-card__quick">
            <span>상품 탐색은 로그인 없이 가능합니다.</span>
            <span>충전·주문·내역 관리는 로그인 후 이어집니다.</span>
          </div>
          <div class="login-required-card__actions">
            <button class="full-width-cta" type="button" data-route="/auth">로그인 / 회원가입</button>
            <button class="ghost-secondary-button" type="button" data-route="/products">서비스 둘러보기</button>
          </div>
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

configureAdminSections({
  state,
  DEFAULT_SITE_NAME,
  advancedOrderFieldBlueprints,
  advancedOrderFieldKeys,
  analyticsTabBlueprints,
  analyticsRangeBlueprints,
  statusMap,
  escapeHtml,
  formatMoney,
  formatNumber,
  formatCompactNumber,
  formatPercent,
  adminSectionPath,
  analyticsRangeDays,
  analyticsWindow,
  analyticsDailySeries,
  getAdminSectionConfig,
  adminSectionItems,
  getAdminPopup,
  getAdminSiteSettings,
  getAdminHomeBanners,
  getAdminPlatformSections,
  getAdminAnalytics,
  getAdminNotices,
  getAdminFaqs,
  getAdminAuditLogs,
  getAdminSuppliers,
  getAdminProducts,
  getAdminCustomers,
  getAdminChargeOrders,
  getAdminCategories,
  getAdminPlatformGroups,
  getSelectedAdminSupplier,
  getSelectedAdminProduct,
  getSelectedAdminCustomer,
  getSelectedAdminHomeBanner,
  getSelectedAdminPlatformSection,
  getSelectedAdminCategory,
  getSelectedManageProduct,
  getSelectedAdminNotice,
  getSelectedAdminFaq,
  getSelectedAdminSupplierService,
  getAdminMkt24ProductSetting,
  getManageProducts,
  currentViewer,
  blankSiteSettingsDraft,
  blankPopupDraft,
  blankHomeBannerDraft,
  blankPlatformSectionDraft,
  blankSupplierDraft,
  blankCustomerDraft,
  blankCategoryDraft,
  blankProductDraft,
  blankNoticeDraft,
  blankFaqDraft,
  siteSettingsPreviewPayload,
  popupPreviewPayload,
  homeBannerToDraft,
  platformSectionToDraft,
  supplierToDraft,
  customerToDraft,
  categoryToDraft,
  productToDraft,
  noticeToDraft,
  faqToDraft,
  renderHomeBannerCard,
  renderPlatformLogoMarkup,
  renderSiteBrandLogoMarkup,
  brandMonogram,
  siteNameOrDefault,
  defaultHomeBannerImageUrl,
  resolveHomeBannerImageUrl,
  supplierApiKeyLabel,
  supplierApiKeyPlaceholder,
  supplierUrlPlaceholder,
  supplierConnectionGuide,
  formPresetLabel,
  formatAdvancedFieldLabel,
  renderAdvancedFieldBadges,
  renderSupplierRequestGuide,
  shouldShowHomePopup,
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
  renderContentAdminSection,
  renderSupplierAdminSection,
  renderCustomerAdminSection,
  renderCatalogAdminSection,
  renderCafe24AdminSection,
  renderAdminChargesSection,
  renderAdminOrdersSection,
  renderAdminOverviewSection,
});

configureCafe24AdminActions({
  state,
  apiGet,
  apiPost,
  refreshAdminData,
  renderRoute,
  showToast,
});

async function renderRoute() {
  const route = getRoute();
  syncShellMode(route);
  try {
    if (!state.bootstrap) {
      showLoading();
      return;
    }
    if (routeNeedsFullBootstrap(route) && state.bootstrapMode !== "full") {
      showLoading("필요한 정보를 불러오는 중...");
      await refreshCoreData({ shell: false });
    }
    if (route.name === "products" && !state.catalog.length) {
      showLoading("상품 목록을 불러오는 중...");
      await loadCatalog();
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
      const selectedCafe24SupplierId = state.ui.adminCafe24SelectedSupplierId || (state.adminBootstrap?.suppliers || [])[0]?.id || "";
      if (state.ui.adminActiveSection === "cafe24" && selectedCafe24SupplierId && !state.adminSupplierServices[selectedCafe24SupplierId]) {
        showLoading("Cafe24 매핑용 공급사 서비스를 불러오는 중...");
        await ensureAdminSupplierServices(selectedCafe24SupplierId);
        state.ui.adminCafe24SelectedSupplierId = selectedCafe24SupplierId;
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

    if (route.name === "admin") {
      consumeCafe24OAuthNotice();
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
    ensureBannerTimer();
    trackPublicRoute(route);
    if (route.name === "home" && !state.catalog.length) {
      loadCatalog().catch(() => {});
    }
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
    app.innerHTML = renderNotFound(readableApiErrorMessage(error?.message || error, "데이터를 불러오는 중 오류가 발생했습니다."));
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

  if (await handleCafe24AdminClick(closest)) {
    return;
  }

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
      showToast("현재 해당 간편 로그인은 사용할 수 없습니다. 이메일로 로그인해 주세요.", "error");
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
    const shouldClearSearch = routeButton.hasAttribute("data-clear-search");
    if (state.ui.loginModalOpen) {
      closeLoginModal({ preserveRedirect: Boolean(path && path.startsWith("/auth")) });
    }
    if (shouldClearSearch) {
      state.ui.search = "";
      state.ui.activePlatform = "";
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
    try {
      await ensureSelectedMkt24ProductSetting();
    } catch (error) {
      showToast(error.message || "MKT24 상품 상세를 불러오지 못했습니다.", "error");
    }
    renderRoute();
    return;
  }

  const refreshMkt24SettingButton = closest("[data-admin-mkt24-detail-refresh]");
  if (refreshMkt24SettingButton) {
    try {
      await ensureSelectedMkt24ProductSetting({ force: true });
      showToast("MKT24 상품 상세를 다시 불러왔습니다.");
    } catch (error) {
      showToast(error.message || "MKT24 상품 상세를 다시 불러오지 못했습니다.", "error");
    }
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

  const adminChargeFilterButton = closest("[data-admin-charge-filter]");
  if (adminChargeFilterButton) {
    state.ui.adminChargeFilter = adminChargeFilterButton.getAttribute("data-admin-charge-filter") || "all";
    renderRoute();
    return;
  }

  const adminContentTabButton = closest("[data-admin-content-tab]");
  if (adminContentTabButton) {
    state.ui.adminContentTab = adminContentTabButton.getAttribute("data-admin-content-tab") || "notices";
    renderRoute();
    return;
  }

  const newNoticeButton = closest("[data-admin-notice-new]");
  if (newNoticeButton) {
    state.ui.adminNoticeMode = "new";
    state.ui.adminSelectedNoticeId = "";
    state.adminNoticeDraft = blankNoticeDraft();
    renderRoute();
    return;
  }

  const selectNoticeButton = closest("[data-admin-notice-select]");
  if (selectNoticeButton) {
    const noticeId = selectNoticeButton.getAttribute("data-admin-notice-select") || "";
    state.ui.adminNoticeMode = "edit";
    state.ui.adminSelectedNoticeId = noticeId;
    state.adminNoticeDraft = noticeToDraft(getAdminNotices().find((notice) => notice.id === noticeId) || null);
    renderRoute();
    return;
  }

  const deleteNoticeButton = closest("[data-admin-notice-delete]");
  if (deleteNoticeButton) {
    const noticeId = deleteNoticeButton.getAttribute("data-admin-notice-delete") || "";
    try {
      await apiPost("/api/admin/notices/delete", { noticeId });
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("공지를 삭제했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "공지 삭제에 실패했습니다.", "error");
    }
    return;
  }

  const newFaqButton = closest("[data-admin-faq-new]");
  if (newFaqButton) {
    state.ui.adminFaqMode = "new";
    state.ui.adminSelectedFaqId = "";
    state.adminFaqDraft = blankFaqDraft();
    renderRoute();
    return;
  }

  const selectFaqButton = closest("[data-admin-faq-select]");
  if (selectFaqButton) {
    const faqId = selectFaqButton.getAttribute("data-admin-faq-select") || "";
    state.ui.adminFaqMode = "edit";
    state.ui.adminSelectedFaqId = faqId;
    state.adminFaqDraft = faqToDraft(getAdminFaqs().find((faq) => faq.id === faqId) || null);
    renderRoute();
    return;
  }

  const deleteFaqButton = closest("[data-admin-faq-delete]");
  if (deleteFaqButton) {
    const faqId = deleteFaqButton.getAttribute("data-admin-faq-delete") || "";
    try {
      await apiPost("/api/admin/faqs/delete", { faqId });
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("FAQ를 삭제했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "FAQ 삭제에 실패했습니다.", "error");
    }
    return;
  }

  const retrySupplierOrderButton = closest("[data-admin-order-retry-supplier]");
  if (retrySupplierOrderButton) {
    const orderId = retrySupplierOrderButton.getAttribute("data-admin-order-retry-supplier") || "";
    try {
      const result = await apiPost("/api/admin/orders/retry-supplier", { orderId });
      await refreshAdminData({ preserveDraft: true });
      showToast(`공급사 재전송 완료: ${result.dispatch?.status || "처리됨"}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "공급사 재전송에 실패했습니다.", "error");
    }
    return;
  }

  const refreshSupplierOrderButton = closest("[data-admin-order-refresh-supplier]");
  if (refreshSupplierOrderButton) {
    const orderId = refreshSupplierOrderButton.getAttribute("data-admin-order-refresh-supplier") || "";
    try {
      const result = await apiPost("/api/admin/orders/supplier-status", { orderId });
      await refreshAdminData({ preserveDraft: true });
      showToast(`공급사 상태 확인: ${result.supplierStatus || "확인됨"}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "공급사 상태 조회에 실패했습니다.", "error");
    }
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
      delete selection.orderIdempotencyKey;
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
      showToast("현재 선택할 수 없는 결제수단입니다. 다른 결제수단을 선택해 주세요.", "error");
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

  if (target.matches("[data-admin-charge-search]")) {
    const cursor = target.selectionStart || target.value.length;
    state.ui.adminChargeSearch = target.value;
    renderRoute().then(() => {
      const input = document.querySelector("[data-admin-charge-search]");
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

  if (target.matches("[data-admin-notice-field]")) {
    const field = target.getAttribute("data-admin-notice-field");
    if (!state.adminNoticeDraft) {
      state.adminNoticeDraft = blankNoticeDraft();
    }
    state.adminNoticeDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return;
  }

  if (target.matches("[data-admin-faq-field]")) {
    const field = target.getAttribute("data-admin-faq-field");
    if (!state.adminFaqDraft) {
      state.adminFaqDraft = blankFaqDraft();
    }
    state.adminFaqDraft[field] = field === "sortOrder" ? Number(target.value || 0) : target.value;
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
  if (await handleCafe24AdminChange(target)) {
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
    ensureSelectedMkt24ProductSetting()
      .catch((error) => showToast(error.message || "MKT24 상품 상세를 불러오지 못했습니다.", "error"))
      .finally(() => renderRoute());
    return;
  }
  if (target.matches("[data-admin-mkt24-setting-field]")) {
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
  if (await handleCafe24AdminSubmit(form, event)) {
    return;
  }

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
      showToast("현재 선택할 수 없는 결제수단입니다.", "error");
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
        showToast("결제창을 준비했습니다. 승인 후 보유금액이 반영됩니다.");
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

  if (form.matches("[data-admin-charge-action-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      await apiPost("/api/admin/charge-orders/action", {
        chargeOrderId: formData.get("chargeOrderId"),
        action: formData.get("action"),
        reference: formData.get("reference"),
        adminMemo: formData.get("adminMemo"),
      });
      await refreshAdminData({ preserveDraft: true });
      showToast("충전 주문 처리를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "충전 주문 처리에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-notice-form]")) {
    event.preventDefault();
    const draft = state.adminNoticeDraft || blankNoticeDraft();
    try {
      const result = await apiPost("/api/admin/notices", {
        id: draft.id,
        title: draft.title,
        body: draft.body,
        tag: draft.tag,
        pinned: draft.pinned,
        publishedAt: draft.publishedAt,
      });
      state.ui.adminContentTab = "notices";
      state.ui.adminNoticeMode = "edit";
      state.ui.adminSelectedNoticeId = result.notice.id;
      state.adminNoticeDraft = noticeToDraft(result.notice);
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("공지를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "공지 저장에 실패했습니다.", "error");
    }
    return;
  }

  if (form.matches("[data-admin-faq-form]")) {
    event.preventDefault();
    const draft = state.adminFaqDraft || blankFaqDraft();
    try {
      const result = await apiPost("/api/admin/faqs", {
        id: draft.id,
        question: draft.question,
        answer: draft.answer,
        sortOrder: draft.sortOrder,
      });
      state.ui.adminContentTab = "faqs";
      state.ui.adminFaqMode = "edit";
      state.ui.adminSelectedFaqId = result.faq.id;
      state.adminFaqDraft = faqToDraft(result.faq);
      await Promise.all([refreshCoreData(), refreshAdminData({ preserveDraft: false })]);
      showToast("FAQ를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "FAQ 저장에 실패했습니다.", "error");
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

  if (form.matches("[data-admin-mkt24-setting-form]")) {
    event.preventDefault();
    try {
      const payload = collectMkt24ProductSettingPayload(form);
      const result = await apiPost("/api/admin/mkt24-product-settings", payload);
      state.adminMkt24ProductSettings[mkt24ProductSettingKey(payload.supplierId, payload.productUuid)] = result.setting || {};
      showToast("MKT24 주문 옵션 설정을 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "MKT24 주문 옵션 설정 저장에 실패했습니다.", "error");
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
  const selection = ensureSelection(detail);
  if (!selection) return;
  const formData = new FormData(form);
  const fields = Object.fromEntries(formData.entries());
  selection.fields = { ...selection.fields, ...fields };
  if (!selection.orderIdempotencyKey) {
    selection.orderIdempotencyKey = createOrderIdempotencyKey();
  }
  const validation = getOrderValidationState(detail, summary.product);
  if (validation.blocked) {
    showToast(validation.reason || "주문 정보를 다시 확인해 주세요.", "error");
    return;
  }

  try {
    const result = await apiPost("/api/orders", {
      productId: summary.product.id,
      fields,
      idempotencyKey: selection.orderIdempotencyKey,
    });
    delete selection.orderIdempotencyKey;
    await refreshCoreData();
    showToast(`주문이 접수되었습니다. ${result.totalPriceLabel} 결제 완료`);
    navigate("/orders");
  } catch (error) {
    showToast(error.message || "주문 접수에 실패했습니다.", "error");
  }
});

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
    const route = getRoute();
    await refreshCoreData({ shell: routeCanUsePublicShell(route) });
    await renderRoute();
  } catch (error) {
    if (isTransientApiError(error) && !init._retried) {
      init._retried = true;
      showLoading("연결을 다시 확인하는 중...");
      try {
        await delay(1200);
        const route = getRoute();
        await refreshCoreData({ shell: routeCanUsePublicShell(route) });
        await renderRoute();
        return;
      } catch (retryError) {
        error = retryError;
      }
    }
    app.innerHTML = renderNotFound(readableApiErrorMessage(error?.message || error, "패널 초기화에 실패했습니다."));
  }
}

init();
