const app = document.querySelector("#app");
const toast = document.querySelector("#toast");

const state = {
  bootstrap: null,
  publicCsrfToken: "",
  catalog: [],
  categoryCache: {},
  orders: [],
  orderCounts: { all: 0, queued: 0, in_progress: 0, completed: 0 },
  transactions: [],
  adminBootstrap: null,
  adminSession: null,
  adminCsrfToken: "",
  adminSupplierServices: {},
  adminCustomerDetails: {},
  adminSiteSettingsDraft: null,
  adminPopupDraft: null,
  adminHomeBannerDraft: null,
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
    bannerIndex: 0,
    loginModalOpen: false,
    loginRedirect: "",
    adminActiveSection: "overview",
    adminAnalyticsTab: "dashboard",
    adminAnalyticsRange: "30d",
    adminCustomerFilter: "all",
    adminCustomerSearch: "",
    adminSupplierMode: "edit",
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

function readRuntimeMeta(name) {
  return document.querySelector(`meta[name="${name}"]`)?.getAttribute("content") || "";
}

function sanitizeApiBaseUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw);
    if (!/^https?:$/.test(parsed.protocol)) return "";
    return parsed.href.replace(/\/+$/, "");
  } catch (_) {
    return "";
  }
}

const runtimeConfig = Object.freeze({
  apiBaseUrl: sanitizeApiBaseUrl(readRuntimeMeta("smm-api-base-url") || window.__SMM_CONFIG__?.apiBaseUrl || ""),
});

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

