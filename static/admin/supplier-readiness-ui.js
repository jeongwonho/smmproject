function supplierIntegrationDisplayName(integrationType) {
  if (integrationType === "mkt24") return "MKT24";
  if (integrationType === "fasttraffic") return "FastTraffic";
  return "classic SMM";
}

function supplierHealthReadinessLabel(status) {
  if (status === "ok") return "정상";
  if (status === "failed") return "실패";
  return "점검 필요";
}

function supplierBalanceReadinessLabel(status) {
  if (status === "ok") return "정상";
  if (status === "failed") return "실패";
  if (status === "unsupported") return "해당 없음";
  return "미확인";
}

function supplierSyncReadinessLabel(status) {
  if (status === "success") return "동기화 정상";
  if (status === "syncing") return "동기화 중";
  if (status === "failed") return "동기화 실패";
  return "동기화 필요";
}

function supplierServiceIdLooksUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || "").trim());
}

function supplierServiceIdLooksNumeric(value) {
  return /^\d+$/.test(String(value || "").trim());
}

function supplierUsesMkt24PanelApi(supplier) {
  return String(supplier?.apiUrl || "").includes("/v3/panel");
}

function supplierApiEndpointCheck(selectedSupplier) {
  const integrationType = selectedSupplier?.integrationType || "classic";
  const apiUrl = String(selectedSupplier?.apiUrl || "").trim();
  if (integrationType === "mkt24") {
    const usesPanelApi = supplierUsesMkt24PanelApi(selectedSupplier);
    return {
      value: usesPanelApi ? "/v3/panel" : "legacy URL",
      ok: usesPanelApi,
      blocking: false,
      description: usesPanelApi
        ? "MKT24 대행사용 표준 endpoint로 service sync와 panel 발주를 실행합니다."
        : "legacy MKT24 URL은 직접 주문 모드입니다. 신규 매핑은 /v3/panel 전환 여부를 먼저 확인하세요.",
    };
  }
  if (integrationType === "fasttraffic") {
    const normalized = apiUrl.includes("fastraffic.co.kr/nblog_api.php") || apiUrl.includes("fasttraffic.co.kr/nblog_api.php");
    return {
      value: normalized ? "전용 endpoint" : "URL 확인",
      ok: normalized,
      blocking: false,
      description: normalized
        ? "FastTraffic 전용 endpoint와 X-Api-Key 헤더 조건으로 발주합니다."
        : "FastTraffic은 https://fastraffic.co.kr/nblog_api.php endpoint를 사용해야 합니다.",
    };
  }
  return {
    value: apiUrl ? "classic API" : "URL 없음",
    ok: Boolean(apiUrl),
    blocking: true,
    description: apiUrl ? "classic SMM API는 services/add/status action을 사용합니다." : "classic 공급사는 API URL이 필요합니다.",
  };
}

function supplierServicePayloadHint(integrationType, selectedService) {
  if (!selectedService) return "서비스 하나를 선택해야 payload preview와 발주가 가능합니다.";
  const guide = selectedService.requestGuide || {};
  const example = guide.callExamplePayload || {};
  const keys = Object.keys(example).filter((key) => key !== "key").slice(0, 5);
  const keyText = keys.length ? `전송 키: ${keys.join(", ")}` : "공급사 payload 예시를 확인하세요.";
  if (integrationType === "mkt24") return `${keyText}. MKT24 panel은 service, link/username, quantity 조합을 확인합니다.`;
  if (integrationType === "fasttraffic") return `${keyText}. FastTraffic은 action별 필수값과 quantityParam이 다릅니다.`;
  return `${keyText}. classic은 service, link 또는 username, quantity 조합을 확인합니다.`;
}

