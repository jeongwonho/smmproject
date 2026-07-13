import { renderCafe24OperationalAuditPanel } from "./cafe24-audit-ui.js";
import { renderCafe24GaAnalyticsTab } from "./cafe24-analytics-ui.js";
import { renderCafe24OpsBoard, renderCafe24QuickControls } from "./cafe24-console-ui.js";
import { renderCafe24ProductLookupPanel } from "./cafe24-product-ui.js";
import { cafe24OrderFlowState, formatCafe24KstDateTime, renderCafe24ManualInputForm, renderCafe24Pagination, renderCafe24PreflightSummary, renderCafe24QueueActionHint, renderCafe24QueueToolbar } from "./cafe24-queue-ui.js";
import { renderCafe24MappingGapReport, renderCafe24MappingWorkflowChecklist } from "./cafe24-workflow-ui.js";
import { renderSupplierDispatchReadinessPanel, renderSupplierDispatchReadinessSnapshot } from "./supplier-readiness-ui.js";
import { supplierSyncInsight } from "./supplier-sync-ui.js";
let runtime = {}, state = {};
let DEFAULT_SITE_NAME = "인스타마트";
let advancedOrderFieldBlueprints = {}, advancedOrderFieldKeys = [];
let analyticsTabBlueprints = [], analyticsRangeBlueprints = [];
let statusMap = {};
export function configureAdminSections(nextRuntime = {}) {
  runtime = nextRuntime;
  state = nextRuntime.state || {};
  DEFAULT_SITE_NAME = nextRuntime.DEFAULT_SITE_NAME || DEFAULT_SITE_NAME;
  advancedOrderFieldBlueprints = nextRuntime.advancedOrderFieldBlueprints || {};
  advancedOrderFieldKeys = nextRuntime.advancedOrderFieldKeys || [];
  analyticsTabBlueprints = nextRuntime.analyticsTabBlueprints || [];
  analyticsRangeBlueprints = nextRuntime.analyticsRangeBlueprints || [];
  statusMap = nextRuntime.statusMap || {};
}
function callRuntime(name, ...args) {
  const fn = runtime[name];
  if (typeof fn !== "function") {
    throw new Error(`Admin sections runtime missing: ${name}`);
  }
  return fn(...args);
}
function escapeHtml(...args) { return callRuntime("escapeHtml", ...args); }
function formatMoney(...args) { return callRuntime("formatMoney", ...args); }
function formatNumber(...args) { return callRuntime("formatNumber", ...args); }
function formatCompactNumber(...args) { return callRuntime("formatCompactNumber", ...args); }
function formatPercent(...args) { return callRuntime("formatPercent", ...args); }
function adminSectionPath(...args) { return callRuntime("adminSectionPath", ...args); }
function analyticsRangeDays(...args) { return callRuntime("analyticsRangeDays", ...args); }
function analyticsWindow(...args) { return callRuntime("analyticsWindow", ...args); }
function analyticsDailySeries(...args) { return callRuntime("analyticsDailySeries", ...args); }
function getAdminSectionConfig(...args) { return callRuntime("getAdminSectionConfig", ...args); }
function adminSectionItems(...args) { return callRuntime("adminSectionItems", ...args); }
function getAdminPopup(...args) { return callRuntime("getAdminPopup", ...args); }
function getAdminSiteSettings(...args) { return callRuntime("getAdminSiteSettings", ...args); }
function getAdminHomeBanners(...args) { return callRuntime("getAdminHomeBanners", ...args); }
function getAdminPlatformSections(...args) { return callRuntime("getAdminPlatformSections", ...args); }
function getAdminAnalytics(...args) { return callRuntime("getAdminAnalytics", ...args); }
function getAdminCafe24Analytics(...args) { return callRuntime("getAdminCafe24Analytics", ...args); }
function getAdminNotices(...args) { return callRuntime("getAdminNotices", ...args); }
function getAdminFaqs(...args) { return callRuntime("getAdminFaqs", ...args); }
function getAdminAuditLogs(...args) { return callRuntime("getAdminAuditLogs", ...args); }
function getAdminSuppliers(...args) { return callRuntime("getAdminSuppliers", ...args); }
function getAdminProducts(...args) { return callRuntime("getAdminProducts", ...args); }
function getAdminCustomers(...args) { return callRuntime("getAdminCustomers", ...args); }
function getAdminChargeOrders(...args) { return callRuntime("getAdminChargeOrders", ...args); }
function getAdminCategories(...args) { return callRuntime("getAdminCategories", ...args); }
function getAdminPlatformGroups(...args) { return callRuntime("getAdminPlatformGroups", ...args); }
function getSelectedAdminSupplier(...args) { return callRuntime("getSelectedAdminSupplier", ...args); }
function getSelectedAdminProduct(...args) { return callRuntime("getSelectedAdminProduct", ...args); }
function getSelectedAdminCustomer(...args) { return callRuntime("getSelectedAdminCustomer", ...args); }
function getSelectedAdminHomeBanner(...args) { return callRuntime("getSelectedAdminHomeBanner", ...args); }
function getSelectedAdminPlatformSection(...args) { return callRuntime("getSelectedAdminPlatformSection", ...args); }
function getSelectedAdminCategory(...args) { return callRuntime("getSelectedAdminCategory", ...args); }
function getSelectedManageProduct(...args) { return callRuntime("getSelectedManageProduct", ...args); }
function getSelectedAdminNotice(...args) { return callRuntime("getSelectedAdminNotice", ...args); }
function getSelectedAdminFaq(...args) { return callRuntime("getSelectedAdminFaq", ...args); }
function getSelectedAdminSupplierService(...args) { return callRuntime("getSelectedAdminSupplierService", ...args); }
function getAdminMkt24ProductSetting(...args) { return callRuntime("getAdminMkt24ProductSetting", ...args); }
function getManageProducts(...args) { return callRuntime("getManageProducts", ...args); }
function currentViewer(...args) { return callRuntime("currentViewer", ...args); }
function blankSiteSettingsDraft(...args) { return callRuntime("blankSiteSettingsDraft", ...args); }
function blankPopupDraft(...args) { return callRuntime("blankPopupDraft", ...args); }
function blankHomeBannerDraft(...args) { return callRuntime("blankHomeBannerDraft", ...args); }
function blankPlatformSectionDraft(...args) { return callRuntime("blankPlatformSectionDraft", ...args); }
function blankSupplierDraft(...args) { return callRuntime("blankSupplierDraft", ...args); }
function blankCustomerDraft(...args) { return callRuntime("blankCustomerDraft", ...args); }
function blankCategoryDraft(...args) { return callRuntime("blankCategoryDraft", ...args); }
function blankProductDraft(...args) { return callRuntime("blankProductDraft", ...args); }
function blankNoticeDraft(...args) { return callRuntime("blankNoticeDraft", ...args); }
function blankFaqDraft(...args) { return callRuntime("blankFaqDraft", ...args); }
function siteSettingsPreviewPayload(...args) { return callRuntime("siteSettingsPreviewPayload", ...args); }
function popupPreviewPayload(...args) { return callRuntime("popupPreviewPayload", ...args); }
function homeBannerToDraft(...args) { return callRuntime("homeBannerToDraft", ...args); }
function platformSectionToDraft(...args) { return callRuntime("platformSectionToDraft", ...args); }
function supplierToDraft(...args) { return callRuntime("supplierToDraft", ...args); }
function customerToDraft(...args) { return callRuntime("customerToDraft", ...args); }
function categoryToDraft(...args) { return callRuntime("categoryToDraft", ...args); }
function productToDraft(...args) { return callRuntime("productToDraft", ...args); }
function noticeToDraft(...args) { return callRuntime("noticeToDraft", ...args); }
function faqToDraft(...args) { return callRuntime("faqToDraft", ...args); }
function renderHomeBannerCard(...args) { return callRuntime("renderHomeBannerCard", ...args); }
function renderPlatformLogoMarkup(...args) { return callRuntime("renderPlatformLogoMarkup", ...args); }
function renderSiteBrandLogoMarkup(...args) { return callRuntime("renderSiteBrandLogoMarkup", ...args); }
function brandMonogram(...args) { return callRuntime("brandMonogram", ...args); }
function siteNameOrDefault(...args) { return callRuntime("siteNameOrDefault", ...args); }
function defaultHomeBannerImageUrl(...args) { return callRuntime("defaultHomeBannerImageUrl", ...args); }
function resolveHomeBannerImageUrl(...args) { return callRuntime("resolveHomeBannerImageUrl", ...args); }
function supplierApiKeyLabel(...args) { return callRuntime("supplierApiKeyLabel", ...args); }
function supplierApiKeyPlaceholder(...args) { return callRuntime("supplierApiKeyPlaceholder", ...args); }
function supplierUrlPlaceholder(...args) { return callRuntime("supplierUrlPlaceholder", ...args); }
function supplierConnectionGuide(...args) { return callRuntime("supplierConnectionGuide", ...args); }
function formPresetLabel(...args) { return callRuntime("formPresetLabel", ...args); }
function formatAdvancedFieldLabel(...args) { return callRuntime("formatAdvancedFieldLabel", ...args); }
function renderAdvancedFieldBadges(...args) { return callRuntime("renderAdvancedFieldBadges", ...args); }
function renderSupplierRequestGuide(...args) { return callRuntime("renderSupplierRequestGuide", ...args); }
function shouldShowHomePopup(...args) { return callRuntime("shouldShowHomePopup", ...args); }
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
function supplierReadinessRequirementClass(requirement = {}) {
  if (requirement.ok === true || requirement.status === "pass") return "is-success";
  if (requirement.blocking === true || requirement.status === "blocked") return "is-error";
  return "is-warn";
}
function supplierReadinessRequirementLabel(requirement = {}) {
  if (requirement.ok === true || requirement.status === "pass") return "통과";
  if (requirement.blocking === true || requirement.status === "blocked") return "차단";
  return "확인";
}
function supplierReadinessContractSummary(readiness = {}) {
  const contract = readiness.dispatchContract || {};
  return [
    contract.label,
    contract.endpointMode,
    contract.authMode,
    contract.serviceIdRule,
  ].filter(Boolean).join(" · ");
}
function renderSupplierReadinessRequirementList(readiness = {}) {
  const requirements = Array.isArray(readiness.requirements) ? readiness.requirements : [];
  const contractSummary = supplierReadinessContractSummary(readiness);
  if (!requirements.length && !contractSummary) return "";
  return `
    <div class="admin-readiness-checks">
      ${contractSummary ? `
        <div class="admin-readiness-check">
          <div class="admin-readiness-check__text">
            <strong>발주 계약</strong>
            <span>${escapeHtml(contractSummary)}</span>
          </div>
          <span class="admin-badge is-neutral">기준</span>
        </div>
      ` : ""}
      ${requirements
        .map(
          (requirement) => {
            const valueSuffix = requirement.value ? ` · ${requirement.value}` : "";
            return `
            <div class="admin-readiness-check">
              <div class="admin-readiness-check__text">
                <strong>${escapeHtml(`${requirement.label || requirement.key || "조건"}${valueSuffix}`)}</strong>
                <span>${escapeHtml(requirement.message || requirement.value || "")}</span>
              </div>
              <span class="admin-badge ${supplierReadinessRequirementClass(requirement)}">${escapeHtml(supplierReadinessRequirementLabel(requirement))}</span>
            </div>
          `;
          }
        )
        .join("")}
    </div>
  `;
}
function cafe24OrderItemProductLabel(item = {}) {
  return item.internalProductName
    || item.rawPayloadPreview?.item?.product_name
    || item.rawPayloadPreview?.item?.productName
    || item.rawPayloadPreview?.item?.product_name_default
    || "매핑 대기";
}

