export function renderCafe24QueueToolbar({ state, escapeHtml }) {
  const paymentFilter = state.ui.adminCafe24PaymentFilter || "all";
  const mappingFilter = state.ui.adminCafe24MappingFilter || "all";
  const statusFilter = state.ui.adminCafe24StatusFilter || "all";
  const statuses = ["ready_to_submit", "waiting_input", "mapping_error", "payment_pending", "payment_review_required", "supplier_submitted", "supplier_progress", "completed", "failed", "cancelled"];
  return `
    <div class="admin-toolbar">
      <div class="search-shell">
        <input class="search-input" type="text" value="${escapeHtml(state.ui.adminCafe24Search || "")}" placeholder="주문번호, 품목코드, 상품번호, 구매자 검색" data-admin-cafe24-filter="search" />
      </div>
      <select class="field-select" data-admin-cafe24-filter="payment">
        <option value="all" ${paymentFilter === "all" ? "selected" : ""}>전체 결제</option>
        <option value="payment_confirmed" ${paymentFilter === "payment_confirmed" ? "selected" : ""}>결제완료</option>
        <option value="payment_pending" ${paymentFilter === "payment_pending" ? "selected" : ""}>결제대기</option>
        <option value="payment_review_required" ${paymentFilter === "payment_review_required" ? "selected" : ""}>검수 필요</option>
        <option value="cancelled" ${paymentFilter === "cancelled" ? "selected" : ""}>취소/환불</option>
      </select>
      <select class="field-select" data-admin-cafe24-filter="mapping">
        <option value="all" ${mappingFilter === "all" ? "selected" : ""}>전체 매핑</option>
        <option value="unmapped" ${mappingFilter === "unmapped" ? "selected" : ""}>미매핑</option>
        <option value="mapped" ${mappingFilter === "mapped" ? "selected" : ""}>매핑됨</option>
      </select>
      <select class="field-select" data-admin-cafe24-filter="status">
        <option value="all" ${statusFilter === "all" ? "selected" : ""}>전체 처리상태</option>
        ${statuses.map((status) => `<option value="${status}" ${statusFilter === status ? "selected" : ""}>${status}</option>`).join("")}
      </select>
    </div>
  `;
}

export function renderCafe24AutoPollCards({ activeIntegration = {}, automation = {}, summary = {}, escapeHtml }) {
  const autoPollStatus = activeIntegration.lastAutoPollStatus || "never";
  const autoPollRisk = ["failed", "reconnect_required"].includes(autoPollStatus);
  const lastTick = automation.lastTick || {};
  const tickStatus = automation.lastTickStatus || lastTick.status || "never";
  const tickRisk = tickStatus === "failed" || Boolean(automation.paused);
  const cafe24Dispatch = lastTick.cafe24Dispatch || {};
  const completion = lastTick.cafe24Completion || {};
  const supplierHealth = lastTick.supplierHealth || {};
  const retryQueueCount = Number(summary.failedCount || 0) + Number(summary.reviewRequiredCount || 0);
  const statusLabel = autoPollStatus === "success"
    ? "정상"
    : autoPollStatus === "running"
      ? "진행 중"
      : autoPollStatus === "reconnect_required"
        ? "재연결 필요"
        : autoPollStatus === "failed"
          ? "실패"
          : "대기";
  return `
    <article class="${tickRisk ? "is-risk" : tickStatus === "success" ? "is-hot" : ""}">
      <span>자동화 Tick</span>
      <strong>${escapeHtml(automation.paused ? "긴급 중단" : tickStatus === "success" ? "정상" : tickStatus === "failed" ? "실패" : "대기")}</strong>
      <small>${escapeHtml(automation.lastTickAt || lastTick.finishedAt || "GitHub Actions 5분 주기")}</small>
    </article>
    <article class="${autoPollRisk ? "is-risk" : autoPollStatus === "success" ? "is-hot" : ""}">
      <span>자동 수집</span>
      <strong>${escapeHtml(statusLabel)}</strong>
      <small>${escapeHtml(activeIntegration.lastAutoPollAt || activeIntegration.lastAutoPollMessage || "외부 스케줄러 미호출")}</small>
    </article>
    <article>
      <span>다음 예상 수집</span>
      <strong>${escapeHtml(activeIntegration.nextAutoPollAt || "5분 주기")}</strong>
      <small>외부 스케줄러 호출 기준</small>
    </article>
    <article class="${Number(cafe24Dispatch.failed || 0) ? "is-risk" : Number(cafe24Dispatch.submitted || 0) ? "is-hot" : ""}">
      <span>자동 발주</span>
      <strong>${escapeHtml(String(Number(cafe24Dispatch.submitted || 0)))}</strong>
      <small>차단 ${escapeHtml(String(Number(cafe24Dispatch.blocked || 0)))} · 실패 ${escapeHtml(String(Number(cafe24Dispatch.failed || 0)))}</small>
    </article>
    <article class="${Number(supplierHealth.failed || 0) ? "is-risk" : Number(supplierHealth.ok || 0) ? "is-hot" : ""}">
      <span>공급사 점검</span>
      <strong>${escapeHtml(String(Number(supplierHealth.ok || 0)))}</strong>
      <small>실패 ${escapeHtml(String(Number(supplierHealth.failed || 0)))}</small>
    </article>
    <article class="${Number(completion.failed || 0) ? "is-risk" : Number(completion.done || 0) ? "is-hot" : ""}">
      <span>Cafe24 완료</span>
      <strong>${escapeHtml(String(Number(completion.done || 0)))}</strong>
      <small>완료 실패 ${escapeHtml(String(Number(completion.failed || 0)))}</small>
    </article>
    <article class="${retryQueueCount ? "is-risk" : ""}">
      <span>재시도/검수</span>
      <strong>${escapeHtml(String(retryQueueCount))}</strong>
      <small>실패+검수 필요 큐</small>
    </article>
  `;
}

