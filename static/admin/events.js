import { handleCafe24AdminChange, handleCafe24AdminClick, handleCafe24AdminSubmit } from "./cafe24.js";

function markHandled(event) {
  event.__instamartHandled = true;
}

export function registerAdminEvents(ctx) {
  const { document: doc = document } = ctx;
  doc.addEventListener("click", async (event) => {
    if (event.__instamartHandled) return;
    const handled = await handleAdminClick(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("input", (event) => {
    if (event.__instamartHandled) return;
    const handled = handleAdminInput(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("change", async (event) => {
    if (event.__instamartHandled) return;
    const handled = await handleAdminChange(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("mousemove", (event) => handleAdminMouseMove(event, ctx));
  doc.addEventListener("mouseleave", (event) => handleAdminMouseLeave(event, ctx), true);
  doc.addEventListener("submit", async (event) => {
    if (event.__instamartHandled) return;
    const handled = await handleAdminSubmit(event, ctx);
    if (handled) markHandled(event);
  });
}

async function handleAdminClick(event, ctx) {
  const { adminSectionPath, apiPost, applySupplierRecommendationToProductDraft, blankCategoryDraft, blankCustomerDraft, blankFaqDraft, blankNoticeDraft, blankPopupDraft, blankProductDraft, blankSiteSettingsDraft, blankSupplierDraft, categoryToDraft, customerToDraft, ensureAdminCustomerDetail, ensureAdminSupplierServices, ensureSelectedMkt24ProductSetting, faqToDraft, getAdminCategories, getAdminFaqs, getAdminNotices, getAdminPlatformGroups, getAdminProducts, getAdminSuppliers, getSelectedAdminCustomer, getSelectedAdminHomeBanner, getSelectedAdminPlatformSection, getSelectedAdminProduct, getSelectedAdminSupplierService, getSelectedManageProduct, homeBannerToDraft, navigate, noticeToDraft, platformSectionToDraft, productToDraft, refreshAdminData, refreshCoreData, renderRoute, resetAdminState, setAdminAnalyticsExclusion, showToast, state, supplierToDraft, updateAdminHomeBannerPreview, updateAdminPlatformSectionPreview, updateAdminPopupPreview, updateAdminSiteSettingsPreview } = ctx;
  const targetElement = event.target instanceof Element ? event.target : event.target?.parentElement;
  const closest = (selector) => targetElement?.closest(selector);
  if (await handleCafe24AdminClick(closest)) {
    return true;
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
    return true;
  }

  const selectHomeBannerButton = closest("[data-admin-home-banner-select]");
  if (selectHomeBannerButton) {
    state.ui.adminSelectedHomeBannerId = selectHomeBannerButton.getAttribute("data-admin-home-banner-select") || "";
    state.adminHomeBannerDraft = homeBannerToDraft(getSelectedAdminHomeBanner());
    renderRoute();
    return true;
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
    return true;
  }

  const selectPlatformSectionButton = closest("[data-admin-platform-section-select]");
  if (selectPlatformSectionButton) {
    state.ui.adminSelectedPlatformSectionId = selectPlatformSectionButton.getAttribute("data-admin-platform-section-select") || "";
    state.adminPlatformSectionDraft = platformSectionToDraft(getSelectedAdminPlatformSection());
    renderRoute();
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
  }

  const adminSectionButton = closest("[data-admin-scroll-section]");
  if (adminSectionButton) {
    const sectionId = adminSectionButton.getAttribute("data-admin-scroll-section") || "overview";
    navigate(adminSectionPath(sectionId));
    return true;
  }

  const analyticsTabButton = closest("[data-admin-analytics-tab]");
  if (analyticsTabButton) {
    state.ui.adminAnalyticsTab = analyticsTabButton.getAttribute("data-admin-analytics-tab") || "dashboard";
    renderRoute();
    return true;
  }

  const analyticsRangeButton = closest("[data-admin-analytics-range]");
  if (analyticsRangeButton) {
    state.ui.adminAnalyticsRange = analyticsRangeButton.getAttribute("data-admin-analytics-range") || "30d";
    renderRoute();
    return true;
  }

  const customerFilterButton = closest("[data-admin-customer-filter]");
  if (customerFilterButton) {
    state.ui.adminCustomerFilter = customerFilterButton.getAttribute("data-admin-customer-filter") || "all";
    renderRoute();
    return true;
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
    return true;
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
    return true;
  }

  const newSupplierButton = closest("[data-admin-supplier-new]");
  if (newSupplierButton) {
    state.ui.adminSupplierMode = "new";
    state.ui.adminSelectedSupplierId = "";
    state.ui.adminSelectedSupplierServiceId = "";
    state.adminSupplierDraft = blankSupplierDraft();
    state.adminConnectionResult = null;
    renderRoute();
    return true;
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
    return true;
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
    return true;
  }

  const syncServicesButton = closest("[data-admin-sync-services]");
  if (syncServicesButton) {
    const supplierId = state.ui.adminSelectedSupplierId;
    if (!supplierId) {
      showToast("먼저 저장된 공급사를 선택해 주세요.", "error");
      return true;
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
    return true;
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
    return true;
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
    return true;
  }

  const applyServiceRecommendationButton = closest("[data-apply-service-recommendation]");
  if (applyServiceRecommendationButton) {
    const service = getSelectedAdminSupplierService();
    const product = getSelectedAdminProduct() || getSelectedManageProduct() || null;
    if (!service?.requestGuide?.formRecommendation) {
      showToast("적용할 추천 양식이 없습니다.", "error");
      return true;
    }
    applySupplierRecommendationToProductDraft(service, { product });
    showToast(product ? "선택한 상품 폼에 추천 양식을 반영했습니다." : "새 상품 제작 폼에 추천 양식을 반영했습니다.");
    renderRoute();
    return true;
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
    return true;
  }

  const deleteMappingButton = closest("[data-admin-delete-mapping]");
  if (deleteMappingButton) {
    const mappingId = deleteMappingButton.getAttribute("data-admin-delete-mapping");
    if (!mappingId) return true;
    try {
      await apiPost("/api/admin/mappings/delete", { mappingId });
      await refreshAdminData({ preserveDraft: true });
      showToast("상품 매핑을 해제했습니다.");
      renderRoute();
    } catch (error) {
      showToast(error.message || "상품 매핑 해제에 실패했습니다.", "error");
    }
    return true;
  }

  const newCustomerButton = closest("[data-admin-customer-new]");
  if (newCustomerButton) {
    state.ui.adminCustomerMode = "new";
    state.ui.adminSelectedCustomerId = "";
    state.adminCustomerDraft = blankCustomerDraft();
    renderRoute();
    return true;
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
    return true;
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
    return true;
  }

  const newCategoryButton = closest("[data-admin-category-new]");
  if (newCategoryButton) {
    state.ui.adminCategoryMode = "new";
    state.adminCategoryDraft = blankCategoryDraft(getAdminPlatformGroups()[0]?.id || "");
    renderRoute();
    return true;
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
    return true;
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
    return true;
  }

  const newProductButton = closest("[data-admin-product-new]");
  if (newProductButton) {
    state.ui.adminProductMode = "new";
    state.ui.adminSelectedManageProductId = "";
    state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    renderRoute();
    return true;
  }

  const selectManageProductButton = closest("[data-admin-manage-product-select]");
  if (selectManageProductButton) {
    const productId = selectManageProductButton.getAttribute("data-admin-manage-product-select") || "";
    const product = getAdminProducts().find((item) => item.id === productId) || null;
    state.ui.adminProductMode = "edit";
    state.ui.adminSelectedManageProductId = productId;
    state.adminProductDraft = productToDraft(product);
    renderRoute();
    return true;
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
    return true;
  }

  const adminOrderFilterButton = closest("[data-admin-order-filter]");
  if (adminOrderFilterButton) {
    state.ui.adminOrderFilter = adminOrderFilterButton.getAttribute("data-admin-order-filter") || "all";
    renderRoute();
    return true;
  }

  const adminChargeFilterButton = closest("[data-admin-charge-filter]");
  if (adminChargeFilterButton) {
    state.ui.adminChargeFilter = adminChargeFilterButton.getAttribute("data-admin-charge-filter") || "all";
    renderRoute();
    return true;
  }

  const adminContentTabButton = closest("[data-admin-content-tab]");
  if (adminContentTabButton) {
    state.ui.adminContentTab = adminContentTabButton.getAttribute("data-admin-content-tab") || "notices";
    renderRoute();
    return true;
  }

  const newNoticeButton = closest("[data-admin-notice-new]");
  if (newNoticeButton) {
    state.ui.adminNoticeMode = "new";
    state.ui.adminSelectedNoticeId = "";
    state.adminNoticeDraft = blankNoticeDraft();
    renderRoute();
    return true;
  }

  const selectNoticeButton = closest("[data-admin-notice-select]");
  if (selectNoticeButton) {
    const noticeId = selectNoticeButton.getAttribute("data-admin-notice-select") || "";
    state.ui.adminNoticeMode = "edit";
    state.ui.adminSelectedNoticeId = noticeId;
    state.adminNoticeDraft = noticeToDraft(getAdminNotices().find((notice) => notice.id === noticeId) || null);
    renderRoute();
    return true;
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
    return true;
  }

  const newFaqButton = closest("[data-admin-faq-new]");
  if (newFaqButton) {
    state.ui.adminFaqMode = "new";
    state.ui.adminSelectedFaqId = "";
    state.adminFaqDraft = blankFaqDraft();
    renderRoute();
    return true;
  }

  const selectFaqButton = closest("[data-admin-faq-select]");
  if (selectFaqButton) {
    const faqId = selectFaqButton.getAttribute("data-admin-faq-select") || "";
    state.ui.adminFaqMode = "edit";
    state.ui.adminSelectedFaqId = faqId;
    state.adminFaqDraft = faqToDraft(getAdminFaqs().find((faq) => faq.id === faqId) || null);
    renderRoute();
    return true;
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
    return true;
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
    return true;
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
    return true;
  }


  return false;
}

function handleAdminInput(event, ctx) {
  const { blankCategoryDraft, blankCustomerDraft, blankFaqDraft, blankNoticeDraft, blankPopupDraft, blankProductDraft, blankSiteSettingsDraft, blankSupplierDraft, getAdminPlatformGroups, getSelectedAdminHomeBanner, getSelectedAdminPlatformSection, homeBannerToDraft, platformSectionToDraft, renderRoute, state, updateAdminHomeBannerPreview, updateAdminPlatformSectionPreview, updateAdminPopupPreview, updateAdminSiteSettingsPreview } = ctx;
  const target = event.target;
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
      if (target.value === "fasttraffic" && !String(state.adminSupplierDraft.apiUrl || "").trim()) {
        state.adminSupplierDraft.apiUrl = "https://fastraffic.co.kr/nblog_api.php";
      }
      renderRoute();
    }
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
  }

  if (target.matches("[data-admin-customer-field]")) {
    const field = target.getAttribute("data-admin-customer-field");
    if (!state.adminCustomerDraft) {
      state.adminCustomerDraft = blankCustomerDraft();
    }
    state.adminCustomerDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return true;
  }

  if (target.matches("[data-admin-notice-field]")) {
    const field = target.getAttribute("data-admin-notice-field");
    if (!state.adminNoticeDraft) {
      state.adminNoticeDraft = blankNoticeDraft();
    }
    state.adminNoticeDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return true;
  }

  if (target.matches("[data-admin-faq-field]")) {
    const field = target.getAttribute("data-admin-faq-field");
    if (!state.adminFaqDraft) {
      state.adminFaqDraft = blankFaqDraft();
    }
    state.adminFaqDraft[field] = field === "sortOrder" ? Number(target.value || 0) : target.value;
    return true;
  }

  if (target.matches("[data-admin-category-field]")) {
    const field = target.getAttribute("data-admin-category-field");
    if (!state.adminCategoryDraft) {
      state.adminCategoryDraft = blankCategoryDraft(getAdminPlatformGroups()[0]?.id || "");
    }
    state.adminCategoryDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return true;
  }

  if (target.matches("[data-admin-product-field]")) {
    const field = target.getAttribute("data-admin-product-field");
    if (!state.adminProductDraft) {
      state.adminProductDraft = blankProductDraft(state.ui.adminSelectedCategoryId);
    }
    state.adminProductDraft[field] = target.type === "checkbox" ? target.checked : target.value;
    return true;
  }


  return false;
}

async function handleAdminChange(event, ctx) {
  const { applyAdminSiteSettingsImage, blankProductDraft, blankPopupDraft, ensureSelectedMkt24ProductSetting, getSelectedAdminHomeBanner, getSelectedAdminPlatformSection, homeBannerToDraft, platformSectionToDraft, readFileAsDataUrl, renderRoute, showToast, state, updateAdminHomeBannerPreview, updateAdminPlatformSectionPreview, updateAdminPopupPreview } = ctx;
  const target = event.target;
  if (await handleCafe24AdminChange(target)) {
    return true;
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
    return true;
  }
  if (target.matches("[data-admin-service-select-box]")) {
    state.ui.adminSelectedSupplierServiceId = target.value || "";
    ensureSelectedMkt24ProductSetting()
      .catch((error) => showToast(error.message || "MKT24 상품 상세를 불러오지 못했습니다.", "error"))
      .finally(() => renderRoute());
    return true;
  }
  if (target.matches("[data-admin-mkt24-setting-field]")) {
    renderRoute();
    return true;
  }
  if (target.matches("[data-admin-popup-image-upload]")) {
    const file = target.files && target.files[0];
    if (!file) return true;
    if (!file.type.startsWith("image/")) {
      showToast("이미지 파일만 업로드할 수 있습니다.", "error");
      target.value = "";
      return true;
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast("팝업 이미지는 5MB 이하로 업로드해 주세요.", "error");
      target.value = "";
      return true;
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
    return true;
  }

  if (target.matches("[data-admin-home-banner-image-upload]")) {
    const file = target.files && target.files[0];
    if (!file) return true;
    if (!file.type.startsWith("image/")) {
      showToast("이미지 파일만 업로드할 수 있습니다.", "error");
      target.value = "";
      return true;
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast("홈 배너 이미지는 5MB 이하로 업로드해 주세요.", "error");
      target.value = "";
      return true;
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
    return true;
  }

  if (target.matches("[data-admin-platform-section-image-upload]")) {
    const file = target.files && target.files[0];
    if (!file) return true;
    if (!file.type.startsWith("image/")) {
      showToast("이미지 파일만 업로드할 수 있습니다.", "error");
      target.value = "";
      return true;
    }
    if (file.size > 2 * 1024 * 1024) {
      showToast("플랫폼 로고 이미지는 2MB 이하로 업로드해 주세요.", "error");
      target.value = "";
      return true;
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
    return true;
  }

  const siteImageType = target.getAttribute("data-admin-site-settings-image-upload");
  if (!siteImageType) return true;
  const file = target.files && target.files[0];
  if (!file) return true;
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

  return false;
}

function handleAdminMouseMove(event, ctx) {
  const { hideAnalyticsChartTooltip, updateAnalyticsChartTooltip } = ctx;
  const target = event.target instanceof Element ? event.target : null;
  const svg = target?.closest(".admin-analytics-chart__svg");
  if (!svg) {
    document.querySelectorAll(".admin-analytics-chart").forEach((chart) => hideAnalyticsChartTooltip(chart));
    return;
  }
  updateAnalyticsChartTooltip(svg.closest(".admin-analytics-chart"), event.clientX);
}

function handleAdminMouseLeave(event, ctx) {
  const { hideAnalyticsChartTooltip } = ctx;
  const target = event.target instanceof Element ? event.target : null;
  const svg = target?.closest(".admin-analytics-chart__svg");
  if (!svg) return;
  hideAnalyticsChartTooltip(svg.closest(".admin-analytics-chart"));
}

async function handleAdminSubmit(event, ctx) {
  const { apiPost, blankCategoryDraft, blankCustomerDraft, blankFaqDraft, blankNoticeDraft, blankPopupDraft, blankProductDraft, blankSiteSettingsDraft, blankSupplierDraft, categoryToDraft, collectMkt24ProductSettingPayload, customerToDraft, ensureAdminCustomerDetail, ensureAdminSupplierServices, faqToDraft, getAdminPlatformGroups, getSelectedAdminHomeBanner, getSelectedAdminPlatformSection, getSelectedAdminProduct, getSelectedAdminSupplier, homeBannerToDraft, mkt24ProductSettingKey, noticeToDraft, platformSectionToDraft, popupToDraft, productToDraft, refreshAdminData, refreshCoreData, renderRoute, resetAdminState, setAdminAnalyticsExclusion, showToast, siteSettingsToDraft, state, supplierToDraft } = ctx;
  const form = event.target;

  if (form.matches("[data-admin-login-form]")) {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await apiPost("/api/admin/login", {
        username: formData.get("adminUsername") || formData.get("username"),
        password: formData.get("adminAccessCode") || formData.get("password"),
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
    return true;
  }

  if (await handleCafe24AdminSubmit(form, event)) {
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
    return true;
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
      return true;
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
    return true;
  }


  return false;
}
