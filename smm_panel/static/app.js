const app = document.querySelector("#app");
const toast = document.querySelector("#toast");

const state = {
  bootstrap: null,
  catalog: [],
  categoryCache: {},
  orders: [],
  orderCounts: { all: 0, queued: 0, in_progress: 0, completed: 0 },
  transactions: [],
  adminBootstrap: null,
  adminSupplierServices: {},
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
    adminSupplierMode: "edit",
    adminSelectedSupplierId: "",
    adminSelectedProductId: "",
    adminSelectedSupplierServiceId: "",
    adminServiceSearch: "",
    adminCustomerMode: "edit",
    adminSelectedCustomerId: "",
    adminCategoryMode: "edit",
    adminSelectedCategoryId: "",
    adminProductMode: "edit",
    adminSelectedManageProductId: "",
    adminOrderFilter: "all",
  },
};

let bannerIntervalId = null;
let previewSequence = 0;
const previewTimers = {};

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

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatMoney(value) {
  return `${Number(value || 0).toLocaleString("ko-KR")}원`;
}

function blankSupplierDraft() {
  return {
    id: "",
    name: "",
    apiUrl: "",
    apiKey: "",
    notes: "",
    isActive: true,
  };
}

function supplierToDraft(supplier) {
  if (!supplier) return blankSupplierDraft();
  return {
    id: supplier.id || "",
    name: supplier.name || "",
    apiUrl: supplier.apiUrl || "",
    apiKey: supplier.apiKey || "",
    notes: supplier.notes || "",
    isActive: Boolean(supplier.isActive),
  };
}

function blankCustomerDraft() {
  return {
    id: "",
    name: "",
    email: "",
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

function getSelectedAdminSupplier() {
  return getAdminSuppliers().find((supplier) => supplier.id === state.ui.adminSelectedSupplierId) || null;
}

function getSelectedAdminProduct() {
  return getAdminProducts().find((product) => product.id === state.ui.adminSelectedProductId) || null;
}

function getSelectedAdminCustomer() {
  return getAdminCustomers().find((customer) => customer.id === state.ui.adminSelectedCustomerId) || null;
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
      const matchingCustomer = customers.find((customer) => customer.id === state.adminCustomerDraft.id);
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

async function refreshAdminData({ preserveDraft = true } = {}) {
  const data = await apiGet("/api/admin/bootstrap");
  state.adminBootstrap = data;
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

function syncShellMode(route) {
  const deviceShell = document.querySelector(".device-shell");
  const isAdmin = route.name === "admin";
  if (deviceShell) {
    deviceShell.classList.toggle("is-admin", isAdmin);
  }
  document.body.classList.toggle("is-admin-route", isAdmin);
}

function apiUrl(path) {
  return path;
}

async function apiGet(path) {
  const response = await fetch(apiUrl(path), { headers: { Accept: "application/json" } });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "요청 처리 중 오류가 발생했습니다.");
  }
  return data;
}

async function apiPost(path, payload) {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "요청 처리 중 오류가 발생했습니다.");
  }
  return data;
}