export function renderCafe24SchedulerNotice({ origin, escapeHtml }) {
  const cronEndpoint = `${origin}/api/cron/cafe24/flow-tick`;
  return `
    <div class="admin-inline-note">
      <strong>5분 Cafe24 주문 처리 설정</strong><br />
      GitHub Actions 외부 스케줄러가 <code>POST ${escapeHtml(cronEndpoint)}</code>를 5분마다 호출하도록 구성되어 있습니다.
      GitHub Actions는 서명된 OIDC 토큰을 사용하고, 다른 스케줄러를 추가할 때는 헤더 <code>Authorization: Bearer &lt;CRON_SECRET&gt;</code>를 사용하세요.
      증분 수집, preflight, 자동 발주, 공급사 상태 조회, Cafe24 구매확정을 순서대로 실행합니다.
    </div>
  `;
}

export function renderCafe24Pagination({ pagination, escapeHtml }) {
  const page = Number(pagination.page || 1);
  const totalPages = Math.max(Number(pagination.totalPages || 1), 1);
  return `
    <div class="admin-pagination">
      <button class="admin-secondary-button" type="button" data-admin-cafe24-page="${escapeHtml(String(Math.max(page - 1, 1)))}" ${page <= 1 ? "disabled" : ""}>이전</button>
      <span>${escapeHtml(String(page))} / ${escapeHtml(String(totalPages))} · 총 ${escapeHtml(String(pagination.total || 0))}건 · 5개씩 보기</span>
      <button class="admin-secondary-button" type="button" data-admin-cafe24-page="${escapeHtml(String(Math.min(page + 1, totalPages)))}" ${page >= totalPages ? "disabled" : ""}>다음</button>
    </div>
  `;
}

