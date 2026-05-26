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
      <small>${escapeHtml(automation.lastTickAt || lastTick.finishedAt || "GitHub Actions 10분 주기")}</small>
    </article>
    <article class="${autoPollRisk ? "is-risk" : autoPollStatus === "success" ? "is-hot" : ""}">
      <span>자동 수집</span>
      <strong>${escapeHtml(statusLabel)}</strong>
      <small>${escapeHtml(activeIntegration.lastAutoPollAt || activeIntegration.lastAutoPollMessage || "외부 스케줄러 미호출")}</small>
    </article>
    <article>
      <span>다음 예상 수집</span>
      <strong>${escapeHtml(activeIntegration.nextAutoPollAt || "10분 주기")}</strong>
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
  const cronEndpoint = `${origin}/api/cron/automation/tick`;
  return `
    <div class="admin-inline-note">
      <strong>10분 자동 주문 처리 설정</strong><br />
      GitHub Actions 외부 스케줄러가 <code>POST ${escapeHtml(cronEndpoint)}</code>를 10분마다 호출하도록 구성되어 있습니다.
      다른 스케줄러를 추가할 때는 헤더 <code>Authorization: Bearer &lt;CRON_SECRET&gt;</code>를 사용하세요.
      수집, 공급사 점검, 자동 발주, 공급사 상태 조회, Cafe24 구매확정을 순서대로 실행합니다.
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

export function renderCafe24ManualInputForm({ item = {}, suppliers = [], supplierServices = [], selectedSupplierId = "", escapeHtml }) {
  if (!cafe24NeedsManualInput(item)) return "";
  const activeSupplierId = item.supplierId || (supplierServices.length ? selectedSupplierId : "") || "";
  const quantity = item.normalizedFields?.orderedCount || item.supplierPayload?.quantity || "";
  const target = item.targetDiagnostics?.input || item.normalizedFields?.targetUrl || item.normalizedFields?.targetValue || "";
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
      <div class="admin-two-column">
        <label class="form-field"><span class="field-label">대상 링크/계정</span><div class="field-shell"><input class="field-input" name="targetValue" value="${escapeHtml(target)}" placeholder="SNS 링크 또는 계정 ID" /></div></label>
        <label class="form-field"><span class="field-label">요청 메모</span><div class="field-shell"><input class="field-input" name="requestMemo" value="${escapeHtml(item.normalizedFields?.requestMemo || "")}" placeholder="공급사 comments로 보낼 메모" /></div></label>
      </div>
      <div class="admin-action-row"><button class="admin-secondary-button" type="submit">수동 보정 저장</button></div>
    </form>
  `;
}