function renderCafe24PaymentAuditPanel(orderItems = []) {
  orderItems = Array.isArray(state.adminCafe24OrderList?.items) ? state.adminCafe24OrderList.items : orderItems;
  const paymentFilter = state.ui.adminCafe24PaymentFilter || "all";
  const mappingFilter = state.ui.adminCafe24MappingFilter || "all";
  const search = String(state.ui.adminCafe24Search || "").trim().toLowerCase();
  const filteredItems = orderItems.filter((item) => {
    if (paymentFilter !== "all" && item.paymentGateStatus !== paymentFilter) return false;
    const isMapped = Boolean(item.mappingId || item.supplierServiceId || item.internalProductName);
    if (mappingFilter === "mapped" && !isMapped) return false;
    if (mappingFilter === "unmapped" && isMapped) return false;
    if (search && !String(item.searchText || "").includes(search)) return false;
    return true;
  });
  const paidUnmappedCount = orderItems.filter((item) => item.paymentGateStatus === "payment_confirmed" && !item.mappingId).length;
  const paidCount = orderItems.filter((item) => item.paymentGateStatus === "payment_confirmed").length;
  const pendingCount = orderItems.filter((item) => item.paymentGateStatus === "payment_pending").length;
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>결제/미매핑 주문 조회</h3>
        <p>수집된 Cafe24 품주를 결제 상태와 매핑 상태 기준으로 확인합니다. 결제완료지만 매핑이 없는 건을 우선 처리하세요.</p>
      </div>

      ${renderAdminInsightStrip(
        [
          { label: "결제완료", value: `${paidCount}건`, description: "공급 후보가 될 수 있는 품주" },
          { label: "결제완료 미매핑", value: `${paidUnmappedCount}건`, description: "매핑 후 재검증 필요", tone: paidUnmappedCount ? "warning" : "success" },
          { label: "결제대기/미확정", value: `${pendingCount}건`, description: "발주 차단 상태" },
          { label: "조회 결과", value: `${filteredItems.length}건`, description: "현재 필터 기준" },
        ],
        "admin-insight-grid--compact"
      )}

      <div class="admin-toolbar">
        <div class="search-shell">
          <input class="search-input" type="text" value="${escapeHtml(state.ui.adminCafe24Search || "")}" placeholder="주문번호, 품목코드, 상품번호, 구매자, 결제수단 검색" data-admin-cafe24-filter="search" />
        </div>
        <select class="field-select" data-admin-cafe24-filter="payment">
          <option value="all" ${paymentFilter === "all" ? "selected" : ""}>전체 결제상태</option>
          <option value="payment_confirmed" ${paymentFilter === "payment_confirmed" ? "selected" : ""}>결제완료</option>
          <option value="payment_pending" ${paymentFilter === "payment_pending" ? "selected" : ""}>결제대기</option>
          <option value="payment_review_required" ${paymentFilter === "payment_review_required" ? "selected" : ""}>검수 필요</option>
          <option value="cancelled" ${paymentFilter === "cancelled" ? "selected" : ""}>취소/환불</option>
        </select>
        <select class="field-select" data-admin-cafe24-filter="mapping">
          <option value="all" ${mappingFilter === "all" ? "selected" : ""}>전체 매핑상태</option>
          <option value="unmapped" ${mappingFilter === "unmapped" ? "selected" : ""}>미매핑</option>
          <option value="mapped" ${mappingFilter === "mapped" ? "selected" : ""}>매핑됨</option>
        </select>
      </div>

      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th>주문/품주</th>
              <th>상품</th>
              <th>결제</th>
              <th>금액/승인</th>
              <th>매핑</th>
              <th>처리</th>
            </tr>
          </thead>
          <tbody>
            ${
              filteredItems.length
                ? filteredItems.map((item) => {
                    const mapped = Boolean(item.mappingId || item.supplierServiceId || item.internalProductName);
                    const canDispatchCafe24Item = item.standardStatus === "ready_to_submit"
                      && item.paymentGateStatus === "payment_confirmed"
                      && !item.supplierOrderUuid;
                    return `
                      <tr>
                        <td>
                          <strong>${escapeHtml(item.orderId)}</strong>
                          <p class="admin-inline-note">${escapeHtml(item.orderItemCode || "-")}</p>
                        </td>
                        <td>
                          <strong>${escapeHtml(cafe24OrderItemProductLabel(item))}</strong>
                          <p class="admin-inline-note">${escapeHtml(item.productNo || "-")} / ${escapeHtml(item.variantCode || "-")}</p>
                        </td>
                        <td>
                          <span class="admin-badge ${item.paymentGateStatus === "payment_confirmed" ? "is-success" : item.paymentGateStatus === "payment_pending" ? "is-warning" : "is-neutral"}">${escapeHtml(item.paymentGateStatus || "-")}</span>
                          <p class="admin-inline-note">${escapeHtml(item.paymentStatus || "-")} · ${escapeHtml(item.paymentMethod || "수단 미확인")}</p>
                        </td>
                        <td>
                          <strong>${escapeHtml(item.paymentAmountLabel || formatMoney(item.paymentAmount || 0))}</strong>
                          <p class="admin-inline-note">${escapeHtml(item.paymentPaidAt || "결제일 미확인")} ${item.paymentReference ? `· ${escapeHtml(item.paymentReference)}` : ""}</p>
                        </td>
                        <td>
                          <span class="admin-badge ${mapped ? "is-success" : "is-warning"}">${mapped ? "매핑됨" : "미매핑"}</span>
                          <p class="admin-inline-note">${escapeHtml(item.supplierExternalServiceId || item.errorMessage || "-")}</p>
                        </td>
                        <td>
                          <div class="admin-action-row">
                            <button class="admin-secondary-button" type="button" data-admin-cafe24-resync-item="${escapeHtml(item.id)}">재동기화</button>
                            <button class="admin-primary-button" type="button" data-admin-cafe24-dispatch-item="${escapeHtml(item.id)}" ${canDispatchCafe24Item ? "" : "disabled"}>발주</button>
                          </div>
                        </td>
                      </tr>
                    `;
                  }).join("")
                : `<tr><td colspan="6">조건에 맞는 Cafe24 결제/주문 품주가 없습니다. 기간을 넓혀 주문 수집을 다시 실행해 주세요.</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderCafe24CollectionResult(result = null) {
  if (!result) return "";
  const summary = result.summary || {};
  const windows = Array.isArray(summary.requestWindows) ? summary.requestWindows : [];
  const queryPages = Array.isArray(summary.queryPages) ? summary.queryPages : [];
  const queryLabel = queryPages.map((page) => `${page.reason || "query"}:${page.dateType || "order_date"}:${Array.isArray(page.paymentStatuses) ? page.paymentStatuses.join("/") : page.paymentStatuses || "all"}:${page.count ?? 0}건`).join(" / ");
  const requestLabel = windows.length ? windows.map((item) => `${item.mallId || "-"} / shop ${item.shopNo || "-"} · ${item.startDate && item.endDate ? `${item.startDate} ~ ${item.endDate}` : item.orderId || "-"} · status ${Array.isArray(item.orderStatuses) ? item.orderStatuses.join(", ") : item.orderStatuses || "all"}`).join(" | ") : "-";
  const errors = Array.isArray(result.errors) ? result.errors.filter(Boolean) : [];
  return `
    <div class="admin-empty-card">
      <strong>최근 Cafe24 수집 결과</strong>
      <p class="admin-inline-note">요청: ${escapeHtml(requestLabel)}</p>
      <div class="admin-mini-metrics">
        <article><span>Cafe24 응답 주문</span><strong>${escapeHtml(String(summary.responseOrderCount ?? 0))}</strong></article>
        <article><span>저장 품주</span><strong>${escapeHtml(String(summary.storedOrderItemCount ?? result.processed ?? 0))}</strong></article>
        <article><span>결제/취소 차단</span><strong>${escapeHtml(String(summary.paymentBlockedCount ?? result.blocked ?? 0))}</strong></article>
        <article><span>검수 필요</span><strong>${escapeHtml(String(summary.reviewRequiredCount ?? result.waitingInput ?? 0))}</strong></article>
        <article><span>발주 대기</span><strong>${escapeHtml(String(summary.submitReadyCount ?? 0))}</strong></article>
      </div>
      ${queryLabel ? `<p class="admin-inline-note">조회 상세: ${escapeHtml(queryLabel)}</p>` : ""}
      ${summary.detailFetchCount ? `<p class="admin-inline-note">품주 상세 보강 조회: ${escapeHtml(String(summary.detailFetchCount))}건${summary.detailFetchErrorCount ? ` · 실패 ${escapeHtml(String(summary.detailFetchErrorCount))}건` : ""}</p>` : ""}
      ${errors.length ? `<p class="admin-inline-note is-danger">${escapeHtml(errors.join(" / "))}</p>` : ""}
    </div>
  `;
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
                  <input class="field-input" type="text" name="badgeText" value="${escapeHtml(draft.badgeText)}" placeholder="예: 신규 서비스 안내" data-admin-popup-field="badgeText" />
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
                    <input class="field-input" type="password" name="password" value="" autocomplete="new-password" placeholder="${draft.id ? "변경 시에만 입력" : "8자 이상 입력"}" data-admin-customer-field="password" />
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
  const failedCount = adminOrders.filter((order) => order.status === "failed").length;
  const cancelledCount = adminOrders.filter((order) => order.status === "cancelled").length;
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
          ["failed", `실패 ${failedCount}`],
          ["cancelled", `취소 ${cancelledCount}`],
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
                  <article><span>유입 경로</span><strong>${escapeHtml(order.orderChannelLabel || order.orderChannel || "자사몰")}</strong></article>
                  <article><span>공급사</span><strong>${escapeHtml(order.supplierName || "미연결")}</strong></article>
                  <article><span>전송 상태</span><strong>${escapeHtml(supplierDispatchLabel)}</strong></article>
                </div>
                <p class="order-card__target">${escapeHtml(order.targetValue || "입력값 없음")}</p>
                <div class="admin-order-callout-grid">
                  <article class="admin-mini-card ${hasDispatchIssue ? "is-risk" : ""}">
                    <span>공급사 전송</span>
                    <strong>${escapeHtml(supplierDispatchLabel)}</strong>
                    <p>${escapeHtml(order.supplierExternalOrderId || order.supplierStatus || order.dispatchStatus || "외부 주문번호 없음")}</p>
                    <p>${escapeHtml(`전송 시도 ${Number(order.dispatchAttempts || 0)}회${order.supplierLastError ? ` · ${order.supplierLastError}` : ""}`)}</p>
                  </article>
                  <article class="admin-mini-card">
                    <span>고객 요청 메모</span>
                    <strong>${escapeHtml(order.notes?.memo || "없음")}</strong>
                    <p>${escapeHtml(order.optionName || "기본 옵션")}</p>
                  </article>
                </div>
                <div class="admin-action-row">
                  ${order.supplierExternalOrderId ? `<button class="admin-secondary-button" type="button" data-admin-order-refresh-supplier="${escapeHtml(order.id)}">공급사 상태 조회</button>` : ""}
                  ${hasDispatchIssue || !order.supplierExternalOrderId ? `<button class="admin-secondary-button" type="button" data-admin-order-retry-supplier="${escapeHtml(order.id)}">발주 재전송</button>` : ""}
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
                            ["failed", "실패"],
                            ["cancelled", "취소"],
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

function cafe24CanDispatchItem(item = {}) {
  const status = item.standardStatus;
  return (status === "ready_to_submit" || status === "failed" || (status === "needs_manual_review" && item.automationErrorCode === "supplier_token_expired"))
    && item.paymentGateStatus === "payment_confirmed" && !item.supplierOrderUuid;
}

function cafe24StatusTone(item = {}) {
  if (item.standardStatus === "failed" || item.paymentGateStatus === "cancelled") return "is-error";
  if (item.standardStatus === "auto_dispatch_excluded") return "is-neutral";
  if (["waiting_input", "mapping_error", "missing_required_field", "invalid_quantity", "invalid_target", "payment_pending", "payment_review_required"].includes(item.standardStatus) || item.paymentGateStatus !== "payment_confirmed") return "is-warning";
  if (["split_scheduled", "split_in_progress", "supplier_submitted", "supplier_progress", "completed"].includes(item.standardStatus)) return "is-success";
  return "is-neutral";
}

function renderCafe24SplitJobSummary(item = {}) {
  const job = item.splitJob || null;
  if (!job) return "";
  const parts = Array.isArray(job.parts) ? job.parts : [];
  const totalParts = parts.length || Number(job.durationDays || 0);
  const completed = Number(job.completedParts || 0);
  const dispatched = Number(job.dispatchedParts || 0);
  const failed = Number(job.failedParts || 0);
  const nextDispatch = formatCafe24KstDateTime(job.nextDispatchAt, "대기 없음");
  return `
    <div class="admin-inline-note">
      분할 발주 ${escapeHtml(job.status || "-")} · ${escapeHtml(String(completed))}/${escapeHtml(String(totalParts))} 완료 · ${escapeHtml(String(dispatched))}회 발주 · 다음 ${escapeHtml(nextDispatch)}
    </div>
    <details class="admin-disclosure cafe24-order-card__details">
      <summary>분할 발주 ${escapeHtml(String(totalParts))}회차 보기</summary>
      <div class="admin-order-card__fact-grid">
        <article><span>1일 수량</span><strong>${escapeHtml(String(job.dailyQuantity || 0))}</strong></article>
        <article><span>반복 횟수</span><strong>${escapeHtml(String(job.durationDays || 0))}회</strong></article>
        <article><span>총 수량</span><strong>${escapeHtml(String(job.totalQuantity || 0))}</strong></article>
        <article><span>실패/검수</span><strong>${escapeHtml(String(failed))}회</strong></article>
      </div>
      <div class="admin-readiness-checks">
        ${parts.map((part) => `
          <div class="admin-readiness-check">
            <div class="admin-readiness-check__text">
              <strong>${escapeHtml(String(part.sequence || "-"))}회차 · ${escapeHtml(String(part.quantity || 0))}</strong>
              <span>${escapeHtml(formatCafe24KstDateTime(part.scheduledAt, "-"))}${part.supplierOrderUuid ? ` · 공급사 ${escapeHtml(part.supplierOrderUuid)}` : ""}${part.errorMessage ? ` · ${escapeHtml(part.errorMessage)}` : ""}</span>
            </div>
            <span class="admin-badge ${part.status === "completed" ? "is-success" : part.status === "failed" || part.status === "needs_manual_review" ? "is-warning" : "is-neutral"}">${escapeHtml(part.status || "-")}</span>
          </div>
        `).join("")}
      </div>
    </details>
  `;
}

function renderCafe24MappingPanel(activeIntegration = {}, products = [], suppliers = [], cafe24SupplierServices = [], selectedCafe24SupplierId = "", mappings = []) {
  const lookupDetail = state.adminCafe24ProductLookup?.detail || {};
  const optionLabels = Array.from(new Set((lookupDetail.options || []).map((option) => option.name).filter(Boolean)));
  const quantityLabel = optionLabels.find((label) => /팔로워|조회|좋아요|구독|수량|유입|댓글|저장/.test(label)) || optionLabels[0] || "팔로워 수";
  const sampleItems = (state.adminCafe24OrderList?.items || state.adminBootstrap?.cafe24OrderItems || []).slice(0, 30);
  const sampleOptions = sampleItems.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.orderId || "-")} · ${escapeHtml(item.productNo || "-")} · ${escapeHtml(item.productName || item.buyerName || "")}</option>`).join("");
  const preview = state.adminCafe24MappingPreview || null;
  const lookupWarnings = state.adminCafe24ProductLookup?.warnings || [];
  const mappingGapReport = state.adminCafe24MappingGapReport || null;
  const selectedCafe24Supplier = suppliers.find((supplier) => supplier.id === selectedCafe24SupplierId) || null;
  const selectedCafe24ServiceId = state.ui.adminCafe24SelectedSupplierServiceId || "";
  const selectedCafe24Service = cafe24SupplierServices.find((service) => service.id === selectedCafe24ServiceId) || null;
  return `
    ${renderCafe24MappingWorkflowChecklist({ activeIntegration, lookupDetail, lookupWarnings, mappingGapReport, serviceCount: cafe24SupplierServices.length, preview, orderItems: sampleItems, escapeHtml, canDispatchItem: cafe24CanDispatchItem })}
    ${renderSupplierDispatchReadinessSnapshot({
      selectedSupplier: selectedCafe24Supplier,
      selectedService: selectedCafe24Service,
      allServices: cafe24SupplierServices,
      activeConnection: null,
      syncStatus: selectedCafe24Supplier?.serviceSyncStatus || "never",
      escapeHtml,
    })}
    <div class="admin-action-row">
      <button class="admin-secondary-button" type="button" data-admin-cafe24-mapping-gaps="${escapeHtml(activeIntegration.id || "")}" ${activeIntegration.id ? "" : "disabled"}>미매핑 진단 실행</button>
    </div>
    ${renderCafe24MappingGapReport({ report: mappingGapReport, escapeHtml })}
    <div class="admin-two-column">
      <form class="admin-panel admin-form" data-admin-cafe24-mapping-form>
        <div class="section-head section-head--compact">
          <h3>Cafe24 상품 → 공급사 서비스 매핑</h3>
          <p>Cafe24 상품번호/품목코드를 기존 공급사 서비스에 직접 연결합니다. 내부 상품 참조는 선택값입니다.</p>
        </div>
        <div class="admin-three-column">
          <label class="form-field"><span class="field-label">상품번호</span><div class="field-shell"><input class="field-input" name="cafe24ProductNo" placeholder="product_no" /></div></label>
          <label class="form-field"><span class="field-label">품목코드</span><div class="field-shell"><input class="field-input" name="cafe24VariantCode" placeholder="variant_code" /></div></label>
          <label class="form-field"><span class="field-label">자체상품코드</span><div class="field-shell"><input class="field-input" name="cafe24CustomProductCode" placeholder="custom_product_code" /></div></label>
        </div>
        <div class="admin-two-column">
          <label class="form-field"><span class="field-label">공급사</span><div class="field-shell"><select class="field-select" name="supplierId" data-admin-cafe24-supplier-select>${suppliers.map((supplier) => `<option value="${escapeHtml(supplier.id)}" ${supplier.id === selectedCafe24SupplierId ? "selected" : ""}>${escapeHtml(supplier.name)}</option>`).join("")}</select></div></label>
          <label class="form-field">
            <span class="field-label">공급사 서비스</span>
            <div class="field-shell">
              <select class="field-select" name="supplierServiceId" data-admin-cafe24-service-select>
                <option value="">공급사 선택 후 서비스 목록을 불러오세요</option>
                ${cafe24SupplierServices.map((service) => `<option value="${escapeHtml(service.id)}" ${service.id === selectedCafe24ServiceId ? "selected" : ""}>${escapeHtml(service.name)} · ${escapeHtml(service.externalServiceId || "")} · ${escapeHtml(service.minAmount || "-")}~${escapeHtml(service.maxAmount || "-")}</option>`).join("")}
              </select>
            </div>
          </label>
        </div>
        <label class="form-field"><span class="field-label">내부 상품 참조(선택)</span><div class="field-shell"><select class="field-select" name="internalProductId"><option value="">내부 상품 없이 공급사 서비스 직접 연결</option>${products.map((product) => `<option value="${escapeHtml(product.id)}">${escapeHtml(product.name)} · ${escapeHtml(product.optionName || "")}</option>`).join("")}</select></div></label>
        <details class="admin-disclosure" open>
          <summary>주문 옵션 수량 매핑</summary>
          <p class="admin-inline-note">선택 옵션값(예: 250명)을 공급사 주문 수량으로 보내며, 후보가 여러 개면 검수 필요 상태로 둡니다.</p>
          <div class="admin-three-column">
            <label class="form-field"><span class="field-label">수량 source</span><div class="field-shell"><select class="field-select" name="quantityMappingMode"><option value="optionQuantity" selected>옵션 라벨에서 숫자 추출</option><option value="itemQuantity">Cafe24 상품 수량 사용</option><option value="fixed">고정 수량</option><option value="json">직접 JSON만 사용</option></select></div></label>
            <label class="form-field"><span class="field-label">옵션 라벨</span><div class="field-shell"><input class="field-input" name="quantityOptionLabel" value="${escapeHtml(quantityLabel)}" list="cafe24-quantity-option-labels" placeholder="예: 팔로워 수" /><datalist id="cafe24-quantity-option-labels">${optionLabels.map((label) => `<option value="${escapeHtml(label)}"></option>`).join("")}</datalist></div></label>
            <label class="form-field"><span class="field-label">고정 수량</span><div class="field-shell"><input class="field-input" name="quantityFixedValue" inputmode="numeric" placeholder="예: 250" /></div></label>
          </div>
          <label class="form-field"><span class="field-label">샘플 주문상품</span><div class="field-shell"><select class="field-select" name="sampleOrderItemId"><option value="">샘플 없이 설정 저장</option>${sampleOptions}</select></div></label>
        </details>
        <details class="admin-disclosure">
          <summary>보조 코드/필드 매핑 설정</summary>
          <div class="admin-two-column">
            <label class="form-field">
              <span class="field-label">공급사 상품 UUID(보조)</span>
              <div class="field-shell"><input class="field-input" name="supplierProductUuid" placeholder="예: productUuid" /></div>
            </label>
            <label class="form-field">
              <span class="field-label">공급사 상품 코드(보조)</span>
              <div class="field-shell"><input class="field-input" name="supplierProductCode" placeholder="예: service code" /></div>
            </label>
          </div>
          <label class="form-field">
            <span class="field-label">필드 매핑 JSON</span>
            <div class="field-shell">
              <textarea class="field-textarea" name="fieldMappingJson" rows="5" placeholder='{"targetUrl":"option:SNS 링크"}'></textarea>
            </div>
          </label>
        </details>
        <label class="admin-toggle"><input type="checkbox" name="autoDispatchEnabled" /><span>이 매핑은 자동 발주 허용(현재 운영 기본값은 OFF)</span></label>
        <input type="hidden" name="mallId" value="${escapeHtml(activeIntegration.mallId || "")}" />
        <input type="hidden" name="shopNo" value="${escapeHtml(String(activeIntegration.shopNo || 1))}" />
        <div class="admin-action-row">
          <button class="admin-secondary-button" type="button" data-admin-cafe24-mapping-preview ${activeIntegration.mallId ? "" : "disabled"}>payload 미리보기</button>
          <button class="admin-primary-button" type="submit" ${activeIntegration.mallId ? "" : "disabled"}>매핑 저장</button>
        </div>
      </form>

      <div class="admin-panel">
        <div class="section-head section-head--compact">
          <h3>매핑 목록</h3>
          <p>동일 mall/shop/product/variant/custom 조합은 하나만 활성화됩니다.</p>
        </div>
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>Cafe24 키</th><th>내부 참조</th><th>공급사 서비스</th><th>상태</th><th>작업</th></tr></thead>
            <tbody>
              ${mappings.length ? mappings.map((mapping) => `
                <tr>
                  <td>${escapeHtml([mapping.cafe24ProductNo, mapping.cafe24VariantCode, mapping.cafe24CustomProductCode].filter(Boolean).join(" / ") || "-")}</td>
                  <td>${escapeHtml(mapping.internalProductName || "선택 안 함")} ${mapping.internalOptionName ? `· ${escapeHtml(mapping.internalOptionName)}` : ""}</td>
                  <td>${escapeHtml(mapping.supplierName || mapping.supplierId || "-")} ${mapping.supplierServiceName || mapping.supplierExternalServiceId ? `· ${escapeHtml(mapping.supplierServiceName || mapping.supplierExternalServiceId)}` : ""}</td>
                  <td><span class="admin-badge ${mapping.enabled ? "is-success" : "is-neutral"}">${mapping.enabled ? "활성" : "비활성"}</span></td>
                  <td><button class="admin-secondary-button" type="button" data-admin-cafe24-delete-mapping="${escapeHtml(mapping.id)}">비활성화</button></td>
                </tr>
              `).join("") : `<tr><td colspan="5">등록된 Cafe24 상품 매핑이 없습니다.</td></tr>`}
            </tbody>
          </table>
        </div>
        ${preview ? `<div class="admin-card admin-subcard"><div class="admin-subcard__head"><strong>최근 payload 미리보기</strong><span class="admin-badge ${preview.ok ? "is-success" : "is-error"}">${preview.ok ? "검증 통과" : "검증 필요"}</span></div>${preview.errors?.length ? `<p class="admin-inline-note">${preview.errors.map((error) => escapeHtml(error)).join("<br />")}</p>` : ""}<div class="admin-two-column"><label class="form-field"><span class="field-label">정규화 필드</span><textarea class="field-textarea" rows="8" readonly>${escapeHtml(JSON.stringify(preview.normalizedFields || {}, null, 2))}</textarea></label><label class="form-field"><span class="field-label">공급사 payload</span><textarea class="field-textarea" rows="8" readonly>${escapeHtml(JSON.stringify(preview.supplierPayload || {}, null, 2))}</textarea></label></div><p class="admin-inline-note">수량 후보: ${escapeHtml((preview.quantityCandidates || []).map((candidate) => `${candidate.value}(${candidate.label || candidate.raw})`).join(", ") || "없음")}</p></div>` : ""}
      </div>
    </div>
  `;
}

