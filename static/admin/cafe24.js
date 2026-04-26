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

export async function handleCafe24AdminClick(closest) {
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
        submitReady: true,
        startDate: formData.get("pollStartDate"),
        endDate: formData.get("pollEndDate"),
      });
      await refreshAdminData({ preserveDraft: true });
      showToast(`Cafe24 수집 완료: ${result.processed || 0}개 처리, ${result.submitted || 0}개 전송`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 주문 수집에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24DeleteMappingButton = closest("[data-admin-cafe24-delete-mapping]");
  if (cafe24DeleteMappingButton) {
    const mappingId = cafe24DeleteMappingButton.getAttribute("data-admin-cafe24-delete-mapping") || "";
    try {
      await apiPost("/api/admin/cafe24/mappings/delete", { mappingId });
      await refreshAdminData({ preserveDraft: true });
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
      showToast(`Cafe24 품주 재처리: ${result.result?.status || "처리됨"}`);
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 품주 재처리에 실패했습니다.", "error");
    }
    return true;
  }

  const cafe24ResyncButton = closest("[data-admin-cafe24-resync-item]");
  if (cafe24ResyncButton) {
    const itemId = cafe24ResyncButton.getAttribute("data-admin-cafe24-resync-item") || "";
    try {
      const result = await apiPost("/api/admin/cafe24/order-items/resync", { itemId });
      await refreshAdminData({ preserveDraft: true });
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
        supplierProductUuid: formData.get("supplierProductUuid"),
        supplierProductCode: formData.get("supplierProductCode"),
        fieldMappingJson: formData.get("fieldMappingJson"),
        enabled: true,
      });
      await refreshAdminData({ preserveDraft: true });
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
      showToast("Cafe24 품주 상태를 저장했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "Cafe24 품주 상태 저장에 실패했습니다.", "error");
    }
    return true;
  }

  return false;
}
