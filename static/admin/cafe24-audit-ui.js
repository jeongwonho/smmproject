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

function numberValue(value, fallback = 0) {
  const nextValue = Number(value);
  return Number.isFinite(nextValue) ? nextValue : fallback;
}

function auditSchemaGaps(audit = {}) {
  const gaps = [];
  if (!audit.operationalReadiness || !Array.isArray(audit.operationalReadiness.checks)) {
    gaps.push("operationalReadiness");
  }
  if (!audit.cafe24ManualWorkflow || typeof audit.cafe24ManualWorkflow !== "object" || !audit.cafe24ManualWorkflow.status) {
    gaps.push("cafe24ManualWorkflow");
  }
  if (!Array.isArray(audit.supplierReadinessByIntegration)) {
    gaps.push("supplierReadinessByIntegration");
  }
  if (!audit.environment?.cronAuth) {
    gaps.push("environment.cronAuth");
  }
  return gaps;
}

function renderAuditSchemaNotice(audit, escapeHtml) {
  const gaps = auditSchemaGaps(audit);
  if (!gaps.length) return "";
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>Audit schema 확인</h3>
        <p>현재 응답이 일부 최신 운영 판정 필드를 포함하지 않습니다.</p>
      </div>
      <div class="admin-inline-note">
        <strong>누락 필드</strong> ${escapeHtml(gaps.join(", "))}
        <br />아래 화면은 legacy 필드 기준으로 요약합니다. 정확한 next workflow와 통합 readiness 판정은 운영 배포가 최신 schema를 반환한 뒤 확인해야 합니다.
      </div>
    </div>
  `;
}

function readinessRequirementClass(requirement = {}) {
  if (requirement.ok === true || requirement.status === "pass") return "is-success";
  if (requirement.blocking === true || requirement.status === "blocked") return "is-error";
  return "is-warn";
}

function renderReadinessRequirementList(requirements = [], escapeHtml) {
  if (!requirements.length) return "";
  return `
    <div class="admin-readiness-checks">
      ${requirements.map((requirement) => `
        <div class="admin-readiness-check">
          <div class="admin-readiness-check__text">
            <strong>${escapeHtml(requirement.label || requirement.key || "조건")} ${requirement.value ? `· ${escapeHtml(requirement.value)}` : ""}</strong>
            <span>${escapeHtml(requirement.message || requirement.code || "")}</span>
          </div>
          ${renderBadge(requirement.status || (requirement.ok ? "pass" : "check"), readinessRequirementClass(requirement), escapeHtml)}
        </div>
      `).join("")}
    </div>
  `;
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
  const readyWithSupplierOrderCount = Number(orderSummary.readyWithSupplierOrderCount || 0);
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
      <article class="admin-insight-card ${readyWithSupplierOrderCount ? "is-warning" : "is-success"}">
        <span>중복 발주 방지</span>
        <strong>${escapeHtml(String(readyWithSupplierOrderCount))}</strong>
        <p>ready 상태지만 공급사 주문번호가 있어 발주 차단</p>
      </article>
    </div>
  `;
}

