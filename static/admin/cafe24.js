let runtime = {};
let state = {};

export function configureCafe24AdminActions(nextRuntime = {}) {
  runtime = nextRuntime;
  state = nextRuntime.state || {};
}

function callRuntime(name, ...args) {
  const fn = runtime[name];
  if (typeof fn !== "function") {
    throw new Error(`Cafe24 admin runtime missing: ${name}`);
  }
  return fn(...args);
}

function apiGet(...args) { return callRuntime("apiGet", ...args); }
function apiPost(...args) { return callRuntime("apiPost", ...args); }
function refreshAdminData(...args) { return callRuntime("refreshAdminData", ...args); }
function renderRoute(...args) { return callRuntime("renderRoute", ...args); }
function showToast(...args) { return callRuntime("showToast", ...args); }

function escapeOptionText(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function buildCafe24FieldMappingJson(formData) {
  const raw = String(formData.get("fieldMappingJson") || "").trim();
  let mapping = {};
  if (raw) {
    try {
      mapping = JSON.parse(raw);
    } catch (error) {
      throw new Error("필드 매핑 JSON 형식이 올바르지 않습니다.");
    }
  }
  const mode = String(formData.get("quantityMappingMode") || "optionQuantity");
  if (mode === "optionQuantity") {
    mapping.orderedCount = {
      source: "option",
      label: String(formData.get("quantityOptionLabel") || "팔로워 수").trim(),
      extract: "quantity_number",
      fallback: "item.quantity",
      ambiguityPolicy: "needs_manual_review",
    };
  } else if (mode === "itemQuantity") {
    mapping.orderedCount = "quantity";
  } else if (mode === "fixed") {
    const value = String(formData.get("quantityFixedValue") || "").trim();
    if (!value) throw new Error("고정 수량을 입력해 주세요.");
    mapping.orderedCount = { source: "fixed", value };
  }
  return JSON.stringify(mapping);
}

const CAFE24_PREFLIGHT_BLOCKER_LABELS = {
  payment_not_confirmed: "결제 미확인",
  mapping_missing: "매핑 없음",
  supplier_mapping_missing: "공급사 매핑 없음",
  supplier_payload_missing: "payload 없음",
  supplier_order_already_exists: "이미 공급사 주문 있음",
  quantity_mismatch: "수량 불일치",
  supplier_missing: "공급사 없음",
  supplier_inactive: "공급사 비활성",
  supplier_service_missing: "공급사 서비스 없음",
  supplier_service_inactive: "공급사 서비스 비활성",
  mkt24_panel_service_id_invalid: "MKT24 서비스 ID 재매핑 필요",
  supplier_services_empty: "활성 공급사 서비스 없음",
  supplier_sync_failed: "공급사 서비스 동기화 실패",
  supplier_health_not_ok: "공급사 health 확인 필요",
  supplier_balance_failed: "공급사 잔액 확인 실패",
};

function describeCafe24PreflightBlocker(reason) {
  const key = String(reason || "").trim();
  if (!key) return "";
  if (CAFE24_PREFLIGHT_BLOCKER_LABELS[key]) return CAFE24_PREFLIGHT_BLOCKER_LABELS[key];
  if (key.startsWith("status_")) return `상태 ${key.slice("status_".length)}`;
  return key;
}

export function cafe24ManualInputToastMessage(result = {}) {
  const preflight = result.preflight && typeof result.preflight === "object" ? result.preflight : null;
  if (preflight?.canDispatch) {
    return "Cafe24 수동 보정 저장: preflight 통과, 단건 발주 가능";
  }
  const blockers = Array.isArray(preflight?.blockingReasons)
    ? preflight.blockingReasons.map(describeCafe24PreflightBlocker).filter(Boolean)
    : [];
  if (blockers.length) {
    return `Cafe24 수동 보정 저장: ${blockers.join(", ")} 확인 필요`;
  }
  return `Cafe24 수동 보정 저장: ${result.item?.standardStatus || "ready_to_submit"}`;
}

function findCafe24OrderItem(itemId) {
  return (state.adminCafe24OrderList?.items || []).find((item) => item.id === itemId) || null;
}

function cafe24ExpectedQuantityForItem(item = {}) {
  return item.normalizedFields?.orderedCount
    || item.supplierPayload?.quantity
    || item.supplierPayload?.orderedCount
    || "";
}

function cafe24MappingGapProductNos() {
  const items = state.adminCafe24OrderList?.items || state.adminBootstrap?.cafe24OrderItems || [];
  const productNos = [];
  for (const item of items) {
    const productNo = String(item?.productNo || "").trim();
    if (!productNo || productNos.includes(productNo)) continue;
    const unmapped = !item.mappingId && !item.supplierServiceId;
    if (item.paymentGateStatus === "payment_confirmed" && unmapped) {
      productNos.push(productNo);
    }
  }
  return productNos.slice(0, 8);
}

export function cafe24PreflightToastMessage(result = {}) {
  if (result.canDispatch) {
    return "Cafe24 preflight 통과: 단건 발주 가능";
  }
  const blockers = Array.isArray(result.blockingReasons)
    ? result.blockingReasons.map(describeCafe24PreflightBlocker).filter(Boolean)
    : [];
  if (blockers.length) {
    return `Cafe24 preflight 차단: ${blockers.join(", ")}`;
  }
  return "Cafe24 preflight 결과를 확인했습니다.";
}

function applyCafe24ProductToMapping(button) {
  const mappingForm = document.querySelector("[data-admin-cafe24-mapping-form]");
  if (!mappingForm) return false;
  const productNoInput = mappingForm.querySelector('[name="cafe24ProductNo"]');
  const variantCodeInput = mappingForm.querySelector('[name="cafe24VariantCode"]');
  const customProductCodeInput = mappingForm.querySelector('[name="cafe24CustomProductCode"]');
  if (productNoInput) productNoInput.value = button.getAttribute("data-admin-cafe24-use-product") || "";
  if (variantCodeInput) variantCodeInput.value = button.getAttribute("data-admin-cafe24-variant-code") || "";
  if (customProductCodeInput) customProductCodeInput.value = button.getAttribute("data-admin-cafe24-custom-product-code") || "";
  return true;
}

async function loadCafe24SupplierServices(supplierId) {
  if (!supplierId) return null;
  if (!state.adminSupplierServices) {
    state.adminSupplierServices = {};
  }
  if (!state.adminSupplierServices[supplierId]) {
    state.adminSupplierServices[supplierId] = await apiGet(`/api/admin/suppliers/${encodeURIComponent(supplierId)}/services`);
  }
  return state.adminSupplierServices[supplierId];
}

export function cafe24OrderItemsQueryKey() {
  const params = new URLSearchParams();
  const integrationId = (state.adminBootstrap?.cafe24Integrations || [])[0]?.id || "";
  if (integrationId) params.set("integrationId", integrationId);
  [["page", state.ui.adminCafe24OrderPage || 1], ["pageSize", 5], ["payment", state.ui.adminCafe24PaymentFilter || "all"], ["mapping", state.ui.adminCafe24MappingFilter || "all"], ["status", state.ui.adminCafe24StatusFilter || "all"]]
    .forEach(([key, value]) => params.set(key, String(value)));
  const search = String(state.ui.adminCafe24Search || "").trim();
  if (search) params.set("q", search);
  return params.toString();
}

export async function refreshCafe24OrderItems({ force = false } = {}) {
  if (!state.adminBootstrap?.cafe24Integrations?.length) {
    state.adminCafe24OrderList = { items: [], summary: {}, pagination: { page: 1, pageSize: 5, total: 0, totalPages: 1 } };
    state.adminCafe24OrderListKey = "";
    return state.adminCafe24OrderList;
  }
  const key = cafe24OrderItemsQueryKey();
  if (!force && state.adminCafe24OrderList && state.adminCafe24OrderListKey === key) return state.adminCafe24OrderList;
  const data = await apiGet(`/api/admin/cafe24/order-items?${key}`);
  state.adminCafe24OrderList = data;
  state.adminCafe24OrderListKey = key;
  return data;
}

export async function refreshCafe24OperationalAudit({ force = false } = {}) {
  if (!force && state.adminCafe24OperationalAudit) return state.adminCafe24OperationalAudit;
  const data = await apiGet("/api/admin/cafe24/operational-audit");
  state.adminCafe24OperationalAudit = {
    ...data,
    fetchedAt: new Date().toISOString(),
  };
  return state.adminCafe24OperationalAudit;
}

export async function handleCafe24AdminChange(target) {
  if (!(target instanceof Element)) return false;
  if (target.matches("[data-admin-cafe24-filter]")) {
    state.ui = state.ui || {};
    const key = target.getAttribute("data-admin-cafe24-filter") || "";
    if (key === "payment") state.ui.adminCafe24PaymentFilter = target.value || "all";
    if (key === "mapping") state.ui.adminCafe24MappingFilter = target.value || "all";
    if (key === "status") state.ui.adminCafe24StatusFilter = target.value || "all";
    if (key === "search") state.ui.adminCafe24Search = target.value || "";
    state.ui.adminCafe24OrderPage = 1;
    await refreshCafe24OrderItems({ force: true });
    renderRoute();
    return true;
  }
  if (target.matches("[data-admin-cafe24-service-select]")) {
    state.ui = state.ui || {};
    state.ui.adminCafe24SelectedSupplierServiceId = target.value || "";
    state.adminCafe24MappingPreview = null;
    renderRoute();
    return true;
  }
  if (!target.matches("[data-admin-cafe24-supplier-select], [data-admin-cafe24-manual-supplier-select]")) return false;
  const supplierId = target.value || "";
  state.ui = state.ui || {};
  state.ui.adminCafe24SelectedSupplierId = supplierId;
  if (target.matches("[data-admin-cafe24-supplier-select]")) {
    state.ui.adminCafe24SelectedSupplierServiceId = "";
    state.adminCafe24MappingPreview = null;
  }
  try {
    const data = await loadCafe24SupplierServices(supplierId);
    const serviceSelect = target.closest("form")?.querySelector("[data-admin-cafe24-service-select], [data-admin-cafe24-manual-service-select]")
      || document.querySelector("[data-admin-cafe24-service-select]");
    if (serviceSelect && data?.services) {
      serviceSelect.innerHTML = [
        `<option value="">공급사 서비스를 선택하세요</option>`,
        ...data.services.map((service) => (
          `<option value="${escapeOptionText(service.id)}">${escapeOptionText(service.name)} · ${escapeOptionText(service.externalServiceId || "")} · ${escapeOptionText(service.minAmount || "-")}~${escapeOptionText(service.maxAmount || "-")}</option>`
        )),
      ].join("");
    }
    showToast("공급사 서비스 목록을 불러왔습니다.");
    if (target.matches("[data-admin-cafe24-supplier-select]")) {
      renderRoute();
    }
  } catch (error) {
    showToast(error.message || "공급사 서비스 목록을 불러오지 못했습니다.", "error");
  }
  return true;
}

export async function handleCafe24AdminClick(closest) {
  const cafe24TabButton = closest("[data-admin-cafe24-tab]");
  if (cafe24TabButton) {
    state.ui = state.ui || {};
    state.ui.adminCafe24Tab = cafe24TabButton.getAttribute("data-admin-cafe24-tab") || "queue";
    const defaultSupplierId = state.ui.adminCafe24SelectedSupplierId || state.adminBootstrap?.suppliers?.[0]?.id || "";
    if ((state.ui.adminCafe24Tab === "queue" || state.ui.adminCafe24Tab === "mapping") && defaultSupplierId) {
      state.ui.adminCafe24SelectedSupplierId = defaultSupplierId;
      await loadCafe24SupplierServices(defaultSupplierId);
    }
    if (state.ui.adminCafe24Tab === "queue" || state.ui.adminCafe24Tab === "monitor") {
      await refreshCafe24OrderItems({ force: true });
    }
    if (state.ui.adminCafe24Tab === "audit") {
      await refreshCafe24OperationalAudit();
    }
    renderRoute();
    return true;
  }

  const cafe24OperationalAuditButton = closest("[data-admin-cafe24-operational-audit-refresh]");
  if (cafe24OperationalAuditButton) {
    try {
      await refreshCafe24OperationalAudit({ force: true });
      showToast("Cafe24 운영 상태를 조회했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 운영 상태 조회에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24MappingGapsButton = closest("[data-admin-cafe24-mapping-gaps]");
  if (cafe24MappingGapsButton) {
    const integrationId = cafe24MappingGapsButton.getAttribute("data-admin-cafe24-mapping-gaps") || "";
    const productNos = cafe24MappingGapProductNos();
    try {
      const result = await apiPost("/api/admin/cafe24/mapping-gaps", {
        integrationId,
        productNos: productNos.join(","),
        includeProductDetails: true,
        limit: 50,
        detailFetchLimit: 5,
        detailApiTimeoutSeconds: 4,
        detailApiMaxAttempts: 2,
        detailApiBudgetSeconds: 24,
      });
      state.adminCafe24MappingGapReport = result;
      const warningCount = (result.warnings || []).length;
      showToast(`Cafe24 미매핑 진단: ${result.summary?.groupCount || 0}개 그룹${warningCount ? ` · warning ${warningCount}개` : ""}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 미매핑 진단에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24PageButton = closest("[data-admin-cafe24-page]");
  if (cafe24PageButton) {
    const page = Number(cafe24PageButton.getAttribute("data-admin-cafe24-page") || "1");
    state.ui.adminCafe24OrderPage = Number.isFinite(page) && page > 0 ? page : 1;
    await refreshCafe24OrderItems({ force: true });
    renderRoute();
    return true;
  }

  const cafe24OauthStartButton = closest("[data-admin-cafe24-oauth-start]");
  if (cafe24OauthStartButton) {
    const form = cafe24OauthStartButton.closest("[data-admin-cafe24-integration-form]");
    const formData = form ? new FormData(form) : new FormData();
    try {
      const result = await apiPost("/api/admin/cafe24/oauth/start", {
        mallId: formData.get("mallId"),
        shopNo: formData.get("shopNo"),
        scopes: formData.get("scopes"),
      });
      showToast("Cafe24 승인 페이지로 이동합니다.");
      window.location.href = result.authorizeUrl;
    } catch (error) {
      showToast(error.message || "Cafe24 OAuth 연결을 시작하지 못했습니다.", "error");
    }
    return true;
  }

  const cafe24ProductDetailButton = closest("[data-admin-cafe24-product-detail]");
  if (cafe24ProductDetailButton) {
    const productNo = cafe24ProductDetailButton.getAttribute("data-admin-cafe24-product-detail") || "";
    const integrationId = cafe24ProductDetailButton.getAttribute("data-admin-cafe24-integration-id") || "";
    try {
      const params = new URLSearchParams();
      if (integrationId) params.set("integrationId", integrationId);
      const suffix = params.toString() ? `?${params.toString()}` : "";
      const result = await apiGet(`/api/admin/cafe24/products/${encodeURIComponent(productNo)}${suffix}`);
      state.adminCafe24ProductLookup = {
        ...(state.adminCafe24ProductLookup || {}),
        detail: result.product || null,
        warnings: result.warnings || [],
      };
      showToast("Cafe24 상품 옵션을 조회했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 상품 옵션 조회에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24UseProductButton = closest("[data-admin-cafe24-use-product]");
  if (cafe24UseProductButton) {
    if (applyCafe24ProductToMapping(cafe24UseProductButton)) {
      showToast("Cafe24 상품 키를 매핑폼에 적용했습니다.");
    }
    return true;
  }

  const cafe24PollButton = closest("[data-admin-cafe24-poll]");
  if (cafe24PollButton) {
    const integrationId = cafe24PollButton.getAttribute("data-admin-cafe24-poll") || "";
    const form = document.querySelector("[data-admin-cafe24-integration-form]");
    const formData = form ? new FormData(form) : new FormData();
    try {
      const result = await apiPost("/api/admin/cafe24/poll", {
        integrationId: integrationId || formData.get("id"),
        submitReady: false,
        startDate: formData.get("pollStartDate"),
        endDate: formData.get("pollEndDate"),
      });
      state.adminCafe24LastPollResult = result;
      await refreshAdminData({ preserveDraft: true });
      state.ui.adminCafe24OrderPage = 1;
      await refreshCafe24OrderItems({ force: true });
      showToast(`Cafe24 수집 완료: ${result.processed || 0}개 처리, ${result.blocked || 0}개 차단`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 주문 수집에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24ResyncByIdButton = closest("[data-admin-cafe24-resync-by-id]");
  if (cafe24ResyncByIdButton) {
    const integrationId = cafe24ResyncByIdButton.getAttribute("data-admin-cafe24-resync-by-id") || "";
    const form = document.querySelector("[data-admin-cafe24-integration-form]");
    const formData = form ? new FormData(form) : new FormData();
    const orderId = String(formData.get("resyncOrderId") || "").trim();
    if (!orderId) {
      showToast("재수집할 Cafe24 주문번호를 입력해 주세요.", "error");
      return true;
    }
    try {
      const result = await apiPost("/api/admin/cafe24/orders/resync-by-id", {
        integrationId: integrationId || formData.get("id"),
        orderId,
        submitReady: false,
      });
      state.adminCafe24LastPollResult = result;
      await refreshAdminData({ preserveDraft: true });
      state.ui.adminCafe24OrderPage = 1;
      await refreshCafe24OrderItems({ force: true });
      showToast(`Cafe24 주문번호 재수집 완료: ${result.processed || 0}개 품주 저장`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 주문번호 재수집에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24DeleteMappingButton = closest("[data-admin-cafe24-delete-mapping]");
  if (cafe24DeleteMappingButton) {
    const mappingId = cafe24DeleteMappingButton.getAttribute("data-admin-cafe24-delete-mapping") || "";
    try {
      await apiPost("/api/admin/cafe24/mappings/delete", { mappingId });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast("Cafe24 상품 매핑을 비활성화했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 상품 매핑 정리에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24MappingPreviewButton = closest("[data-admin-cafe24-mapping-preview]");
  if (cafe24MappingPreviewButton) {
    const form = cafe24MappingPreviewButton.closest("[data-admin-cafe24-mapping-form]");
    const formData = form ? new FormData(form) : new FormData();
    try {
      const result = await apiPost("/api/admin/cafe24/mappings/preview", {
        mallId: formData.get("mallId"),
        shopNo: formData.get("shopNo"),
        cafe24ProductNo: formData.get("cafe24ProductNo"),
        cafe24VariantCode: formData.get("cafe24VariantCode"),
        cafe24CustomProductCode: formData.get("cafe24CustomProductCode"),
        internalProductId: formData.get("internalProductId"),
        supplierId: formData.get("supplierId"),
        supplierServiceId: formData.get("supplierServiceId"),
        supplierProductUuid: formData.get("supplierProductUuid"),
        supplierProductCode: formData.get("supplierProductCode"),
        fieldMappingJson: buildCafe24FieldMappingJson(formData),
        sampleOrderItemId: formData.get("sampleOrderItemId"),
      });
      state.ui = state.ui || {};
      state.ui.adminCafe24SelectedSupplierId = String(formData.get("supplierId") || "");
      state.ui.adminCafe24SelectedSupplierServiceId = String(formData.get("supplierServiceId") || "");
      state.adminCafe24MappingPreview = result;
      showToast(result.ok ? "Cafe24 매핑 payload를 확인했습니다." : "Cafe24 매핑 검증이 필요합니다.", result.ok ? "success" : "error");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 매핑 미리보기에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24RetryButton = closest("[data-admin-cafe24-retry-item]");
  if (cafe24RetryButton) {
    const itemId = cafe24RetryButton.getAttribute("data-admin-cafe24-retry-item") || "";
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/retry", { itemId });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast(`Cafe24 품주 재처리: ${result.result?.status || "처리됨"}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 품주 재처리에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24PreflightButton = closest("[data-admin-cafe24-preflight-item]");
  if (cafe24PreflightButton) {
    const itemId = cafe24PreflightButton.getAttribute("data-admin-cafe24-preflight-item") || "";
    const item = findCafe24OrderItem(itemId);
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/preflight", {
        itemId,
        expectedQuantity: cafe24ExpectedQuantityForItem(item),
      });
      state.adminCafe24Preflights = {
        ...(state.adminCafe24Preflights || {}),
        [itemId]: result,
      };
      showToast(cafe24PreflightToastMessage(result), result.canDispatch ? "success" : "error");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 preflight 확인에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24ManualPreviewButton = closest("[data-admin-cafe24-manual-preview-item]");
  if (cafe24ManualPreviewButton) {
    const itemId = cafe24ManualPreviewButton.getAttribute("data-admin-cafe24-manual-preview-item") || "";
    const form = cafe24ManualPreviewButton.closest("[data-admin-cafe24-item-manual-form]");
    const formData = form ? new FormData(form) : new FormData();
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/manual-input/preview", {
        itemId: formData.get("itemId") || itemId,
        supplierId: formData.get("supplierId"),
        supplierServiceId: formData.get("supplierServiceId"),
        targetValue: formData.get("targetValue"),
        orderedCount: formData.get("orderedCount"),
        requestMemo: formData.get("requestMemo"),
        expectedQuantity: formData.get("orderedCount"),
      });
      state.adminCafe24ManualPreviews = {
        ...(state.adminCafe24ManualPreviews || {}),
        [itemId]: result,
      };
      if (result.preflight) {
        state.adminCafe24Preflights = {
          ...(state.adminCafe24Preflights || {}),
          [itemId]: result.preflight,
        };
      }
      showToast(
        result.preflight?.canDispatch
          ? "수동 보정 preview 통과: 저장 후 단건 발주 가능"
          : cafe24PreflightToastMessage(result.preflight || {}),
        result.preflight?.canDispatch ? "success" : "error"
      );
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 수동 보정 preview에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24DispatchButton = closest("[data-admin-cafe24-dispatch-item]");
  if (cafe24DispatchButton) {
    const itemId = cafe24DispatchButton.getAttribute("data-admin-cafe24-dispatch-item") || "";
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/dispatch", { itemId });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast(`Cafe24 공급사 발주: ${result.status || "처리됨"}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 공급사 발주에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24ResyncButton = closest("[data-admin-cafe24-resync-item]");
  if (cafe24ResyncButton) {
    const itemId = cafe24ResyncButton.getAttribute("data-admin-cafe24-resync-item") || "";
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/resync", { itemId });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast(`Cafe24 품주 재동기화: ${result.result?.status || "확인됨"}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 품주 재동기화에 실패했습니다.", "error");
    }
    return true;
  }

  return false;
}

export async function handleCafe24AdminSubmit(form, event) {
  if (form.matches("[data-admin-cafe24-product-search-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    const params = new URLSearchParams();
    ["integrationId", "q", "productNo"].forEach((key) => {
      const value = String(formData.get(key) || "").trim();
      if (value) params.set(key, value);
    });
    params.set("limit", "20");
    try {
      const result = await apiGet(`/api/admin/cafe24/products?${params.toString()}`);
      state.adminCafe24ProductLookup = {
        products: result.products || [],
        detail: null,
        query: result.query || {
          keyword: formData.get("q"),
          productNo: formData.get("productNo"),
          limit: 20,
          offset: 0,
        },
        warnings: [],
      };
      showToast(`Cafe24 상품 ${result.count || 0}개를 조회했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 상품 조회에 실패했습니다.", "error");
    }
    return true;
  }

  if (form.matches("[data-admin-cafe24-integration-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/admin/cafe24/integrations", {
        id: formData.get("id"),
        mallId: formData.get("mallId"),
        shopNo: formData.get("shopNo"),
        accessToken: formData.get("accessToken"),
        refreshToken: formData.get("refreshToken"),
        expiresAt: formData.get("expiresAt"),
        refreshTokenExpiresAt: formData.get("refreshTokenExpiresAt"),
        scopes: formData.get("scopes"),
        autoSubmit: Boolean(formData.get("autoSubmit")),
        isActive: Boolean(formData.get("isActive")),
      });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast(`${result.integration.mallId} Cafe24 연동을 저장했습니다.`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 연동 저장에 실패했습니다.", "error");
    }
    return true;
  }

  if (form.matches("[data-admin-cafe24-mapping-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/admin/cafe24/mappings", {
        mallId: formData.get("mallId"),
        shopNo: formData.get("shopNo"),
        cafe24ProductNo: formData.get("cafe24ProductNo"),
        cafe24VariantCode: formData.get("cafe24VariantCode"),
        cafe24CustomProductCode: formData.get("cafe24CustomProductCode"),
        internalProductId: formData.get("internalProductId"),
        supplierId: formData.get("supplierId"),
        supplierServiceId: formData.get("supplierServiceId"),
        supplierProductUuid: formData.get("supplierProductUuid"),
        supplierProductCode: formData.get("supplierProductCode"),
        fieldMappingJson: buildCafe24FieldMappingJson(formData),
        autoDispatchEnabled: Boolean(formData.get("autoDispatchEnabled")),
        enabled: true,
      });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast(`${result.mapping.internalProductName || "Cafe24"} 매핑을 저장했습니다.`);
      form.reset();
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 상품 매핑 저장에 실패했습니다.", "error");
    }
    return true;
  }

  if (form.matches("[data-admin-cafe24-item-status-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      await apiPost("/api/admin/cafe24/order-items/status", {
        itemId: formData.get("itemId"),
        status: formData.get("status"),
        memo: formData.get("memo"),
      });
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast("Cafe24 품주 상태를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 품주 상태 저장에 실패했습니다.", "error");
    }
    return true;
  }

  if (form.matches("[data-admin-cafe24-item-manual-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/manual-input", {
        itemId: formData.get("itemId"),
        supplierId: formData.get("supplierId"),
        supplierServiceId: formData.get("supplierServiceId"),
        targetValue: formData.get("targetValue"),
        orderedCount: formData.get("orderedCount"),
        requestMemo: formData.get("requestMemo"),
      });
      if (result.item?.id && result.preflight) {
        state.adminCafe24Preflights = {
          ...(state.adminCafe24Preflights || {}),
          [result.item.id]: result.preflight,
        };
      }
      await refreshAdminData({ preserveDraft: true });
      await refreshCafe24OrderItems({ force: true });
      showToast(cafe24ManualInputToastMessage(result));
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 수동 보정 저장에 실패했습니다.", "error");
    }
    return true;
  }

  return false;
}
