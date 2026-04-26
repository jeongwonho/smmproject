import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DEFAULT_ROOT = path.resolve(__dirname, "..");

const LINE_BUDGETS = [
  ["static/app.js", 5200],
  ["static/admin/pages.js", 800],
  ["static/admin/sections.js", 3800],
  ["static/public/pages.js", 1400],
  ["static/public/charge.js", 800],
  ["static/public/auth.js", 600],
  ["static/styles/public.css", 2300],
  ["static/styles/admin.css", 800],
  ["static/styles/shared.css", 5200],
];

async function readText(root, relativePath) {
  return readFile(path.join(root, relativePath), "utf8");
}

function countLines(content) {
  return content.split(/\r?\n/).length;
}

async function listFiles(dir, prefix = "") {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relativePath = path.join(prefix, entry.name);
    const absolutePath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFiles(absolutePath, relativePath)));
    } else {
      files.push(relativePath);
    }
  }
  return files;
}

function assertNoBoundaryImports(errors, relativePath, content) {
  if (relativePath.startsWith("static/public/") && /from\s+["'][^"']*admin\//.test(content)) {
    errors.push(`${relativePath}: public module must not import admin modules.`);
  }
  if (relativePath.startsWith("static/admin/") && /from\s+["'][^"']*public\//.test(content)) {
    errors.push(`${relativePath}: admin module must not import public modules.`);
  }
}

function assertAppIsThin(errors, content) {
  const blockedPatterns = [
    [/function\s+renderAdmin[A-Z]/, "admin render functions belong in static/admin/*.js"],
    [/function\s+renderAnalytics[A-Z]/, "admin analytics render functions belong in static/admin/*.js"],
    [/function\s+renderCustomerAdminSection/, "admin customer section belongs in static/admin/sections.js"],
    [/function\s+renderCatalogAdminSection/, "admin catalog section belongs in static/admin/sections.js"],
    [/function\s+renderSupplierAdminSection/, "admin supplier section belongs in static/admin/sections.js"],
  ];
  for (const [pattern, message] of blockedPatterns) {
    if (pattern.test(content)) {
      errors.push(`static/app.js: ${message}.`);
    }
  }
}

function assertStyleEntrypoints(errors, indexHtml) {
  if (!indexHtml.includes('/static/styles/shared.css')) {
    errors.push("static/index.html: shared stylesheet entry is missing.");
  }
  if (!indexHtml.includes('/static/styles/public.css')) {
    errors.push("static/index.html: public stylesheet entry is missing.");
  }
  if (indexHtml.includes('/static/styles/admin.css')) {
    errors.push("static/index.html: public entry must not load admin.css directly.");
  }
}

export async function runArchitectureCheck(options = {}) {
  const root = options.root || DEFAULT_ROOT;
  const errors = [];
  const warnings = [];

  for (const [relativePath, budget] of LINE_BUDGETS) {
    const content = await readText(root, relativePath);
    const lines = countLines(content);
    if (lines > budget) {
      errors.push(`${relativePath}: ${lines} lines exceeds architecture budget ${budget}. Split new work into a domain module.`);
    }
  }

  const staticFiles = (await listFiles(path.join(root, "static")))
    .filter((relativePath) => relativePath.endsWith(".js"))
    .map((relativePath) => path.join("static", relativePath));
  for (const relativePath of staticFiles) {
    const content = await readText(root, relativePath);
    assertNoBoundaryImports(errors, relativePath, content);
  }

  const appJs = await readText(root, "static/app.js");
  assertAppIsThin(errors, appJs);

  const indexHtml = await readText(root, "static/index.html");
  assertStyleEntrypoints(errors, indexHtml);

  if (warnings.length) {
    for (const warning of warnings) console.warn(`[architecture] ${warning}`);
  }
  if (errors.length) {
    const details = errors.map((error) => `- ${error}`).join("\n");
    throw new Error(`Architecture check failed:\n${details}`);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runArchitectureCheck().catch((error) => {
    console.error(error.message || error);
    process.exitCode = 1;
  });
}
