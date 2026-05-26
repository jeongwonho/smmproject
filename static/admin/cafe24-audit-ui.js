function badgeClass(ok, warn = false) {
  if (ok) return "is-success";
  return warn ? "is-warn" : "is-error";
}

function renderBadge(label, className, escapeHtml) {
  return `<span class="admin-badge ${className}">${escapeHtml(label)}</span>`;
}

function statusBadge(status, escapeHtml) {
  const value = String(status || "unknown");
  if (["connected", "ok", "success", "payment_confirmed"].includes(value)) return renderBadge(value, "is-success", escapeHtml);
  if (["token_expiring", "refreshing", "syncing", "unknown", "never"].includes(value)) return renderBadge(value, "is-warn", escapeHtml);
  if (["reconnect_required", "failed", "cancelled"].includes(value)) return renderBadge(value, "is-error", escapeHtml);
  return renderBadge(value, "is-neutral", escapeHtml);
}

function envStatusLabel(value) {
  return String(value || "") === "set" ? "set" : "unset";
}

function renderAuditEmpty(escapeHtml) {
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>운영 상태 Audit</h3>
        <p>현재 admin 세션으로 운영 DB/환경변수 기준 Cafe24 상태를 조회합니다.</p>
      </div>
      <div class="admin-empty-card">
        <strong>아직 조회하지 않았습니다.</strong>
        <p>토큰 값과 API Key 원문은 표시하지 않고, 설정 여부와 상태만 확인합니다.</p>
        <div class="admin-action-row">
          <button class="admin-primary-button" type="button" data-admin-cafe24-operational-audit-refresh>운영 상태 조회</button>
        </div>
      </div>
    </div>
  `;
}

function renderAuditSummary(audit, escapeHtml) {
  const counts = audit.counts || {};
  const mappings = audit.cafe24Mappings || {};
  const orderItems = audit.cafe24OrderItems || {};
  const dispatchPolicy = audit.cafe24DispatchPolicy || {};
  const integrations = audit.cafe24Integrations || [];
  const reconnectCount = integrations.filter((item) => ["reconnect_required", "failed"].includes(item.tokenStatus)).length;
  const orderSummary = orderItems.summary || {};
  const readyCount = Number(orderSummary.readyToSubmitCount ?? orderItems.standardStatusCounts?.ready_to_submit ?? 0);
  const manualInputCount = Number(orderSummary.manualInputRequiredCount || 0);
  const policyOk = dispatchPolicy.canAutoDispatchNow || dispatchPolicy.status === "manual_mapping_mode";
  return `
    <div class="admin-insight-grid admin-insight-grid--compact">
      <article class="admin-insight-card">
        <span>DB backend</span>
        <strong>${escapeHtml(audit.environment?.databaseBackend || "-")}</strong>
        <p>${escapeHtml(audit.environment?.runtimeMode || "local")}</p>
      </article>
      <article class="admin-insight-card ${reconnectCount ? "is-warning" : "is-success"}">
        <span>Cafe24 토큰</span>
        <strong>${escapeHtml(reconnectCount ? `${reconnectCount}개 재연결` : "점검 가능")}</strong>
        <p>연동 ${escapeHtml(String(counts.cafe24_integrations || 0))}개</p>
      </article>
      <article class="admin-insight-card">
        <span>상품 매핑</span>
        <strong>${escapeHtml(String(mappings.enabled || 0))}</strong>
        <p>자동 발주 ${escapeHtml(String(mappings.autoDispatchEnabled || 0))}개</p>
      </article>
      <article class="admin-insight-card ${policyOk ? "is-success" : "is-warning"}">
        <span>자동 발주 정책</span>
        <strong>${escapeHtml(dispatchPolicy.canAutoDispatchNow ? "autoSubmit ON" : "autoSubmit OFF")}</strong>
        <p>${escapeHtml(dispatchPolicy.message || "Cafe24 autoSubmit과 매핑 자동발주 상태를 확인합니다.")}</p>
      </article>
      <article class="admin-insight-card ${readyCount ? "is-success" : ""}">
        <span>최근 품주</span>
        <strong>${escapeHtml(String(counts.cafe24_order_items || 0))}</strong>
        <p>발주 대기 ${escapeHtml(String(readyCount))}개</p>
      </article>
      <article class="admin-insight-card ${manualInputCount ? "is-warning" : "is-success"}">
        <span>수동 보정</span>
        <strong>${escapeHtml(String(manualInputCount))}</strong>
        <p>개인결제/필드 보정 필요</p>
      </article>
    </div>
  `;
}

function renderEnvironment(audit, escapeHtml) {
  const env = audit.environment?.env || {};
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>환경/DB</h3>
        <p>${escapeHtml(audit.environment?.productionRuntime ? "production runtime" : "non-production runtime")} · ${escapeHtml(audit.fetchedAt || "")}</p>
      </div>
      <div class="admin-mapping-preview">
        ${Object.entries(env).map(([key, value]) => `
          <article class="admin-mini-card">
            <span>${escapeHtml(key)}</span>
            <strong>${escapeHtml(envStatusLabel(value))}</strong>
            ${renderBadge(envStatusLabel(value), value === "set" ? "is-success" : "is-neutral", escapeHtml)}
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

function renderIntegrations(audit, escapeHtml) {
  const integrations = audit.cafe24Integrations || [];
  const dispatchPolicy = audit.cafe24DispatchPolicy || {};
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>Cafe24 연동/Tokens</h3>
        <p>토큰 원문 없이 저장 여부, 만료, 재연결 필요 여부와 autoSubmit 정책을 표시합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        <article class="admin-mini-card ${dispatchPolicy.canAutoDispatchNow ? "" : "is-risk"}">
          <span>운영 발주 모드</span>
          <strong>${escapeHtml(dispatchPolicy.status || "unknown")}</strong>
          <p>${escapeHtml(dispatchPolicy.message || "")}</p>
        </article>
        <article class="admin-mini-card">
          <span>자동 발주 후보</span>
          <strong>${escapeHtml(String(dispatchPolicy.autoSubmitReadyItemCount || 0))}건</strong>
          <p>수동 승인 대기 ${escapeHtml(String(dispatchPolicy.manualReadyItemCount || 0))}건 · 자동매핑 ${escapeHtml(String(dispatchPolicy.autoDispatchMappingCount || 0))}개</p>
        </article>
      </div>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>Mall</th><th>Token</th><th>저장 상태</th><th>Auto submit</th><th>Poll</th><th>Sync</th></tr></thead>
          <tbody>
            ${integrations.length ? integrations.map((item) => `
              <tr>
                <td>${escapeHtml(item.mallId || "-")} / ${escapeHtml(String(item.shopNo || 1))}</td>
                <td>${statusBadge(item.tokenStatus, escapeHtml)}<br />${escapeHtml(item.tokenStatusMessage || "")}</td>
                <td>Access ${escapeHtml(item.hasAccessToken ? "set" : "unset")} · Refresh ${escapeHtml(item.hasRefreshToken ? "set" : "unset")}<br />Refresh 만료 ${escapeHtml(item.refreshTokenExpiresAt || "-")}</td>
                <td>${renderBadge(item.autoSubmit ? "ON" : "OFF", item.autoSubmit ? "is-success" : "is-warn", escapeHtml)}<br />${escapeHtml(item.autoSubmit ? "자동 발주 후보 포함" : "수동 승인/단건 발주 모드")}</td>
                <td>${escapeHtml(item.lastPollAt || "-")}<br />${escapeHtml(item.pollCursor || "")}</td>
                <td>${statusBadge(item.lastSyncStatus, escapeHtml)}<br />${escapeHtml(item.lastSyncMessage || item.updatedAt || "")}</td>
              </tr>
            `).join("") : `<tr><td colspan="6">Cafe24 연동이 없습니다.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMappings(audit, escapeHtml) {
  const mappings = audit.cafe24Mappings?.recent || [];
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>최근 매핑</h3>
        <p>상품번호/품목코드/자체상품코드가 공급사 서비스와 연결된 상태입니다.</p>
      </div>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>Cafe24 키</th><th>공급사</th><th>상태</th><th>수정일</th></tr></thead>
          <tbody>
            ${mappings.length ? mappings.map((item) => `
              <tr>
                <td>${escapeHtml([item.cafe24ProductNo, item.cafe24VariantCode, item.cafe24CustomProductCode].filter(Boolean).join(" / ") || "-")}</td>
                <td>${escapeHtml(item.supplierName || item.supplierId || "-")}<br />${escapeHtml(item.supplierServiceName || item.supplierExternalServiceId || item.supplierServiceId || "-")}</td>
                <td>${renderBadge(item.enabled ? "활성" : "비활성", item.enabled ? "is-success" : "is-neutral", escapeHtml)} ${item.autoDispatchEnabled ? renderBadge("자동발주", "is-warn", escapeHtml) : ""}</td>
                <td>${escapeHtml(item.updatedAt || "-")}</td>
              </tr>
            `).join("") : `<tr><td colspan="4">최근 매핑이 없습니다.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderOrderItems(audit, escapeHtml) {
  const orderItems = audit.cafe24OrderItems?.recent || [];
  const statusCounts = audit.cafe24OrderItems?.standardStatusCounts || {};
  const paymentCounts = audit.cafe24OrderItems?.paymentGateStatusCounts || {};
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>최근 주문 품주</h3>
        <p>상태: ${escapeHtml(JSON.stringify(statusCounts))} · 결제: ${escapeHtml(JSON.stringify(paymentCounts))}</p>
      </div>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>주문/품주</th><th>상품 키</th><th>상태</th><th>공급사</th><th>최근 처리</th></tr></thead>
          <tbody>
            ${orderItems.length ? orderItems.map((item) => `
              <tr>
                <td>${escapeHtml(item.orderId || "-")}<br />${escapeHtml(item.orderItemCode || "-")}</td>
                <td>${escapeHtml([item.productNo, item.variantCode, item.customProductCode].filter(Boolean).join(" / ") || "-")}</td>
                <td>${statusBadge(item.standardStatus, escapeHtml)}<br />${statusBadge(item.paymentGateStatus, escapeHtml)}</td>
                <td>${escapeHtml(item.supplierExternalServiceId || item.supplierServiceId || "-")}<br />${escapeHtml(item.supplierOrderUuid || "")}</td>
                <td>${escapeHtml(item.lastSyncedAt || item.updatedAt || "-")}<br />${escapeHtml(item.errorMessage || item.automationErrorCode || "")}</td>
              </tr>
            `).join("") : `<tr><td colspan="5">최근 Cafe24 품주가 없습니다.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderSuppliers(audit, escapeHtml) {
  const suppliers = audit.suppliers || [];
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>공급사 readiness</h3>
        <p>service sync, health check, balance 상태와 활성 서비스 수를 함께 확인합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        ${suppliers.map((item) => `
          <article class="admin-mini-card ${item.healthStatus === "failed" || item.serviceSyncStatus === "failed" ? "is-risk" : ""}">
            <span>${escapeHtml(item.integrationType || "classic")}</span>
            <strong>${escapeHtml(item.name || item.id)}</strong>
            <p>서비스 ${escapeHtml(String(item.activeServiceCount || 0))}개 · 비활성 ${escapeHtml(String(item.inactiveServiceCount || 0))}개</p>
            <p>sync ${escapeHtml(item.serviceSyncStatus || "never")} · health ${escapeHtml(item.healthStatus || "unknown")} · balance ${escapeHtml(item.balanceStatus || "unknown")}</p>
          </article>
        `).join("") || `<div class="admin-empty-card"><strong>공급사가 없습니다.</strong></div>`}
      </div>
    </div>
  `;
}

export function renderCafe24OperationalAuditPanel({ audit, escapeHtml }) {
  if (!audit) return renderAuditEmpty(escapeHtml);
  return `
    <div class="admin-stack">
      <div class="admin-action-row admin-action-row--top">
        <button class="admin-primary-button" type="button" data-admin-cafe24-operational-audit-refresh>운영 상태 다시 조회</button>
      </div>
      ${renderAuditSummary(audit, escapeHtml)}
      ${renderEnvironment(audit, escapeHtml)}
      ${renderIntegrations(audit, escapeHtml)}
      ${renderMappings(audit, escapeHtml)}
      ${renderOrderItems(audit, escapeHtml)}
      ${renderSuppliers(audit, escapeHtml)}
    </div>
  `;
}
