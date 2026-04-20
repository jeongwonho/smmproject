export function renderHelpMarkup({ data, escapeHtml }) {
  const company = data.company || {};
  const quickAnchors = [
    ["support", "빠른 지원"],
    ["guide", "이용 가이드"],
    ["notice", "공지"],
    ["faq", "FAQ"],
  ];
  return `
    <div class="page page-help">
      <header class="topbar">
        <button class="icon-button" type="button" data-route="/">‹</button>
        <strong class="topbar-title">도움말 허브</strong>
        <button class="icon-button" type="button" data-route="/products">▦</button>
      </header>
      <div class="topbar-spacer"></div>

      <section class="content-section">
        <div class="help-hero-card">
          <span class="help-hero-card__eyebrow">Support Hub</span>
          <strong>주문 전 확인해야 할 정보와 운영 안내를 한곳에 모았습니다</strong>
          <p>로그인 없이도 이용 가이드, 공지, FAQ, 정책 문서를 바로 확인할 수 있습니다.</p>
          <div class="help-anchor-row">
            ${quickAnchors
              .map(
                ([id, label]) => `
                  <a class="help-anchor-chip" href="#${escapeHtml(id)}">${escapeHtml(label)}</a>
                `
              )
              .join("")}
          </div>
        </div>
      </section>

      <section class="content-section" id="support">
        <div class="section-head">
          <h2>빠른 지원</h2>
          <p>로그인 없이도 주문 전 필요한 정보와 운영 안내를 확인할 수 있습니다.</p>
        </div>
        <div class="support-grid">
          ${data.supportLinks
            .map(
              (item) => `
                <button class="support-card" type="button" data-route="${item.route}">
                  <span class="support-card__icon">${escapeHtml(item.icon)}</span>
                  <strong>${escapeHtml(item.title)}</strong>
                  <p>${escapeHtml(item.subtitle)}</p>
                </button>
              `
            )
            .join("")}
        </div>
        <article class="guide-card help-contact-card">
          <strong>운영 문의</strong>
          <p>문의 채널: ${escapeHtml(company.contact || "support@example.com")}</p>
          <p>운영 시간: ${escapeHtml(company.hours || "평일 10:00 - 19:00")}</p>
        </article>
      </section>

      <section class="content-section" id="guide">
        <div class="section-head">
          <h2>이용 가이드</h2>
          <p>처음 방문한 고객도 바로 이해할 수 있게 핵심 흐름만 정리했습니다.</p>
        </div>
        <div class="guide-list">
          ${(data.guides || [])
            .map(
              (guide) => `
                <article class="guide-card">
                  <strong>${escapeHtml(guide.title)}</strong>
                  <p>${escapeHtml(guide.description)}</p>
                </article>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="content-section" id="notice">
        <div class="section-head">
          <h2>공지사항</h2>
        </div>
        <div class="notice-list">
          ${data.notices
            .map(
              (notice) => `
                <article class="notice-card">
                  <div class="notice-card__top">
                    <span class="mini-badge">${escapeHtml(notice.tag)}</span>
                    <span>${escapeHtml(notice.publishedLabel)}</span>
                  </div>
                  <strong>${escapeHtml(notice.title)}</strong>
                  <p>${escapeHtml(notice.body)}</p>
                </article>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="content-section" id="faq">
        <div class="section-head">
          <h2>FAQ</h2>
        </div>
        <div class="faq-list">
          ${data.faqs
            .map(
              (faq) => `
                <details class="faq-item">
                  <summary>${escapeHtml(faq.question)}</summary>
                  <p>${escapeHtml(faq.answer)}</p>
                </details>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="content-section footer-section">
        <div class="guide-list">
          ${(data.legalDocuments || [])
            .map(
              (doc) => `
                <button class="guide-card guide-card--link" type="button" data-route="/legal/${doc.key}">
                  <strong>${escapeHtml(doc.title)}</strong>
                  <p>${escapeHtml(doc.summary)}</p>
                </button>
              `
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

export function renderLegalPageMarkup({ documentItem, escapeHtml }) {
  return `
    <div class="page page-help">
      <header class="topbar">
        <button class="icon-button" type="button" data-route="/help">‹</button>
        <strong class="topbar-title">${escapeHtml(documentItem.title)}</strong>
        <button class="icon-button" type="button" data-route="/products">▦</button>
      </header>
      <div class="topbar-spacer"></div>
      <section class="content-section">
        <article class="html-card legal-card">
          <span class="mini-badge">v${escapeHtml(documentItem.version)}</span>
          <h2>${escapeHtml(documentItem.title)}</h2>
          <p>${escapeHtml(documentItem.summary)}</p>
          <div class="legal-card__note">아래 내용은 서비스 운영에 맞춰 관리자에서 갱신할 수 있는 정책 전문 영역입니다.</div>
          <div class="guide-list">
            ${documentItem.body.map((line) => `<article class="guide-card"><p>${escapeHtml(line)}</p></article>`).join("")}
          </div>
        </article>
      </section>
    </div>
  `;
}
