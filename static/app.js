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
import { configureAdminPages, renderAdminAuth, renderAdmin } from "./admin/pages.js";
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
import { configureCafe24AdminActions, cafe24OrderItemsQueryKey, refreshCafe24OrderItems } from "./admin/cafe24.js";
import { registerAdminEvents } from "./admin/events.js";
import { registerPublicEvents } from "./public/events.js";
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
    title: popup?.title || "서비스 안내를 확인해 주세요",
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
  const logoImageUrl = String(platform?.logoImageUrl || "").trim();
  if (logoImageUrl) {
    return `
      <span class="${className} is-image">
        <img src="${escapeHtml(logoImageUrl)}" alt="${escapeHtml(platform?.displayName || "")}" loading="lazy" />
      </span>
    `;
  }
  return `<span class="${className}">${escapeHtml(platform?.icon || "●")}</span>`;
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
  return integrationType === "mkt24" ? "API Key" : "API Key";
}

function supplierApiKeyPlaceholder(integrationType, hasId) {
  if (hasId) {
    return integrationType === "mkt24" ? "새 API Key 입력 시에만 변경됩니다." : "새 키 입력 시에만 변경됩니다.";
  }
  return integrationType === "mkt24" ? "공급사 API Key" : "공급사 API Key";
}

function supplierUrlPlaceholder(integrationType) {
  return integrationType === "mkt24" ? "https://api.mkt24.co.kr/v3/panel" : "https://example.com/api/v2";
}

function supplierConnectionGuide(integrationType) {
  if (integrationType === "mkt24") {
    return {
      status: "MKT24 대행사용 API는 /v3/panel 엔드포인트에 key + action 방식으로 연결합니다.",
      balance: "표준 SMM panel 방식의 services/add/status 응답을 기준으로 상태를 확인합니다.",
      dispatch: "API URL은 https://api.mkt24.co.kr/v3/panel, API Key는 공급사에서 발급받은 key 값을 사용하세요.",
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
  if ((data.cafe24Integrations || []).length) {
    await refreshCafe24OrderItems({ force: true });
  }
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

function showLoading(message = "인스타마트를 불러오는 중...") {
  app.innerHTML = `
    <div class="loading-screen">
      <div class="loading-card loading-card--brand">
        <div class="loading-logo-skeleton" aria-hidden="true">
          <img src="${escapeHtml(DEFAULT_LIGHT_BRAND_LOGO_URL)}" alt="" />
        </div>
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
  refreshCafe24OrderItems,
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
      if (state.ui.adminActiveSection === "cafe24") {
        const nextCafe24OrderListKey = cafe24OrderItemsQueryKey();
        if (!state.adminCafe24OrderList || state.adminCafe24OrderListKey !== nextCafe24OrderListKey) {
          showLoading("Cafe24 주문 1개월 목록을 불러오는 중...");
          await refreshCafe24OrderItems();
        }
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
    if (route.name === "home") {
      setHomeBannerIndex(state.ui.bannerIndex);
    }
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
            <i></i>
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

const eventContext = {
  adminSectionPath, apiPost, applyAdminSiteSettingsImage, applySupplierRecommendationToProductDraft, blankCategoryDraft,
  blankChargeDraft, blankCustomerDraft, blankFaqDraft, blankNoticeDraft, blankPopupDraft, blankProductDraft, blankSiteSettingsDraft,
  blankSupplierDraft, calculateSummary, categoryToDraft, chargeAmountSummary, chargeMethodConfig, clearPublicSessionState,
  closeChargeDetail, closeLoginModal, closePopupForSession, collectMkt24ProductSettingPayload, createOrderIdempotencyKey,
  currentSignupState, customerToDraft, dismissPopupToday, document, ensureAdminCustomerDetail, ensureAdminSupplierServices,
  ensureChargeDraft, ensureSelectedMkt24ProductSetting, ensureSelection, faqToDraft, formatMoney, getAdminCategories,
  getAdminFaqs, getAdminNotices, getAdminPlatformGroups, getAdminProducts, getAdminSuppliers, getOrderValidationState,
  getPreviewSource, getRoute, getSelectedAdminCustomer, getSelectedAdminHomeBanner, getSelectedAdminPlatformSection,
  getSelectedAdminProduct, getSelectedAdminSupplier, getSelectedAdminSupplierService, getSelectedManageProduct, getSelectedProduct,
  hideAnalyticsChartTooltip, homeBannerToDraft, isLoggedIn, mkt24ProductSettingKey, navigate, noticeToDraft, openChargeDetail,
  openLoginModal, parseCurrencyInput, platformSectionToDraft, popupToDraft, postAuthRedirectPath, productToDraft, readFileAsDataUrl,
  refreshAdminData, refreshCoreData, renderRoute, resetAdminState, resetSignupFlow, scheduleLinkPreview, setAdminAnalyticsExclusion,
  setHomeBannerIndex, showToast, siteSettingsToDraft, state, supplierToDraft, updateAdminHomeBannerPreview,
  updateAdminPlatformSectionPreview, updateAdminPopupPreview, updateAdminSiteSettingsPreview, updateAnalyticsChartTooltip,
  updateLiveSummary, updateSignupPasswordFeedback,
};
registerAdminEvents(eventContext);
registerPublicEvents(eventContext);

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
