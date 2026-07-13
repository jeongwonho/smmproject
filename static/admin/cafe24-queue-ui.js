export function renderCafe24QueueToolbar({ state, escapeHtml }) {
  const paymentFilter = state.ui.adminCafe24PaymentFilter || "all";
  const mappingFilter = state.ui.adminCafe24MappingFilter || "all";
  const statusFilter = state.ui.adminCafe24StatusFilter || "all";
  const search = state.ui.adminCafe24Search || "";
  const hasAdvancedFilter = paymentFilter !== "all" || mappingFilter !== "all" || statusFilter !== "all";
  const statuses = ["ready_to_submit", "waiting_input", "mapping_error", "auto_dispatch_excluded", "payment_pending", "payment_review_required", "split_scheduled", "split_in_progress", "supplier_submitted", "supplier_progress", "completed", "failed", "cancelled"];
  return `
    <form class="admin-toolbar cafe24-order-search" data-admin-cafe24-search-form>
      <div class="search-shell cafe24-order-search__field">
        <input class="search-input" type="search" name="q" value="${escapeHtml(search)}" placeholder="주문번호로 검색 (예: 20260617-000001)" data-admin-cafe24-filter="search" />
      </div>
      <button class="admin-primary-button" type="submit">검색</button>
      <button class="admin-secondary-button cafe24-order-search__clear" type="button" data-admin-cafe24-clear-search ${search ? "" : "hidden"}>초기화</button>
      <details class="admin-disclosure cafe24-filter-disclosure" ${hasAdvancedFilter ? "open" : ""}>
        <summary>결제/매핑/처리상태 필터${hasAdvancedFilter ? " 적용됨" : ""}</summary>
        <div class="cafe24-filter-grid">
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
      </details>
    </form>
  `;
}

export function formatCafe24KstDateTime(value, fallback = "") {
  const raw = String(value || "").trim();
  if (!raw) {
    return fallback;
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return raw;
  }
  const parts = new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(parsed);
  const part = (type) => parts.find((item) => item.type === type)?.value || "";
  return `${part("year")}. ${part("month")}. ${part("day")}. ${part("hour")}:${part("minute")} KST`;
}

const CAFE24_REQUIRED_ORDER_FLOW_SCOPES = ["mall.read_order", "mall.write_order", "mall.read_product"];

export function cafe24OrderFlowState(activeIntegration = {}) {
  if (!activeIntegration.id) {
    return {
      risk: true,
      status: "missing",
      label: "미연결",
      message: "Cafe24 OAuth 연결 후 주문 수집을 시작할 수 있습니다.",
      missingScopes: CAFE24_REQUIRED_ORDER_FLOW_SCOPES,
    };
  }
  const requiredScopes = Array.isArray(activeIntegration.requiredScopes) && activeIntegration.requiredScopes.length
    ? activeIntegration.requiredScopes
    : CAFE24_REQUIRED_ORDER_FLOW_SCOPES;
  const scopes = Array.isArray(activeIntegration.scopes) ? activeIntegration.scopes : [];
  const missingScopes = Array.isArray(activeIntegration.missingScopes)
    ? activeIntegration.missingScopes
    : requiredScopes.filter((scope) => !scopes.includes(scope));
  if (missingScopes.length) {
    return {
      risk: true,
      status: "insufficient_scope",
      label: "권한 부족",
      message: `Cafe24 주문 처리 권한이 부족합니다. 재연결 필요: ${missingScopes.join(", ")}`,
      missingScopes,
    };
  }
  if (activeIntegration.orderFlowReady === false || activeIntegration.orderFlowStatus && activeIntegration.orderFlowStatus !== "ready") {
    return {
      risk: true,
      status: activeIntegration.orderFlowStatus || "not_ready",
      label: activeIntegration.orderFlowStatusLabel || "점검 필요",
      message: activeIntegration.orderFlowStatusMessage || activeIntegration.lastSyncMessage || "Cafe24 주문 처리 상태를 확인해 주세요.",
      missingScopes,
    };
  }
  if (activeIntegration.lastSyncStatus === "failed") {
    return {
      risk: true,
      status: "collection_failed",
      label: "수집 실패",
      message: activeIntegration.lastSyncMessage || "최근 Cafe24 주문 수집이 실패했습니다.",
      missingScopes,
    };
  }
  return {
    risk: false,
    status: "ready",
    label: activeIntegration.orderFlowStatusLabel || "정상",
    message: activeIntegration.orderFlowStatusMessage || "Cafe24 주문 수집/발주 권한이 준비되어 있습니다.",
    missingScopes,
  };
}

