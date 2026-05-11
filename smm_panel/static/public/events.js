const PUBLIC_EVENT_HANDLED = "__instamartPublicHandled";

function markHandled(event) {
  event.__instamartHandled = true;
  event[PUBLIC_EVENT_HANDLED] = true;
}

export function registerPublicEvents(ctx) {
  const { document: doc = document } = ctx;
  doc.addEventListener("click", async (event) => {
    if (event.__instamartHandled) return;
    const handled = await handlePublicClick(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("input", (event) => {
    if (event.__instamartHandled) return;
    const handled = handlePublicInput(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("change", (event) => {
    if (event.__instamartHandled) return;
    const handled = handlePublicChange(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("submit", async (event) => {
    if (event.__instamartHandled) return;
    const handled = await handlePublicSubmit(event, ctx);
    if (handled) markHandled(event);
  });
  doc.addEventListener("keydown", (event) => {
    if (event.__instamartHandled) return;
    const handled = handlePublicKeydown(event, ctx);
    if (handled) markHandled(event);
  });
}

async function handlePublicClick(event, ctx) {
  const {
    apiPost, blankChargeDraft, calculateSummary, chargeAmountSummary, chargeMethodConfig, clearPublicSessionState,
    closeChargeDetail, closeLoginModal, closePopupForSession, createOrderIdempotencyKey, currentSignupState,
    dismissPopupToday, ensureChargeDraft, ensureSelection, formatMoney, getOrderValidationState, getPreviewSource,
    getRoute, getSelectedProduct, isLoggedIn, navigate, openChargeDetail, openLoginModal, parseCurrencyInput,
    postAuthRedirectPath, refreshCoreData, renderRoute, resetSignupFlow, scheduleLinkPreview, setHomeBannerIndex,
    showToast, state, updateLiveSummary, updateSignupPasswordFeedback,
  } = ctx;
  const targetElement = event.target instanceof Element ? event.target : event.target?.parentElement;
  const closest = (selector) => targetElement?.closest(selector);
  const authTabButton = closest("[data-auth-tab]");
  if (authTabButton) {
    state.ui.authTab = authTabButton.getAttribute("data-auth-tab") || "login";
    renderRoute();
    return true;
  }

  const oauthProviderButton = closest("[data-oauth-provider]");
  if (oauthProviderButton) {
    const provider = oauthProviderButton.getAttribute("data-oauth-provider") || "";
    const providerConfig = (state.bootstrap?.authConfig?.oauthProviders || []).find((item) => item.provider === provider);
    if (!providerConfig?.enabled) {
      showToast("현재 해당 간편 로그인은 사용할 수 없습니다. 이메일로 로그인해 주세요.", "error");
      return true;
    }
    navigate(providerConfig.startPath);
    return true;
  }

  const publicLoginOpenButton = closest("[data-public-login-open]");
  if (publicLoginOpenButton) {
    openLoginModal(window.location.pathname || "/");
    return true;
  }

  const publicLoginCloseButton = closest("[data-public-login-close]");
  if (publicLoginCloseButton) {
    closeLoginModal();
    renderRoute();
    return true;
  }

  const passwordToggleButton = closest("[data-password-toggle]");
  if (passwordToggleButton) {
    const shell = passwordToggleButton.closest(".field-shell--password");
    const input = shell?.querySelector("input");
    if (input instanceof HTMLInputElement) {
      input.type = input.type === "password" ? "text" : "password";
      passwordToggleButton.textContent = input.type === "password" ? "보기" : "숨기기";
    }
    return true;
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
    return true;
  }

  const signupResendButton = closest("[data-public-signup-resend]");
  if (signupResendButton) {
    const signup = currentSignupState();
    if (!signup.email) {
      showToast("먼저 이메일을 입력해 주세요.", "error");
      return true;
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
    return true;
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
    return true;
  }

  const homeFooterToggleButton = closest("[data-home-footer-toggle]");
  if (homeFooterToggleButton) {
    state.ui.homeFooterExpanded = !state.ui.homeFooterExpanded;
    renderRoute();
    return true;
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
    return true;
  }

  const homeSearchSubmitButton = closest("[data-home-search-submit]");
  if (homeSearchSubmitButton) {
    navigate("/products");
    return true;
  }

  const popupDismissTodayButton = closest("[data-popup-dismiss-today]");
  if (popupDismissTodayButton) {
    const popup = state.bootstrap?.popup;
    dismissPopupToday(popup);
    closePopupForSession(popup);
    renderRoute();
    return true;
  }

  const popupCloseButton = closest("[data-popup-close]");
  if (popupCloseButton) {
    closePopupForSession(state.bootstrap?.popup);
    renderRoute();
    return true;
  }

  const platformButton = closest("[data-platform-select]");
  if (platformButton) {
    state.ui.activePlatform = platformButton.getAttribute("data-platform-select");
    renderRoute();
    return true;
  }

  const bannerDot = closest("[data-banner-index]");
  if (bannerDot) {
    setHomeBannerIndex(Number(bannerDot.getAttribute("data-banner-index")) || 0);
    return true;
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
    return true;
  }

  const filterButton = closest("[data-order-filter]");
  if (filterButton) {
    state.ui.orderFilter = filterButton.getAttribute("data-order-filter");
    renderRoute();
    return true;
  }

  const chargeTabButton = closest("[data-charge-tab]");
  if (chargeTabButton) {
    state.ui.chargeTab = chargeTabButton.getAttribute("data-charge-tab") || "create";
    closeChargeDetail();
    renderRoute();
    return true;
  }

  const chargeHistoryModeButton = closest("[data-charge-history-mode]");
  if (chargeHistoryModeButton) {
    state.ui.chargeHistoryMode = chargeHistoryModeButton.getAttribute("data-charge-history-mode") || "chargeOrders";
    closeChargeDetail();
    renderRoute();
    return true;
  }

  const chargeQuickAmountButton = closest("[data-charge-quick-amount]");
  if (chargeQuickAmountButton) {
    const draft = ensureChargeDraft();
    const delta = Number(chargeQuickAmountButton.getAttribute("data-charge-quick-amount") || 0);
    const nextAmount = parseCurrencyInput(draft.amountInput) + delta;
    draft.amountInput = String(nextAmount);
    renderRoute();
    return true;
  }

  const chargePaymentChannelButton = closest("[data-charge-payment-channel]");
  if (chargePaymentChannelButton) {
    const nextChannel = chargePaymentChannelButton.getAttribute("data-charge-payment-channel") || "card";
    const method = chargeMethodConfig(nextChannel);
    if (method && !method.enabled) {
      showToast("현재 선택할 수 없는 결제수단입니다. 다른 결제수단을 선택해 주세요.", "error");
      return true;
    }
    const draft = ensureChargeDraft();
    draft.paymentChannel = nextChannel;
    renderRoute();
    return true;
  }

  const chargeSubmitButton = closest("[data-charge-submit]");
  if (chargeSubmitButton) {
    const form = document.querySelector("[data-charge-create-form]");
    if (form instanceof HTMLFormElement) {
      form.requestSubmit();
    }
    return true;
  }

  const chargeDetailButton = closest("[data-charge-detail-open]");
  if (chargeDetailButton) {
    openChargeDetail(
      chargeDetailButton.getAttribute("data-charge-detail-kind") || "chargeOrders",
      chargeDetailButton.getAttribute("data-charge-detail-open") || "",
    );
    renderRoute();
    return true;
  }

  const chargeDetailCloseButton = closest("[data-charge-detail-close]");
  if (chargeDetailCloseButton) {
    closeChargeDetail();
    renderRoute();
    return true;
  }

  return false;
}

function handlePublicInput(event, ctx) {
  const { closeChargeDetail, ensureChargeDraft, ensureSelection, getPreviewSource, getRoute, getSelectedProduct, parseCurrencyInput, renderRoute, scheduleLinkPreview, state, updateLiveSummary, updateSignupPasswordFeedback, currentSignupState } = ctx;
  const target = event.target;
  if (target.matches("[data-signup-email-input]")) {
    currentSignupState().email = target.value;
    return true;
  }
  if (target.matches("[data-signup-name-input], [data-signup-password-input]")) {
    updateSignupPasswordFeedback(target.closest("[data-public-signup-complete-form]"));
    return true;
  }
  if (target.matches("[data-home-search-input]")) {
    state.ui.search = target.value;
    return true;
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
    return true;
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
    return true;
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
    return true;
  }

  if (target.matches("[data-charge-receipt-field]")) {
    const draft = ensureChargeDraft();
    const field = target.getAttribute("data-charge-receipt-field") || "";
    const nextValue = target.type === "checkbox" ? target.checked : target.value;
    draft.receiptPayload = { ...(draft.receiptPayload || {}), [field]: nextValue };
    if (target.type === "radio" || target.tagName === "SELECT") {
      renderRoute();
    }
    return true;
  }

  if (target.matches("[data-charge-filter]")) {
    const field = target.getAttribute("data-charge-filter") || "";
    if (field === "status") state.ui.chargeStatusFilter = target.value || "all";
    if (field === "method") state.ui.chargeMethodFilter = target.value || "all";
    if (field === "period") state.ui.chargePeriodFilter = target.value || "all";
    closeChargeDetail();
    renderRoute();
    return true;
  }

  if (target.matches("[data-order-field]")) {
    const route = getRoute();
    if (route.name !== "detail") return true;
    const detail = state.categoryCache[route.id];
    if (!detail) return true;
    const selection = ensureSelection(detail);
    selection.fields[target.name] = target.value;
    updateLiveSummary();
    const previewSource = getPreviewSource(detail, getSelectedProduct(detail));
    if (previewSource && previewSource.key === target.name) {
      scheduleLinkPreview(detail);
    }
  }

  return false;
}

function handlePublicChange(event, ctx) {
  const { closeChargeDetail, renderRoute, state } = ctx;
  const target = event.target;
  if (target.matches("[data-charge-filter]")) {
    const field = target.getAttribute("data-charge-filter") || "";
    if (field === "status") state.ui.chargeStatusFilter = target.value || "all";
    if (field === "method") state.ui.chargeMethodFilter = target.value || "all";
    if (field === "period") state.ui.chargePeriodFilter = target.value || "all";
    closeChargeDetail();
    renderRoute();
    return true;
  }

  return false;
}

async function handlePublicSubmit(event, ctx) {
  const { apiPost, blankChargeDraft, calculateSummary, chargeAmountSummary, chargeMethodConfig, closeLoginModal, createOrderIdempotencyKey, currentSignupState, ensureChargeDraft, ensureSelection, formatMoney, getOrderValidationState, getRoute, isLoggedIn, navigate, openChargeDetail, postAuthRedirectPath, refreshCoreData, renderRoute, resetSignupFlow, showToast, state } = ctx;
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
        return true;
      }
      renderRoute();
      showToast("로그인되었습니다.");
    } catch (error) {
      showToast(error.message || "로그인에 실패했습니다.", "error");
    }
    return true;
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
    return true;
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
    return true;
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
        return true;
      }
      renderRoute();
      showToast("회원가입이 완료되었습니다.");
    } catch (error) {
      showToast(error.message || "회원가입에 실패했습니다.", "error");
    }
    return true;
  }
  if (form.matches("[data-charge-create-form]")) {
    event.preventDefault();
    const draft = ensureChargeDraft();
    const chargeConfig = state.bootstrap?.chargeConfig || {};
    const amountSummary = chargeAmountSummary(draft.amountInput);
    const method = chargeMethodConfig(draft.paymentChannel);
    if (!draft.agreementChecked) {
      showToast("충전 유의사항과 환불 안내에 동의해 주세요.", "error");
      return true;
    }
    if (amountSummary.amount < Number(chargeConfig.minimumAmount || 5000)) {
      showToast(`최소 충전 금액은 ${formatMoney(chargeConfig.minimumAmount || 5000)}입니다.`, "error");
      return true;
    }
    if (!method?.enabled) {
      showToast("현재 선택할 수 없는 결제수단입니다.", "error");
      return true;
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
        return true;
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
    return true;
  }
  if (!form.matches("[data-order-form]")) return false;
  event.preventDefault();

  const route = getRoute();
  if (route.name !== "detail") return true;
  if (!isLoggedIn()) {
    state.ui.loginRedirect = window.location.pathname || "/products";
    navigate("/auth");
    showToast("주문하려면 먼저 로그인해 주세요.", "error");
    return true;
  }
  const detail = state.categoryCache[route.id];
  if (!detail) return true;

  const summary = calculateSummary(detail);
  if (!summary) return true;
  const selection = ensureSelection(detail);
  if (!selection) return true;
  const formData = new FormData(form);
  const fields = Object.fromEntries(formData.entries());
  selection.fields = { ...selection.fields, ...fields };
  if (!selection.orderIdempotencyKey) {
    selection.orderIdempotencyKey = createOrderIdempotencyKey();
  }
  const validation = getOrderValidationState(detail, summary.product);
  if (validation.blocked) {
    showToast(validation.reason || "주문 정보를 다시 확인해 주세요.", "error");
    return true;
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

  return false;
}

function handlePublicKeydown(event, ctx) {
  const { navigate } = ctx;
  const target = event.target;

  if (target.matches("[data-home-search-input]") && event.key === "Enter") {
    event.preventDefault();
    navigate("/products");
  }

  return false;
}
