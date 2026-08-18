const ORDER_PROGRESS_ERROR =
  "주문 정보를 확인하지 못했습니다. 입력값을 다시 확인해 주세요.";

export function blankOrderProgressState() {
  return {
    form: {
      orderNumber: "",
      buyerName: "",
      phoneNumber: "",
    },
    loading: false,
    error: "",
    result: null,
    currentResult: null,
    historyResult: null,
    historyLoading: false,
    historyError: "",
    view: "current",
  };
}

function formatOrderDate(value) {
  const raw = String(value || "").trim();
  if (!raw) return "미지원";
  const matched = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return matched ? `${matched[1]}-${matched[2]}-${matched[3]}` : raw;
}

function formatQuantity(value, unit) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return "미지원";
  return `${new Intl.NumberFormat("ko-KR").format(Math.round(numeric))}${unit || ""}`;
}

function progressToneClass(percent) {
  if (percent >= 100) return "is-complete";
  if (percent >= 70) return "is-advanced";
  if (percent >= 30) return "is-building";
  return "is-starting";
}

function renderProgress(item, escapeHtml) {
  const progress = item?.progress || {};
  const percent = Number(progress.percent);
  if (!progress.supported || !Number.isFinite(percent)) {
    return `
      <div class="order-progress-details__row">
        <dt>진행률</dt>
        <dd><span class="order-progress-unsupported">미지원</span></dd>
      </div>
    `;
  }
  const safePercent = Math.max(0, Math.min(100, Math.round(percent)));
  const toneClass = progressToneClass(safePercent);
  return `
    <div class="order-progress-details__row">
      <dt>진행률</dt>
      <dd>${escapeHtml(`${safePercent}%`)}</dd>
    </div>
    <div class="order-progress-meter ${toneClass}">
      <progress
        class="order-progress-meter__track"
        aria-label="${escapeHtml(`${item.serviceName || "서비스"} 진행률`)}"
        value="${safePercent}"
        max="100"
      >
        ${escapeHtml(`${safePercent}%`)}
      </progress>
      <strong>${escapeHtml(`${safePercent}%`)}</strong>
    </div>
  `;
}

function renderQuantityRows(item, escapeHtml) {
  const unit = String(item?.unit || "");
  if (item?.dailyQuantity) {
    return `
      <div class="order-progress-details__row order-progress-details__row--quantities">
        <dt>1일 수량</dt>
        <dd>${escapeHtml(formatQuantity(item.dailyQuantity, unit))}</dd>
        <dt>총 수량</dt>
        <dd>${escapeHtml(formatQuantity(item.totalQuantity, unit))}</dd>
      </div>
    `;
  }
  return `
    <div class="order-progress-details__row">
      <dt>총 수량</dt>
      <dd>${escapeHtml(formatQuantity(item?.totalQuantity, unit))}</dd>
    </div>
  `;
}

function renderServiceItem(item, index, escapeHtml) {
  const status = String(item?.status || "in_progress");
  const statusClass =
    status === "completed"
      ? "is-complete"
      : status === "attention"
      ? "is-attention"
      : "is-progress";
  return `
    <article class="order-progress-service">
      <div class="order-progress-service__columns" aria-hidden="true">
        <span>${index + 1}</span>
        <span>서비스명</span>
        <span>상태</span>
      </div>
      <div class="order-progress-service__title">
        <h2>${escapeHtml(item?.serviceName || "서비스")}</h2>
        <strong class="order-progress-status ${statusClass}">
          ${escapeHtml(item?.statusLabel || "진행중")}
        </strong>
      </div>
      <dl class="order-progress-details">
        <div class="order-progress-details__row">
          <dt>계정명</dt>
          <dd>${escapeHtml(item?.accountName || "미지원")}</dd>
        </div>
        ${renderQuantityRows(item, escapeHtml)}
        ${renderProgress(item, escapeHtml)}
      </dl>
    </article>
  `;
}

function renderOrderGroup(order, escapeHtml) {
  const items = Array.isArray(order?.items) ? order.items : [];
  return `
    <section class="order-progress-order-group">
      <dl class="order-progress-meta">
        <div>
          <dt>주문번호</dt>
          <dd>${escapeHtml(order?.orderNumber || "")}</dd>
        </div>
        <div>
          <dt>주문일자</dt>
          <dd>${escapeHtml(formatOrderDate(order?.orderDate))}</dd>
        </div>
      </dl>
      <div class="order-progress-services">
        ${items.map((item, index) => renderServiceItem(item, index, escapeHtml)).join("")}
      </div>
    </section>
  `;
}