export function cafe24AutoPollState(activeIntegration = {}) {
  const flowState = cafe24OrderFlowState(activeIntegration);
  if (flowState.risk) {
    return flowState;
  }
  const autoPollStatus = activeIntegration.lastAutoPollStatus || "never";
  if (autoPollStatus === "success") {
    return { risk: false, status: autoPollStatus, label: "정상", message: activeIntegration.lastAutoPollMessage || "" };
  }
  if (autoPollStatus === "running") {
    return { risk: false, status: autoPollStatus, label: "진행 중", message: activeIntegration.lastAutoPollMessage || "" };
  }
  if (autoPollStatus === "reconnect_required") {
    return { risk: true, status: autoPollStatus, label: "재연결 필요", message: activeIntegration.lastAutoPollMessage || "Cafe24 OAuth 재연결이 필요합니다." };
  }
  if (autoPollStatus === "failed") {
    return { risk: true, status: autoPollStatus, label: "실패", message: activeIntegration.lastAutoPollMessage || "최근 자동 수집이 실패했습니다." };
  }
  return { risk: false, status: autoPollStatus, label: "대기", message: activeIntegration.lastAutoPollMessage || "" };
}

export function renderCafe24AutoPollCards({ activeIntegration = {}, automation = {}, summary = {}, escapeHtml }) {
  const autoPollState = cafe24AutoPollState(activeIntegration);
  const autoPollStatus = autoPollState.status;
  const autoPollRisk = autoPollState.risk;
  const lastTick = automation.lastTick || {};
  const tickStatus = automation.lastTickStatus || lastTick.status || "never";
  const tickRisk = ["failed", "partial_failed"].includes(tickStatus) || Boolean(automation.paused);
  const cafe24Dispatch = lastTick.cafe24Dispatch || {};
  const completion = lastTick.cafe24Completion || {};
  const supplierHealth = lastTick.supplierHealth || {};
  const retryQueueCount = Number(summary.failedCount || 0) + Number(summary.reviewRequiredCount || 0);
  const lastTickLabel = formatCafe24KstDateTime(automation.lastTickAt || lastTick.finishedAt, "실행 이력 없음");
  const lastAutoPollLabel = autoPollRisk
    ? autoPollState.message
    : activeIntegration.lastAutoPollAt
      ? formatCafe24KstDateTime(activeIntegration.lastAutoPollAt)
    : activeIntegration.lastAutoPollMessage || "외부 스케줄러 미호출";
  const nextAutoPollLabel = activeIntegration.nextAutoPollAt
    ? formatCafe24KstDateTime(activeIntegration.nextAutoPollAt)
    : "5분 주기";
  return `
    <article class="${tickRisk ? "is-risk" : tickStatus === "success" ? "is-hot" : ""}">
      <span>자동화 Tick</span>
      <strong>${escapeHtml(automation.paused ? "긴급 중단" : tickStatus === "success" ? "정상" : tickStatus === "partial_failed" ? "부분 실패" : tickStatus === "failed" ? "실패" : "대기")}</strong>
      <small>${escapeHtml(lastTickLabel)}</small>
    </article>
    <article class="${autoPollRisk ? "is-risk" : autoPollStatus === "success" ? "is-hot" : ""}">
      <span>자동 수집</span>
      <strong>${escapeHtml(autoPollState.label)}</strong>
      <small>${escapeHtml(lastAutoPollLabel)}</small>
    </article>
    <article>
      <span>다음 예상 수집</span>
      <strong>${escapeHtml(nextAutoPollLabel)}</strong>
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
  } else if (status === "auto_dispatch_excluded") {
    tone = "is-neutral";
    label = "자동발주 제외";
    message = "개인결제 등 공급사 자동발주 대상이 아닌 품주입니다. 매핑 누락 경고가 아니라 운영자가 수동 처리 후 상태만 관리하는 항목입니다.";
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
