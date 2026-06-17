function renderCafe24ProductUseButton({ product = {}, variant = {}, escapeHtml }) {
  const productNo = product.productNo || "";
  const variantCode = variant.variantCode || "";
  const customProductCode = variant.customProductCode || product.customProductCode || "";
  return `
    <button
      class="admin-secondary-button"
      type="button"
      data-admin-cafe24-use-product="${escapeHtml(productNo)}"
      data-admin-cafe24-variant-code="${escapeHtml(variantCode)}"
      data-admin-cafe24-custom-product-code="${escapeHtml(customProductCode)}"
    >매핑폼에 적용</button>
  `;
}

export function renderCafe24ProductLookupPanel({ state = {}, activeIntegration = {}, escapeHtml }) {
  const lookup = state.adminCafe24ProductLookup || {};
  const products = lookup.products || [];
  const detail = lookup.detail || null;
  const query = lookup.query || {};
  const warnings = lookup.warnings || [];
  const integrationId = activeIntegration.id || "";
  const useButton = (product, variant = {}) => renderCafe24ProductUseButton({ product, variant, escapeHtml });
  return `
    <div class="admin-panel admin-form">
      <div class="section-head section-head--compact">
        <h3>2) Cafe24 상품/옵션 조회</h3>
        <p>매핑 전에 Cafe24 상품번호, 품목코드, 자체상품코드와 옵션 구성을 확인합니다.</p>
      </div>
      <form class="admin-two-column" data-admin-cafe24-product-search-form>
        <input type="hidden" name="integrationId" value="${escapeHtml(integrationId)}" />
        <label class="form-field">
          <span class="field-label">상품명/상품번호 검색</span>
          <div class="field-shell"><input class="field-input" name="q" value="${escapeHtml(query.keyword || query.q || "")}" placeholder="상품명 또는 product_no" /></div>
        </label>
        <label class="form-field">
          <span class="field-label">상품번호 직접 조회</span>
          <div class="field-shell"><input class="field-input" name="productNo" value="${escapeHtml(query.productNo || "")}" placeholder="product_no" /></div>
        </label>
        <div class="admin-action-row">
          <button class="admin-primary-button" type="submit" ${integrationId ? "" : "disabled"}>Cafe24 상품 조회</button>
        </div>
      </form>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>상품</th><th>상품번호</th><th>자체코드</th><th>상태</th><th>작업</th></tr></thead>
          <tbody>
            ${products.length ? products.map((product) => `
              <tr>
                <td>
                  <strong>${escapeHtml(product.productName || "상품명 없음")}</strong>
                  ${product.price ? `<span class="admin-inline-note">${escapeHtml(product.price)}</span>` : ""}
                </td>
                <td>${escapeHtml(product.productNo || "-")}</td>
                <td>${escapeHtml(product.customProductCode || product.productCode || "-")}</td>
                <td>${escapeHtml([product.display, product.selling].filter(Boolean).join(" / ") || "-")}</td>
                <td>
                  <div class="admin-action-row">
                    <button class="admin-secondary-button" type="button" data-admin-cafe24-product-detail="${escapeHtml(product.productNo || "")}" data-admin-cafe24-integration-id="${escapeHtml(integrationId)}">옵션 보기</button>
                    ${useButton(product)}
                  </div>
                </td>
              </tr>
            `).join("") : `<tr><td colspan="5">조회된 Cafe24 상품이 없습니다. 상품명 또는 상품번호로 검색해 주세요.</td></tr>`}
          </tbody>
        </table>
      </div>
      ${
        detail
          ? `
            <div class="admin-empty-card">
              <div class="admin-action-row">
                <span class="admin-badge is-neutral">선택 상품</span>
                <strong>${escapeHtml(detail.productName || "상품명 없음")}</strong>
                <span>${escapeHtml(detail.productNo || "")}</span>
                ${useButton(detail)}
              </div>
              ${warnings.length ? `<p class="admin-inline-note">${warnings.map((warning) => escapeHtml(warning)).join("<br />")}</p>` : ""}
              <div class="admin-two-column">
                <div>
                  <h4>상품 옵션</h4>
                  ${
                    (detail.options || []).length
                      ? `<ul class="admin-guide-list">${detail.options.map((option) => `
                          <li>
                            <strong>${escapeHtml(option.name || "옵션")}</strong>
                            <span>${escapeHtml((option.values || []).join(", ") || option.value || "-")}</span>
                          </li>
                        `).join("")}</ul>`
                      : `<p class="admin-inline-note">등록된 옵션 정보가 없습니다.</p>`
                  }
                </div>
                <div>
                  <h4>품목/옵션 코드</h4>
                  <div class="admin-table-wrap">
                    <table class="admin-table">
                      <thead><tr><th>품목코드</th><th>옵션</th><th>자체코드</th><th>작업</th></tr></thead>
                      <tbody>
                        ${(detail.variants || []).length ? detail.variants.map((variant) => `
                          <tr>
                            <td>${escapeHtml(variant.variantCode || variant.productCode || "-")}</td>
                            <td>${escapeHtml(variant.optionText || "-")}</td>
                            <td>${escapeHtml(variant.customProductCode || "-")}</td>
                            <td>${useButton(detail, variant)}</td>
                          </tr>
                        `).join("") : `<tr><td colspan="4">품목 코드가 없습니다. 옵션 없는 단일 상품이면 상품번호만 매핑해도 됩니다.</td></tr>`}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              <details>
                <summary>원본 상품 payload 보기</summary>
                <pre class="admin-code-block">${escapeHtml(JSON.stringify(detail.raw || {}, null, 2))}</pre>
              </details>
            </div>
          `
          : ""
      }
    </div>
  `;
}
