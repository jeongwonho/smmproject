import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { runArchitectureCheck } from "./scripts/architecture-check.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const staticDir = path.join(__dirname, "static");
const distDir = path.join(__dirname, "dist");
const distStaticDir = path.join(distDir, "static");

const apiBaseUrl = String(process.env.SMM_PANEL_PUBLIC_API_BASE_URL || "").trim();
const publicManagedHead = [
  '<meta name="description" content="인스타마트는 SNS 계정 비밀번호를 요구하지 않는 마케팅 서비스 주문 플랫폼입니다. 상품별 안내와 정책을 확인한 뒤 주문할 수 있습니다." />',
  '<meta name="theme-color" content="#b96bc6" />',
  '<meta property="og:title" content="인스타마트" />',
  '<meta property="og:description" content="SNS 계정 비밀번호 없이 계정 ID 또는 게시물 URL로 주문할 수 있는 마케팅 서비스 플랫폼입니다." />',
  '<meta property="og:type" content="website" />',
  '<meta name="twitter:card" content="summary" />',
].join("\n    ");
const adminManagedHead = [
  '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex" />',
  '<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex" />',
  '<meta name="description" content="인스타마트 관리자 콘솔" />',
].join("\n    ");

async function build() {
  await runArchitectureCheck({ root: __dirname });

  await rm(distDir, { recursive: true, force: true });
  await mkdir(distStaticDir, { recursive: true });
  await cp(staticDir, distStaticDir, { recursive: true });

  let indexHtml = await readFile(path.join(staticDir, "index.html"), "utf8");
  indexHtml = indexHtml.replace(
    '<meta name="smm-api-base-url" content="" data-managed-runtime="api-base" />',
    `<meta name="smm-api-base-url" content="${apiBaseUrl.replace(/"/g, "&quot;")}" data-managed-runtime="api-base" />`
  );
  indexHtml = indexHtml.replace("<!-- SMM_MANAGED_HEAD -->", publicManagedHead);

  await writeFile(path.join(distDir, "index.html"), indexHtml, "utf8");
  await writeFile(
    path.join(distDir, "robots.txt"),
    await readFile(path.join(staticDir, "robots.txt"), "utf8"),
    "utf8"
  );

  const adminHtml = indexHtml
    .replace(publicManagedHead, adminManagedHead)
    .replaceAll('data-route-surface="public"', 'data-route-surface="admin"')
    .replace(
      '<link rel="stylesheet" href="/static/styles/public.css" data-surface-style="public" />',
      '<link rel="stylesheet" href="/static/styles/admin.css" data-surface-style="admin" />'
    );
  await writeFile(path.join(distDir, "admin.html"), adminHtml, "utf8");
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
