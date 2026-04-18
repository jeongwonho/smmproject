export function parseRoute(pathname, normalizeAdminSectionId) {
  const normalizedPath = String(pathname || "").replace(/\/+$/, "") || "/";
  if (normalizedPath === "/") return { name: "home" };
  if (normalizedPath === "/admin") return { name: "admin", section: "overview" };
  if (normalizedPath.startsWith("/admin/")) {
    const sectionId = decodeURIComponent(normalizedPath.split("/")[2] || "");
    return { name: "admin", section: normalizeAdminSectionId(sectionId) };
  }
  if (normalizedPath === "/products") return { name: "products" };
  if (normalizedPath.startsWith("/products/")) return { name: "detail", id: decodeURIComponent(normalizedPath.split("/")[2]) };
  if (normalizedPath === "/auth") return { name: "auth" };
  if (normalizedPath === "/help") return { name: "help" };
  if (normalizedPath === "/legal/terms") return { name: "legal", documentKey: "terms" };
  if (normalizedPath === "/legal/privacy") return { name: "legal", documentKey: "privacy" };
  if (normalizedPath === "/legal/marketing") return { name: "legal", documentKey: "marketing" };
  if (normalizedPath === "/charge") return { name: "charge" };
  if (normalizedPath === "/orders") return { name: "orders" };
  if (normalizedPath === "/my") return { name: "my" };
  return { name: "home" };
}
