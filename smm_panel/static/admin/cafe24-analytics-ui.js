function formatRatioPercent(value, digits = 1) {
  const numeric = Number(value || 0);
  return `${(numeric * 100).toFixed(digits)}%`;
}

function formatCafe24AnalyticsDate(value = "") {
  const text = String(value || "");
  if (text.length !== 8) return text || "-";
  return `${text.slice(4, 6)}/${text.slice(6, 8)}`;
}

function formatCafe24AnalyticsTimestamp(value = "") {
  const parsed = new Date(String(value || ""));
  if (Number.isNaN(parsed.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

function checklistTone(status) {
  if (status === "완료") return "is-success";
  if (status === "확인 필요" || status === "대기") return "is-warning";
  return "is-neutral";
}

function recommendationTone(tone) {
  if (tone === "good") return "is-success";
  if (tone === "bad") return "is-error";
  if (tone === "warn") return "is-warning";
  return "is-neutral";
}

export function renderCafe24GaAnalyticsTab({
  analytics,
  escapeHtml,
  formatMoney,
  formatNumber,
  renderAnalyticsOverviewCards,
  renderAnalyticsTable,
}) {
  if (!analytics) {
    return `
      <div class="admin-empty-card">
        <strong>Cafe24/GA 데이터를 불러오는 중입니다.</strong>
        <p>GA4 연결 상태와 최근 구매 퍼널을 확인하고 있습니다.</p>
      </div>
    `;
  }

  const overview = analytics.overview || {};
  const funnel = Array.isArray(analytics.funnel) ? analytics.funnel : [];
  const channels = Array.isArray(analytics.channels) ? analytics.channels : [];
  const pages = Array.isArray(analytics.pages) ? analytics.pages : [];
  const trend = Array.isArray(analytics.trend) ? analytics.trend : [];
  const eventHealth = Array.isArray(analytics.eventHealth) ? analytics.eventHealth : [];
  const recommendations = Array.isArray(analytics.recommendations) ? analytics.recommendations : [];
  const setupChecklist = Array.isArray(analytics.setupChecklist) ? analytics.setupChecklist : [];
  const beginCheckout = funnel.find((item) => item.key === "begin_checkout")?.count || 0;
  const purchaseCount = overview.purchaseCount || funnel.find((item) => item.key === "purchase")?.count || 0;
  const checkoutToPurchaseRate = beginCheckout ? purchaseCount / beginCheckout : 0;
  const maxTrendSessions = Math.max(...trend.map((item) => Number(item.sessions || 0)), 1);
  const adSpend = Number(overview.adSpend || 0);
  const roas = Number(overview.roas || 0);

  return `
    <div class="admin-analytics-stack cafe24-ga-analytics">
      ${renderAnalyticsOverviewCards([
        { label: `${analytics.rangeLabel || "선택 기간"} 세션`, value: formatNumber(overview.sessions), detail: `사용자 ${formatNumber(overview.users)}명` },
        { label: "구매 매출", value: formatMoney(overview.revenue), detail: `전환 ${formatNumber(overview.conversions)}건` },
        { label: "구매 건수", value: `${formatNumber(purchaseCount)}건`, detail: `객단가 ${formatMoney(overview.averageOrderValue)}` },
        { label: "결제시작 → 구매", value: formatRatioPercent(checkoutToPurchaseRate, 1), detail: `결제시작 ${formatNumber(beginCheckout)}건` },
        { label: "광고비", value: formatMoney(adSpend), detail: `CPA ${formatMoney(overview.costPerPurchase || 0)}` },
        { label: "ROAS", value: `${roas.toFixed(roas >= 10 ? 0 : 2)}x`, detail: adSpend > 0 ? "광고비 대비 매출" : "광고비 데이터 대기" },
      ])}

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>GA4 연결 상태</h2>
              <p>${escapeHtml(analytics.message || "GA4 Data API에서 집계한 최신 리포트입니다.")}</p>
            </div>
            <span class="admin-badge ${analytics.connected ? "is-success" : analytics.error ? "is-error" : "is-warning"}">${analytics.connected ? "GA4 연결" : analytics.error ? "연결 오류" : "연결 필요"}</span>
          </div>
          <div class="cafe24-ga-source-grid">
            <article>
              <span>데이터 소스</span>
              <strong>${escapeHtml(analytics.connected ? `GA4 ${analytics.propertyId || ""}` : "데이터 없음")}</strong>
            </article>
            <article>
              <span>업데이트</span>
              <strong>${escapeHtml(formatCafe24AnalyticsTimestamp(analytics.generatedAt))}</strong>
            </article>
          </div>
          ${analytics.error ? `<p class="admin-inline-note cafe24-ga-error">${escapeHtml(analytics.error)}</p>` : ""}
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>우선 조치</h2>
              <p>GA4 이벤트 상태를 기준으로 바로 확인할 운영 액션입니다.</p>
            </div>
          </div>
          <div class="cafe24-ga-insight-list">
            ${recommendations
              .map((item) => `
                <article class="cafe24-ga-insight">
                  <span class="admin-badge ${recommendationTone(item.tone)}">${escapeHtml(item.tone === "good" ? "확대" : item.tone === "bad" ? "긴급" : "점검")}</span>
                  <div>
                    <strong>${escapeHtml(item.title)}</strong>
                    <p>${escapeHtml(item.body)}</p>
                  </div>
                </article>
              `)
              .join("") || `<p class="admin-inline-note">실제 GA4 데이터가 연결되면 운영 권장사항이 표시됩니다.</p>`}
          </div>
        </section>
      </div>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>카페24 구매 퍼널</h2>
              <p>상품 조회부터 구매까지의 이벤트 수집 흐름입니다.</p>
            </div>
            <span class="admin-badge ${purchaseCount > 0 ? "is-success" : "is-warning"}">${purchaseCount > 0 ? "구매 수집" : "구매 확인 필요"}</span>
          </div>
          <div class="cafe24-ga-funnel">
            ${funnel
              .map((step) => {
                const rate = Number(step.rate || 0);
                const width = Math.max(4, Math.min(100, rate * 100));
                return `
                  <article class="cafe24-ga-funnel__step">
                    <div>
                      <strong>${escapeHtml(step.label)}</strong>
                      <span>${escapeHtml(formatNumber(step.count))}건</span>
                      <em>${escapeHtml(formatRatioPercent(rate, rate > 0 && rate < 0.01 ? 2 : 1))}</em>
                    </div>
                    <i><b style="width: ${width.toFixed(2)}%"></b></i>
                  </article>
                `;
              })
              .join("")}
          </div>
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>일별 세션 추세</h2>
              <p>선택 기간의 세션 흐름을 빠르게 확인합니다.</p>
            </div>
          </div>
          <div class="cafe24-ga-bars">
            ${trend
              .map((item) => `
                <div class="cafe24-ga-bars__item">
                  <span>${escapeHtml(formatNumber(item.sessions))}</span>
                  <i><b style="height: ${Math.max(8, (Number(item.sessions || 0) / maxTrendSessions) * 100).toFixed(2)}%"></b></i>
                  <small>${escapeHtml(formatCafe24AnalyticsDate(item.date))}</small>
                </div>
              `)
              .join("")}
          </div>
        </section>
      </div>

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>매체/캠페인별 성과</h2>
            <p>GA4 sessionSourceMedium과 sessionCampaignName 기준입니다. 광고비가 있으면 ROAS와 CPA까지 계산합니다.</p>
          </div>
          <span class="admin-badge ${adSpend > 0 ? "is-success" : "is-neutral"}">${adSpend > 0 ? "ROAS 계산" : "UTM 기준"}</span>
        </div>
        ${renderAnalyticsTable(
          ["매체", "캠페인", "세션", "전환", "매출", "광고비", "ROAS", "CPA", "CVR"],
          channels.map((channel) => {
            const rate = Number(channel.conversionRate || 0);
            const channelRoas = Number(channel.roas || 0);
            return [
              escapeHtml(channel.sourceMedium),
              escapeHtml(channel.campaign),
              escapeHtml(formatNumber(channel.sessions)),
              escapeHtml(formatNumber(channel.conversions)),
              escapeHtml(formatMoney(channel.revenue)),
              escapeHtml(formatMoney(channel.adSpend || 0)),
              escapeHtml(channelRoas > 0 ? `${channelRoas.toFixed(channelRoas >= 10 ? 0 : 2)}x` : "-"),
              escapeHtml(channel.cpa ? formatMoney(channel.cpa) : "-"),
              escapeHtml(formatRatioPercent(rate, rate > 0 && rate < 0.01 ? 2 : 1)),
            ];
          }),
          "GA4 매체 데이터가 아직 없습니다."
        )}
      </section>

      <div class="admin-analytics-grid admin-analytics-grid--split">
        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>이벤트 수집 상태</h2>
              <p>카페24 브릿지와 GA4 이벤트 이름이 제대로 맞는지 확인합니다.</p>
            </div>
            <span class="admin-badge is-neutral">${escapeHtml(formatNumber(overview.events))} events</span>
          </div>
          <div class="cafe24-ga-event-grid">
            ${eventHealth
              .map((event) => `
                <article>
                  <strong>${escapeHtml(event.eventName)}</strong>
                  <span>${escapeHtml(formatNumber(event.count))}회 · ${escapeHtml(formatNumber(event.users))}명</span>
                  ${Number(event.revenue || 0) > 0 ? `<em>${escapeHtml(formatMoney(event.revenue))}</em>` : ""}
                </article>
              `)
              .join("")}
          </div>
        </section>

        <section class="admin-card admin-analytics-card">
          <div class="admin-analytics-card__head">
            <div>
              <h2>연결 체크리스트</h2>
              <p>구매 최적화 전에 반드시 확인할 수집 조건입니다.</p>
            </div>
          </div>
          <div class="cafe24-ga-checklist">
            ${setupChecklist
              .map((item) => `
                <article>
                  <div>
                    <strong>${escapeHtml(item.label)}</strong>
                    <p>${escapeHtml(item.detail)}</p>
                  </div>
                  <span class="admin-badge ${checklistTone(item.status)}">${escapeHtml(item.status)}</span>
                </article>
              `)
              .join("")}
          </div>
        </section>
      </div>

      <section class="admin-card admin-analytics-card">
        <div class="admin-analytics-card__head">
          <div>
            <h2>상위 페이지</h2>
            <p>카페24 상품/주문 페이지 중 전환 기여가 큰 경로를 확인합니다.</p>
          </div>
          <span class="admin-badge is-neutral">페이지뷰 기준</span>
        </div>
        ${renderAnalyticsTable(
          ["경로", "조회", "사용자", "전환", "매출"],
          pages.map((page) => [
            `<code>${escapeHtml(page.path)}</code>`,
            escapeHtml(formatNumber(page.views)),
            escapeHtml(formatNumber(page.users)),
            escapeHtml(formatNumber(page.conversions)),
            escapeHtml(formatMoney(page.revenue)),
          ]),
          "GA4 페이지 데이터가 아직 없습니다."
        )}
      </section>
    </div>
  `;
}