function siteSettingsToDraft(siteSettings) {
  if (!siteSettings) return blankSiteSettingsDraft();
  const faviconUrl = siteSettings.faviconUrl || "";
  const shareImageUrl = siteSettings.shareImageUrl || "";
  return {
    siteName: siteSettings.siteName || "",
    siteDescription: siteSettings.siteDescription || "",
    useMailSmsSiteName: Boolean(siteSettings.useMailSmsSiteName),
    mailSmsSiteName: siteSettings.mailSmsSiteName || "",
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
  const isAdmin = route.name === "admin";
  if (deviceShell) {
    deviceShell.classList.toggle("is-admin", isAdmin);
  }
  document.body.classList.toggle("is-admin-route", isAdmin);
  applySitePresentation(route);
}

function applySitePresentation(route) {
  const isAdmin = route.name === "admin";
  const siteSettings = state.adminBootstrap?.siteSettings || state.bootstrap?.siteSettings || {};
  const siteName = String(siteSettings.siteName || "Pulse24").trim() || "Pulse24";
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
  if (["/api/orders", "/api/charge", "/api/logout"].includes(path) && state.publicCsrfToken) {
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
  const pathname = window.location.pathname.replace(/\/+$/, "") || "/";
  if (pathname === "/") return { name: "home" };
  if (pathname === "/admin") return { name: "admin", section: "overview" };
  if (pathname.startsWith("/admin/")) {
    const sectionId = decodeURIComponent(pathname.split("/")[2] || "");
    return { name: "admin", section: normalizeAdminSectionId(sectionId) };
  }
  if (pathname === "/products") return { name: "products" };
  if (pathname.startsWith("/products/")) return { name: "detail", id: decodeURIComponent(pathname.split("/")[2]) };
  if (pathname === "/charge") return { name: "charge" };
  if (pathname === "/orders") return { name: "orders" };
  if (pathname === "/my") return { name: "my" };
  return { name: "home" };
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
    const [ordersData, transactionData] = await Promise.all([apiGet("/api/orders"), apiGet("/api/transactions")]);
    state.orders = ordersData.orders;
    state.orderCounts = ordersData.counts;
    state.transactions = transactionData.transactions;
  } else {
    state.orders = [];
    state.orderCounts = { all: 0, queued: 0, in_progress: 0, completed: 0 };
    state.transactions = [];
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
  const note = document.querySelector("[data-order-validation-note]");
  if (note) {
    note.textContent = validation.reason || "";
    note.hidden = !validation.reason;
    note.classList.toggle("is-blocked", validation.blocked);
    note.classList.toggle("is-ready", !validation.blocked && Boolean(validation.reason));
  }
  document.querySelectorAll("[data-order-submit-button]").forEach((button) => {
    button.disabled = Boolean(validation.blocked);
    button.textContent = validation.blocked ? "주문 불가" : "주문하기";
  });
}

function renderBottomNav(activeKey) {
  return `
    <nav class="bottom-nav">
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

function renderFrame(content, activeKey, extraSticky = "") {
  return `
    <div class="phone-frame">
      ${content}
      ${extraSticky}
      ${renderBottomNav(activeKey)}
      ${renderPublicLoginModal()}
    </div>
  `;
}

function renderPublicLoginModal() {
  if (!state.ui.loginModalOpen || isLoggedIn()) return "";
  return `
    <div class="auth-modal-layer">
      <button class="auth-modal-layer__backdrop" type="button" aria-label="로그인 닫기" data-public-login-close></button>
      <div class="auth-modal">
        <div class="auth-modal__head">
          <span class="auth-modal__eyebrow">Member Login</span>
          <strong>로그인 후 주문을 이어갈 수 있어요</strong>
          <p>주문 내역, 캐시 충전, 상품 구매는 로그인된 고객 계정에서만 이용할 수 있습니다.</p>
        </div>
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
        <button class="auth-modal__close" type="button" data-public-login-close>닫기</button>
      </div>
    </div>
  `;
}

function renderAdminFrame(content) {
  return `
    <div class="admin-frame">
      ${content}
    </div>
  `;
}

function renderAdminTopbar(title, description, metrics = []) {
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

function renderAdminWorkspaceNav(stats = {}, popup = null) {
  const sections = adminSectionItems(stats, popup);
  return `
    <div class="admin-rail-card">
      <div class="admin-rail-card__top">
        <span class="admin-rail-card__eyebrow">Desktop Console</span>
        <strong>운영 섹션</strong>
        <p>관리 항목이 더 많아져도 좌측 탐색에서 빠르게 이동할 수 있도록 PC 중심 구조로 정리했습니다.</p>
      </div>
      <div class="admin-section-nav">
        ${sections
          .map(
            (section) => `
              <button
                class="admin-section-nav__button ${state.ui.adminActiveSection === section.id ? "is-active" : ""}"
                type="button"
                data-admin-scroll-section="${section.id}"
              >
                <span>${escapeHtml(section.label)}</span>
                <strong>${escapeHtml(section.stat || "")}</strong>
                <small>${escapeHtml(section.description)}</small>
              </button>
            `
          )
          .join("")}
      </div>
      <div class="admin-rail-card__foot">
        <span class="admin-badge is-neutral">PC 최적화</span>
        <span class="admin-badge is-neutral">Bot 차단</span>
      </div>
    </div>
  `;
}

function renderAdminAuthRail(session = {}) {
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
    clearButton.disabled = !draft.imageUrl;
  }
}

function renderSiteSettingsPreviewMarkup(siteSettings) {
  const preview = siteSettingsPreviewPayload(siteSettings);
  const origin = window.location.origin || "https://your-site.example";
  return `
    <div class="admin-site-preview-stack">
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
  const faviconMeta = document.querySelector("[data-admin-site-settings-favicon-meta]");
  const shareMeta = document.querySelector("[data-admin-site-settings-share-meta]");
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
  if (faviconMeta) {
    faviconMeta.textContent = draft.faviconName || (draft.faviconUrl ? "저장된 파비콘 연결됨" : "파비콘 없음");
  }
  if (shareMeta) {
    shareMeta.textContent = draft.shareImageName || (draft.shareImageUrl ? "저장된 대표 이미지 연결됨" : "대표 이미지 없음");
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
                <p>파비콘과 공유 대표 이미지는 저장 즉시 헤드 메타와 미리보기에 반영됩니다.</p>
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

function renderHomeBannerAdminSection() {
  const banners = getAdminHomeBanners();
  const draft = state.adminHomeBannerDraft || homeBannerToDraft(banners[0]);
  const imageMeta = draft.imageName || (draft.imageUrl ? "저장된 배너 이미지 연결됨" : "이미지 없음");

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
            <strong>배너 편집</strong>
          </div>
          <form class="admin-form" data-admin-home-banner-form>
            <label class="form-field">
              <span class="field-label">배너 제목</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="title" value="${escapeHtml(draft.title)}" data-admin-home-banner-field="title" />
              </div>
            </label>
            <label class="form-field">
              <span class="field-label">배너 설명</span>
              <textarea class="field-textarea" name="subtitle" rows="3" data-admin-home-banner-field="subtitle">${escapeHtml(draft.subtitle)}</textarea>
            </label>
            <div class="admin-popup-upload">
              <div class="admin-popup-upload__head">
                <div>
                  <strong>배너 이미지</strong>
                  <p>권장 사이즈: 1600 x 720px 이상, JPG/PNG/WebP, 5MB 이하. 중요한 텍스트는 좌측 또는 중앙에 두는 것을 권장합니다.</p>
                </div>
                <span class="admin-badge is-neutral">${escapeHtml(imageMeta)}</span>
              </div>
              <div class="admin-popup-upload__controls">
                <label class="admin-secondary-button admin-secondary-button--file" for="admin-home-banner-image-upload">이미지 업로드</label>
                <input class="admin-popup-upload__input" id="admin-home-banner-image-upload" type="file" accept="image/png,image/jpeg,image/webp" data-admin-home-banner-image-upload />
                <button class="admin-secondary-button" type="button" data-admin-home-banner-image-clear ${draft.imageUrl ? "" : "disabled"}>이미지 제거</button>
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
              <label class="form-field">
                <span class="field-label">버튼 문구</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="ctaLabel" value="${escapeHtml(draft.ctaLabel)}" data-admin-home-banner-field="ctaLabel" />
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
              <label class="form-field">
                <span class="field-label">테마</span>
                <div class="field-shell">
                  <select class="field-select" name="theme" data-admin-home-banner-field="theme">
                    ${[
                      ["blue", "Blue"],
                      ["mint", "Mint"],
                      ["dark", "Dark"],
                    ]
                      .map(([value, label]) => `<option value="${value}" ${draft.theme === value ? "selected" : ""}>${label}</option>`)
                      .join("")}
                  </select>
                </div>
              </label>
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
    const haystack = [
      customer.name,
      customer.emailMasked,
      customer.phoneMasked,
      customer.tier,
      customer.role,
      customer.notes,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>고객/계정 관리</h2>
        <p>고객 계정을 생성하고 등급, 역할, 활성 상태, 잔액을 관리할 수 있습니다.</p>
      </div>

      <div class="admin-management-layout">
        <div class="admin-card admin-subcard">
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
                placeholder="이름, 등급, 역할, 메모 검색"
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
                    class="admin-supplier-card ${state.ui.adminSelectedCustomerId === customer.id && state.ui.adminCustomerMode !== "new" ? "is-active" : ""}"
                    type="button"
                    data-admin-select-customer="${customer.id}"
                  >
                    <div class="admin-supplier-card__top">
                      <strong>${escapeHtml(customer.name)}</strong>
                      <span class="admin-badge ${customer.isActive ? "is-success" : "is-neutral"}">${customer.isActive ? "활성" : "비활성"}</span>
                    </div>
                    <p>${escapeHtml(customer.emailMasked || "이메일 비공개")}</p>
                    <div class="admin-supplier-card__meta">
                      <span>${escapeHtml(customer.role)}</span>
                      <span>${escapeHtml(customer.tier)}</span>
                      <span>주문 ${escapeHtml(String(customer.orderCount || 0))}</span>
                      <span>잔액 ${escapeHtml(customer.balanceLabel)}</span>
                    </div>
                    <div class="admin-supplier-card__meta">
                      <span>${customer.hasPassword ? "로그인 가능" : "비밀번호 없음"}</span>
                      <span>${escapeHtml(customer.phoneMasked || "연락처 비공개")}</span>
                      <span>누적 ${escapeHtml(customer.totalSpentLabel || "0원")}</span>
                      <span>${escapeHtml(customer.lastOrderLabel || "주문 이력 없음")}</span>
                    </div>
                  </button>
                `
              )
                  .join("")
              : `<div class="admin-empty-card"><strong>조건에 맞는 고객이 없습니다.</strong><p>필터나 검색어를 바꿔 다시 확인해 주세요.</p></div>`}
          </div>
        </div>

        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>${draft.id ? "계정 수정" : "새 계정 생성"}</strong>
          </div>
          <form class="admin-form" data-admin-customer-form>
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

          ${
            selectedCustomer
              ? `
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
              : ""
          }
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

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>상품 관리</h2>
        <p>카테고리 생성/편집과 상품 생성/편집/삭제를 통해 사용자 패널 노출 상품을 직접 관리할 수 있습니다.</p>
      </div>

      <div class="admin-management-layout">
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

        <div class="admin-card admin-subcard">
          <div class="admin-subcard__head">
            <strong>${categoryDraft.id ? "카테고리 수정" : "카테고리 생성"}</strong>
          </div>
          <form class="admin-form" data-admin-category-form>
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
            </div>
            <div class="admin-two-column">
              <label class="form-field">
                <span class="field-label">상품 코드</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="productCode" value="${escapeHtml(productDraft.productCode)}" data-admin-product-field="productCode" />
                </div>
              </label>
              <label class="form-field">
                <span class="field-label">배지</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="badge" value="${escapeHtml(productDraft.badge)}" data-admin-product-field="badge" />
                </div>
              </label>
            </div>
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
            <label class="form-field">
              <span class="field-label">정렬 순서</span>
              <div class="field-shell">
                <input class="field-input" type="number" name="sortOrder" value="${escapeHtml(String(productDraft.sortOrder || 0))}" data-admin-product-field="sortOrder" />
              </div>
            </label>
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
    const haystack = [
      order.orderNumber,
      order.customerName,
      order.customerEmailMasked,
      order.productName,
      order.optionName,
      order.targetValue,
      order.supplierName,
      order.supplierStatus,
      order.notes?.adminMemo || "",
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>주문 운영</h2>
        <p>최근 주문을 확인하고 상태를 수동으로 업데이트할 수 있습니다.</p>
      </div>

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
            return `
              <article class="admin-order-card">
                <div class="admin-order-card__top">
                  <div>
                    <span class="order-card__platform">${escapeHtml(order.platformIcon)} ${escapeHtml(order.platformName)}</span>
                    <strong>${escapeHtml(order.productName)}</strong>
                    <p>${escapeHtml(order.customerName)} · ${escapeHtml(order.customerEmailMasked || "비공개")}</p>
                  </div>
                  <span class="status-pill ${status.className}">${escapeHtml(status.label)}</span>
                </div>
                <div class="admin-order-card__meta">
                  <span>${escapeHtml(order.orderNumber)}</span>
                  <span>${escapeHtml(order.totalPriceLabel)}</span>
                  <span>${escapeHtml(order.createdLabel)}</span>
                  ${order.supplierName ? `<span>${escapeHtml(order.supplierName)} / ${escapeHtml(order.supplierStatus || "미전송")}</span>` : ""}
                </div>
                <p class="order-card__target">${escapeHtml(order.targetValue || "입력값 없음")}</p>
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

function renderAdminAuth() {
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
  const sections = adminSectionItems(stats, popup);
  const username = state.adminSession?.username || "admin";
  const siteName = getAdminSiteSettings()?.siteName || state.bootstrap?.siteSettings?.siteName || "Pulse24";

  return `
    <header class="admin-erp-header">
      <div class="admin-erp-brand">
        <div class="admin-erp-brand__mark">P</div>
        <div class="admin-erp-brand__text">
          <strong>${escapeHtml(siteName)} ERP</strong>
          <span>Operations Console</span>
        </div>
      </div>

      <nav class="admin-erp-tabs">
        ${sections
          .map(
            (section) => `
              <button
                class="admin-erp-tab ${state.ui.adminActiveSection === section.id ? "is-active" : ""}"
                type="button"
                data-admin-scroll-section="${section.id}"
              >
                <span>${escapeHtml(section.label)}</span>
                <small>${escapeHtml(section.stat || "")}</small>
              </button>
            `
          )
          .join("")}
      </nav>

      <div class="admin-erp-header__right">
        <div class="admin-erp-user">
          <span class="admin-erp-user__avatar">${escapeHtml(username.slice(0, 1).toUpperCase())}</span>
          <div>
            <strong>${escapeHtml(username)}</strong>
            <span>관리자 세션 진행 중</span>
          </div>
        </div>
        <button class="admin-erp-utility" type="button" data-route="/">사용자 패널</button>
        <button class="admin-erp-utility" type="button" data-admin-refresh>새로고침</button>
        <button class="admin-erp-utility is-primary" type="button" data-admin-logout>로그아웃</button>
      </div>
    </header>
  `;
}

function renderAdminErpIconRail(stats = {}, popup = null) {
  const sections = adminSectionItems(stats, popup);
  return `
    <aside class="admin-erp-iconbar">
      <div class="admin-erp-iconbar__menu">
        ${sections
          .map(
            (section) => `
              <button
                class="admin-erp-iconbutton ${state.ui.adminActiveSection === section.id ? "is-active" : ""}"
                type="button"
                data-admin-scroll-section="${section.id}"
                title="${escapeHtml(section.label)}"
              >
                <span>${escapeHtml(section.icon || "•")}</span>
              </button>
            `
          )
          .join("")}
      </div>
      <div class="admin-erp-iconbar__footer">
        <button class="admin-erp-iconbutton" type="button" data-route="/" title="사용자 패널">
          <span>⌂</span>
        </button>
      </div>
    </aside>
  `;
}

function renderAdminErpSidebar(stats = {}, popup = null) {
  const sections = adminSectionItems(stats, popup);
  const activeSection = getAdminSectionConfig();
  const siteSettings = getAdminSiteSettings() || state.bootstrap?.siteSettings || null;
  const controlItems = [
    { label: "봇 차단", value: "활성", description: "/admin, /api/admin 색인 차단" },
    { label: "사이트명", value: siteSettings?.siteName || "미설정", description: "기본 설정에서 브랜딩과 메타를 관리" },
    { label: "공급사 수", value: `${Number(stats.supplierCount || 0)}개`, description: "API 연동 공급사 등록 현황" },
    { label: "팝업 상태", value: popup?.isActive ? "노출중" : "비노출", description: popup?.route || "이동 경로 미설정" },
  ];

  return `
    <aside class="admin-erp-sidebar">
      <section class="admin-erp-sidebar__section">
        <span class="admin-erp-sidebar__eyebrow">Current Module</span>
        <strong class="admin-erp-sidebar__title">${escapeHtml(activeSection.title)}</strong>
        <p class="admin-erp-sidebar__copy">${escapeHtml(activeSection.summary)}</p>
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
        <span class="admin-erp-sidebar__eyebrow">Control Board</span>
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
  const savedSecretSummary = integrationType === "mkt24"
    ? `x-api-key ${draft.hasApiKey ? draft.apiKeyMasked || "설정됨" : "미설정"} · Bearer ${draft.hasBearerToken ? draft.bearerTokenMasked || "설정됨" : "미설정"}`
    : draft.hasApiKey
      ? draft.apiKeyMasked || "설정됨"
      : "미설정";
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
          <div class="section-head section-head--compact">
            <h2>API 연결 상태</h2>
            <p>${escapeHtml(integrationGuide.status)}</p>
          </div>

          <div class="admin-connection-grid">
            <article class="admin-connection-card">
              <span>연결 상태</span>
              <strong>${activeConnection ? renderAdminHealthBadge(activeConnection.status || activeConnection.lastTestStatus) : renderAdminHealthBadge("never")}</strong>
              <p>${escapeHtml(activeConnection?.message || activeConnection?.lastTestMessage || "아직 연결 확인을 진행하지 않았습니다.")}</p>
            </article>
            <article class="admin-connection-card">
              <span>확인된 URL</span>
              <strong>${escapeHtml(activeConnection?.resolvedApiUrl || selectedSupplier?.apiUrl || draft.apiUrl || "-")}</strong>
              <p>${escapeHtml(activeConnection?.checkedAt || selectedSupplier?.lastCheckedAt || "최근 확인 기록이 없습니다.")}</p>
            </article>
            <article class="admin-connection-card">
              <span>잔액</span>
              <strong>${escapeHtml(activeConnection?.balance ? `${activeConnection.balance} ${activeConnection.currency || ""}`.trim() : selectedSupplier?.lastBalance ? `${selectedSupplier.lastBalance} ${selectedSupplier.lastCurrency || ""}`.trim() : "-")}</strong>
              <p>${escapeHtml(integrationGuide.balance)}</p>
            </article>
            <article class="admin-connection-card">
              <span>서비스 수</span>
              <strong>${escapeHtml(String(activeConnection?.serviceCount || selectedSupplier?.lastServiceCount || selectedSupplier?.serviceCount || 0))}</strong>
              <p>서비스 동기화 전에도 연결 테스트 단계에서 개수를 확인합니다.</p>
            </article>
          </div>

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
              ${escapeHtml(selectedService ? `선택됨: ${selectedService.name} (#${selectedService.externalServiceId})` : "서비스를 선택하면 우측 매핑 폼에 반영됩니다.")} ·
              전체 ${escapeHtml(String(allServices.length))}개 / 표시 ${escapeHtml(String(filteredServices.length))}개
            </div>
          </div>

          ${
            filteredServices.length
              ? `
                <label class="form-field">
                  <span class="field-label">동기화된 서비스 선택</span>
                  <div class="field-shell field-shell--selectbox">
                    <select class="field-select admin-service-selectbox" size="14" data-admin-service-select-box>
                      ${filteredServices
                        .map(
                          (service) => `
                            <option value="${escapeHtml(service.id)}" ${state.ui.adminSelectedSupplierServiceId === service.id ? "selected" : ""}>
                              ${escapeHtml(`${service.category || "분류 없음"} | ${service.name} (#${service.externalServiceId}) | ${service.minAmount}~${service.maxAmount}`)}
                            </option>
                          `
                        )
                        .join("")}
                    </select>
                  </div>
                </label>
                ${
                  selectedService
                    ? `
                      <div class="admin-mini-card">
                        <span>선택 서비스 상세</span>
                        <strong>${escapeHtml(selectedService.name)} (#${escapeHtml(selectedService.externalServiceId)})</strong>
                        <p>${escapeHtml(selectedService.category || "분류 없음")} · Rate ${escapeHtml(selectedService.rateLabel)} · ${escapeHtml(String(selectedService.minAmount || 0))} ~ ${escapeHtml(String(selectedService.maxAmount || 0))} · ${selectedService.refill ? "리필 가능" : "리필 없음"}</p>
                      </div>
                      ${renderSupplierRequestGuide(selectedService, { applyLabel: selectedProduct ? "선택한 상품 제작 폼에 추천 적용" : "새 상품 제작 폼에 추천 적용" })}
                    `
                    : ""
                }
              `
              : `<div class="admin-empty-card"><strong>표시할 서비스가 없습니다.</strong><p>공급사를 저장하고 서비스 동기화를 먼저 실행하거나 검색어를 조정해 주세요.</p></div>`
          }
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

function renderAdminActiveSection(sectionId, context) {
  if (sectionId === "analytics") return renderAnalyticsAdminSection();
  if (sectionId === "settings") return renderSiteSettingsAdminSection();
  if (sectionId === "popup") return renderPopupAdminSection();
  if (sectionId === "suppliers") return renderSupplierAdminSection(context);
  if (sectionId === "customers") return renderCustomerAdminSection();
  if (sectionId === "catalog") return renderCatalogAdminSection();
  if (sectionId === "orders") return renderAdminOrdersSection();
  return renderAdminOverviewSection(context.stats, context.popup);
}

function renderAdmin() {
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
  const filteredServices = allServices
    .filter((service) => {
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
        ${renderAdminErpIconRail(stats, popup)}
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

function renderHomeBannerCard(banner, { compact = false, index = 0, total = 1, interactive = true } = {}) {
  const hasImage = Boolean(banner?.imageUrl);
  const title = banner?.title || "프로모션 배너";
  const subtitle = banner?.subtitle || "";
  const ctaLabel = banner?.ctaLabel || "바로 보기";
  const route = banner?.route || "/";
  const theme = banner?.theme || "blue";
  const counter = total > 1 && !compact ? `${index + 1} / ${total}` : "";
  const tag = interactive ? "button" : "div";
  const routeAttr = interactive ? ` type="button" data-route="${escapeHtml(route)}"` : "";
  return `
    <${tag} class="home-banner-card home-banner-card--${compact ? "compact" : "feature"} home-banner-card--${escapeHtml(theme)} ${hasImage ? "has-image" : ""}"${routeAttr}>
      ${
        hasImage
          ? `
            <span class="home-banner-card__media">
              <img src="${escapeHtml(banner.imageUrl)}" alt="${escapeHtml(title)}" loading="lazy" />
            </span>
            <span class="home-banner-card__overlay"></span>
          `
          : ""
      }
      <span class="home-banner-card__copy">
        ${compact ? "" : `<span class="home-banner-card__eyebrow">PROMOTION</span>`}
        <strong>${escapeHtml(title)}</strong>
        ${subtitle ? `<em>${escapeHtml(subtitle)}</em>` : ""}
      </span>
      <span class="home-banner-card__meta">
        ${counter ? `<span class="home-banner-card__counter">${escapeHtml(counter)}</span>` : ""}
        <span class="home-banner-card__cta">${escapeHtml(ctaLabel)}</span>
      </span>
    </${tag}>
  `;
}

function renderHome() {
  const data = state.bootstrap;
  if (!data) return "";
  const authenticated = isLoggedIn();
  const user = data.user;
  const siteDescription =
    data.siteSettings?.siteDescription ||
    "원하는 플랫폼과 상품을 빠르게 찾고 주문까지 이어지는 SMM 주문 패널입니다.";
  const activeBanners = (data.banners || []).filter((banner) => banner.isActive !== false);
  const safeBannerIndex = activeBanners.length ? state.ui.bannerIndex % activeBanners.length : 0;
  if (safeBannerIndex !== state.ui.bannerIndex) {
    state.ui.bannerIndex = safeBannerIndex;
  }
  const topBanner = activeBanners[0] || null;
  const quickLinks = data.topLinks?.length ? data.topLinks : [{ label: "서비스 소개서", route: "/products" }, { label: "이용 가이드", route: "/my" }];
  const counterValueA = authenticated ? formatCompactNumber(user?.balance || 0) : "0";
  const counterValueB = authenticated ? formatNumber(state.orderCounts.all || 0) : "0";

  return renderFrame(
    `
      <div class="page page-home page-home--renewed">
        <section class="home-hero">
          <div class="home-hero__header">
            <div class="home-hero__brandmark" aria-label="${escapeHtml(data.app.name)}">${escapeHtml(user?.avatarLabel || "P24")}</div>
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
              <button class="home-hero__chat" type="button" data-route="/products/cat_custom_request" aria-label="상담 연결">●</button>
            </div>
          </div>

          <div class="home-hero__body">
            <button
              class="home-login-card ${authenticated ? "is-authenticated" : ""}"
              type="button"
              ${authenticated ? 'data-route="/my"' : "data-public-login-open"}
            >
              <div class="home-login-card__copy">
                <strong>${escapeHtml(authenticated ? `${user.name}님, 바로 주문할까요?` : "로그인이 필요해요")}</strong>
                <span>${escapeHtml(authenticated ? `보유 캐시 ${user.balanceLabel} · 주문 ${formatNumber(state.orderCounts.all || 0)}건` : siteDescription)}</span>
              </div>
              <span class="home-login-card__arrow">›</span>
            </button>
            <div class="home-hero__counters">
              <div class="home-hero__counter">
                <strong>${escapeHtml(counterValueA)}</strong>
                <span>M</span>
              </div>
              <div class="home-hero__counter">
                <strong>${escapeHtml(counterValueB)}</strong>
                <span>P</span>
              </div>
            </div>
          </div>
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

        <section class="content-section content-section--tight">
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
        </section>

        <section class="content-section content-section--tight">
          <div class="home-platform-grid">
            ${data.platforms
              .map(
                (platform) => `
                  <button
                    class="home-platform-card"
                    type="button"
                    data-route="/products"
                    data-platform-id="${platform.id}"
                  >
                    <span class="home-platform-card__icon" style="--platform-accent:${escapeHtml(platform.accentColor)}">${escapeHtml(platform.icon)}</span>
                    <strong>${escapeHtml(platform.displayName)}</strong>
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        ${
          activeBanners.length
            ? `
              <section class="content-section">
                <div class="banner-carousel banner-carousel--media">
                  <div class="banner-track" style="transform: translateX(-${safeBannerIndex * 100}%);">
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

        <section class="content-section home-section-grid">
          <div class="home-section-grid__main">
            <div class="section-head">
              <h2>추천 서비스</h2>
              <p>자주 찾는 서비스만 짧고 또렷하게 정리했습니다.</p>
            </div>
            <div class="spotlight-list">
              ${data.featuredServices
                .map(
                  (item) => `
                    <button class="spotlight-card" type="button" data-route="${item.route}">
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
          </div>

          <div class="home-section-grid__side">
            <div class="section-head">
              <h2>빠른 안내</h2>
              <p>상담, 공지, FAQ를 홈에서 바로 확인할 수 있습니다.</p>
            </div>
            <div class="support-grid support-grid--compact">
              ${data.supportLinks
                .map(
                  (item) => `
                    <button class="support-card" type="button" data-route="${item.route}">
                      <span class="support-card__icon">${escapeHtml(item.icon)}</span>
                      <strong>${escapeHtml(item.title)}</strong>
                      <p>${escapeHtml(item.subtitle)}</p>
                    </button>
                  `
                )
                .join("")}
            </div>
          </div>
        </section>

        <section class="content-section footer-section">
          <div class="footer-meta">
            <p><strong>${escapeHtml(data.company.name)}</strong></p>
            <p>대표: ${escapeHtml(data.company.representative)}</p>
            <p>문의: ${escapeHtml(data.company.contact)}</p>
            <p>운영시간: ${escapeHtml(data.company.hours)}</p>
          </div>
        </section>
      </div>
    `,
    "home",
    renderHomePopupOverlay()
  );
}

function renderProducts() {
  const platforms = filteredCatalog();
  const activePlatform = getCurrentPlatform(platforms);

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

        <div class="catalog-layout">
          <aside class="platform-rail">
            ${platforms
              .map(
                (platform) => `
                  <button
                    class="platform-rail__item ${activePlatform && platform.id === activePlatform.id ? "is-active" : ""}"
                    type="button"
                    data-platform-select="${platform.id}"
                  >
                    <span>${escapeHtml(platform.icon)}</span>
                    <strong>${escapeHtml(platform.displayName)}</strong>
                  </button>
                `
              )
              .join("")}
          </aside>

          <section class="catalog-main">
            ${
              activePlatform
                ? `
                  <div class="catalog-hero">
                    <span class="catalog-hero__eyebrow">${escapeHtml(activePlatform.displayName)}</span>
                    <h2>${escapeHtml(activePlatform.description)}</h2>
                  </div>
                  ${activePlatform.groups
                    .map(
                      (group) => `
                        <section class="catalog-group">
                          <div class="section-head section-head--compact">
                            <h3>${escapeHtml(group.name)}</h3>
                            <p>${escapeHtml(group.description)}</p>
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
                    <strong>검색 결과가 없습니다.</strong>
                    <p>다른 키워드로 다시 검색해 주세요.</p>
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

function renderLoginRequiredPage(title, description, activeKey = "home") {
  return renderFrame(
    `
      <div class="page page-login-required">
        <section class="empty-card empty-card--center empty-card--auth">
          <span class="empty-card__eyebrow">로그인 필요</span>
          <strong>${escapeHtml(title)}</strong>
          <p>${escapeHtml(description)}</p>
          <button class="full-width-cta" type="button" data-public-login-open>로그인하기</button>
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

function renderDetail(detail) {
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
        </section>

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
          <div class="section-head section-head--compact">
            <h2>주문 폼</h2>
            <p>${escapeHtml(detail.description)}</p>
          </div>
          <form class="detail-form-card" id="order-form" data-order-form="${detail.id}">
            <div class="detail-form-layout ${previewSource ? "has-preview" : ""}">
              <div class="detail-form-layout__fields">
                ${Object.entries(template)
                  .filter(([key]) => key !== "requestMemo")
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
                  ${escapeHtml(orderValidation.reason || "")}
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

function renderCharge() {
  const user = state.bootstrap?.user;
  const quickAmounts = [30000, 50000, 100000, 300000];

  return renderFrame(
    `
      <div class="page page-charge">
        <header class="topbar">
          <button class="icon-button" type="button" data-route="/">‹</button>
          <strong class="topbar-title">캐시 충전</strong>
          <button class="icon-button" type="button" data-route="/orders">◎</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="wallet-board">
          <p class="wallet-board__eyebrow">${escapeHtml(user?.name || "데모 사용자")}</p>
          <strong>${escapeHtml(user?.balanceLabel || "0원")}</strong>
          <span>상품 주문 시 자동 차감되는 데모 캐시입니다.</span>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>빠른 충전</h2>
            <p>충전 버튼을 누르면 즉시 데모 잔액에 반영됩니다.</p>
          </div>
          <div class="charge-grid">
            ${quickAmounts
              .map(
                (amount) => `
                  <button class="charge-chip" type="button" data-charge-amount="${amount}">
                    ${formatMoney(amount)}
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>거래 내역</h2>
            <p>주문 차감과 캐시 충전 내역을 한 화면에서 확인할 수 있어요.</p>
          </div>
          <div class="transaction-list">
            ${state.transactions
              .map(
                (tx) => `
                  <article class="transaction-card">
                    <div>
                      <strong>${escapeHtml(tx.memo)}</strong>
                      <p>${escapeHtml(tx.createdLabel)}</p>
                    </div>
                    <div class="transaction-card__amount ${tx.amount > 0 ? "is-positive" : "is-negative"}">
                      <strong>${escapeHtml(tx.amountLabel)}</strong>
                      <span>잔액 ${escapeHtml(tx.balanceAfterLabel)}</span>
                    </div>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      </div>
    `,
    "charge"
  );
}

function renderOrders() {
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
            ${visibleOrders
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
                        ? `<div class="order-card__note">메모: ${escapeHtml(order.notes.memo)}</div>`
                        : ""
                    }
                  </article>
                `;
              })
              .join("")}
          </div>
        </section>
      </div>
    `,
    "orders"
  );
}

function renderMy() {
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
          <div class="section-head">
            <h2>도움말 바로가기</h2>
            <p>레퍼런스 홈에서 이어지는 FAQ/공지/상담/가이드 흐름을 한곳에 모았습니다.</p>
          </div>
          <div class="support-grid">
            ${data.supportLinks
              .map(
                (item) => `
                  <button class="support-card" type="button" data-route="${item.route}">
                    <span class="support-card__icon">${escapeHtml(item.icon)}</span>
                    <strong>${escapeHtml(item.title)}</strong>
                    <p>${escapeHtml(item.subtitle)}</p>
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>공지사항</h2>
          </div>
          <div class="notice-list">
            ${data.notices
              .map(
                (notice) => `
                  <article class="notice-card">
                    <div class="notice-card__top">
                      <span class="mini-badge">${escapeHtml(notice.tag)}</span>
                      <span>${escapeHtml(notice.publishedLabel)}</span>
                    </div>
                    <strong>${escapeHtml(notice.title)}</strong>
                    <p>${escapeHtml(notice.body)}</p>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>FAQ</h2>
          </div>
          <div class="faq-list">
            ${data.faqs
              .map(
                (faq) => `
                  <details class="faq-item">
                    <summary>${escapeHtml(faq.question)}</summary>
                    <p>${escapeHtml(faq.answer)}</p>
                  </details>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>이용 가이드</h2>
            <p>홈 → 주문 탭 → 상품 상세 → 충전/주문 → 내역 확인 흐름으로 설계되어 있습니다.</p>
          </div>
          <div class="guide-list">
            <article class="guide-card"><strong>1. 홈에서 진입</strong><p>배너, 관심 태그, 추천 카드에서 원하는 상품으로 빠르게 이동합니다.</p></article>
            <article class="guide-card"><strong>2. 상품 구조 탐색</strong><p>좌측 플랫폼 레일과 우측 카드 리스트로 카탈로그를 빠르게 훑습니다.</p></article>
            <article class="guide-card"><strong>3. 주문 폼 입력</strong><p>상품 유형에 따라 계정형, URL형, 키워드형 폼을 다르게 렌더링합니다.</p></article>
            <article class="guide-card"><strong>4. 충전과 주문 내역</strong><p>캐시 충전과 주문 상태 조회가 각각 독립된 화면으로 이어집니다.</p></article>
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>운영 바로가기</h2>
            <p>고객, 상품, 주문, 공급사 관리를 한 번에 처리하는 관리자 화면으로 바로 이동합니다.</p>
          </div>
          <div class="support-grid">
            ${[
              ["고객 관리", "계정 생성, 역할 변경, 잔액 조정까지 한 화면에서 운영합니다."],
              ["상품 관리", "카테고리 생성과 상품 등록, 편집, 숨김 처리를 바로 진행합니다."],
              ["주문 운영", "최근 주문 상태와 내부 메모를 수동으로 관리합니다."],
              ["공급사 연동", "외부 API 연결 확인과 서비스 동기화, 상품 매핑을 설정합니다."],
            ]
              .map(
                ([title, subtitle]) => `
                  <button class="support-card" type="button" data-route="/admin">
                    <span class="support-card__icon">→</span>
                    <strong>${escapeHtml(title)}</strong>
                    <p>${escapeHtml(subtitle)}</p>
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section footer-section">
          <button class="full-width-cta" type="button" data-route="/admin">운영 관리자 열기</button>
        </section>
      </div>
    `,
    "my"
  );
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
    } else if (route.name === "admin") {
      app.innerHTML = renderAdmin();
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
    if (route.name === "detail" && route.id && state.categoryCache[route.id]) {
      scheduleLinkPreview(state.categoryCache[route.id], { immediate: true });
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
  state.ui.loginModalOpen = true;
  renderRoute();
}

function closeLoginModal() {
  state.ui.loginModalOpen = false;
  state.ui.loginRedirect = "";
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
    openLoginModal(path);
    return;
  }
  if (push) {
    window.history.pushState({}, "", path);
  }
  renderRoute();
}

function ensureBannerTimer() {
  if (bannerIntervalId || !state.bootstrap?.banners?.length) return;
  bannerIntervalId = window.setInterval(() => {
    if (getRoute().name !== "home") return;
    state.ui.bannerIndex = (state.ui.bannerIndex + 1) % state.bootstrap.banners.length;
    renderRoute();
  }, 4500);
}

async function applyAdminSiteSettingsImage(kind, file) {
  if (!state.adminSiteSettingsDraft) {
    state.adminSiteSettingsDraft = blankSiteSettingsDraft();
  }
  const isFavicon = kind === "favicon";
  if (!file.type.startsWith("image/")) {
    throw new Error("이미지 파일만 업로드할 수 있습니다.");
  }
  if (isFavicon && file.size > 1024 * 1024) {
    throw new Error("파비콘 이미지는 1MB 이하로 업로드해 주세요.");
  }
  if (!isFavicon && file.size > 5 * 1024 * 1024) {
    throw new Error("대표 이미지는 5MB 이하로 업로드해 주세요.");
  }
  const encoded = await readFileAsDataUrl(file);
  if (isFavicon) {
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
  const publicLoginOpenButton = event.target.closest("[data-public-login-open]");
  if (publicLoginOpenButton) {
    openLoginModal(window.location.pathname || "/");
    return;
  }

  const publicLoginCloseButton = event.target.closest("[data-public-login-close]");
  if (publicLoginCloseButton) {
    closeLoginModal();
    renderRoute();
    return;
  }

  const publicLogoutButton = event.target.closest("[data-public-logout]");
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

  const routeButton = event.target.closest("[data-route]");
  if (routeButton) {
    const path = routeButton.getAttribute("data-route");
    const platformId = routeButton.getAttribute("data-platform-id");
    if (platformId) {
      state.ui.activePlatform = platformId;
      state.ui.search = "";
    }
    navigate(path);
    return;
  }

  const homeSearchSubmitButton = event.target.closest("[data-home-search-submit]");
  if (homeSearchSubmitButton) {
    navigate("/products");
    return;
  }

  const popupDismissTodayButton = event.target.closest("[data-popup-dismiss-today]");
  if (popupDismissTodayButton) {
    const popup = state.bootstrap?.popup;
    dismissPopupToday(popup);
    closePopupForSession(popup);
    renderRoute();
    return;
  }

  const popupCloseButton = event.target.closest("[data-popup-close]");
  if (popupCloseButton) {
    closePopupForSession(state.bootstrap?.popup);
    renderRoute();
    return;
  }

  const clearPopupImageButton = event.target.closest("[data-admin-popup-image-clear]");
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

  const selectHomeBannerButton = event.target.closest("[data-admin-home-banner-select]");
  if (selectHomeBannerButton) {
    state.ui.adminSelectedHomeBannerId = selectHomeBannerButton.getAttribute("data-admin-home-banner-select") || "";
    state.adminHomeBannerDraft = homeBannerToDraft(getSelectedAdminHomeBanner());
    renderRoute();
    return;
  }

  const clearHomeBannerImageButton = event.target.closest("[data-admin-home-banner-image-clear]");
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

  const clearFaviconButton = event.target.closest("[data-admin-site-settings-favicon-clear]");
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

  const clearShareImageButton = event.target.closest("[data-admin-site-settings-share-clear]");
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

  const adminSectionButton = event.target.closest("[data-admin-scroll-section]");
  if (adminSectionButton) {
    const sectionId = adminSectionButton.getAttribute("data-admin-scroll-section") || "overview";
    navigate(adminSectionPath(sectionId));
    return;
  }

  const analyticsTabButton = event.target.closest("[data-admin-analytics-tab]");
  if (analyticsTabButton) {
    state.ui.adminAnalyticsTab = analyticsTabButton.getAttribute("data-admin-analytics-tab") || "dashboard";
    renderRoute();
    return;
  }

  const analyticsRangeButton = event.target.closest("[data-admin-analytics-range]");
  if (analyticsRangeButton) {
    state.ui.adminAnalyticsRange = analyticsRangeButton.getAttribute("data-admin-analytics-range") || "30d";
    renderRoute();
    return;
  }

  const customerFilterButton = event.target.closest("[data-admin-customer-filter]");
  if (customerFilterButton) {
    state.ui.adminCustomerFilter = customerFilterButton.getAttribute("data-admin-customer-filter") || "all";
    renderRoute();
    return;
  }

  const adminRefreshButton = event.target.closest("[data-admin-refresh]");
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

  const adminLogoutButton = event.target.closest("[data-admin-logout]");
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

  const newSupplierButton = event.target.closest("[data-admin-supplier-new]");
  if (newSupplierButton) {
    state.ui.adminSupplierMode = "new";
    state.ui.adminSelectedSupplierId = "";
    state.ui.adminSelectedSupplierServiceId = "";
    state.adminSupplierDraft = blankSupplierDraft();
    state.adminConnectionResult = null;
    renderRoute();
    return;
  }

  const supplierButton = event.target.closest("[data-admin-select-supplier]");
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

  const testConnectionButton = event.target.closest("[data-admin-test-connection]");
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

  const syncServicesButton = event.target.closest("[data-admin-sync-services]");
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

  const serviceButton = event.target.closest("[data-admin-service-select]");
  if (serviceButton) {
    state.ui.adminSelectedSupplierServiceId = serviceButton.getAttribute("data-admin-service-select") || "";
    renderRoute();
    return;
  }

  const applyServiceRecommendationButton = event.target.closest("[data-apply-service-recommendation]");
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

  const productButton = event.target.closest("[data-admin-product-select]");
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

  const deleteMappingButton = event.target.closest("[data-admin-delete-mapping]");
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

  const newCustomerButton = event.target.closest("[data-admin-customer-new]");
  if (newCustomerButton) {
    state.ui.adminCustomerMode = "new";
    state.ui.adminSelectedCustomerId = "";
    state.adminCustomerDraft = blankCustomerDraft();
    renderRoute();
    return;
  }

  const selectCustomerButton = event.target.closest("[data-admin-select-customer]");
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

  const deleteCustomerButton = event.target.closest("[data-admin-delete-customer]");
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

  const newCategoryButton = event.target.closest("[data-admin-category-new]");
  if (newCategoryButton) {
    state.ui.adminCategoryMode = "new";
    state.adminCategoryDraft = blankCategoryDraft(getAdminPlatformGroups()[0]?.id || "");
    renderRoute();
    return;
  }

  const selectCategoryButton = event.target.closest("[data-admin-category-select]");
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

  const deleteCategoryButton = event.target.closest("[data-admin-delete-category]");
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

  const newProductButton = event.target.closest("[data-admin-product-new]");
  if (newProductButton) {
    state.ui.adminProductMode = "new";
    state.ui.adminSelectedManageProductId = "";
    state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    renderRoute();
    return;
  }

  const selectManageProductButton = event.target.closest("[data-admin-manage-product-select]");
  if (selectManageProductButton) {
    const productId = selectManageProductButton.getAttribute("data-admin-manage-product-select") || "";
    const product = getAdminProducts().find((item) => item.id === productId) || null;
    state.ui.adminProductMode = "edit";
    state.ui.adminSelectedManageProductId = productId;
    state.adminProductDraft = productToDraft(product);
    renderRoute();
    return;
  }

  const deleteProductButton = event.target.closest("[data-admin-delete-product]");
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

  const adminOrderFilterButton = event.target.closest("[data-admin-order-filter]");
  if (adminOrderFilterButton) {
    state.ui.adminOrderFilter = adminOrderFilterButton.getAttribute("data-admin-order-filter") || "all";
    renderRoute();
    return;
  }

  const platformButton = event.target.closest("[data-platform-select]");
  if (platformButton) {
    state.ui.activePlatform = platformButton.getAttribute("data-platform-select");
    renderRoute();
    return;
  }

  const bannerDot = event.target.closest("[data-banner-index]");
  if (bannerDot) {
    state.ui.bannerIndex = Number(bannerDot.getAttribute("data-banner-index")) || 0;
    renderRoute();
    return;
  }

  const optionButton = event.target.closest("[data-option-select]");
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

  const filterButton = event.target.closest("[data-order-filter]");
  if (filterButton) {
    state.ui.orderFilter = filterButton.getAttribute("data-order-filter");
    renderRoute();
    return;
  }

  const chargeButton = event.target.closest("[data-charge-amount]");
  if (chargeButton) {
    const amount = Number(chargeButton.getAttribute("data-charge-amount"));
    try {
      await apiPost("/api/charge", { amount });
      await refreshCoreData();
      showToast(`${formatMoney(amount)} 충전이 완료되었습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "충전에 실패했습니다.", "error");
    }
  }
});

document.addEventListener("input", (event) => {
  const target = event.target;
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

  if (target.matches("[data-admin-site-settings-field]")) {
    const field = target.getAttribute("data-admin-site-settings-field");
    if (!state.adminSiteSettingsDraft) {
      state.adminSiteSettingsDraft = blankSiteSettingsDraft();
    }
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    state.adminSiteSettingsDraft[field] = nextValue;
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

  const siteImageType = target.getAttribute("data-admin-site-settings-image-upload");
  if (!siteImageType) return;
  const file = target.files && target.files[0];
  if (!file) return;
  try {
    await applyAdminSiteSettingsImage(siteImageType, file);
    showToast(siteImageType === "favicon" ? "파비콘이 적용되었습니다. 저장하면 실제 사이트에 반영됩니다." : "대표 이미지가 적용되었습니다. 저장하면 공유 미리보기에 반영됩니다.");
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
      const redirectPath = state.ui.loginRedirect || window.location.pathname || "/";
      const result = await apiPost("/api/login", {
        email: formData.get("email"),
        password: formData.get("password"),
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

  if (form.matches("[data-admin-site-settings-form]")) {
    event.preventDefault();
    const draft = state.adminSiteSettingsDraft || blankSiteSettingsDraft();
    try {
      const result = await apiPost("/api/admin/site-settings", {
        siteName: draft.siteName,
        siteDescription: draft.siteDescription,
        useMailSmsSiteName: draft.useMailSmsSiteName,
        mailSmsSiteName: draft.mailSmsSiteName,
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
    openLoginModal(window.location.pathname || "/");
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
