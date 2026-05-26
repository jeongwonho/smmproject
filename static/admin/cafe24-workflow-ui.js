function cafe24ManualInputCandidate(item = {}) {
  return item.paymentGateStatus === "payment_confirmed"
    && !item.supplierOrderUuid
    && ["waiting_input", "mapping_error", "missing_required_field", "invalid_quantity", "invalid_target", "supplier_range_error", "needs_manual_review"].includes(item.standardStatus);
}

export function renderCafe24MappingWorkflowChecklist({
  activeIntegration = {},
  lookupDetail = {},
  serviceCount = 0,
  preview = null,
  orderItems = [],
  escapeHtml,
  canDispatchItem,
}) {
  const tokenStatus = activeIntegration.tokenStatus || "missing";
  const hasUsableToken = Boolean(activeIntegration.mallId) && !["reconnect_required", "failed"].includes(tokenStatus);
  const hasLookupSelection = Boolean(lookupDetail.productNo || lookupDetail.product_no || (lookupDetail.variants || []).length);
  const hasSupplierServices = Number(serviceCount || 0) > 0;
  const hasPreview = Boolean(preview);
  const hasReadyDispatchCandidate = orderItems.some((item) => canDispatchItem(item));
  const manualInputCount = orderItems.filter(cafe24ManualInputCandidate).length;
  const steps = [
    {
      label: "1. Cafe24 연동",
      value: activeIntegration.mallId ? `${activeIntegration.mallId} / ${activeIntegration.shopNo || 1}` : "미연동",
      ok: hasUsableToken,
      description: hasUsableToken ? "상품 조회와 최근 주문 수집을 실행할 수 있습니다." : "토큰 재연결 또는 Cafe24 OAuth 연결이 필요합니다.",
    },
    {
      label: "2. 상품/옵션 조회",
      value: hasLookupSelection ? "조회됨" : "대기",
      ok: hasLookupSelection,
      description: "상품 조회 탭에서 상품번호, 품목코드, 자체상품코드를 확인한 뒤 매핑폼에 적용합니다.",
    },
    {
      label: "3. 공급사 서비스",
      value: hasSupplierServices ? `${serviceCount}개 로드` : "서비스 필요",
      ok: hasSupplierServices,
      description: "service sync 결과에서 실제 발주에 사용할 공급사 서비스를 선택합니다.",
    },
    {
      label: "4. Payload preview",
      value: hasPreview ? (preview.ok ? "검증 통과" : "검증 필요") : "미실행",
      ok: Boolean(preview?.ok),
      description: hasPreview ? "정규화 필드와 공급사 payload를 저장 전 확인했습니다." : "샘플 품주 또는 직접 입력값으로 payload 미리보기를 먼저 실행하세요.",
    },
    {
      label: "5. 단건 발주 후보",
      value: hasReadyDispatchCandidate ? "발주 가능 품주 있음" : manualInputCount ? `수동 보정 ${manualInputCount}건` : "대기",
      ok: hasReadyDispatchCandidate,
      description: hasReadyDispatchCandidate
        ? "결제완료, 매핑완료, 필드검증 통과 품주만 주문 처리 큐에서 발주 버튼이 활성화됩니다."
        : manualInputCount
          ? "개인결제처럼 옵션/수량 후보가 없는 품주는 주문 처리 탭에서 수동 보정 저장 후 preflight와 단건 발주를 확인합니다."
          : "결제완료, 매핑완료, 필드검증 통과 품주가 생기면 주문 처리 큐에서 발주 버튼이 활성화됩니다.",
    },
  ];
  return `
    <div class="admin-panel">
      <div class="section-head section-head--compact">
        <h3>Cafe24 매핑 워크플로우</h3>
        <p>상품 조회 → 옵션/품목코드 적용 → 공급사 서비스 선택 → payload preview → 단건 발주 순서로 검증합니다.</p>
      </div>
      <div class="admin-mapping-preview">
        ${steps.map((step) => `
          <article class="admin-mini-card ${step.ok ? "" : "is-risk"}">
            <span>${escapeHtml(step.label)}</span>
            <strong>${escapeHtml(step.value)}</strong>
            <p>${escapeHtml(step.description)}</p>
            <span class="admin-badge ${step.ok ? "is-success" : "is-warn"}">${step.ok ? "완료" : "확인 필요"}</span>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}