function renderLookupResults(progressState, escapeHtml) {
  const result = progressState?.result || {};
  const isActiveView = progressState?.view === "active";
  const orders = isActiveView
    ? Array.isArray(result.orders)
      ? result.orders
      : []
    : result.order
    ? [result.order]
    : [];
  const verificationLabel = isActiveView
    ? orders.length
      ? `진행중인 주문 ${orders.length}건을 확인했습니다.`
      : "현재 진행중인 주문이 없습니다."
    : "주문 정보가 확인되었습니다.";
  const nextView = isActiveView ? "current" : "active";
  const buttonLabel = progressState.historyLoading
    ? "조회 중..."
    : isActiveView
    ? "현재 주문만 보기"
    : "전체 주문 조회";
  return `
    <section class="order-progress-results" aria-label="주문 조회 결과" data-order-progress-results>
      <div class="order-progress-results__toolbar">
        <div class="order-progress-verified">
          <span aria-hidden="true"></span>
          <p><i aria-hidden="true">✓</i>${escapeHtml(verificationLabel)}</p>
          <span aria-hidden="true"></span>
        </div>
        <button
          type="button"
          class="order-progress-view-button"
          data-order-progress-view="${nextView}"
          ${progressState.historyLoading ? "disabled" : ""}
        >
          ${escapeHtml(buttonLabel)}
        </button>
      </div>
      ${
        progressState.historyError
          ? `<p class="order-progress-history-error" role="alert">${escapeHtml(
              progressState.historyError,
            )}</p>`
          : ""
      }
      ${
        orders.length
          ? `<div class="order-progress-order-list">
              ${orders.map((order) => renderOrderGroup(order, escapeHtml)).join("")}
            </div>`
          : `<div class="order-progress-empty">현재 진행중인 주문이 없습니다.</div>`
      }
    </section>
  `;
}

export function renderOrderProgressPage({ state, escapeHtml, logoUrl }) {
  const progressState = state.orderProgress || blankOrderProgressState();
  const form = progressState.form || {};
  return `
    <main class="order-progress-page">
      <header class="order-progress-header">
        <a class="order-progress-brand" href="/" aria-label="인스타마트 홈">
          <img src="${escapeHtml(logoUrl)}" alt="" />
          <span>Instamart</span>
        </a>
        <h1>주문 진행 현황</h1>
      </header>

      <form
        class="order-progress-form"
        data-order-progress-form
        aria-busy="${progressState.loading ? "true" : "false"}"
        novalidate
      >
        <label>
          <span>주문번호</span>
          <input
            type="text"
            name="orderNumber"
            data-order-progress-input
            value="${escapeHtml(form.orderNumber || "")}"
            placeholder="주문번호를 입력해 주세요"
            autocomplete="off"
            maxlength="64"
            ${progressState.loading ? "disabled" : ""}
            required
          />
        </label>
        <label>
          <span>구매자명</span>
          <input
            type="text"
            name="buyerName"
            data-order-progress-input
            value="${escapeHtml(form.buyerName || "")}"
            placeholder="구매자명을 입력해 주세요"
            autocomplete="name"
            maxlength="80"
            ${progressState.loading ? "disabled" : ""}
            required
          />
        </label>
        <label>
          <span>휴대폰번호</span>
          <input
            type="tel"
            name="phoneNumber"
            data-order-progress-input
            value="${escapeHtml(form.phoneNumber || "")}"
            placeholder="휴대폰번호를 입력해 주세요"
            autocomplete="tel"
            inputmode="tel"
            maxlength="24"
            ${progressState.loading ? "disabled" : ""}
            required
          />
        </label>
        <button type="submit" ${progressState.loading ? "disabled" : ""}>
          ${progressState.loading ? "조회 중..." : "주문 조회"}
        </button>
        ${
          progressState.error
            ? `<p class="order-progress-error" role="alert">${escapeHtml(progressState.error)}</p>`
            : ""
        }
      </form>

      ${progressState.result ? renderLookupResults(progressState, escapeHtml) : ""}
    </main>
  `;
}

