export function readRuntimeMeta(doc, name) {
  return doc.querySelector(`meta[name="${name}"]`)?.getAttribute("content") || "";
}

export function sanitizeApiBaseUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw);
    if (!/^https?:$/.test(parsed.protocol)) return "";
    return parsed.href.replace(/\/+$/, "");
  } catch (_) {
    return "";
  }
}

export function createRuntimeConfig(doc, win) {
  return Object.freeze({
    apiBaseUrl: sanitizeApiBaseUrl(readRuntimeMeta(doc, "smm-api-base-url") || win.__SMM_CONFIG__?.apiBaseUrl || ""),
  });
}