function renderLegacyOperationalReadiness(audit, escapeHtml) {
  const integrations = audit.cafe24Integrations || [];
  const activeIntegrations = integrations.filter((item) => item.isActive);
  const connectedIntegrations = activeIntegrations.filter((item) => ["connected", "token_expiring"].includes(item.tokenStatus));
  const reconnectIntegrations = activeIntegrations.filter((item) => ["reconnect_required", "failed"].includes(item.tokenStatus));
  const dispatchPolicy = audit.cafe24DispatchPolicy || {};
  const orderSummary = audit.cafe24OrderItems?.summary || {};
  const suppliers = audit.suppliers || [];
  const supplierReadyCount = suppliers.filter((item) => item.autoDispatchReadiness?.ok === true).length;
  const supplierBlockedCount = suppliers.filter((item) => item.autoDispatchReadiness && item.autoDispatchReadiness.ok !== true).length;
  const readyCount = numberValue(orderSummary.readyToSubmitCount ?? dispatchPolicy.readyItemCount);
  const manualInputCount = numberValue(orderSummary.manualInputRequiredCount);
  const reviewCount = numberValue(orderSummary.reviewRequiredCount);
  const excludedCount = numberValue(orderSummary.autoDispatchExcludedCount);
  const cards = [
    {
      label: "Cafe24 token",
      value: `${connectedIntegrations.length} connected`,
      detail: reconnectIntegrations.length ? `${reconnectIntegrations.length}개 재연결 필요` : "활성 연동 token 상태 확인됨",
      ok: connectedIntegrations.length > 0 && reconnectIntegrations.length === 0,
    },
    {
      label: "발주 정책",
      value: dispatchPolicy.status || "unknown",
      detail: dispatchPolicy.message || "legacy 응답의 cafe24DispatchPolicy 기준",
      ok: dispatchPolicy.canAutoDispatchNow || ["manual_approval_mode", "manual_mapping_mode"].includes(dispatchPolicy.status),
    },
    {
      label: "주문 큐",
      value: `${readyCount} ready`,
      detail: `수동 보정 ${manualInputCount}건 · 검토 ${reviewCount}건 · 제외 ${excludedCount}건`,
      ok: readyCount > 0 && manualInputCount === 0 && reviewCount === 0,
    },
    {
      label: "공급사",
      value: `${supplierReadyCount} ready`,
      detail: supplierBlockedCount ? `${supplierBlockedCount}개 차단/확인 필요` : "공급사별 readiness 통과",
      ok: supplierReadyCount > 0 && supplierBlockedCount === 0,
    },
  ];
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>운영 readiness</h3>
        <p>최신 readiness payload가 없어 legacy 필드로만 요약합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        ${cards.map((card) => `
          <article class="admin-mini-card ${card.ok ? "" : "is-risk"}">
            <span>${escapeHtml(card.label)}</span>
            <strong>${escapeHtml(card.value)}</strong>
            <p>${escapeHtml(card.detail)}</p>
            ${renderBadge(card.ok ? "확인됨" : "확인 필요", card.ok ? "is-success" : "is-warn", escapeHtml)}
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

function renderOperationalReadiness(audit, escapeHtml) {
  const readiness = audit.operationalReadiness || {};
  if (!Array.isArray(readiness.checks)) {
    return renderLegacyOperationalReadiness(audit, escapeHtml);
  }
  const checks = Array.isArray(readiness.checks) ? readiness.checks : [];
  const status = readiness.status || "unknown";
  const statusClass = status === "ready" ? "is-success" : status === "blocked" ? "is-error" : "is-warn";
  const checkClass = (check) => {
    if (check.status === "pass" || check.ok === true) return "is-success";
    if (check.status === "blocked" || check.severity === "critical") return "is-error";
    return "is-warn";
  };
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>운영 readiness</h3>
        <p>운영 DB/env 기준으로 Cafe24 주문 수집, 매핑, 발주 후보, 공급사 상태를 한 번에 판정합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        <article class="admin-mini-card ${status === "blocked" ? "is-risk" : ""}">
          <span>상태</span>
          <strong>${escapeHtml(status)}</strong>
          <p>${escapeHtml(readiness.message || "")}</p>
          ${renderBadge(status, statusClass, escapeHtml)}
        </article>
        <article class="admin-mini-card">
          <span>차단/확인</span>
          <strong>${escapeHtml(String(readiness.blockedCount || 0))} / ${escapeHtml(String(readiness.warningCount || 0))}</strong>
          <p>blocked는 필수 조치, warning은 발주 전 운영 확인 항목입니다.</p>
        </article>
      </div>
      <div class="admin-readiness-checks">
        ${checks.map((check) => `
          <div class="admin-readiness-check">
            <div class="admin-readiness-check__text">
              <strong>${escapeHtml(check.label || check.key || "조건")} ${check.value ? `· ${escapeHtml(check.value)}` : ""}</strong>
              <span>${escapeHtml(check.message || "")}</span>
            </div>
            ${renderBadge(check.status || check.severity || "unknown", checkClass(check), escapeHtml)}
          </div>
        `).join("") || `<div class="admin-empty-card"><strong>readiness check가 없습니다.</strong></div>`}
      </div>
    </div>
  `;
}

function legacyManualWorkflowStatus({ readyCount, manualInputCount, reviewCount, readyWithSupplierOrderCount }) {
  if (readyCount > 0) {
    return {
      status: "preflight_required",
      nextWorkflow: "Cafe24 Preflight One",
      nextAction: "legacy 응답에서는 후보 목록을 만들 수 없습니다. 주문 품주 목록에서 ready_to_submit 대상의 preflight를 먼저 확인하세요.",
    };
  }
  if (manualInputCount > 0 || reviewCount > 0) {
    return {
      status: "manual_input_required",
      nextWorkflow: "Cafe24 Mapping Gaps",
      nextAction: "수동 보정/검토 품주가 있습니다. mapping gaps와 manual input preview로 대상값과 수량을 먼저 확인하세요.",
    };
  }
  if (readyWithSupplierOrderCount > 0) {
    return {
      status: "supplier_status_required",
      nextWorkflow: "Cafe24 Check Supplier Status",
      nextAction: "공급사 주문번호가 있는 품주는 중복 발주하지 말고 상태 조회와 완료 처리를 확인하세요.",
    };
  }
  return {
    status: "waiting_for_orders",
    nextWorkflow: "Cafe24 Order Poll",
    nextAction: "현재 legacy 응답 기준으로 즉시 처리할 품주가 없습니다.",
  };
}

function renderLegacyManualWorkflow(audit, escapeHtml) {
  const dispatchPolicy = audit.cafe24DispatchPolicy || {};
  const orderSummary = audit.cafe24OrderItems?.summary || {};
  const readyCount = numberValue(orderSummary.readyToSubmitCount ?? dispatchPolicy.readyItemCount);
  const manualInputCount = numberValue(orderSummary.manualInputRequiredCount);
  const reviewCount = numberValue(orderSummary.reviewRequiredCount);
  const readyWithSupplierOrderCount = numberValue(orderSummary.readyWithSupplierOrderCount);
  const workflow = legacyManualWorkflowStatus({
    readyCount,
    manualInputCount,
    reviewCount,
    readyWithSupplierOrderCount,
  });
  const statusClass = workflow.status === "waiting_for_orders" ? "is-neutral" : "is-warn";
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>수동 보정/단건 발주 작업</h3>
        <p>최신 workflow payload가 없어 legacy queue count 기준으로만 다음 작업을 제안합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        <article class="admin-mini-card ${workflow.status === "waiting_for_orders" ? "" : "is-risk"}">
          <span>다음 상태</span>
          <strong>${escapeHtml(workflow.status)}</strong>
          <p>${escapeHtml(workflow.nextAction)}</p>
          ${renderBadge(workflow.nextWorkflow, statusClass, escapeHtml)}
        </article>
        <article class="admin-mini-card ${readyCount ? "" : "is-risk"}">
          <span>단건 발주 후보</span>
          <strong>${escapeHtml(String(readyCount))}건</strong>
          <p>legacy 응답에서는 preflight 입력값 목록이 제공되지 않습니다.</p>
        </article>
        <article class="admin-mini-card ${manualInputCount || reviewCount ? "is-risk" : ""}">
          <span>수동 보정/검토</span>
          <strong>${escapeHtml(String(manualInputCount))} / ${escapeHtml(String(reviewCount))}건</strong>
          <p>target secret과 수량 확인은 최신 manual workflow payload에서 정확히 표시됩니다.</p>
        </article>
        <article class="admin-mini-card ${readyWithSupplierOrderCount ? "is-risk" : ""}">
          <span>중복 발주 방지</span>
          <strong>${escapeHtml(String(readyWithSupplierOrderCount))}건</strong>
          <p>공급사 주문번호가 있으면 발주 대신 상태 조회를 우선합니다.</p>
        </article>
      </div>
    </div>
  `;
}

function renderManualWorkflow(audit, escapeHtml) {
  const workflow = audit.cafe24ManualWorkflow || {};
  if (!workflow.status) {
    return renderLegacyManualWorkflow(audit, escapeHtml);
  }
  const requiredSecrets = Array.isArray(workflow.requiredSecretNames) ? workflow.requiredSecretNames : [];
  const manualCandidates = Array.isArray(workflow.manualInputCandidates) ? workflow.manualInputCandidates : [];
  const dispatchCandidates = Array.isArray(workflow.dispatchCandidates) ? workflow.dispatchCandidates : [];
  const status = workflow.status || "unknown";
  const statusClass = status === "dispatch_ready" || status === "manual_input_required"
    ? "is-success"
    : status === "blocked" || status === "supplier_readiness_required"
      ? "is-error"
      : "is-warn";
  const renderInputs = (inputs = {}) => Object.entries(inputs)
    .map(([key, value]) => `${key}=${value}`)
    .join(" · ");
  const renderCandidateRows = (candidates, emptyMessage) => candidates.length ? candidates.map((item) => `
    <tr>
      <td>${escapeHtml(item.orderId || "-")}<br />${escapeHtml(item.orderItemCode || "-")}</td>
      <td>${escapeHtml([item.productNo, item.variantCode, item.customProductCode].filter(Boolean).join(" / ") || "-")}</td>
      <td>${statusBadge(item.standardStatus, escapeHtml)}<br />${escapeHtml(item.errorMessage || item.automationErrorCode || "")}</td>
      <td>${escapeHtml(item.nextWorkflow || "-")}<br />${escapeHtml(renderInputs(item.workflowInputs || {}))}</td>
    </tr>
  `).join("") : `<tr><td colspan="4">${escapeHtml(emptyMessage)}</td></tr>`;
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>수동 보정/단건 발주 작업</h3>
        <p>실제 대상값은 화면에 표시하지 않고, 다음 workflow와 차단 조건만 운영자가 확인합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        <article class="admin-mini-card ${status === "blocked" || status === "supplier_readiness_required" ? "is-risk" : ""}">
          <span>다음 상태</span>
          <strong>${escapeHtml(status)}</strong>
          <p>${escapeHtml(workflow.nextAction || "")}</p>
          ${renderBadge(workflow.nextWorkflow || "확인 필요", statusClass, escapeHtml)}
        </article>
        <article class="admin-mini-card ${Number(workflow.dispatchReadyCount || 0) ? "" : "is-risk"}">
          <span>단건 발주 후보</span>
          <strong>${escapeHtml(String(workflow.dispatchReadyCount || 0))}건</strong>
          <p>수동 보정 없이 발주 가능: ${escapeHtml(workflow.canDispatchWithoutManualInput ? "예" : "아니오")}</p>
        </article>
        <article class="admin-mini-card ${Number(workflow.manualInputRequiredCount || 0) ? "is-risk" : ""}">
          <span>수동 보정 후보</span>
          <strong>${escapeHtml(String(workflow.manualInputRequiredCount || 0))}건</strong>
          <p>공급사 ready ${escapeHtml(String(workflow.supplierReadyCount || 0))}곳 · 매핑 필요 ${escapeHtml(String(workflow.mappingRequiredCount || 0))}건 · 자동발주 제외 ${escapeHtml(String(workflow.autoDispatchExcludedCount || 0))}건</p>
        </article>
        <article class="admin-mini-card">
          <span>Secret 입력 규칙</span>
          <strong>${escapeHtml(requiredSecrets[0] || "CAFE24_MANUAL_TARGET_VALUE")}</strong>
          <p>${escapeHtml(workflow.safeInputRule || "고객 대상값은 repository secret으로만 전달합니다.")}</p>
        </article>
      </div>
      <div class="admin-inline-note">
        <strong>허용된 target secret</strong><br />
        ${escapeHtml(requiredSecrets.join(", ") || "CAFE24_MANUAL_TARGET_VALUE")}
        <br />${escapeHtml(workflow.secretVisibility || "repository secret 존재 여부는 앱 런타임에서 직접 확인할 수 없습니다.")}
      </div>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>주문/품주</th><th>상품 키</th><th>상태</th><th>다음 workflow 입력</th></tr></thead>
          <tbody>
            ${renderCandidateRows(manualCandidates, "수동 보정 후보가 없습니다.")}
          </tbody>
        </table>
      </div>
      ${dispatchCandidates.length ? `
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>주문/품주</th><th>상품 키</th><th>상태</th><th>preflight 입력</th></tr></thead>
            <tbody>
              ${renderCandidateRows(dispatchCandidates, "단건 발주 후보가 없습니다.")}
            </tbody>
          </table>
        </div>
      ` : ""}
    </div>
  `;
}

function renderEnvironment(audit, escapeHtml) {
  const environment = audit.environment || {};
  const env = audit.environment?.env || {};
  const cronAuth = environment.cronAuth || {};
  const runtimeMode = environment.runtimeMode || (environment.productionRuntime ? "production" : "local");
  const runtimeSource = environment.runtimeModeSource || "legacy";
  const databaseBackend = environment.databaseBackend || "unknown";
  const sqlitePath = environment.sqlitePath || "";
  const runtimeCards = [
    {
      key: "Runtime mode",
      value: runtimeMode,
      detail: `source ${runtimeSource} · ${environment.productionRuntime ? "production runtime" : "non-production runtime"}`,
      status: environment.productionRuntime && runtimeMode === "local" ? "warning" : "ok",
    },
    {
      key: "Database backend",
      value: databaseBackend,
      detail: databaseBackend === "sqlite" && sqlitePath ? sqlitePath : "운영 DB 연결 기준",
      status: environment.productionRuntime && databaseBackend === "sqlite" ? "warning" : "ok",
    },
    {
      key: "Cron auth",
      value: cronAuth.status || "legacy",
      detail: cronAuth.message || "CRON_SECRET 또는 GitHub Actions OIDC 토큰으로 cron API를 호출합니다.",
      status: cronAuth.githubActionsVerifier === "oidc" || cronAuth.serverSecretConfigured ? "ok" : "warning",
    },
    {
      key: "Expected Actions repo",
      value: cronAuth.expectedRepository || "jeongwonho/smmproject",
      detail: `audience ${cronAuth.expectedAudience || "instamart-cron"} · events ${(cronAuth.acceptedEvents || ["schedule", "workflow_dispatch"]).join(", ")} · sources ${(cronAuth.acceptedBearerSources || ["cron_secret", "github_actions_oidc"]).join(", ")}`,
      status: "ok",
    },
  ];
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>환경/DB</h3>
        <p>${escapeHtml(runtimeMode)} · ${escapeHtml(databaseBackend)} · ${escapeHtml(audit.fetchedAt || "")}</p>
      </div>
      <div class="admin-mapping-preview">
        ${runtimeCards.map((item) => `
          <article class="admin-mini-card ${item.status === "warning" ? "is-risk" : ""}">
            <span>${escapeHtml(item.key)}</span>
            <strong>${escapeHtml(item.value)}</strong>
            <p>${escapeHtml(item.detail)}</p>
            ${renderBadge(item.status === "warning" ? "확인 필요" : "확인됨", item.status === "warning" ? "is-warn" : "is-success", escapeHtml)}
          </article>
        `).join("")}
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
  const integrationSummaries = Array.isArray(audit.supplierReadinessByIntegration) ? audit.supplierReadinessByIntegration : [];
  const hasIntegrationSummaries = Array.isArray(audit.supplierReadinessByIntegration);
  const statusClass = (status) => {
    if (status === "ready") return "is-success";
    if (status === "blocked") return "is-error";
    if (status === "not_configured") return "is-neutral";
    return "is-warn";
  };
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>공급사 readiness</h3>
        <p>MKT24, FastTraffic, classic별 service sync, health check, 발주 계약 조건을 함께 확인합니다.</p>
      </div>
      ${hasIntegrationSummaries ? "" : `
        <div class="admin-inline-note">
          <strong>통합 readiness 요약 없음</strong><br />
          현재 audit 응답에는 공급사 유형별 집계가 없습니다. 아래 공급사별 readiness만 legacy 필드 기준으로 확인하세요.
        </div>
      `}
      ${integrationSummaries.length ? `
        <div class="admin-mapping-preview">
          ${integrationSummaries.map((item) => {
            const contract = item.dispatchContract || {};
            const blockedCodes = Array.isArray(item.blockedCodes) ? item.blockedCodes.filter(Boolean) : [];
            const reviewCodes = Array.isArray(item.reviewCodes) ? item.reviewCodes.filter(Boolean) : [];
            return `
              <article class="admin-mini-card ${item.status === "blocked" ? "is-risk" : ""}">
                <span>${escapeHtml(item.label || item.integrationType || "공급사")}</span>
                <strong>${escapeHtml(String(item.readySupplierCount || 0))} / ${escapeHtml(String(item.supplierCount || 0))} ready</strong>
                <p>서비스 ${escapeHtml(String(item.activeServiceCount || 0))}개 · sync ${escapeHtml((item.serviceSyncStatuses || []).join(", ") || "-")} · health ${escapeHtml((item.healthStatuses || []).join(", ") || "-")}</p>
                <p>contract ${escapeHtml(contract.endpointMode || "-")} · ${escapeHtml(contract.authMode || "-")} · ${escapeHtml(contract.serviceIdRule || "-")}</p>
                <p>${escapeHtml(item.message || "")}</p>
                ${blockedCodes.length ? `<p>blocked ${escapeHtml(blockedCodes.join(", "))}</p>` : ""}
                ${reviewCodes.length ? `<p>review ${escapeHtml(reviewCodes.join(", "))}</p>` : ""}
                ${renderBadge(item.status || "unknown", statusClass(item.status), escapeHtml)}
              </article>
            `;
          }).join("")}
        </div>
      ` : ""}
      <div class="admin-mapping-preview">
        ${suppliers.map((item) => {
          const readiness = item.autoDispatchReadiness || {};
          const readinessOk = readiness.ok === true;
          const readinessCode = readiness.code || "unknown";
          const readinessClass = readinessOk ? "is-success" : readiness.retryable ? "is-warn" : "is-error";
          const requirements = Array.isArray(readiness.requirements) ? readiness.requirements : [];
          const contract = readiness.dispatchContract || {};
          const reviewCodes = Array.isArray(readiness.reviewCodes) ? readiness.reviewCodes.filter(Boolean) : [];
          return `
            <article class="admin-mini-card ${readinessOk ? "" : "is-risk"}">
              <span>${escapeHtml(item.integrationType || "classic")}</span>
              <strong>${escapeHtml(item.name || item.id)}</strong>
              <p>서비스 ${escapeHtml(String(item.activeServiceCount || 0))}개 · 비활성 ${escapeHtml(String(item.inactiveServiceCount || 0))}개</p>
              <p>sync ${escapeHtml(item.serviceSyncStatus || "never")} · health ${escapeHtml(item.healthStatus || "unknown")} · balance ${escapeHtml(item.balanceStatus || "unknown")}</p>
              <p>contract ${escapeHtml(contract.label || item.integrationType || "classic")} · ${escapeHtml(contract.endpointMode || "-")} · ${escapeHtml(contract.authMode || "-")} · ${escapeHtml(contract.serviceIdRule || "-")}</p>
              <p>readiness ${escapeHtml(readinessCode)} · ${escapeHtml(readiness.nextAction || readiness.message || "상세 메시지 없음")}</p>
              ${reviewCodes.length ? `<p>review ${escapeHtml(reviewCodes.join(", "))}</p>` : ""}
              ${renderBadge(readinessOk ? "발주 가능" : "발주 차단", readinessClass, escapeHtml)}
              ${renderReadinessRequirementList(requirements, escapeHtml)}
            </article>
          `;
        }).join("") || `<div class="admin-empty-card"><strong>공급사가 없습니다.</strong></div>`}
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
      ${renderAuditSchemaNotice(audit, escapeHtml)}
      ${renderAuditSummary(audit, escapeHtml)}
      ${renderOperationalReadiness(audit, escapeHtml)}
      ${renderManualWorkflow(audit, escapeHtml)}
      ${renderEnvironment(audit, escapeHtml)}
      ${renderIntegrations(audit, escapeHtml)}
      ${renderMappings(audit, escapeHtml)}
      ${renderOrderItems(audit, escapeHtml)}
      ${renderSuppliers(audit, escapeHtml)}
    </div>
  `;
}
