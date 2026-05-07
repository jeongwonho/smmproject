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
  if (!target.matches("[data-admin-cafe24-supplier-select]")) return false;
  const supplierId = target.value || "";
  state.ui = state.ui || {};
  state.ui.adminCafe24SelectedSupplierId = supplierId;
  try {
    const data = await loadCafe24SupplierServices(supplierId);
    const serviceSelect = document.querySelector("[data-admin-cafe24-service-select]");
    if (serviceSelect && data?.services) {
      serviceSelect.innerHTML = [
        `<option value="">공급사 서비스를 선택하세요</option>`,
        ...data.services.map((service) => (
          `<option value="${escapeOptionText(service.id)}">${escapeOptionText(service.name)} · ${escapeOptionText(service.externalServiceId || "")} · ${escapeOptionText(service.minAmount || "-")}~${escapeOptionText(service.maxAmount || "-")}</option>`
        )),
      ].join("");
    }
    showToast("공급사 서비스 목록을 불러왔습니다.");
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
    if (state.ui.adminCafe24Tab === "queue" || state.ui.adminCafe24Tab === "monitor") {
      await refreshCafe24OrderItems({ force: true });
    }
    renderRoute();
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
        fieldMappingJson: formData.get("fieldMappingJson"),
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

  return false;
}
