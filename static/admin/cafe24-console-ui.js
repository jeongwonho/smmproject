import { formatCafe24KstDateTime, renderCafe24SchedulerNotice } from "./cafe24-queue-ui.js";

export function renderCafe24OpsBoard({ state = {}, orderItems = [], mappings = [], activeIntegration = {}, escapeHtml, canDispatchItem }) {
  const summary = state.adminCafe24OrderList?.summary || {};
  const rangeLabel = state.adminCafe24OrderList?.pagination?.from && state.adminCafe24OrderList?.pagination?.to
    ? `${state.adminCafe24OrderList.pagination.from.slice(0, 10)} ~ ${state.adminCafe24OrderList.pagination.to.slice(0, 10)}`
    : "최근 1개월";
  const totalCount = Number(summary.totalCount ?? orderItems.length ?? 0);
  const paymentConfirmed = Number(summary.paymentConfirmedCount ?? orderItems.filter((item) => item.paymentGateStatus === "payment_confirmed").length);
  const readyToSubmit = Number(summary.readyToSubmitCount ?? orderItems.filter((item) => canDispatchItem(item)).length);
  const mappingMissing = Number(summary.unmappedCount ?? orderItems.filter((item) => item.paymentGateStatus === "payment_confirmed" && !item.mappingId && item.standardStatus !== "auto_dispatch_excluded").length);
  const autoDispatchExcluded = Number(summary.autoDispatchExcludedCount ?? orderItems.filter((item) => item.standardStatus === "auto_dispatch_excluded").length);
  const needsReview = Number(summary.reviewRequiredCount ?? orderItems.filter((item) => ["waiting_input", "mapping_error", "field_extract_failed", "missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error", "needs_manual_review", "payment_review_required"].includes(item.standardStatus)).length);
  const manualInputRequired = Number(summary.manualInputRequiredCount ?? orderItems.filter((item) => (
    item.paymentGateStatus === "payment_confirmed"
    && !item.supplierOrderUuid
    && ["waiting_input", "mapping_error", "missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error", "needs_manual_review"].includes(item.standardStatus)
  )).length);
  const failed = Number(summary.failedCount ?? orderItems.filter((item) => item.standardStatus === "failed").length);
  const tokenRisk = !activeIntegration.id || ["reconnect_required", "failed"].includes(activeIntegration.tokenStatus || "");
  const automation = state.adminBootstrap?.automation || {};
  const lastTick = automation.lastTick || {};
  const tickStatus = automation.lastTickStatus || lastTick.status || "never";
  const tickRisk = tickStatus === "failed" || Boolean(automation.paused);
  const autoPollStatus = activeIntegration.lastAutoPollStatus || "never";
  const autoPollRisk = ["failed", "reconnect_required"].includes(autoPollStatus);
  const autoPollLabel = autoPollStatus === "success"
    ? "정상"
    : autoPollStatus === "running"
      ? "진행 중"
      : autoPollStatus === "reconnect_required"
        ? "재연결 필요"
        : autoPollStatus === "failed"
          ? "실패"
          : "대기";
  const lastTickLabel = formatCafe24KstDateTime(automation.lastTickAt || lastTick.finishedAt, "GitHub Actions 5분 주기");
  const lastAutoPollLabel = activeIntegration.lastAutoPollAt
    ? formatCafe24KstDateTime(activeIntegration.lastAutoPollAt)
    : activeIntegration.lastAutoPollMessage || "아직 호출 기록 없음";
  return `
    <div class="cafe24-ops-board">
      <article class="${tokenRisk ? "is-risk" : ""}">
        <span>연결 상태</span>
        <strong>${escapeHtml(activeIntegration.tokenStatusLabel || "미연결")}</strong>
        <small>${escapeHtml(activeIntegration.mallId || "OAuth 연결 필요")}</small>
      </article>
      <article class="${tickRisk ? "is-risk" : tickStatus === "success" ? "is-hot" : ""}">
        <span>5분 자동화</span>
        <strong>${escapeHtml(automation.paused ? "긴급 중단" : tickStatus === "success" ? "정상" : tickStatus === "failed" ? "실패" : "대기")}</strong>
        <small>${escapeHtml(lastTickLabel)}</small>
      </article>
      <article class="${autoPollRisk ? "is-risk" : autoPollStatus === "success" ? "is-hot" : ""}">
        <span>주문 수집</span>
        <strong>${escapeHtml(autoPollLabel)}</strong>
        <small>${escapeHtml(lastAutoPollLabel)}</small>
      </article>
      <article>
        <span>최근 1개월 주문</span>
        <strong>${escapeHtml(String(totalCount))}</strong>
        <small>${escapeHtml(rangeLabel)} · 결제완료 ${escapeHtml(String(paymentConfirmed))}건</small>
      </article>
      <article class="${mappingMissing ? "is-risk" : ""}">
        <span>매핑 필요</span>
        <strong>${escapeHtml(String(mappingMissing))}</strong>
        <small>상품 매핑 ${escapeHtml(String(mappings.length))}개</small>
      </article>
      <article>
        <span>자동발주 제외</span>
        <strong>${escapeHtml(String(autoDispatchExcluded))}</strong>
        <small>개인결제/수동 처리 정책</small>
      </article>
      <article class="${needsReview ? "is-risk" : ""}">
        <span>검수 필요</span>
        <strong>${escapeHtml(String(needsReview))}</strong>
        <small>필드/결제/수량 확인</small>
      </article>
      <article class="${manualInputRequired ? "is-risk" : ""}">
        <span>수동 보정</span>
        <strong>${escapeHtml(String(manualInputRequired))}</strong>
        <small>개인결제/입력값 직접 보정</small>
      </article>
      <article class="${readyToSubmit ? "is-hot" : ""}">
        <span>발주 대기</span>
        <strong>${escapeHtml(String(readyToSubmit))}</strong>
        <small>자동/수동 발주 가능</small>
      </article>
      <article class="${failed ? "is-risk" : ""}">
        <span>발주 실패</span>
        <strong>${escapeHtml(String(failed))}</strong>
        <small>재시도/확인 필요</small>
      </article>
    </div>
  `;
}