function getRoute() {
  const pathname = window.location.pathname.replace(/\/+$/, "") || "/";
  if (pathname === "/") return { name: "home" };
  if (pathname === "/admin") return { name: "admin" };
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
  const [bootstrapData, ordersData, transactionData] = await Promise.all([
    apiGet("/api/bootstrap"),
    apiGet("/api/orders"),
    apiGet("/api/transactions"),
  ]);
  state.bootstrap = bootstrapData;
  state.orders = ordersData.orders;
  state.orderCounts = ordersData.counts;
  state.transactions = transactionData.transactions;
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

function getPreviewSource(product) {
  if (!product) return null;
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
  const previewSource = getPreviewSource(product);

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
      <div class="preview-card is-valid">
        <div class="preview-card__image-wrap">
          <img class="preview-card__image" src="${escapeHtml(preview.imageUrl)}" alt="링크 썸네일 미리보기" />
          <span class="preview-card__badge">확인됨</span>
        </div>
        <div class="preview-card__body">
          <span class="preview-card__eyebrow">${escapeHtml(preview.sourceLabel || previewSource.label)}</span>
          <strong>${escapeHtml(preview.title || "링크 미리보기")}</strong>
          <p>${escapeHtml(preview.displayInput || preview.resolvedUrl)}</p>
          ${
            preview.resolvedUrl
              ? `<a class="preview-card__link" href="${escapeHtml(preview.resolvedUrl)}" target="_blank" rel="noreferrer">원본 열기</a>`
              : ""
          }
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
}

async function requestLinkPreview(detail, { immediate = false } = {}) {
  const summary = calculateSummary(detail);
  if (!summary) return;
  const previewSource = getPreviewSource(summary.product);
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

function renderCustomerAdminSection() {
  const customers = getAdminCustomers();
  const selectedCustomer = getSelectedAdminCustomer();
  const draft = state.adminCustomerDraft || blankCustomerDraft();

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
          <div class="admin-customer-list">
            ${customers
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
                    <p>${escapeHtml(customer.email)}</p>
                    <div class="admin-supplier-card__meta">
                      <span>${escapeHtml(customer.role)}</span>
                      <span>${escapeHtml(customer.tier)}</span>
                      <span>주문 ${escapeHtml(String(customer.orderCount || 0))}</span>
                      <span>잔액 ${escapeHtml(customer.balanceLabel)}</span>
                    </div>
                    <div class="admin-supplier-card__meta">
                      <span>누적 ${escapeHtml(customer.totalSpentLabel || "0원")}</span>
                      <span>${escapeHtml(customer.lastOrderLabel || "주문 이력 없음")}</span>
                    </div>
                  </button>
                `
              )
              .join("")}
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
                      ["package", "패키지형"],
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
  const visibleOrders = activeFilter === "all" ? adminOrders : adminOrders.filter((order) => order.status === activeFilter);

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

      <div class="admin-order-list">
        ${visibleOrders
          .map((order) => {
            const status = statusMap[order.status] || statusMap.queued;
            return `
              <article class="admin-order-card">
                <div class="admin-order-card__top">
                  <div>
                    <span class="order-card__platform">${escapeHtml(order.platformIcon)} ${escapeHtml(order.platformName)}</span>
                    <strong>${escapeHtml(order.productName)}</strong>
                    <p>${escapeHtml(order.customerName)} · ${escapeHtml(order.customerEmail)}</p>
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
          .join("")}
      </div>
    </section>
  `;
}

function renderAdmin() {
  const suppliers = getAdminSuppliers();
  const products = getAdminProducts();
  const stats = state.adminBootstrap?.stats || {};
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
    })
    .slice(0, 120);
  const selectedService =
    allServices.find((service) => service.id === state.ui.adminSelectedSupplierServiceId) ||
    filteredServices.find((service) => service.id === state.ui.adminSelectedSupplierServiceId) ||
    null;
  const connectionResult = state.adminConnectionResult;
  const activeConnection = connectionResult || selectedSupplier;

  return renderAdminFrame(`
    <div class="admin-page">
      <section class="admin-hero">
        <div>
          <p class="admin-hero__eyebrow">Operations Admin</p>
          <h1>패널 운영 관리자</h1>
          <p>공급사 연동, 고객/계정 관리, 상품 생성과 편집, 주문 운영까지 한 화면에서 처리할 수 있도록 관리자 기능을 확장했습니다.</p>
        </div>
        <div class="admin-hero__actions">
          <button class="admin-ghost-button" type="button" data-route="/">사용자 패널</button>
          <button class="admin-ghost-button" type="button" data-admin-refresh>새로고침</button>
          <button class="admin-primary-button" type="button" data-admin-supplier-new>새 공급사</button>
        </div>
      </section>

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
              <p><code>/api</code>, <code>/api/v2</code> 형태를 모두 시도하도록 백엔드에서 자동 보정합니다.</p>
            </div>
            <form class="admin-form" data-admin-supplier-form>
              <label class="form-field">
                <span class="field-label">공급사 이름</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="name" value="${escapeHtml(draft.name)}" data-admin-supplier-field="name" />
                </div>
              </label>

              <label class="form-field">
                <span class="field-label">API URL</span>
                <div class="field-shell">
                  <input class="field-input" type="url" name="apiUrl" value="${escapeHtml(draft.apiUrl)}" placeholder="https://example.com/api/v2" data-admin-supplier-field="apiUrl" />
                </div>
              </label>

              <label class="form-field">
                <span class="field-label">API Key</span>
                <div class="field-shell">
                  <input class="field-input" type="text" name="apiKey" value="${escapeHtml(draft.apiKey)}" placeholder="${draft.id ? "비워두면 기존 키 유지" : ""}" data-admin-supplier-field="apiKey" />
                </div>
              </label>

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
              <p>잔액 조회와 서비스 목록 조회가 모두 성공해야 연결 확인으로 처리됩니다.</p>
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
                <p>공급사 응답의 balance / currency 값을 그대로 표시합니다.</p>
              </article>
              <article class="admin-connection-card">
                <span>서비스 수</span>
                <strong>${escapeHtml(String(activeConnection?.serviceCount || selectedSupplier?.lastServiceCount || selectedSupplier?.serviceCount || 0))}</strong>
                <p>서비스 동기화 전에도 연결 테스트 단계에서 개수를 확인합니다.</p>
              </article>
            </div>

            <div class="admin-action-row admin-action-row--top">
              <button class="admin-secondary-button" type="button" data-admin-test-connection>API 연결 재확인</button>
              <button
                class="admin-primary-button"
                type="button"
                data-admin-sync-services
                ${selectedSupplier?.id ? "" : "disabled"}
              >
                서비스 동기화
              </button>
            </div>
          </section>

          <section class="admin-card">
            <div class="section-head section-head--compact">
              <h2>공급사 서비스 목록</h2>
              <p>${escapeHtml(selectedSupplier ? `${selectedSupplier.name}에서 불러온 서비스입니다.` : "공급사를 선택하면 서비스 목록이 표시됩니다.")}</p>
            </div>

            <div class="admin-toolbar">
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
                ${escapeHtml(selectedService ? `선택됨: ${selectedService.name} (#${selectedService.externalServiceId})` : "서비스를 선택하면 우측 매핑 폼에 반영됩니다.")}
              </div>
            </div>

            <div class="admin-service-list">
              ${
                filteredServices.length
                  ? filteredServices
                      .map(
                        (service) => `
                          <button
                            class="admin-service-card ${state.ui.adminSelectedSupplierServiceId === service.id ? "is-active" : ""}"
                            type="button"
                            data-admin-service-select="${service.id}"
                          >
                            <div class="admin-service-card__top">
                              <strong>${escapeHtml(service.name)}</strong>
                              <span>#${escapeHtml(service.externalServiceId)}</span>
                            </div>
                            <p>${escapeHtml(service.category || "분류 없음")}</p>
                            <div class="admin-service-card__meta">
                              <span>Rate ${escapeHtml(service.rateLabel)}</span>
                              <span>${escapeHtml(String(service.minAmount || 0))} ~ ${escapeHtml(String(service.maxAmount || 0))}</span>
                              <span>${service.refill ? "리필 가능" : "리필 없음"}</span>
                            </div>
                          </button>
                        `
                      )
                      .join("")
                  : `<div class="admin-empty-card"><strong>표시할 서비스가 없습니다.</strong><p>공급사를 저장하고 서비스 동기화를 먼저 실행해 주세요.</p></div>`
              }
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
                          <button
                            class="admin-primary-button"
                            type="submit"
                            ${selectedSupplier?.id && selectedService?.id ? "" : "disabled"}
                          >
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

          ${renderCustomerAdminSection()}
          ${renderCatalogAdminSection()}
          ${renderAdminOrdersSection()}
        </main>
      </div>
    </div>
  `);
}

function renderHome() {
  const data = state.bootstrap;
  if (!data) return "";
  return renderFrame(
    `
      <div class="page page-home">
        <section class="hero-shell">
          <div class="hero-top">
            <div>
              <p class="hero-kicker">${escapeHtml(data.app.subtitle)}</p>
              <h1>${escapeHtml(data.app.name)}</h1>
              <p class="hero-description">
                레퍼런스 사이트의 모바일 우선 SMM 패널 흐름을 바탕으로, 홈-카탈로그-상세주문-충전-내역까지 이어지는 구조를 그대로 재설계했습니다.
              </p>
            </div>
            <button class="hero-contact" type="button" data-route="/products/cat_custom_request">1:1 상담</button>
          </div>

          <div class="hero-links">
            ${data.topLinks
              .map(
                (link) => `
                  <button class="chip-link" type="button" data-route="${link.route}">
                    ${escapeHtml(link.label)}
                  </button>
                `
              )
              .join("")}
          </div>

          <div class="wallet-hero-card">
            <div>
              <p class="wallet-hero-card__label">${escapeHtml(data.user.name)} · ${escapeHtml(data.user.tier)}</p>
              <strong>${escapeHtml(data.user.balanceLabel)}</strong>
            </div>
            <div class="wallet-hero-card__actions">
              <button class="ghost-pill" type="button" data-route="/charge">충전하기</button>
              <button class="solid-pill" type="button" data-route="/orders">주문내역</button>
            </div>
          </div>

          <div class="hero-stats-grid">
            ${data.heroStats
              .map(
                (stat) => `
                  <article class="hero-stat">
                    <span>${escapeHtml(stat.label)}</span>
                    <strong>${escapeHtml(stat.value)}</strong>
                  </article>
                `
              )
              .join("")}
          </div>

          <div class="platform-pill-row">
            ${data.platforms
              .map(
                (platform) => `
                  <button
                    class="platform-pill"
                    type="button"
                    data-route="/products"
                    data-platform-id="${platform.id}"
                    style="--pill-accent:${platform.accentColor};"
                  >
                    <span>${escapeHtml(platform.icon)}</span>
                    <span>${escapeHtml(platform.displayName)}</span>
                  </button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>혜택 & 이벤트</h2>
            <p>홈 상단 배너, 추천 카드, CTA 구조를 모바일 패널 스타일로 맞췄습니다.</p>
          </div>
          <div class="banner-carousel">
            <div class="banner-track" style="transform: translateX(-${state.ui.bannerIndex * 100}%);">
              ${data.banners
                .map(
                  (banner) => `
                    <article class="banner-card banner-card--${escapeHtml(banner.theme)}">
                      <div class="banner-copy">
                        <span class="banner-badge">Pulse24 Pick</span>
                        <h3>${escapeHtml(banner.title)}</h3>
                        <p>${escapeHtml(banner.subtitle)}</p>
                      </div>
                      <button class="banner-cta" type="button" data-route="${banner.route}">
                        ${escapeHtml(banner.ctaLabel)}
                      </button>
                    </article>
                  `
                )
                .join("")}
            </div>
          </div>
          <div class="banner-dots">
            ${data.banners
              .map(
                (_, index) => `
                  <button
                    class="banner-dot ${index === state.ui.bannerIndex ? "is-active" : ""}"
                    type="button"
                    data-banner-index="${index}"
                    aria-label="배너 ${index + 1}"
                  ></button>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>혹시 이런 서비스 관심 있으세요?</h2>
            <p>레퍼런스의 관심 태그 구성을 참고해 빠른 진입 경로를 만들었습니다.</p>
          </div>
          <div class="interest-grid">
            ${data.interestTags
              .map(
                (tag) => `
                  <button class="interest-tag" type="button" data-route="${tag.route}">
                    ${escapeHtml(tag.title)}
                  </button>
                `
              )
              .join("")}
          </div>
          <button class="full-width-cta" type="button" data-route="/products">전체 서비스 보기</button>
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>실속 있는 추천 서비스</h2>
            <p>인기 카드, 간단 설명, 화살표 CTA 흐름을 참고한 추천 리스트입니다.</p>
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
        </section>

        <section class="content-section">
          <div class="section-head">
            <h2>시간을 아껴드릴게요</h2>
            <p>FAQ, 공지, 상담, 가이드를 홈에서 바로 이동하도록 구성했습니다.</p>
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
            <h2>왜 Pulse24를 선택해야 할까요?</h2>
            <p>안전성, 속도, 유연성, 상담 확장 구조를 카드형 혜택 블록으로 정리했습니다.</p>
          </div>
          <div class="benefit-list">
            ${data.benefits
              .map(
                (benefit) => `
                  <article class="benefit-card">
                    <span class="benefit-card__icon">${escapeHtml(benefit.icon)}</span>
                    <div>
                      <strong>${escapeHtml(benefit.title)}</strong>
                      <p>${escapeHtml(benefit.description)}</p>
                    </div>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>

        <section class="content-section footer-section">
          <div class="section-head">
            <h2>운영 정보</h2>
            <p>브랜드 자산은 자체 제작으로 교체하고, 정보 구조만 레퍼런스를 참고했습니다.</p>
          </div>
          <div class="footer-meta">
            <p><strong>${escapeHtml(data.company.name)}</strong></p>
            <p>대표: ${escapeHtml(data.company.representative)}</p>
            <p>문의: ${escapeHtml(data.company.contact)}</p>
            <p>운영시간: ${escapeHtml(data.company.hours)}</p>
          </div>
        </section>
      </div>
    `,
    "home"
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
  const previewSource = getPreviewSource(selectedProduct);

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
        <button class="sticky-order-bar__button" type="submit" form="order-form">
          주문하기
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
          <button class="icon-button" type="button" data-route="/charge">₩</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="profile-card">
          <div class="profile-card__avatar">${escapeHtml(data.user.avatarLabel)}</div>
          <div class="profile-card__copy">
            <strong>${escapeHtml(data.user.name)}</strong>
            <p>${escapeHtml(data.user.email)}</p>
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
      if (!state.adminBootstrap) {
        showLoading("관리자 페이지를 준비하는 중...");
        await refreshAdminData({ preserveDraft: false });
      } else {
        syncAdminSelections({ preserveDraft: true });
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

    updateLiveSummary();
    if (route.name === "detail" && route.id && state.categoryCache[route.id]) {
      scheduleLinkPreview(state.categoryCache[route.id], { immediate: true });
    }
    ensureBannerTimer();
  } catch (error) {
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
}

function navigate(path, { push = true } = {}) {
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

document.addEventListener("click", async (event) => {
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

  const adminRefreshButton = event.target.closest("[data-admin-refresh]");
  if (adminRefreshButton) {
    try {
      await refreshAdminData({ preserveDraft: false });
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
        apiKey: draft.apiKey,
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
    const customer = getAdminCustomers().find((item) => item.id === customerId) || null;
    state.ui.adminCustomerMode = "edit";
    state.ui.adminSelectedCustomerId = customerId;
    state.adminCustomerDraft = customerToDraft(customer);
    renderRoute();
    return;
  }

  const deleteCustomerButton = event.target.closest("[data-admin-delete-customer]");
  if (deleteCustomerButton) {
    const customerId = deleteCustomerButton.getAttribute("data-admin-delete-customer");
    try {
      await apiPost("/api/admin/customers/delete", { customerId });
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
    const previewSource = getPreviewSource(getSelectedProduct(detail));
    if (previewSource && previewSource.key === target.name) {
      scheduleLinkPreview(detail);
    }
  }
});

document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (form.matches("[data-admin-customer-form]")) {
    event.preventDefault();
    const draft = state.adminCustomerDraft || blankCustomerDraft();
    try {
      const result = await apiPost("/api/admin/customers", {
        id: draft.id,
        name: draft.name,
        email: draft.email,
        phone: draft.phone,
        tier: draft.tier,
        role: draft.role,
        notes: draft.notes,
        isActive: draft.isActive,
      });
      state.ui.adminCustomerMode = "edit";
      state.ui.adminSelectedCustomerId = result.customer.id;
      state.adminCustomerDraft = customerToDraft(result.customer);
      await refreshAdminData({ preserveDraft: false });
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
      await refreshAdminData({ preserveDraft: false });
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
        apiKey: draft.apiKey,
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
  const detail = state.categoryCache[route.id];
  if (!detail) return;

  const summary = calculateSummary(detail);
  if (!summary) return;
  const formData = new FormData(form);
  const fields = Object.fromEntries(formData.entries());
  state.productSelections[detail.id].fields = { ...state.productSelections[detail.id].fields, ...fields };

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
