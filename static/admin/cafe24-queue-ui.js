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

export function renderCafe24AutoPollCards({ activeIntegration = {}, escapeHtml }) {
  const autoPollStatus = activeIntegration.lastAutoPollStatus || "never";
  const autoPollRisk = ["failed", "reconnect_required"].includes(autoPollStatus);
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
  `;
}

export function renderCafe24SchedulerNotice({ origin, escapeHtml }) {
  const cronEndpoint = `${origin}/api/cron/cafe24/orders/poll`;
  return `
    <div class="admin-inline-note">
      <strong>10분 자동 수집 설정</strong><br />
      GitHub Actions 외부 스케줄러가 <code>POST ${escapeHtml(cronEndpoint)}</code>를 10분마다 호출하도록 구성되어 있습니다.
      다른 스케줄러를 추가할 때는 헤더 <code>Authorization: Bearer &lt;CRON_SECRET&gt;</code>를 사용하세요.
      Access token은 서버에서 자동 갱신하며, refresh token 만료/폐기 시에만 OAuth 재연결이 필요합니다.
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