function renderCafe24OrderQueuePanel(orderItems = [], suppliers = [], supplierServices = [], selectedSupplierId = "") {
  const list = state.adminCafe24OrderList || {};
  const pagination = list.pagination || { page: state.ui.adminCafe24OrderPage || 1, pageSize: 5, total: orderItems.length, totalPages: 1 };
  const sourceItems = Array.isArray(list.items) ? list.items : orderItems;
  const sortedItems = [...sourceItems].sort((a, b) => {
    const aScore = cafe24CanDispatchItem(a) ? 0 : a.standardStatus === "failed" ? 1 : !a.mappingId ? 2 : 3;
    const bScore = cafe24CanDispatchItem(b) ? 0 : b.standardStatus === "failed" ? 1 : !b.mappingId ? 2 : 3;
    return aScore - bScore;
  });
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>주문 처리 큐</h3>
        <p>최근 1개월 Cafe24 품주를 5개씩 조회합니다. 결제완료·매핑완료·필드검증 통과 품주만 공급사 발주가 활성화됩니다.</p>
      </div>
      ${renderCafe24QueueToolbar({ state, escapeHtml })}
      <div class="admin-order-list cafe24-order-list">
        ${sortedItems.length ? sortedItems.map((item) => {
          const canDispatchCafe24Item = cafe24CanDispatchItem(item);
          const preflight = state.adminCafe24Preflights?.[item.id] || null;
          return `
            <article class="admin-order-card ${item.standardStatus === "failed" ? "is-risk" : ""}">
              <div class="admin-order-card__top">
                <div>
                  <span class="order-card__platform">Cafe24 · ${escapeHtml(item.mallId)} / ${escapeHtml(String(item.shopNo))}</span>
                  <strong>${escapeHtml(cafe24OrderItemProductLabel(item))}</strong>
                  <p>${escapeHtml(item.orderId)} · ${escapeHtml(item.orderItemCode)}${item.orderDate ? ` · ${escapeHtml(item.orderDate)}` : ""}</p>
                </div>
                <div class="admin-order-card__statusbox">
                  <span class="admin-order-card__number">${escapeHtml(item.orderStatusCode || "-")}</span>
                  <span class="admin-badge ${cafe24StatusTone(item)}">${escapeHtml(item.standardStatus)}</span>
                </div>
              </div>
              <div class="cafe24-order-card__summary">
                <span>품목 ${escapeHtml(item.variantCode || "-")}</span>
                <span>상품 ${escapeHtml(item.productNo || "-")}</span>
                <span>결제 ${escapeHtml(item.paymentGateStatus || "-")}</span>
                <span>공급사 ${escapeHtml(item.supplierExternalServiceId || "-")}</span>
                <span>재시도 ${escapeHtml(String(item.retryCount || 0))}회</span>
              </div>
              ${renderCafe24QueueActionHint({ item, canDispatch: canDispatchCafe24Item, escapeHtml })}
              ${renderCafe24PreflightSummary({ preflight, escapeHtml })}
              ${renderCafe24SplitJobSummary(item)}
              ${item.errorMessage ? `<p class="admin-inline-note">${escapeHtml(item.errorMessage)}</p>` : ""}
              <div class="admin-action-row cafe24-order-card__primary-actions">
                <button class="admin-secondary-button" type="button" data-admin-cafe24-preflight-item="${escapeHtml(item.id)}">preflight</button>
                <button class="admin-primary-button" type="button" data-admin-cafe24-dispatch-item="${escapeHtml(item.id)}" ${canDispatchCafe24Item ? "" : "disabled"}>공급사 발주</button>
              </div>
              <details class="admin-disclosure cafe24-order-card__details">
                <summary>상세/수동 처리 열기</summary>
                <div class="admin-order-card__fact-grid">
                  <article><span>상품번호</span><strong>${escapeHtml(item.productNo || "-")}</strong></article>
                  <article><span>품목코드</span><strong>${escapeHtml(item.variantCode || "-")}</strong></article>
                  <article><span>결제 게이트</span><strong>${escapeHtml(item.paymentGateStatus || "-")}</strong></article>
                  <article><span>결제 근거</span><strong>${escapeHtml(item.paymentStatusSource || "-")}</strong></article>
                  <article><span>공급사</span><strong>${escapeHtml(item.supplierExternalServiceId || "-")}</strong></article>
                  <article><span>구매자</span><strong>${escapeHtml(item.buyerName || "-")}</strong></article>
                  <article><span>재시도</span><strong>${escapeHtml(String(item.retryCount || 0))}회</strong></article>
                  <article><span>주문 입력값</span><strong>${escapeHtml(item.targetDiagnostics?.input || "-")}</strong></article>
                  <article><span>공급 링크</span><strong>${escapeHtml(item.targetDiagnostics?.supplierLink || "-")}</strong></article>
                </div>
                ${item.targetDiagnostics?.message ? `<p class="admin-inline-note">대상 확인: ${escapeHtml(item.targetDiagnostics.message)}</p>` : ""}
                ${item.targetDiagnostics?.normalized ? `<p class="admin-inline-note">입력값을 공급사 전송 형식으로 변환했습니다: ${escapeHtml(item.targetDiagnostics.input || "-")} → ${escapeHtml(item.targetDiagnostics.supplierLink || "-")}</p>` : ""}
                ${renderCafe24ManualInputForm({
                  item,
                  suppliers,
                  supplierServices,
                  selectedSupplierId,
                  manualPreview: state.adminCafe24ManualPreviews?.[item.id] || null,
                  escapeHtml,
                })}
                <details class="admin-disclosure">
                  <summary>정규화/공급 payload 보기</summary>
                  <pre>${escapeHtml(JSON.stringify({ target: item.targetDiagnostics, fields: item.normalizedFields, supplierPayload: item.supplierPayload, supplierResponse: item.supplierResponse, raw: item.rawPayloadPreview }, null, 2))}</pre>
                </details>
                <div class="admin-action-row">
                  <button class="admin-secondary-button" type="button" data-admin-cafe24-resync-item="${escapeHtml(item.id)}">재동기화</button>
                  <button class="admin-secondary-button" type="button" data-admin-cafe24-retry-item="${escapeHtml(item.id)}">재검증</button>
                </div>
                <form class="admin-order-form" data-admin-cafe24-item-status-form>
                  <input type="hidden" name="itemId" value="${escapeHtml(item.id)}" />
                  <div class="admin-three-column">
                    <label class="form-field">
                      <span class="field-label">수동 상태</span>
                      <div class="field-shell">
                        <select class="field-select" name="status">
                          ${["received", "payment_pending", "payment_review_required", "waiting_input", "mapping_error", "auto_dispatch_excluded", "missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error", "needs_manual_review", "ready_to_submit", "split_scheduled", "split_in_progress", "submitting", "supplier_submitted", "supplier_progress", "completed", "failed", "cancelled"].map((status) => `<option value="${status}" ${item.standardStatus === status ? "selected" : ""}>${status}</option>`).join("")}
                        </select>
                      </div>
                    </label>
                    <label class="form-field admin-order-form__memo">
                      <span class="field-label">운영 메모</span>
                      <div class="field-shell"><input class="field-input" name="memo" value="${escapeHtml(item.errorMessage || "")}" /></div>
                    </label>
                    <div class="admin-order-form__submit">
                      <button class="admin-secondary-button" type="submit">상태 저장</button>
                    </div>
                  </div>
                </form>
              </details>
            </article>
          `;
        }).join("") : `<div class="admin-empty-card"><strong>조건에 맞는 Cafe24 주문이 없습니다.</strong><p>상단에서 최근 1개월 실시간 조회를 실행하거나 주문번호로 직접 조회해 주세요.</p></div>`}
      </div>
      ${renderCafe24Pagination({ pagination, escapeHtml })}
    </div>
  `;
}

function renderCafe24ConnectionPanel(activeIntegration = {}, cafe24OAuthRedirectUri = "") {
  const tokenStatus = activeIntegration.tokenStatus || "reconnect_required";
  const orderFlowState = cafe24OrderFlowState(activeIntegration);
  const tokenBadgeClass = {
    connected: "is-success",
    token_expiring: "is-warn",
    refreshing: "is-warn",
    reconnect_required: "is-error",
    failed: "is-error",
  }[tokenStatus] || "is-neutral";
  const badgeClass = orderFlowState.risk ? "is-error" : tokenBadgeClass;
  const statusLabel = orderFlowState.risk ? orderFlowState.label : activeIntegration.tokenStatusLabel || "미연결";
  const statusMessage = orderFlowState.risk
    ? orderFlowState.message
    : activeIntegration.tokenStatusMessage || "OAuth 연결 후 주문 수집을 시작할 수 있습니다.";
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>연결 설정</h3>
        <p>토큰은 OAuth로 저장·갱신합니다. 수동 토큰 입력은 운영 실수를 막기 위해 숨겼습니다.</p>
      </div>
      <div class="admin-empty-card">
        <div class="admin-action-row">
          <span class="admin-badge ${badgeClass}">${escapeHtml(statusLabel)}</span>
          <strong>${escapeHtml(activeIntegration.mallId || "Cafe24 Mall ID 미설정")}</strong>
        </div>
        <p>${escapeHtml(statusMessage)}</p>
        <p class="admin-inline-note">
          Access 만료: ${escapeHtml(activeIntegration.expiresAt || "미확인")} ·
          Refresh 만료: ${escapeHtml(activeIntegration.refreshTokenExpiresAt || "미확인")} ·
          마지막 갱신: ${escapeHtml(activeIntegration.tokenLastRefreshedAt || "없음")}
        </p>
      </div>
      <p class="admin-inline-note">
        Cafe24 Developers Redirect URL:
        <code>${escapeHtml(cafe24OAuthRedirectUri || "서버에서 확인 불가")}</code>
        <br />이 값과 Cafe24 앱 설정값이 1글자까지 동일해야 합니다.
      </p>
    </div>
  `;
}