export function handleOrderProgressInput(event, ctx) {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) || !target.matches("[data-order-progress-input]")) {
    return false;
  }
  const { state } = ctx;
  state.orderProgress = state.orderProgress || blankOrderProgressState();
  if (Object.prototype.hasOwnProperty.call(state.orderProgress.form, target.name)) {
    state.orderProgress.form[target.name] = target.value;
  }
  if (state.orderProgress.result || state.orderProgress.error) {
    state.orderProgress.result = null;
    state.orderProgress.currentResult = null;
    state.orderProgress.historyResult = null;
    state.orderProgress.historyError = "";
    state.orderProgress.view = "current";
    state.orderProgress.error = "";
    document.querySelector("[data-order-progress-results]")?.remove();
    document.querySelector(".order-progress-error")?.remove();
  }
  return true;
}

export async function handleOrderProgressSubmit(event, ctx) {
  const { apiPost, renderRoute, state } = ctx;
  const formElement = event.target;
  if (!(formElement instanceof HTMLFormElement) || !formElement.matches("[data-order-progress-form]")) {
    return false;
  }
  event.preventDefault();
  if (state.orderProgress?.loading) return true;

  const formData = new FormData(formElement);
  const form = {
    orderNumber: String(formData.get("orderNumber") || "").trim(),
    buyerName: String(formData.get("buyerName") || "").trim(),
    phoneNumber: String(formData.get("phoneNumber") || "").trim(),
  };
  state.orderProgress = state.orderProgress || blankOrderProgressState();
  state.orderProgress.form = form;
  state.orderProgress.result = null;
  state.orderProgress.currentResult = null;
  state.orderProgress.historyResult = null;
  state.orderProgress.historyError = "";
  state.orderProgress.view = "current";
  state.orderProgress.error = "";

  if (!form.orderNumber || !form.buyerName || !form.phoneNumber) {
    state.orderProgress.error = "주문번호, 구매자명, 휴대폰번호를 모두 입력해 주세요.";
    await renderRoute();
    return true;
  }

  state.orderProgress.loading = true;
  await renderRoute();
  try {
    const result = await apiPost("/api/order-progress/lookup", form);
    state.orderProgress.result = result.found ? result : null;
    state.orderProgress.currentResult = result.found ? result : null;
    state.orderProgress.error = result.found ? "" : ORDER_PROGRESS_ERROR;
  } catch (error) {
    state.orderProgress.result = null;
    state.orderProgress.error = error?.message || "주문 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  } finally {
    state.orderProgress.loading = false;
    await renderRoute();
  }
  if (state.orderProgress.result) {
    document.querySelector("[data-order-progress-results]")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
  return true;
}

export async function handleOrderProgressViewClick(event, ctx) {
  const target = event.target instanceof Element ? event.target : event.target?.parentElement;
  const button = target?.closest("[data-order-progress-view]");
  if (!(button instanceof HTMLButtonElement)) {
    return false;
  }
  event.preventDefault();
  const { apiPost, renderRoute, state } = ctx;
  state.orderProgress = state.orderProgress || blankOrderProgressState();
  const progressState = state.orderProgress;
  const nextView = button.getAttribute("data-order-progress-view") || "active";

  if (nextView === "current") {
    progressState.view = "current";
    progressState.result = progressState.currentResult;
    progressState.historyError = "";
    await renderRoute();
    document.querySelector("[data-order-progress-results]")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    return true;
  }
  if (progressState.historyLoading || !progressState.currentResult) {
    return true;
  }

  progressState.historyLoading = true;
  progressState.historyError = "";
  await renderRoute();
  try {
    const result = await apiPost(
      "/api/order-progress/active",
      progressState.form,
    );
    if (!result.found) {
      throw new Error(ORDER_PROGRESS_ERROR);
    }
    progressState.historyResult = result;
    progressState.result = result;
    progressState.view = "active";
  } catch (error) {
    progressState.result = progressState.currentResult;
    progressState.view = "current";
    progressState.historyError =
      error?.message || "전체 주문 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  } finally {
    progressState.historyLoading = false;
    await renderRoute();
  }
  document.querySelector("[data-order-progress-results]")?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
  return true;
}
