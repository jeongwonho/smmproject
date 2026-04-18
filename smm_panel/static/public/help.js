export function renderHelpMarkup({ data, escapeHtml }) {
  return `
    <div class="page page-help">
      <header class="topbar">
        <button class="icon-button" type="button" data-route="/">‹</button>
        <strong class="topbar-title">도움말 허브</strong>
        <button class="icon-button" type="button" data-route="/products">▦</button>
      </header>
      <div class="topbar-spacer"></div>

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
          <div class="guide-list">
            ${documentItem.body.map((line) => `<article class="guide-card"><p>${escapeHtml(line)}</p></article>`).join("")}
          </div>
        </article>
      </section>
    </div>
  `;
}
