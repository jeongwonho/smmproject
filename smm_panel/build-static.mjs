import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const staticDir = path.join(__dirname, "static");
const distDir = path.join(__dirname, "dist");
const distStaticDir = path.join(distDir, "static");

const apiBaseUrl = String(process.env.SMM_PANEL_PUBLIC_API_BASE_URL || "").trim();

async function build() {
  await rm(distDir, { recursive: true, force: true });
  await mkdir(distStaticDir, { recursive: true });
  await cp(staticDir, distStaticDir, { recursive: true });

  let indexHtml = await readFile(path.join(staticDir, "index.html"), "utf8");
  indexHtml = indexHtml.replace(
    '<meta name="smm-api-base-url" content="" data-managed-runtime="api-base" />',
    `<meta name="smm-api-base-url" content="${apiBaseUrl.replace(/"/g, "&quot;")}" data-managed-runtime="api-base" />`
  );

  await writeFile(path.join(distDir, "index.html"), indexHtml, "utf8");
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
