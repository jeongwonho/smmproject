export function renderChargePage(runtime, renderFrame) {
  const {
    state,
    escapeHtml,
    formatMoney,
    ensureChargeDraft,
    chargeAmountSummary,
    chargeMethodConfig,
    filteredChargeOrders,
    filteredWalletEntries,
    formatCurrencyInput,
  } = runtime;

  const wallet = state.wallet || {
    availableBalance: 0,
    availableBalanceLabel: "0원",
    pendingBalance: 0,
    pendingBalanceLabel: "0원",
    totalBalance: 0,
    totalBalanceLabel: "0원",
  };
  const chargeConfig = state.bootstrap?.chargeConfig || { methods: [], bankTransfer: {}, policyHighlights: [] };
  const draft = ensureChargeDraft();
  const summary = chargeAmountSummary(draft.amountInput);
  const methods = chargeConfig.methods || [];
  const activeMethod = chargeMethodConfig(draft.paymentChannel) || methods[0] || null;
  const chargeOrders = filteredChargeOrders();
  const walletEntries = filteredWalletEntries();
  const historyItems = state.ui.chargeHistoryMode === "walletLedger" ? walletEntries : chargeOrders;
  const selectedDetail =
    state.ui.chargeDetailOpen && state.ui.chargeDetailId
      ? (
          state.ui.chargeDetailKind === "walletLedger"
            ? (state.walletLedger || []).find((item) => item.id === state.ui.chargeDetailId)
            : (state.chargeOrders || []).find((item) => item.id === state.ui.chargeDetailId)
        ) || null
      : null;

  const agreementReady = Boolean(draft.agreementChecked);
  const amountReady = summary.amount >= Number(chargeConfig.minimumAmount || 5000);
  const methodReady = Boolean(activeMethod?.enabled);
  const depositorReady = draft.paymentChannel !== "bank_transfer" || Boolean(String(draft.depositorName || "").trim());
  const receiptReady =
    draft.receiptType === "none" ||
    (draft.receiptType === "cash_receipt" &&
      (String(draft.receiptPayload.phoneNumber || "").trim() || String(draft.receiptPayload.businessNumber || "").trim())) ||
    (draft.receiptType === "tax_invoice" &&
      ["businessName", "businessNumber", "recipientEmail"].every((key) => String(draft.receiptPayload[key] || "").trim()));
  const ctaDisabled = !(agreementReady && amountReady && methodReady && depositorReady && receiptReady);
  const ctaReason = !amountReady
    ? `최소 충전 금액은 ${formatMoney(chargeConfig.minimumAmount || 5000)}입니다.`
    : !methodReady
      ? "선택한 결제수단은 아직 사용할 수 없습니다."
      : !depositorReady
        ? "입금자명을 입력해 주세요."
        : !receiptReady
          ? "증빙 신청 정보를 모두 입력해 주세요."
          : !agreementReady
            ? "충전 유의사항과 환불 불가 안내에 동의해 주세요."
            : "";

  const historySummary = `
    <div class="charge-balance-board">
      <article class="charge-balance-board__item">
        <span>사용 가능</span>
        <strong>${escapeHtml(wallet.availableBalanceLabel)}</strong>
      </article>
      <article class="charge-balance-board__item">
        <span>입금 대기</span>
        <strong>${escapeHtml(wallet.pendingBalanceLabel)}</strong>
      </article>
      <article class="charge-balance-board__item">
        <span>총 보유금액</span>
        <strong>${escapeHtml(wallet.totalBalanceLabel)}</strong>
      </article>
    </div>
  `;

  return renderFrame(
    `
      <div class="page page-charge page-charge-wallet">
        <header class="topbar">
          <button class="icon-button" type="button" data-route="/">‹</button>
          <strong class="topbar-title">보유금액</strong>
          <button class="icon-button" type="button" data-route="/help">?</button>
        </header>
        <div class="topbar-spacer"></div>

        <section class="content-section content-section--tight">
          <div class="charge-wallet-hero">
            <div>
              <span class="charge-wallet-hero__label">현재 보유금액</span>
              <strong>${escapeHtml(wallet.availableBalanceLabel)}</strong>
            </div>
            <div class="charge-wallet-hero__meta">
              <span>입금 대기 ${escapeHtml(wallet.pendingBalanceLabel)}</span>
              <span>총합 ${escapeHtml(wallet.totalBalanceLabel)}</span>
            </div>
          </div>
          <div class="charge-subtabs" role="tablist" aria-label="충전 탭">
            <button class="charge-subtab ${state.ui.chargeTab === "create" ? "is-active" : ""}" type="button" data-charge-tab="create">충전하기</button>
            <button class="charge-subtab ${state.ui.chargeTab === "history" ? "is-active" : ""}" type="button" data-charge-tab="history">이용내역</button>
          </div>
        </section>

        ${
          state.ui.chargeTab === "create"
            ? `
              <section class="content-section content-section--tight">
                <div class="charge-form-card">
                  <div class="charge-form-card__head">
                    <div>
                      <h2>충전 금액 입력</h2>
                      <p>원하시는 충전 금액을 입력하고 결제 방식을 선택해 주세요.</p>
                    </div>
                    <div class="charge-expected-card">
                      <span>충전 후 예상 보유금액</span>
                      <strong>${escapeHtml(formatMoney(summary.expectedBalance))}</strong>
                    </div>
                  </div>

                  <form class="charge-create-form" data-charge-create-form>
                    <label class="form-field">
                      <span class="field-label">충전 금액</span>
                      <div class="field-shell charge-amount-shell">
                        <input
                          class="field-input charge-amount-input"
                          type="text"
                          inputmode="numeric"
                          placeholder="예: 50,000"
                          value="${escapeHtml(formatCurrencyInput(draft.amountInput))}"
                          data-charge-amount-input
                        />
                        <span class="field-unit">원</span>
                      </div>
                    </label>

                    <div class="charge-quick-grid">
                      ${[
                        [5000, "+5천"],
                        [10000, "+1만"],
                        [50000, "+5만"],
                        [100000, "+10만"],
                        [500000, "+50만"],
                        [1000000, "+100만"],
                      ]
                        .map(
                          ([amount, label]) => `
                            <button class="charge-quick-chip" type="button" data-charge-quick-amount="${amount}">
                              ${escapeHtml(label)}
                            </button>
                          `
                        )
                        .join("")}
                    </div>

                    <div class="charge-amount-breakdown">
                      <article>
                        <span>충전금액</span>
                        <strong>${escapeHtml(formatMoney(summary.amount))}</strong>
                      </article>
                      <article>
                        <span>부가세</span>
                        <strong>${escapeHtml(formatMoney(summary.vat))}</strong>
                      </article>
                      <article>
                        <span>최종결제금액</span>
                        <strong>${escapeHtml(formatMoney(summary.total))}</strong>
                      </article>
                    </div>

                    <div class="charge-method-block">
                      <div class="section-head section-head--compact">
                        <h2>결제방식 선택</h2>
                      </div>
                      <div class="charge-method-segment">
                        ${methods
                          .map(
                            (method) => `
                              <button
                                class="charge-method-pill ${draft.paymentChannel === method.id ? "is-active" : ""} ${method.enabled ? "" : "is-disabled"}"
                                type="button"
                                data-charge-payment-channel="${escapeHtml(method.id)}"
                              >
                                <strong>${escapeHtml(method.label)}</strong>
                                <span>${escapeHtml(method.enabled ? method.description : "준비 중")}</span>
                              </button>
                            `
                          )
                          .join("")}
                      </div>

                      ${
                        draft.paymentChannel === "card"
                          ? `
                            <div class="charge-method-detail">
                              <label class="form-field">
                                <span class="field-label">결제 수단</span>
                                <div class="select-shell">
                                  <select class="field-select" data-charge-draft-field="paymentMethodDetail">
                                    ${[
                                      ["general_card", "일반 카드"],
                                      ["kakao_pay", "카카오페이"],
                                      ["naver_pay", "네이버페이"],
                                      ["tosspay", "토스페이"],
                                      ["payco", "PAYCO"],
                                    ]
                                      .map(
                                        ([value, label]) => `
                                          <option value="${escapeHtml(value)}" ${draft.paymentMethodDetail === value ? "selected" : ""}>
                                            ${escapeHtml(label)}
                                          </option>
                                        `
                                      )
                                      .join("")}
                                  </select>
                                </div>
                              </label>
                              <p class="charge-inline-note ${activeMethod?.enabled ? "" : "is-warning"}">
                                ${escapeHtml(
                                  activeMethod?.enabled
                                    ? "서버에서 충전 주문을 생성한 뒤 PG 결제 세션을 시작합니다."
                                    : "카드/간편결제는 PG 연동 후 활성화됩니다. 현재는 계좌입금을 이용해 주세요."
                                )}
                              </p>
                            </div>
                          `
                          : `
                            <div class="charge-method-detail">
                              <div class="deposit-account-box">
                                <strong>${escapeHtml(chargeConfig.bankTransfer?.bankName || "계좌입금")}</strong>
                                <p>${escapeHtml(chargeConfig.bankTransfer?.accountNumber || "운영 계좌 정보가 설정되지 않았습니다.")}</p>
                                <span>${escapeHtml(chargeConfig.bankTransfer?.accountHolder || "")}</span>
                              </div>
                              <label class="form-field">
                                <span class="field-label">입금자명</span>
                                <div class="field-shell">
                                  <input
                                    class="field-input"
                                    type="text"
                                    placeholder="입금자명을 입력해 주세요"
                                    value="${escapeHtml(draft.depositorName)}"
                                    data-charge-draft-field="depositorName"
                                  />
                                </div>
                              </label>
                              <p class="charge-inline-note">${escapeHtml(chargeConfig.bankTransfer?.depositGuide || "")}</p>
                            </div>
                          `
                      }
                    </div>

                    <div class="charge-receipt-block">
                      <div class="section-head section-head--compact">
                        <h2>증빙 신청</h2>
                      </div>
                      <div class="charge-radio-row">
                        ${[
                          ["none", "안함"],
                          ["cash_receipt", "현금영수증"],
                          ["tax_invoice", "세금계산서"],
                        ]
                          .map(
                            ([value, label]) => `
                              <label class="charge-radio-pill ${draft.receiptType === value ? "is-active" : ""}">
                                <input type="radio" name="receiptType" value="${escapeHtml(value)}" data-charge-draft-field="receiptType" ${draft.receiptType === value ? "checked" : ""} />
                                <span>${escapeHtml(label)}</span>
                              </label>
                            `
                          )
                          .join("")}
                      </div>
                      ${
                        draft.receiptType === "cash_receipt"
                          ? `
                            <div class="charge-receipt-grid">
                              <label class="form-field">
                                <span class="field-label">휴대폰 번호</span>
                                <div class="field-shell">
                                  <input class="field-input" type="tel" placeholder="01012345678" value="${escapeHtml(draft.receiptPayload.phoneNumber || "")}" data-charge-receipt-field="phoneNumber" />
                                </div>
                              </label>
                              <label class="form-field">
                                <span class="field-label">사업자번호(선택)</span>
                                <div class="field-shell">
                                  <input class="field-input" type="text" placeholder="숫자만 입력" value="${escapeHtml(draft.receiptPayload.businessNumber || "")}" data-charge-receipt-field="businessNumber" />
                                </div>
                              </label>
                              <div class="charge-radio-row">
                                ${[
                                  ["personal", "개인소득공제"],
                                  ["business", "지출증빙"],
                                ]
                                  .map(
                                    ([value, label]) => `
                                      <label class="charge-radio-pill ${draft.receiptPayload.purpose === value ? "is-active" : ""}">
                                        <input type="radio" name="receiptPurpose" value="${escapeHtml(value)}" data-charge-receipt-field="purpose" ${draft.receiptPayload.purpose === value ? "checked" : ""} />
                                        <span>${escapeHtml(label)}</span>
                                      </label>
                                    `
                                  )
                                  .join("")}
                              </div>
                            </div>
                          `
                          : ""
                      }
                      ${
                        draft.receiptType === "tax_invoice"
                          ? `
                            <div class="charge-receipt-grid">
                              <label class="form-field">
                                <span class="field-label">상호명</span>
                                <div class="field-shell">
                                  <input class="field-input" type="text" value="${escapeHtml(draft.receiptPayload.businessName || "")}" data-charge-receipt-field="businessName" />
                                </div>
                              </label>
                              <label class="form-field">
                                <span class="field-label">사업자등록번호</span>
                                <div class="field-shell">
                                  <input class="field-input" type="text" value="${escapeHtml(draft.receiptPayload.businessNumber || "")}" data-charge-receipt-field="businessNumber" />
                                </div>
                              </label>
                              <label class="form-field">
                                <span class="field-label">수신 이메일</span>
                                <div class="field-shell">
                                  <input class="field-input" type="email" value="${escapeHtml(draft.receiptPayload.recipientEmail || "")}" data-charge-receipt-field="recipientEmail" />
                                </div>
                              </label>
                              <label class="form-field">
                                <span class="field-label">담당자명</span>
                                <div class="field-shell">
                                  <input class="field-input" type="text" value="${escapeHtml(draft.receiptPayload.contactName || "")}" data-charge-receipt-field="contactName" />
                                </div>
                              </label>
                            </div>
                          `
                          : ""
                      }
                    </div>

                    <div class="charge-notice-box">
                      <strong>충전 유의사항</strong>
                      <ul>
                        ${(chargeConfig.policyHighlights || [])
                          .map((item) => `<li>${escapeHtml(item)}</li>`)
                          .join("")}
                      </ul>
                      <label class="charge-agreement">
                        <input type="checkbox" ${draft.agreementChecked ? "checked" : ""} data-charge-draft-field="agreementChecked" />
                        <span>충전 유의사항과 환불 불가 정책을 확인했습니다.</span>
                      </label>
                    </div>
                  </form>
                </div>
              </section>
            `
            : `
              <section class="content-section content-section--tight">
                ${historySummary}
                <div class="charge-history-toolbar">
                  <div class="charge-toggle-row">
                    <button class="charge-toggle-pill ${state.ui.chargeHistoryMode === "chargeOrders" ? "is-active" : ""}" type="button" data-charge-history-mode="chargeOrders">충전내역</button>
                    <button class="charge-toggle-pill ${state.ui.chargeHistoryMode === "walletLedger" ? "is-active" : ""}" type="button" data-charge-history-mode="walletLedger">보유금액 내역</button>
                  </div>
                  <div class="charge-filter-grid">
                    <label class="select-shell">
                      <select class="field-select" data-charge-filter="period">
                        ${[
                          ["all", "전체 기간"],
                          ["7d", "최근 7일"],
                          ["30d", "최근 30일"],
                          ["90d", "최근 90일"],
                        ]
                          .map(
                            ([value, label]) => `<option value="${escapeHtml(value)}" ${state.ui.chargePeriodFilter === value ? "selected" : ""}>${escapeHtml(label)}</option>`
                          )
                          .join("")}
                      </select>
                    </label>
                    <label class="select-shell">
                      <select class="field-select" data-charge-filter="status">
                        ${[
                          ["all", "전체 상태"],
                          ["awaiting_payment", "결제 대기"],
                          ["awaiting_deposit", "입금 대기"],
                          ["paid", "결제 완료"],
                          ["failed", "실패"],
                          ["cancelled", "취소"],
                          ["refunded", "환불 완료"],
                        ]
                          .map(
                            ([value, label]) => `<option value="${escapeHtml(value)}" ${state.ui.chargeStatusFilter === value ? "selected" : ""}>${escapeHtml(label)}</option>`
                          )
                          .join("")}
                      </select>
                    </label>
                    <label class="select-shell">
                      <select class="field-select" data-charge-filter="method">
                        ${[
                          ["all", "전체 수단"],
                          ["card", "카드/간편결제"],
                          ["bank_transfer", "계좌입금"],
                        ]
                          .map(
                            ([value, label]) => `<option value="${escapeHtml(value)}" ${state.ui.chargeMethodFilter === value ? "selected" : ""}>${escapeHtml(label)}</option>`
                          )
                          .join("")}
                      </select>
                    </label>
                  </div>
                </div>
                <div class="charge-history-list">
                  ${
                    historyItems.length
                      ? historyItems
                          .map((item) => {
                            const title = state.ui.chargeHistoryMode === "walletLedger" ? item.memo : item.orderCode;
                            const amountLabel = state.ui.chargeHistoryMode === "walletLedger" ? item.amountLabel : item.totalAmountLabel;
                            const statusLabel = state.ui.chargeHistoryMode === "walletLedger" ? item.statusLabel : item.statusLabel;
                            const methodLabel = state.ui.chargeHistoryMode === "walletLedger" ? item.paymentChannelLabel : item.paymentChannelLabel;
                            const meta = state.ui.chargeHistoryMode === "walletLedger" ? item.balanceAfterLabel : item.createdLabel;
                            return `
                              <button class="charge-history-item" type="button" data-charge-detail-open="${escapeHtml(item.id)}" data-charge-detail-kind="${escapeHtml(state.ui.chargeHistoryMode)}">
                                <div class="charge-history-item__copy">
                                  <strong>${escapeHtml(title || "충전 내역")}</strong>
                                  <p>${escapeHtml(methodLabel)} · ${escapeHtml(statusLabel)}</p>
                                  <span>${escapeHtml(meta)}</span>
                                </div>
                                <div class="charge-history-item__side">
                                  <strong>${escapeHtml(amountLabel)}</strong>
                                  <span>${escapeHtml(item.createdLabel || item.createdAt || "")}</span>
                                </div>
                              </button>
                            `;
                          })
                          .join("")
                      : `
                        <article class="empty-card empty-card--compact">
                          <strong>아직 이용내역이 없습니다.</strong>
                          <p>충전 주문을 만들거나 보유금액이 변동되면 이곳에 기록됩니다.</p>
                        </article>
                      `
                  }
                </div>
              </section>
            `
        }
      </div>

      ${
        state.ui.chargeTab === "create"
          ? `
            <div class="charge-sticky-summary">
              <div class="charge-sticky-summary__price">
                <span>충전금액 ${escapeHtml(formatMoney(summary.amount))}</span>
                <strong>${escapeHtml(formatMoney(summary.total))}</strong>
              </div>
              <button class="charge-sticky-summary__button" type="button" data-charge-submit ${ctaDisabled ? "disabled" : ""}>
                충전하기
              </button>
            </div>
            <div class="charge-sticky-summary__note ${ctaReason ? "is-visible" : ""}">${escapeHtml(ctaReason)}</div>
          `
          : ""
      }

      ${
        selectedDetail
          ? `
            <div class="charge-detail-sheet ${state.ui.chargeDetailOpen ? "is-open" : ""}" data-charge-detail-sheet>
              <button class="charge-detail-sheet__backdrop" type="button" data-charge-detail-close aria-label="닫기"></button>
              <section class="charge-detail-sheet__panel">
                <div class="charge-detail-sheet__grab" aria-hidden="true"></div>
                <div class="charge-detail-sheet__head">
                  <strong>${escapeHtml(state.ui.chargeDetailKind === "walletLedger" ? "보유금액 내역 상세" : "충전 내역 상세")}</strong>
                  <button class="icon-button" type="button" data-charge-detail-close>×</button>
                </div>
                <div class="charge-detail-sheet__body">
                  ${
                    state.ui.chargeDetailKind === "walletLedger"
                      ? `
                        <dl class="charge-detail-list">
                          <div><dt>내역</dt><dd>${escapeHtml(selectedDetail.memo || "")}</dd></div>
                          <div><dt>금액</dt><dd>${escapeHtml(selectedDetail.amountLabel || "")}</dd></div>
                          <div><dt>잔액</dt><dd>${escapeHtml(selectedDetail.balanceAfterLabel || "")}</dd></div>
                          <div><dt>상태</dt><dd>${escapeHtml(selectedDetail.statusLabel || "")}</dd></div>
                          <div><dt>수단</dt><dd>${escapeHtml(selectedDetail.paymentChannelLabel || "")}</dd></div>
                          <div><dt>시각</dt><dd>${escapeHtml(selectedDetail.createdAt || "")}</dd></div>
                          ${selectedDetail.reference ? `<div><dt>참조번호</dt><dd>${escapeHtml(selectedDetail.reference)}</dd></div>` : ""}
                        </dl>
                      `
                      : `
                        <dl class="charge-detail-list">
                          <div><dt>주문번호</dt><dd>${escapeHtml(selectedDetail.orderCode || "")}</dd></div>
                          <div><dt>충전금액</dt><dd>${escapeHtml(selectedDetail.amountLabel || "")}</dd></div>
                          <div><dt>부가세</dt><dd>${escapeHtml(selectedDetail.vatAmountLabel || "")}</dd></div>
                          <div><dt>최종결제금액</dt><dd>${escapeHtml(selectedDetail.totalAmountLabel || "")}</dd></div>
                          <div><dt>결제수단</dt><dd>${escapeHtml(selectedDetail.paymentChannelLabel || "")}</dd></div>
                          <div><dt>상태</dt><dd>${escapeHtml(selectedDetail.statusLabel || "")}</dd></div>
                          <div><dt>증빙</dt><dd>${escapeHtml(selectedDetail.receiptTypeLabel || "미신청")}</dd></div>
                          ${selectedDetail.reference ? `<div><dt>참조번호</dt><dd>${escapeHtml(selectedDetail.reference)}</dd></div>` : ""}
                          ${selectedDetail.depositorName ? `<div><dt>입금자명</dt><dd>${escapeHtml(selectedDetail.depositorName)}</dd></div>` : ""}
                          ${selectedDetail.failureReason ? `<div><dt>실패 사유</dt><dd>${escapeHtml(selectedDetail.failureReason)}</dd></div>` : ""}
                          <div><dt>생성 시각</dt><dd>${escapeHtml(selectedDetail.createdAt || "")}</dd></div>
                        </dl>
                      `
                  }
                </div>
              </section>
            </div>
          `
          : ""
      }
    `,
    "charge"
  );
}