function renderCafe24AdminSection() {
  const integrations = state.adminBootstrap?.cafe24Integrations || [];
  const mappings = state.adminBootstrap?.cafe24ProductMappings || [];
  const orderItems = state.adminCafe24OrderList?.items || state.adminBootstrap?.cafe24OrderItems || [];
  const cafe24OAuthRedirectUri = state.adminBootstrap?.cafe24OAuthRedirectUri || "";
  const products = getAdminProducts();
  const suppliers = getAdminSuppliers();
  const activeIntegration = integrations[0] || {};
  const selectedCafe24SupplierId = state.ui.adminCafe24SelectedSupplierId || suppliers[0]?.id || "";
  const cafe24SupplierServices = selectedCafe24SupplierId ? state.adminSupplierServices[selectedCafe24SupplierId]?.services || [] : [];
  const allowedTabs = new Set(["queue", "mapping", "lookup", "monitor", "audit", "settings"]);
  const activeCafe24Tab = allowedTabs.has(state.ui.adminCafe24Tab) ? state.ui.adminCafe24Tab : "queue";
  const advancedCafe24TabActive = ["lookup", "monitor", "audit", "settings"].includes(activeCafe24Tab);
  const lastCollectionResult = state.adminCafe24LastPollResult || null;
  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>Cafe24 주문 처리 콘솔</h2>
        <p>주문 수집, 상품 매핑, 검수, 공급사 발주, 예외 상태를 한 화면 흐름으로 확인합니다.</p>
      </div>
      ${renderCafe24OpsBoard({ state, orderItems, mappings, activeIntegration, escapeHtml, canDispatchItem: cafe24CanDispatchItem })}
      ${renderCafe24QuickControls({ activeIntegration, escapeHtml, origin: window.location.origin })}
      ${renderCafe24CollectionResult(lastCollectionResult)}
      <nav class="admin-analytics-subnav cafe24-primary-tabs">
        <button class="admin-analytics-subnav__item ${activeCafe24Tab === "queue" ? "is-active" : ""}" type="button" data-admin-cafe24-tab="queue">
          <strong>주문</strong><small>검색/검수/발주</small>
        </button>
        <button class="admin-analytics-subnav__item ${activeCafe24Tab === "mapping" ? "is-active" : ""}" type="button" data-admin-cafe24-tab="mapping">
          <strong>매핑</strong><small>상품 → 공급사</small>
        </button>
      </nav>
      <details class="admin-disclosure cafe24-advanced-tabs" ${advancedCafe24TabActive ? "open" : ""}>
        <summary>상품 조회/진단/연동 설정</summary>
        <nav class="admin-analytics-subnav">
        <button class="admin-analytics-subnav__item ${activeCafe24Tab === "lookup" ? "is-active" : ""}" type="button" data-admin-cafe24-tab="lookup">
          <strong>상품 조회</strong><small>옵션/품목코드</small>
        </button>
        <button class="admin-analytics-subnav__item ${activeCafe24Tab === "monitor" ? "is-active" : ""}" type="button" data-admin-cafe24-tab="monitor">
          <strong>흐름 점검</strong><small>결제/예외</small>
        </button>
        <button class="admin-analytics-subnav__item ${activeCafe24Tab === "audit" ? "is-active" : ""}" type="button" data-admin-cafe24-tab="audit">
          <strong>운영 Audit</strong><small>DB/토큰</small>
        </button>
        <button class="admin-analytics-subnav__item ${activeCafe24Tab === "settings" ? "is-active" : ""}" type="button" data-admin-cafe24-tab="settings">
          <strong>연동</strong><small>OAuth/Redirect</small>
        </button>
        </nav>
      </details>
      ${activeCafe24Tab === "queue" ? renderCafe24OrderQueuePanel(orderItems, suppliers, cafe24SupplierServices, selectedCafe24SupplierId) : ""}
      ${activeCafe24Tab === "mapping" ? renderCafe24MappingPanel(activeIntegration, products, suppliers, cafe24SupplierServices, selectedCafe24SupplierId, mappings) : ""}
      ${activeCafe24Tab === "lookup" ? renderCafe24ProductLookupPanel({ state, activeIntegration, escapeHtml }) : ""}
      ${activeCafe24Tab === "monitor" ? renderCafe24PaymentAuditPanel(orderItems) : ""}
      ${activeCafe24Tab === "audit" ? renderCafe24OperationalAuditPanel({ audit: state.adminCafe24OperationalAudit, escapeHtml }) : ""}
      ${activeCafe24Tab === "settings" ? renderCafe24ConnectionPanel(activeIntegration, cafe24OAuthRedirectUri) : ""}
    </section>
  `;
}
function renderAdminChargesSection() {
  const chargeOrders = getAdminChargeOrders();
  const activeFilter = state.ui.adminChargeFilter;
  const search = state.ui.adminChargeSearch.trim().toLowerCase();
  const filteredOrders = activeFilter === "all" ? chargeOrders : chargeOrders.filter((order) => order.status === activeFilter);
  const visibleOrders = filteredOrders.filter((order) => !search || String(order.searchText || "").includes(search));
  const awaitingDepositCount = chargeOrders.filter((order) => order.status === "awaiting_deposit").length;
  const awaitingPaymentCount = chargeOrders.filter((order) => order.status === "awaiting_payment").length;
  const paidCount = chargeOrders.filter((order) => order.status === "paid").length;
  const issueCount = chargeOrders.filter((order) => ["failed", "expired", "cancelled", "refund_requested"].includes(order.status)).length;

  const filters = [
    ["all", `전체 ${chargeOrders.length}`],
    ["awaiting_deposit", `입금대기 ${awaitingDepositCount}`],
    ["awaiting_payment", `결제대기 ${awaitingPaymentCount}`],
    ["paid", `완료 ${paidCount}`],
    ["failed", `실패 ${chargeOrders.filter((order) => order.status === "failed").length}`],
    ["cancelled", `취소 ${chargeOrders.filter((order) => order.status === "cancelled").length}`],
  ];

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>충전 운영</h2>
        <p>계좌입금 충전 요청을 확인하고 보유금액 반영, 실패, 취소 처리를 기록합니다.</p>
      </div>

      ${renderAdminInsightStrip(
        [
          { label: "입금 대기", value: `${awaitingDepositCount}건`, description: "관리자 확인 후 보유금액 반영 필요" },
          { label: "결제 대기", value: `${awaitingPaymentCount}건`, description: "카드/간편결제 승인 대기" },
          { label: "완료", value: `${paidCount}건`, description: "보유금액 반영 완료" },
          { label: "확인 필요", value: `${issueCount}건`, description: "실패, 취소, 환불 요청 상태" },
        ],
        "admin-insight-grid--compact"
      )}

      <div class="filter-row admin-filter-row">
        ${filters
          .map(
            ([key, label]) => `
              <button class="filter-chip ${activeFilter === key ? "is-active" : ""}" type="button" data-admin-charge-filter="${key}">
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
            value="${escapeHtml(state.ui.adminChargeSearch)}"
            placeholder="충전번호, 고객명, 이메일, 입금자명, 참조번호 검색"
            data-admin-charge-search
          />
        </div>
        <p class="admin-inline-note">현재 표시: ${escapeHtml(String(visibleOrders.length))}건</p>
      </div>

      <div class="admin-order-list">
        ${visibleOrders.length
          ? visibleOrders
              .map((order) => {
                const isPending = ["created", "awaiting_deposit", "awaiting_payment"].includes(order.status);
                const isRisk = ["failed", "expired", "cancelled", "refund_requested"].includes(order.status);
                return `
                  <article class="admin-order-card ${isRisk ? "is-risk" : ""}">
                    <div class="admin-order-card__top">
                      <div>
                        <span class="order-card__platform">${escapeHtml(order.paymentChannelLabel || "충전")}</span>
                        <strong>${escapeHtml(order.orderCode)}</strong>
                        <p>${escapeHtml(order.customerName || "고객")} · ${escapeHtml(order.customerEmailMasked || "비공개")}</p>
                      </div>
                      <div class="admin-order-card__statusbox">
                        <span class="admin-order-card__number">${escapeHtml(order.createdLabel || order.createdAt || "")}</span>
                        <span class="admin-badge ${isRisk ? "is-warning" : order.status === "paid" ? "is-success" : "is-neutral"}">${escapeHtml(order.statusLabel || order.status)}</span>
                      </div>
                    </div>
                    <div class="admin-order-card__fact-grid">
                      <article><span>충전 금액</span><strong>${escapeHtml(order.amountLabel)}</strong></article>
                      <article><span>부가세</span><strong>${escapeHtml(order.vatAmountLabel)}</strong></article>
                      <article><span>최종 결제</span><strong>${escapeHtml(order.totalAmountLabel)}</strong></article>
                      <article><span>증빙</span><strong>${escapeHtml(order.receiptTypeLabel || "안함")}</strong></article>
                    </div>
                    <div class="admin-order-callout-grid">
                      <article class="admin-mini-card">
                        <span>입금자명</span>
                        <strong>${escapeHtml(order.depositorName || "미입력")}</strong>
                        <p>${escapeHtml(order.reference || "참조번호 없음")}</p>
                      </article>
                      <article class="admin-mini-card ${isRisk ? "is-risk" : ""}">
                        <span>처리 상태</span>
                        <strong>${escapeHtml(order.statusLabel || order.status)}</strong>
                        <p>${escapeHtml(order.failureReason || order.confirmedAt || order.expiresAt || "확인 대기")}</p>
                      </article>
                    </div>
                    ${isPending
                      ? `
                        <form class="admin-order-form" data-admin-charge-action-form>
                          <input type="hidden" name="chargeOrderId" value="${escapeHtml(order.id)}" />
                          <div class="admin-three-column">
                            <label class="form-field">
                              <span class="field-label">처리</span>
                              <div class="field-shell">
                                <select class="field-select" name="action">
                                  <option value="approve_deposit">입금 확인</option>
                                  <option value="mark_failed">실패 처리</option>
                                  <option value="cancel">취소 처리</option>
                                </select>
                              </div>
                            </label>
                            <label class="form-field">
                              <span class="field-label">참조번호</span>
                              <div class="field-shell">
                                <input class="field-input" type="text" name="reference" value="${escapeHtml(order.reference || "")}" placeholder="입금 확인 번호 또는 메모" />
                              </div>
                            </label>
                            <label class="form-field admin-order-form__memo">
                              <span class="field-label">운영 메모</span>
                              <div class="field-shell">
                                <input class="field-input" type="text" name="adminMemo" placeholder="처리 사유를 입력해 주세요." />
                              </div>
                            </label>
                          </div>
                          <div class="admin-action-row">
                            <button class="admin-secondary-button" type="submit">처리 저장</button>
                          </div>
                        </form>
                      `
                      : ""}
                  </article>
                `;
              })
              .join("")
          : `<div class="admin-empty-card"><strong>조건에 맞는 충전 주문이 없습니다.</strong><p>상태 필터나 검색어를 바꿔 다시 확인해 주세요.</p></div>`}
      </div>
    </section>
  `;
}

function renderContentAdminSection() {
  const notices = getAdminNotices();
  const faqs = getAdminFaqs();
  const auditLogs = getAdminAuditLogs();
  const tab = state.ui.adminContentTab || "notices";
  const noticeDraft = state.adminNoticeDraft || noticeToDraft(getSelectedAdminNotice());
  const faqDraft = state.adminFaqDraft || faqToDraft(getSelectedAdminFaq());

  const noticePanel = `
    <div class="admin-management-layout admin-management-layout--catalog-top">
      <div class="admin-card admin-subcard">
        <div class="admin-subcard__head">
          <strong>공지 목록</strong>
          <button class="admin-secondary-button" type="button" data-admin-notice-new>새 공지</button>
        </div>
        <div class="admin-product-list">
          ${
            notices.length
              ? notices
                  .map(
                    (notice) => `
                      <button
                        class="admin-product-card ${state.ui.adminSelectedNoticeId === notice.id && state.ui.adminNoticeMode !== "new" ? "is-active" : ""}"
                        type="button"
                        data-admin-notice-select="${escapeHtml(notice.id)}"
                      >
                        <div class="admin-product-card__top">
                          <strong>${escapeHtml(notice.title)}</strong>
                          <span class="admin-badge ${notice.pinned ? "is-success" : "is-neutral"}">${notice.pinned ? "고정" : escapeHtml(notice.tag || "공지")}</span>
                        </div>
                        <p>${escapeHtml(notice.body)}</p>
                        <div class="admin-product-card__meta">
                          <span>${escapeHtml(notice.publishedAt || "-")}</span>
                        </div>
                      </button>
                    `
                  )
                  .join("")
              : `<div class="admin-empty-card"><strong>등록된 공지가 없습니다.</strong><p>첫 공지를 작성하면 고객 도움말 공지 영역에 반영됩니다.</p></div>`
          }
        </div>
      </div>

      <div class="admin-card admin-subcard admin-pane">
        <div class="admin-subcard__head">
          <strong>${noticeDraft.id ? "공지 수정" : "공지 작성"}</strong>
        </div>
        <form class="admin-form" data-admin-notice-form>
          <div class="admin-two-column">
            <label class="form-field">
              <span class="field-label">제목</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="title" value="${escapeHtml(noticeDraft.title)}" data-admin-notice-field="title" />
              </div>
            </label>
            <label class="form-field">
              <span class="field-label">태그</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="tag" value="${escapeHtml(noticeDraft.tag)}" data-admin-notice-field="tag" />
              </div>
            </label>
          </div>
          <label class="form-field">
            <span class="field-label">내용</span>
            <textarea class="field-textarea" name="body" rows="6" data-admin-notice-field="body">${escapeHtml(noticeDraft.body)}</textarea>
          </label>
          <div class="admin-two-column">
            <label class="form-field">
              <span class="field-label">게시 시각</span>
              <div class="field-shell">
                <input class="field-input" type="text" name="publishedAt" value="${escapeHtml(noticeDraft.publishedAt)}" data-admin-notice-field="publishedAt" />
              </div>
            </label>
            <label class="admin-toggle">
              <input type="checkbox" name="pinned" ${noticeDraft.pinned ? "checked" : ""} data-admin-notice-field="pinned" />
              <span>상단 고정</span>
            </label>
          </div>
          <div class="admin-action-row">
            <button class="admin-primary-button" type="submit">${noticeDraft.id ? "공지 저장" : "공지 등록"}</button>
            ${noticeDraft.id ? `<button class="admin-secondary-button" type="button" data-admin-notice-delete="${escapeHtml(noticeDraft.id)}">공지 삭제</button>` : ""}
          </div>
        </form>
      </div>
    </div>
  `;

  const faqPanel = `
    <div class="admin-management-layout admin-management-layout--catalog-top">
      <div class="admin-card admin-subcard">
        <div class="admin-subcard__head">
          <strong>FAQ 목록</strong>
          <button class="admin-secondary-button" type="button" data-admin-faq-new>새 FAQ</button>
        </div>
        <div class="admin-product-list">
          ${
            faqs.length
              ? faqs
                  .map(
                    (faq) => `
                      <button
                        class="admin-product-card ${state.ui.adminSelectedFaqId === faq.id && state.ui.adminFaqMode !== "new" ? "is-active" : ""}"
                        type="button"
                        data-admin-faq-select="${escapeHtml(faq.id)}"
                      >
                        <div class="admin-product-card__top">
                          <strong>${escapeHtml(faq.question)}</strong>
                          <span class="admin-badge is-neutral">#${escapeHtml(String(faq.sortOrder || 0))}</span>
                        </div>
                        <p>${escapeHtml(faq.answer)}</p>
                      </button>
                    `
                  )
                  .join("")
              : `<div class="admin-empty-card"><strong>등록된 FAQ가 없습니다.</strong><p>고객 문의를 줄일 수 있는 FAQ를 먼저 등록해 주세요.</p></div>`
          }
        </div>
      </div>
      <div class="admin-card admin-subcard admin-pane">
        <div class="admin-subcard__head">
          <strong>${faqDraft.id ? "FAQ 수정" : "FAQ 작성"}</strong>
        </div>
        <form class="admin-form" data-admin-faq-form>
          <label class="form-field">
            <span class="field-label">질문</span>
            <div class="field-shell">
              <input class="field-input" type="text" name="question" value="${escapeHtml(faqDraft.question)}" data-admin-faq-field="question" />
            </div>
          </label>
          <label class="form-field">
            <span class="field-label">답변</span>
            <textarea class="field-textarea" name="answer" rows="7" data-admin-faq-field="answer">${escapeHtml(faqDraft.answer)}</textarea>
          </label>
          <label class="form-field">
            <span class="field-label">정렬 순서</span>
            <div class="field-shell">
              <input class="field-input" type="number" name="sortOrder" value="${escapeHtml(String(faqDraft.sortOrder || 0))}" data-admin-faq-field="sortOrder" />
            </div>
          </label>
          <div class="admin-action-row">
            <button class="admin-primary-button" type="submit">${faqDraft.id ? "FAQ 저장" : "FAQ 등록"}</button>
            ${faqDraft.id ? `<button class="admin-secondary-button" type="button" data-admin-faq-delete="${escapeHtml(faqDraft.id)}">FAQ 삭제</button>` : ""}
          </div>
        </form>
      </div>
    </div>
  `;

  const auditPanel = `
    <div class="admin-card admin-subcard">
      <div class="admin-subcard__head">
        <strong>최근 관리자 작업 로그</strong>
        <span class="admin-badge is-neutral">최근 ${escapeHtml(String(auditLogs.length))}건</span>
      </div>
      <div class="admin-detail-list">
        ${
          auditLogs.length
            ? auditLogs
                .map(
                  (log) => `
                    <article>
                      <strong>${escapeHtml(log.message || log.action)}</strong>
                      <span>${escapeHtml(log.createdLabel || log.createdAt || "-")} · ${escapeHtml(log.actor || "admin")} · ${escapeHtml(log.entityType || "-")}/${escapeHtml(log.entityId || "-")}</span>
                    </article>
                  `
                )
                .join("")
            : `<article><strong>기록된 관리자 작업이 없습니다.</strong><span>위험 작업을 처리하면 이곳에 기록됩니다.</span></article>`
        }
      </div>
    </div>
  `;

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>콘텐츠/운영 로그</h2>
        <p>고객에게 노출되는 공지와 FAQ를 직접 관리하고 주요 운영 작업 기록을 확인합니다.</p>
      </div>
      ${renderAdminInsightStrip(
        [
          { label: "공지", value: `${notices.length}개`, description: "도움말 공지 영역에 노출" },
          { label: "고정 공지", value: `${notices.filter((notice) => notice.pinned).length}개`, description: "상단 우선 표시" },
          { label: "FAQ", value: `${faqs.length}개`, description: "고객 문의 전환 방어" },
          { label: "운영 로그", value: `${auditLogs.length}건`, description: "최근 관리자 작업 기록" },
        ],
        "admin-insight-grid--compact"
      )}
      <div class="filter-row admin-filter-row">
        ${[
          ["notices", "공지"],
          ["faqs", "FAQ"],
          ["logs", "운영 로그"],
        ]
          .map(
            ([key, label]) => `
              <button class="filter-chip ${tab === key ? "is-active" : ""}" type="button" data-admin-content-tab="${key}">
                ${escapeHtml(label)}
              </button>
            `
          )
          .join("")}
      </div>
      ${tab === "faqs" ? faqPanel : tab === "logs" ? auditPanel : noticePanel}
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
                <i></i>
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
  if (activeTab === "cafe24_ga") {
    body = renderCafe24GaAnalyticsTab({
      analytics: getAdminCafe24Analytics(),
      escapeHtml,
      formatMoney,
      formatNumber,
      renderAnalyticsOverviewCards,
      renderAnalyticsTable,
    });
  }

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

function renderMkt24ProductSettingPanel(selectedSupplier, selectedService) {
  if (selectedSupplier?.integrationType !== "mkt24" || !selectedService?.externalServiceId) return "";
  const setting = getAdminMkt24ProductSetting(selectedSupplier.id, selectedService.externalServiceId);
  if (!setting) {
    return `
      <div class="admin-card admin-subcard">
        <div class="admin-subcard__head">
          <strong>MKT24 주문 옵션 설정</strong>
          <span class="admin-badge is-warning">상세 필요</span>
        </div>
        <p class="admin-inline-note">선택한 MKT24 상품의 formStructure와 optionInfo 설정을 불러와야 주문 payload를 구성할 수 있습니다.</p>
        <div class="admin-action-row">
          <button class="admin-secondary-button" type="button" data-admin-mkt24-detail-refresh>상품 상세 불러오기</button>
        </div>
      </div>
    `;
  }

  const detail = setting.detailSnapshot || {};
  const fieldConfig = setting.fieldConfig || {};
  const optionConfig = setting.optionConfig || {};
  const fieldEntries = Object.entries(fieldConfig);
  const optionDefaultsText = JSON.stringify(optionConfig.defaults || {}, null, 2);
  const previewText = setting.payloadPreviewError
    ? setting.payloadPreviewError
    : JSON.stringify(setting.payloadPreview || {}, null, 2);
  const minMaxText = `${detail.minAmount ?? selectedService.minAmount ?? 0}~${detail.maxAmount ?? selectedService.maxAmount ?? 0}`;
  return `
    <div class="admin-card admin-subcard">
      <div class="admin-subcard__head">
        <strong>MKT24 주문 옵션 설정</strong>
        <span class="admin-badge ${setting.isActive ? "is-success" : "is-neutral"}">${setting.isActive ? "활성" : "비활성"}</span>
      </div>
      <p class="admin-inline-note">
        상품 UUID ${escapeHtml(setting.productUuid)} · ${escapeHtml(setting.productTypeName || detail.productTypeName || "상품 유형 없음")} · 수량 ${escapeHtml(String(minMaxText))}
      </p>
      <form class="admin-form" data-admin-mkt24-setting-form>
        <label class="admin-toggle">
          <input type="checkbox" name="isActive" ${setting.isActive ? "checked" : ""} data-admin-mkt24-setting-field />
          <span>이 MKT24 상품 설정으로 주문 발주 허용</span>
        </label>

        <div class="admin-mapping-preview">
          <article class="admin-mini-card">
            <span>상품명</span>
            <strong>${escapeHtml(setting.fullName || detail.fullName || selectedService.name || "")}</strong>
          </article>
          <article class="admin-mini-card">
            <span>동기화</span>
            <strong>${escapeHtml(setting.lastSyncedAt || "기록 없음")}</strong>
          </article>
        </div>

        <div class="admin-stack">
          <strong>사용자 입력 필드</strong>
          ${
            fieldEntries.length
              ? fieldEntries
                  .map(([fieldKey, config]) => renderMkt24FieldConfigRow(fieldKey, config))
                  .join("")
              : `<div class="admin-empty-card"><strong>formStructure가 없습니다.</strong><p>구조가 없는 상품은 관리자 기본값 기반으로만 payload를 만들 수 있습니다.</p></div>`
          }
        </div>

        <div class="admin-stack">
          <div class="admin-subcard__head">
            <strong>optionInfo 기본값</strong>
            <span class="admin-badge ${detail.supportsOrderOptions ? "is-success" : "is-neutral"}">${detail.supportsOrderOptions ? "지원" : "미지원"}</span>
          </div>
          <label class="admin-toggle">
            <input type="checkbox" name="optionEnabled" ${optionConfig.enabled ? "checked" : ""} ${detail.supportsOrderOptions ? "" : "disabled"} data-admin-mkt24-setting-field />
            <span>주문 payload에 optionInfo 포함</span>
          </label>
          <label class="form-field">
            <span class="field-label">optionInfo defaults JSON</span>
            <textarea class="field-textarea" name="optionDefaultsJson" rows="7" spellcheck="false" data-admin-mkt24-setting-field>${escapeHtml(optionDefaultsText)}</textarea>
          </label>
        </div>

        <div class="admin-stack">
          <strong>주문 payload preview</strong>
          <textarea class="field-textarea" rows="10" readonly>${escapeHtml(previewText)}</textarea>
        </div>

        <div class="admin-action-row">
          <button class="admin-primary-button" type="submit">MKT24 옵션 설정 저장</button>
          <button class="admin-secondary-button" type="button" data-admin-mkt24-detail-refresh>상품 상세 다시 불러오기</button>
        </div>
      </form>
    </div>
  `;
}

function renderMkt24FieldConfigRow(fieldKey, config = {}) {
  const isQuantity = fieldKey === "orderedCount";
  const label = config.label || fieldKey;
  return `
    <div class="admin-card admin-subcard" data-mkt24-field-row="${escapeHtml(fieldKey)}">
      <div class="admin-subcard__head">
        <strong>${escapeHtml(label)}</strong>
        <span class="admin-badge is-neutral">${escapeHtml(config.variant || "input")}</span>
      </div>
      <p class="admin-inline-note">${escapeHtml(fieldKey)} · ${(config.rules || []).map((rule) => escapeHtml(rule)).join(", ") || "검증 규칙 없음"}</p>
      <div class="admin-mapping-preview">
        <label class="admin-toggle">
          <input type="checkbox" name="field_${escapeHtml(fieldKey)}_enabled" ${config.enabled !== false ? "checked" : ""} data-admin-mkt24-setting-field />
          <span>사용</span>
        </label>
        <label class="admin-toggle">
          <input type="checkbox" name="field_${escapeHtml(fieldKey)}_required" ${config.required ? "checked" : ""} data-admin-mkt24-setting-field />
          <span>필수</span>
        </label>
        <label class="form-field">
          <span class="field-label">입력 방식</span>
          <div class="field-shell">
            <select class="field-select" name="field_${escapeHtml(fieldKey)}_inputMode" data-admin-mkt24-setting-field>
              <option value="user_input" ${config.inputMode !== "admin_default" ? "selected" : ""}>고객 입력 우선</option>
              <option value="admin_default" ${config.inputMode === "admin_default" ? "selected" : ""}>관리자 기본값 고정</option>
            </select>
          </div>
        </label>
        <label class="form-field">
          <span class="field-label">기본값</span>
          <div class="field-shell">
            <input class="field-input" type="text" name="field_${escapeHtml(fieldKey)}_defaultValue" value="${escapeHtml(config.defaultValue ?? "")}" data-admin-mkt24-setting-field />
          </div>
        </label>
      </div>
      ${
        isQuantity
          ? `
            <div class="admin-mapping-preview">
              <label class="form-field">
                <span class="field-label">최소</span>
                <input class="field-input" type="number" name="field_${escapeHtml(fieldKey)}_min" value="${escapeHtml(String(config.min ?? ""))}" data-admin-mkt24-setting-field />
              </label>
              <label class="form-field">
                <span class="field-label">최대</span>
                <input class="field-input" type="number" name="field_${escapeHtml(fieldKey)}_max" value="${escapeHtml(String(config.max ?? ""))}" data-admin-mkt24-setting-field />
              </label>
              <label class="form-field">
                <span class="field-label">단위</span>
                <input class="field-input" type="number" name="field_${escapeHtml(fieldKey)}_step" value="${escapeHtml(String(config.step ?? 1))}" data-admin-mkt24-setting-field />
              </label>
            </div>
          `
          : ""
      }
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
    ? `API Key ${draft.hasApiKey ? draft.apiKeyMasked || "설정됨" : "미설정"} · /v3/panel 방식은 Bearer Token을 사용하지 않음`
    : integrationType === "fasttraffic"
      ? `FastTraffic API Key ${draft.hasApiKey ? draft.apiKeyMasked || "설정됨" : "미설정"} · X-Api-Key 헤더 방식`
      : draft.hasApiKey
        ? draft.apiKeyMasked || "설정됨"
        : "미설정";
  const connectionState = activeConnection?.status || activeConnection?.lastTestStatus || "never";
  const syncStatus = activeConnection?.serviceSyncStatus || selectedSupplier?.serviceSyncStatus || "never";
  const inactiveServiceCount = Number(selectedSupplier?.inactiveServiceCount || 0);
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
                    (supplier) => {
                      const readiness = supplier.autoDispatchReadiness || {};
                      const readinessOk = readiness.ok === true;
                      const readinessClass = readinessOk ? "is-success" : readiness.retryable ? "is-warn" : "is-error";
                      return `
                        <button
                          class="admin-supplier-card ${state.ui.adminSelectedSupplierId === supplier.id && state.ui.adminSupplierMode !== "new" ? "is-active" : ""}"
                          type="button"
                          data-admin-select-supplier="${supplier.id}"
                        >
                          <div class="admin-supplier-card__top">
                            <strong>${escapeHtml(supplier.name)}</strong>
                            ${renderAdminHealthBadge(supplier.lastTestStatus)}
                          </div>
                          <p class="admin-inline-note">${escapeHtml(supplier.integrationType === "mkt24" ? "MKT24 API 연동" : supplier.integrationType === "fasttraffic" ? "FastTraffic API 연동" : "기존 SMM API 연동")}</p>
                          <p>${escapeHtml(supplier.apiUrl)}</p>
                          <div class="admin-supplier-card__meta">
                            <span>서비스 ${escapeHtml(String(supplier.serviceCount || 0))}</span>
                            ${Number(supplier.inactiveServiceCount || 0) ? `<span>비활성 ${escapeHtml(String(supplier.inactiveServiceCount || 0))}</span>` : ""}
                            <span>매핑 ${escapeHtml(String(supplier.mappingCount || 0))}</span>
                            <span>${supplier.isActive ? "활성" : "비활성"}</span>
                          </div>
                          <p class="admin-inline-note">
                            <span class="admin-badge ${readinessClass}">${escapeHtml(readinessOk ? "발주 가능" : "발주 차단")}</span>
                            ${escapeHtml(readiness.nextAction || readiness.message || readiness.code || "readiness 확인 필요")}
                          </p>
                          ${renderSupplierReadinessRequirementList(readiness)}
                        </button>
                      `;
                    }
                  )
                  .join("")
              : `<div class="admin-empty-card"><strong>등록된 공급사가 없습니다.</strong><p>새 공급사를 추가한 뒤 연결 확인과 동기화를 진행해 주세요.</p></div>`}
          </div>
        </section>

        <section class="admin-card">
          <div class="section-head section-head--compact">
            <h2>${draft.id ? "공급사 수정" : "공급사 등록"}</h2>
            <p>${escapeHtml(integrationType === "mkt24" ? "MKT24 대행사용 API는 https://api.mkt24.co.kr/v3/panel 엔드포인트를 사용합니다." : integrationType === "fasttraffic" ? "FastTraffic은 https://fastraffic.co.kr/nblog_api.php 엔드포인트와 X-Api-Key 헤더를 사용합니다." : "/api, /api/v2 형태를 모두 시도하도록 백엔드에서 자동 보정합니다.")}</p>
          </div>
          <form class="admin-form" data-admin-supplier-form>
            <label class="form-field">
              <span class="field-label">연동 방식</span>
              <div class="field-shell">
                <select class="field-select" name="integrationType" data-admin-supplier-field="integrationType">
                  <option value="classic" ${integrationType === "classic" ? "selected" : ""}>기존 SMM API</option>
                  <option value="mkt24" ${integrationType === "mkt24" ? "selected" : ""}>MKT24 API</option>
                  <option value="fasttraffic" ${integrationType === "fasttraffic" ? "selected" : ""}>FastTraffic API</option>
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
                <input class="field-input" type="password" name="apiKey" value="${escapeHtml(draft.apiKey)}" autocomplete="new-password" placeholder="${escapeHtml(supplierApiKeyPlaceholder(integrationType, Boolean(draft.id)))}" data-admin-supplier-field="apiKey" />
              </div>
            </label>
            ${integrationType === "mkt24"
              ? `<p class="admin-inline-note">MKT24 대행사용 API는 기존 API Key만 사용합니다. Bearer Token은 저장하거나 갱신할 필요가 없습니다.</p>`
              : integrationType === "fasttraffic"
                ? `<p class="admin-inline-note">FastTraffic은 로그인 계정이 아니라 API 페이지에서 발급한 64자 API Key만 저장합니다. 주문 등록은 분당 제한이 있어 자동 발주 시 throttle을 적용합니다.</p>`
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
                description: inactiveServiceCount ? `비활성 ${inactiveServiceCount}개 · ${integrationGuide.balance}` : integrationGuide.balance,
              },
              supplierSyncInsight(selectedSupplier, syncStatus),
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
        ${renderSupplierDispatchReadinessPanel({
          selectedSupplier,
          selectedService,
          allServices,
          activeConnection,
          connectionState,
          syncStatus,
          escapeHtml,
          renderAdminInsightStrip,
        })}
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
                    ${renderMkt24ProductSettingPanel(selectedSupplier, selectedService)}
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
export {
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
  updateAdminSiteSettingsPreview
};