function supplierDispatchReadinessChecks({
  selectedSupplier,
  selectedService,
  allServices,
  activeConnection,
  connectionState,
  syncStatus,
}) {
  const integrationType = selectedSupplier?.integrationType || "classic";
  const services = Array.isArray(allServices) ? allServices : [];
  const serviceCount = Number(activeConnection?.serviceCount || selectedSupplier?.serviceCount || selectedSupplier?.lastServiceCount || services.length || 0);
  const healthStatus = String(selectedSupplier?.healthStatus || "unknown");
  const balanceStatus = String(selectedSupplier?.balanceStatus || "unknown");
  const selectedExternalServiceId = String(selectedService?.externalServiceId || "").trim();
  const endpointCheck = supplierApiEndpointCheck(selectedSupplier);
  const checks = [
    {
      label: "공급사 활성",
      value: selectedSupplier?.isActive ? "활성" : "비활성",
      ok: Boolean(selectedSupplier?.isActive),
      blocking: true,
      description: selectedSupplier?.isActive ? "자동 발주 대상에 포함됩니다." : "비활성 공급사는 자동/수동 발주가 차단됩니다.",
    },
    {
      label: "API 인증",
      value: selectedSupplier?.hasApiKey ? "Key 저장됨" : "Key 없음",
      ok: Boolean(selectedSupplier?.hasApiKey),
      blocking: true,
      description: integrationType === "fasttraffic"
        ? "FastTraffic은 X-Api-Key 헤더로 인증합니다."
        : integrationType === "mkt24"
          ? "MKT24 /v3/panel은 key 파라미터만 사용합니다."
          : "classic SMM API는 key 파라미터로 services/add/status를 호출합니다.",
    },
    {
      label: "API endpoint",
      value: endpointCheck.value,
      ok: endpointCheck.ok,
      blocking: endpointCheck.blocking,
      description: endpointCheck.description,
    },
    {
      label: "Health check",
      value: supplierHealthReadinessLabel(healthStatus),
      ok: healthStatus === "ok",
      blocking: true,
      description: selectedSupplier?.healthMessage || (connectionState === "success" ? "최근 연결 확인은 성공했지만 자동 발주 health 상태를 확인해야 합니다." : "상태 점검이 ok여야 자동 발주가 진행됩니다."),
    },
    {
      label: "서비스 동기화",
      value: supplierSyncReadinessLabel(syncStatus),
      ok: serviceCount > 0 && syncStatus !== "failed",
      blocking: true,
      description: syncStatus === "failed"
        ? selectedSupplier?.serviceSyncMessage || "최근 서비스 동기화 실패를 먼저 해소해야 합니다."
        : `활성 서비스 후보 ${String(serviceCount)}개`,
    },
    {
      label: "서비스 선택",
      value: selectedService ? `#${selectedExternalServiceId || selectedService.id}` : "미선택",
      ok: Boolean(selectedService?.id && selectedExternalServiceId),
      blocking: true,
      description: supplierServicePayloadHint(integrationType, selectedService),
    },
    {
      label: "잔액 확인",
      value: supplierBalanceReadinessLabel(balanceStatus),
      ok: balanceStatus !== "failed",
      blocking: balanceStatus === "failed",
      description: selectedSupplier?.supportsBalanceCheck === false
        ? "이 공급사는 잔액 조회 없이 health/service 조건으로 판단합니다."
        : balanceStatus === "failed"
          ? "잔액 조회 실패 상태에서는 발주 전 점검이 필요합니다."
          : "잔액 실패 상태가 아니면 readiness 차단 조건은 아닙니다.",
    },
  ];

  if (integrationType === "mkt24") {
    const panelApi = supplierUsesMkt24PanelApi(selectedSupplier);
    const uuidLike = supplierServiceIdLooksUuid(selectedExternalServiceId);
    const numericId = supplierServiceIdLooksNumeric(selectedExternalServiceId);
    checks.push({
      label: "MKT24 발주 ID",
      value: !selectedService ? "서비스 필요" : panelApi && uuidLike ? "UUID 매핑 차단" : panelApi && !numericId ? "ID 형식 확인" : "panel ID 준비",
      ok: Boolean(selectedService) && (!panelApi || (numericId && !uuidLike)),
      blocking: Boolean(selectedService) && panelApi && uuidLike,
      description: panelApi
        ? "MKT24 /v3/panel 발주는 상품 UUID가 아니라 숫자형 panel 서비스 ID로 매핑해야 합니다."
        : "현재 URL은 /v3/panel 모드가 아니므로 MKT24 설정을 다시 확인하세요.",
    });
  } else if (integrationType === "fasttraffic") {
    checks.push({
      label: "FastTraffic payload",
      value: selectedService ? "정적 action 준비" : "서비스 필요",
      ok: Boolean(selectedService),
      blocking: !selectedService,
      description: "정적 카탈로그의 action별 필수값과 quantityParam으로 주문 payload를 구성합니다.",
    });
  } else {
    checks.push({
      label: "classic payload",
      value: selectedService ? "service/add 준비" : "서비스 필요",
      ok: Boolean(selectedService),
      blocking: !selectedService,
      description: "service ID, link, quantity를 classic SMM action=add payload로 보냅니다.",
    });
  }

  return checks;
}