function cafe24QueueStage(item = {}, canDispatch = false) {
  const status = String(item.standardStatus || "");
  if (item.paymentGateStatus !== "payment_confirmed") return { label: "결제 확인", tone: "is-warn", detail: "결제완료가 확인되면 다음 단계로 이동합니다." };
  if (item.supplierOrderUuid) return { label: status === "completed" ? "완료" : "공급 진행", tone: "is-success", detail: item.supplierOrderUuid };
  if (canDispatch) return { label: "발주 가능", tone: "is-success", detail: "preflight 후 공급사 발주 대상입니다." };
  if (!item.mappingId && !item.supplierServiceId) return { label: "매핑 필요", tone: "is-warn", detail: "Cafe24 상품을 공급사 서비스에 연결하세요." };
  if (cafe24NeedsManualInput(item)) return { label: "수동 보정", tone: "is-warn", detail: "대상/수량/서비스를 보정하면 발주할 수 있습니다." };
  if (status === "failed") return { label: "실패 재시도", tone: "is-error", detail: item.errorMessage || "공급사 오류와 retry 조건을 확인하세요." };
  return { label: "검수 필요", tone: "is-neutral", detail: item.errorMessage || status || "재검증을 실행하세요." };
}

export function renderCafe24OrderQueuePanel({ state, orderItems = [], suppliers = [], supplierServices = [], selectedSupplierId = "", escapeHtml, canDispatchItem, statusTone, productLabel }) {
  const list = state.adminCafe24OrderList || {};
  const pagination = list.pagination || { page: state.ui.adminCafe24OrderPage || 1, pageSize: 5, total: orderItems.length, totalPages: 1 };
  const sourceItems = Array.isArray(list.items) ? list.items : orderItems;
  const sortedItems = [...sourceItems].sort((a, b) => {
    const aScore = canDispatchItem(a) ? 0 : a.standardStatus === "failed" ? 1 : !a.mappingId ? 2 : 3;
    const bScore = canDispatchItem(b) ? 0 : b.standardStatus === "failed" ? 1 : !b.mappingId ? 2 : 3;
    return aScore - bScore;
  });
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>주문 처리 큐</h3>
        <p>운영자는 다음 액션이 필요한 품주부터 확인하고, payload/수동 상태 변경은 고급 영역에서 처리합니다.</p>
      </div>
      ${renderCafe24QueueToolbar({ state, escapeHtml })}
      <div class="admin-order-list cafe24-order-list">
        ${sortedItems.length ? sortedItems.map((item) => {
          const canDispatch = canDispatchItem(item);
          const preflight = state.adminCafe24Preflights?.[item.id] || null;
          const stage = cafe24QueueStage(item, canDispatch);
          const manualInputForm = renderCafe24ManualInputForm({ item, suppliers, supplierServices, selectedSupplierId, manualPreview: state.adminCafe24ManualPreviews?.[item.id] || null, escapeHtml });
          return `
            <article class="admin-order-card cafe24-order-card ${item.standardStatus === "failed" ? "is-risk" : ""}">
              <div class="admin-order-card__top">
                <div>
                  <span class="order-card__platform">Cafe24 · ${escapeHtml(item.mallId)} / ${escapeHtml(String(item.shopNo))}</span>
                  <strong>${escapeHtml(productLabel(item))}</strong>
                  <p>${escapeHtml(item.orderId)} · ${escapeHtml(item.orderItemCode)}${item.orderDate ? ` · ${escapeHtml(item.orderDate)}` : ""}</p>
                </div>
                <div class="admin-order-card__statusbox">
                  <span class="admin-order-card__number">${escapeHtml(item.orderStatusCode || "-")}</span>
                  <span class="admin-badge ${stage.tone}">${escapeHtml(stage.label)}</span>
                  <small>${escapeHtml(item.standardStatus || "-")}</small>
                </div>
              </div>
              <div class="cafe24-card-next-action">
                <div><span>다음 액션</span><strong>${escapeHtml(stage.detail || "-")}</strong></div>
                <span class="admin-badge ${statusTone(item)}">${escapeHtml(item.paymentGateStatus || "-")}</span>
              </div>
              <div class="admin-order-card__fact-grid cafe24-card-summary-grid">
                <article><span>상품번호</span><strong>${escapeHtml(item.productNo || "-")}</strong></article>
                <article><span>품목코드</span><strong>${escapeHtml(item.variantCode || "-")}</strong></article>
                <article><span>매핑</span><strong>${escapeHtml(item.mappingId ? "연결됨" : "미매핑")}</strong></article>
                <article><span>공급사</span><strong>${escapeHtml(item.supplierExternalServiceId || "-")}</strong></article>
                <article><span>구매자</span><strong>${escapeHtml(item.buyerName || "-")}</strong></article>
                <article><span>주문 입력값</span><strong>${escapeHtml(item.targetDiagnostics?.input || "-")}</strong></article>
              </div>
              ${renderCafe24QueueActionHint({ item, canDispatch, escapeHtml })}
              ${renderCafe24PreflightSummary({ preflight, escapeHtml })}
              ${manualInputForm ? `<details class="admin-disclosure cafe24-card-disclosure" ${cafe24NeedsManualInput(item) ? "open" : ""}><summary>수동 보정 입력</summary>${manualInputForm}</details>` : ""}
              <div class="admin-action-row">
                <button class="admin-secondary-button" type="button" data-admin-cafe24-resync-item="${escapeHtml(item.id)}">재동기화</button>
                <button class="admin-secondary-button" type="button" data-admin-cafe24-retry-item="${escapeHtml(item.id)}">재검증</button>
                <button class="admin-secondary-button" type="button" data-admin-cafe24-preflight-item="${escapeHtml(item.id)}">preflight</button>
                <button class="admin-primary-button" type="button" data-admin-cafe24-dispatch-item="${escapeHtml(item.id)}" ${canDispatch ? "" : "disabled"}>공급사 발주</button>
              </div>
              <details class="admin-disclosure cafe24-order-advanced">
                <summary>고급 진단 / 수동 상태 수정</summary>
                ${item.targetDiagnostics?.message ? `<p class="admin-inline-note">대상 확인: ${escapeHtml(item.targetDiagnostics.message)}</p>` : ""}
                ${item.targetDiagnostics?.normalized ? `<p class="admin-inline-note">정규화: ${escapeHtml(item.targetDiagnostics.input || "-")} -> ${escapeHtml(item.targetDiagnostics.supplierLink || "-")}</p>` : ""}
                ${item.errorMessage ? `<p class="admin-inline-note">${escapeHtml(item.errorMessage)}</p>` : ""}
                <pre>${escapeHtml(JSON.stringify({ target: item.targetDiagnostics, fields: item.normalizedFields, supplierPayload: item.supplierPayload, supplierResponse: item.supplierResponse, raw: item.rawPayloadPreview }, null, 2))}</pre>
                <form class="admin-order-form" data-admin-cafe24-item-status-form>
                  <input type="hidden" name="itemId" value="${escapeHtml(item.id)}" />
                  <div class="admin-three-column">
                    <label class="form-field"><span class="field-label">수동 상태</span><div class="field-shell"><select class="field-select" name="status">${["received", "payment_pending", "payment_review_required", "waiting_input", "mapping_error", "missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error", "needs_manual_review", "ready_to_submit", "submitting", "supplier_submitted", "supplier_progress", "completed", "failed", "cancelled"].map((status) => `<option value="${status}" ${item.standardStatus === status ? "selected" : ""}>${status}</option>`).join("")}</select></div></label>
                    <label class="form-field admin-order-form__memo"><span class="field-label">운영 메모</span><div class="field-shell"><input class="field-input" name="memo" value="${escapeHtml(item.errorMessage || "")}" /></div></label>
                    <div class="admin-order-form__submit"><button class="admin-secondary-button" type="submit">상태 저장</button></div>
                  </div>
                </form>
              </details>
            </article>
          `;
        }).join("") : `<div class="admin-empty-card"><strong>조건에 맞는 Cafe24 주문이 없습니다.</strong><p>상단에서 최근 1개월 수동 수집을 실행하거나 주문번호로 직접 조회해 주세요.</p></div>`}
      </div>
      ${renderCafe24Pagination({ pagination, escapeHtml })}
    </div>
  `;
}

function cafe24NeedsManualInput(item = {}) {
  return item.paymentGateStatus === "payment_confirmed"
    && !item.supplierOrderUuid
    && ["waiting_input", "mapping_error", "missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error", "needs_manual_review"].includes(item.standardStatus);
}

export function renderCafe24QueueActionHint({ item = {}, canDispatch = false, escapeHtml }) {
  const missingMapping = !item.mappingId && !item.supplierServiceId;
  const status = String(item.standardStatus || "");
  const errorMessage = String(item.errorMessage || "");
  let tone = "is-neutral";
  let label = "상태 확인";
  let message = "재검증 후 payload preview와 발주 가능 여부를 확인하세요.";

  if (item.paymentGateStatus !== "payment_confirmed") {
    tone = "is-warn";
    label = "결제 확인 필요";
    message = "Cafe24 결제완료가 확인되기 전에는 매핑/수동 보정을 해도 공급사 발주가 차단됩니다.";
  } else if (item.supplierOrderUuid) {
    tone = "is-success";
    label = "발주 진행 중";
    message = "이미 공급사 주문번호가 있어 중복 발주를 막고 상태 조회/완료 처리만 진행합니다.";
  } else if (canDispatch) {
    tone = "is-success";
    label = "발주 가능";
    message = "결제, 매핑, payload가 준비되었습니다. 운영 정책에 맞춰 단건 발주 또는 자동 발주를 진행할 수 있습니다.";
  } else if (missingMapping && (status === "waiting_input" || errorMessage.includes("매핑"))) {
    tone = "is-warn";
    label = "매핑 또는 수동 보정 필요";
    message = "상품/품목코드로 공급사 서비스를 매핑하세요. 개인결제처럼 옵션·수량 후보가 없는 품주는 아래 수동 보정에서 공급사 서비스, 대상, 수량을 입력해야 합니다.";
  } else if (["missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error"].includes(status)) {
    tone = "is-warn";
    label = "입력값 보정 필요";
    message = "공급사 payload에 필요한 대상/수량이 부족하거나 범위를 벗어났습니다. 재검증하거나 아래 수동 보정값을 저장하세요.";
  } else if (status === "needs_manual_review") {
    tone = "is-warn";
    label = "운영 검수 필요";
    message = "공급사 응답 또는 인증 상태가 애매합니다. 공급사 상태를 확인한 뒤 재검증/재발주 여부를 결정하세요.";
  } else if (status === "failed") {
    tone = "is-error";
    label = "발주 실패";
    message = "공급사 오류를 확인하고 retry 한도, health check, 서비스 매핑을 점검한 뒤 재발주하세요.";
  }

  return `
    <div class="admin-inline-note">
      <span class="admin-badge ${tone}">${escapeHtml(label)}</span>
      ${escapeHtml(message)}
    </div>
  `;
}

export function renderCafe24PreflightSummary({ preflight = null, escapeHtml }) {
  if (!preflight) return "";
  const blockingReasons = Array.isArray(preflight.blockingReasons) ? preflight.blockingReasons : [];
  const quantity = preflight.quantity || {};
  const supplierPayload = preflight.supplierPayload || {};
  const readiness = preflight.supplierReadiness || {};
  const canDispatch = preflight.canDispatch === true;
  return `
    <div class="admin-inline-note">
      <span class="admin-badge ${canDispatch ? "is-success" : "is-warn"}">${canDispatch ? "preflight 통과" : "preflight 차단"}</span>
      수량 ${escapeHtml(String(quantity.normalized ?? "-"))}${quantity.expected ? ` / 예상 ${escapeHtml(String(quantity.expected))}` : ""}
      · service ${escapeHtml(supplierPayload.service || "-")}
      · readiness ${escapeHtml(readiness.code || "unknown")}
      ${blockingReasons.length ? `<br />차단: ${escapeHtml(blockingReasons.join(", "))}` : ""}
    </div>
  `;
}

export function renderCafe24ManualInputForm({ item = {}, suppliers = [], supplierServices = [], selectedSupplierId = "", manualPreview = null, escapeHtml }) {
  if (!cafe24NeedsManualInput(item)) return "";
  const activeSupplierId = item.supplierId || selectedSupplierId || "";
  const quantity = item.normalizedFields?.orderedCount || item.supplierPayload?.quantity || "";
  const target = item.targetDiagnostics?.input || item.normalizedFields?.targetUrl || item.normalizedFields?.targetValue || "";
  const previewPreflight = manualPreview?.preflight || null;
  const previewCanDispatch = previewPreflight?.canDispatch === true;
  const previewPayload = manualPreview
    ? {
        wouldUpdate: manualPreview.wouldUpdate || {},
        normalizedFields: manualPreview.normalizedFields || {},
        supplierPayload: manualPreview.supplierPayload || {},
      }
    : null;
  const selectedSupplier = suppliers.find((supplier) => supplier.id === activeSupplierId) || null;
  const serviceHelp = activeSupplierId
    ? supplierServices.length
      ? `${selectedSupplier?.name || "선택 공급사"} 서비스 ${supplierServices.length}개 중 하나를 선택하세요.`
      : "공급사 서비스 목록을 불러오는 중이거나 동기화된 서비스가 없습니다. 공급사를 다시 선택하거나 service sync를 먼저 실행하세요."
    : "공급사를 선택하면 해당 공급사의 서비스 목록을 불러옵니다.";
  const supplierOptions = [
    `<option value="">공급사 선택</option>`,
    ...suppliers.map((supplier) => `<option value="${escapeHtml(supplier.id)}" ${supplier.id === activeSupplierId ? "selected" : ""}>${escapeHtml(supplier.name)}</option>`),
  ].join("");
  const serviceOptions = [
    `<option value="">공급사 서비스를 선택하세요</option>`,
    ...supplierServices.map((service) => `<option value="${escapeHtml(service.id)}" ${service.id === item.supplierServiceId ? "selected" : ""}>${escapeHtml(service.name)} · ${escapeHtml(service.externalServiceId || "")} · ${escapeHtml(service.minAmount || "-")}~${escapeHtml(service.maxAmount || "-")}</option>`),
  ].join("");
  return `
    <form class="admin-order-form" data-admin-cafe24-item-manual-form>
      <input type="hidden" name="itemId" value="${escapeHtml(item.id)}" />
      <div class="admin-three-column">
        <label class="form-field"><span class="field-label">공급사</span><div class="field-shell"><select class="field-select" name="supplierId" data-admin-cafe24-manual-supplier-select>${supplierOptions}</select></div></label>
        <label class="form-field"><span class="field-label">공급사 서비스</span><div class="field-shell"><select class="field-select" name="supplierServiceId" data-admin-cafe24-manual-service-select>${serviceOptions}</select></div></label>
        <label class="form-field"><span class="field-label">수량</span><div class="field-shell"><input class="field-input" name="orderedCount" inputmode="numeric" value="${escapeHtml(quantity)}" placeholder="예: 50" /></div></label>
      </div>
      <p class="admin-inline-note">${escapeHtml(serviceHelp)}</p>
      <div class="admin-two-column">
        <label class="form-field"><span class="field-label">대상 링크/계정</span><div class="field-shell"><input class="field-input" name="targetValue" value="${escapeHtml(target)}" placeholder="SNS 링크 또는 계정 ID" /></div></label>
        <label class="form-field"><span class="field-label">요청 메모</span><div class="field-shell"><input class="field-input" name="requestMemo" value="${escapeHtml(item.normalizedFields?.requestMemo || "")}" placeholder="공급사 comments로 보낼 메모" /></div></label>
      </div>
      ${previewPreflight ? renderCafe24PreflightSummary({ preflight: previewPreflight, escapeHtml }) : ""}
      ${
        manualPreview
          ? `
            <details class="admin-disclosure" ${previewCanDispatch ? "" : "open"}>
              <summary>수동 보정 payload preview</summary>
              <pre>${escapeHtml(JSON.stringify(previewPayload, null, 2))}</pre>
            </details>
          `
          : ""
      }
      <div class="admin-action-row">
        <button class="admin-secondary-button" type="button" data-admin-cafe24-manual-preview-item="${escapeHtml(item.id)}">payload preview</button>
        <button class="admin-primary-button" type="submit">수동 보정 저장</button>
      </div>
    </form>
  `;
}