export function renderCafe24QuickControls({ activeIntegration = {}, escapeHtml, origin = "" }) {
  return `
    <form class="admin-panel admin-form cafe24-quick-controls" data-admin-cafe24-integration-form>
      <input type="hidden" name="id" value="${escapeHtml(activeIntegration.id || "")}" />
      <input type="hidden" name="scopes" value="${escapeHtml((activeIntegration.scopes || ["mall.read_order", "mall.write_order", "mall.read_product"]).join(","))}" />
      <div class="section-head section-head--compact">
        <h3>주문번호 빠른 확인</h3>
        <p>메일에는 왔는데 큐에 없는 주문은 주문번호를 넣어 단건 재수집합니다. 자동 발주는 안전 조건을 통과한 품주만 서버 Tick에서 처리됩니다.</p>
      </div>
      <div class="cafe24-quick-lookup">
        <label class="form-field cafe24-control-grid__wide">
          <span class="field-label">주문번호 직접 조회</span>
          <div class="field-shell"><input class="field-input" name="resyncOrderId" placeholder="예: 20260506-000001" /></div>
        </label>
        <button class="admin-primary-button" type="button" data-admin-cafe24-resync-by-id="${escapeHtml(activeIntegration.id || "")}" ${activeIntegration.id ? "" : "disabled"}>단건 재수집</button>
      </div>
      <details class="admin-disclosure cafe24-advanced-controls">
        <summary>기간 수집/연동 설정 열기</summary>
        <div class="cafe24-control-grid">
          <label class="form-field">
            <span class="field-label">Mall ID</span>
            <div class="field-shell"><input class="field-input" name="mallId" value="${escapeHtml(activeIntegration.mallId || "")}" placeholder="예: instamart" /></div>
          </label>
          <label class="form-field">
            <span class="field-label">Shop No</span>
            <div class="field-shell"><input class="field-input" name="shopNo" type="number" value="${escapeHtml(String(activeIntegration.shopNo || 1))}" /></div>
          </label>
          <label class="form-field">
            <span class="field-label">수집 시작일</span>
            <div class="field-shell"><input class="field-input" name="pollStartDate" type="date" /></div>
          </label>
          <label class="form-field">
            <span class="field-label">수집 종료일</span>
            <div class="field-shell"><input class="field-input" name="pollEndDate" type="date" /></div>
          </label>
        </div>
        <div class="admin-action-row">
          <button class="admin-secondary-button" type="button" data-admin-cafe24-poll="${escapeHtml(activeIntegration.id || "")}" ${activeIntegration.id ? "" : "disabled"}>최근 1개월 수동 수집</button>
          <button class="admin-secondary-button" type="button" data-admin-cafe24-oauth-start>OAuth 연결/재연결</button>
          <button class="admin-secondary-button" type="submit">연동 저장</button>
        </div>
        <div class="admin-action-row">
          <label class="admin-toggle">
            <input type="checkbox" name="isActive" ${activeIntegration.isActive !== false ? "checked" : ""} />
            <span>연동 활성화</span>
          </label>
          <label class="admin-toggle"><input type="checkbox" name="autoSubmit" ${activeIntegration.autoSubmit !== false ? "checked" : ""} /><span>자동 발주 활성화</span></label>
        </div>
        <p class="admin-inline-note">자동 발주는 결제완료, 매핑완료, 공급사 상태 정상, 중복 발주 없음 조건을 모두 통과한 주문만 실행합니다. 긴급 중단은 <code>SMM_PANEL_AUTOMATION_PAUSED=1</code>로 제어합니다.</p>
        ${renderCafe24SchedulerNotice({ origin, escapeHtml })}
      </details>
    </form>
  `;
}