function renderSupplierReadinessBadge(check, escapeHtml) {
  const className = check.ok ? "is-success" : check.blocking ? "is-error" : "is-warn";
  const label = check.ok ? "통과" : check.blocking ? "차단" : "확인";
  return `<span class="admin-badge ${className}">${escapeHtml(label)}</span>`;
}

export function renderSupplierDispatchReadinessPanel({
  selectedSupplier,
  selectedService,
  allServices,
  activeConnection,
  connectionState,
  syncStatus,
  escapeHtml,
  renderAdminInsightStrip,
}) {
  if (!selectedSupplier) {
    return `
      <section class="admin-card">
        <div class="section-head section-head--compact">
          <h2>자동 발주 준비 상태</h2>
          <p>공급사를 선택하면 service sync, health check, 공급사별 발주 조건을 한 번에 점검합니다.</p>
        </div>
        <div class="admin-empty-card"><strong>공급사 선택 필요</strong><p>왼쪽 목록에서 운영 공급사를 선택하세요.</p></div>
      </section>
    `;
  }

  const checks = supplierDispatchReadinessChecks({
    selectedSupplier,
    selectedService,
    allServices,
    activeConnection,
    connectionState,
    syncStatus,
  });
  const blockingChecks = checks.filter((check) => !check.ok && check.blocking);
  const reviewChecks = checks.filter((check) => !check.ok && !check.blocking);
  const integrationType = selectedSupplier.integrationType || "classic";
  const statusValue = blockingChecks.length
    ? `${blockingChecks.length}개 차단`
    : reviewChecks.length
      ? `${reviewChecks.length}개 확인`
      : "발주 가능";
  const statusTone = blockingChecks.length ? "warning" : "success";

  return `
    <section class="admin-card">
      <div class="section-head section-head--compact">
        <h2>자동 발주 준비 상태</h2>
        <p>${escapeHtml(supplierIntegrationDisplayName(integrationType))} 기준으로 자동/수동 발주 전에 필요한 조건을 확인합니다.</p>
      </div>

      ${renderAdminInsightStrip(
        [
          {
            label: "발주 readiness",
            value: statusValue,
            description: blockingChecks.length ? blockingChecks.map((check) => check.label).join(", ") : "현재 선택값으로 발주 차단 조건이 없습니다.",
            tone: statusTone,
          },
          {
            label: "Service sync",
            value: supplierSyncReadinessLabel(syncStatus),
            description: selectedSupplier.serviceSyncMessage || selectedSupplier.serviceSyncCompletedAt || "동기화 완료 이력이 필요합니다.",
            tone: syncStatus === "failed" ? "warning" : syncStatus === "success" ? "success" : "warning",
          },
          {
            label: "Health check",
            value: supplierHealthReadinessLabel(selectedSupplier.healthStatus || "unknown"),
            description: selectedSupplier.healthMessage || selectedSupplier.healthCheckedAt || "health_status가 ok여야 자동 발주됩니다.",
            tone: selectedSupplier.healthStatus === "ok" ? "success" : "warning",
          },
          {
            label: "공급사별 조건",
            value: supplierIntegrationDisplayName(integrationType),
            description: checks[checks.length - 1]?.description || "",
            tone: checks[checks.length - 1]?.ok ? "success" : "warning",
          },
        ],
        "admin-insight-grid--compact"
      )}

      <div class="admin-mapping-preview">
        ${checks
          .map(
            (check) => `
              <article class="admin-mini-card ${!check.ok && check.blocking ? "is-risk" : ""}">
                <span>${escapeHtml(check.label)}</span>
                <strong>${escapeHtml(check.value)}</strong>
                <p>${escapeHtml(check.description || "")}</p>
                ${renderSupplierReadinessBadge(check, escapeHtml)}
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}
