const state = {
  bootstrap: null,
  currentProject: null,
  referenceDrafts: [],
  activeJob: null,
  jobTimer: null,
  selectedVariantId: "",
  reviewScope: { type: "project", key: "" },
  lastPin: { x: 50, y: 50 },
};

const els = {
  noticeBar: document.querySelector("#notice-bar"),
  heroStats: document.querySelector("#hero-stats"),
  accessUrlList: document.querySelector("#access-url-list"),
  projectList: document.querySelector("#project-list"),
  refreshBootstrapButton: document.querySelector("#refresh-bootstrap-button"),
  newProjectButton: document.querySelector("#new-project-button"),
  heroAnalyzeButton: document.querySelector("#hero-analyze-button"),
  projectForm: document.querySelector("#project-form"),
  saveProjectButton: document.querySelector("#save-project-button"),
  analyzeBrandButton: document.querySelector("#analyze-brand-button"),
  referenceFiles: document.querySelector("#reference-files"),
  referenceList: document.querySelector("#reference-list"),
  projectStatusPill: document.querySelector("#project-status-pill"),
  projectSummary: document.querySelector("#project-summary"),
  projectNotices: document.querySelector("#project-notices"),
  brandOverview: document.querySelector("#brand-overview"),
  toneChipList: document.querySelector("#tone-chip-list"),
  paletteList: document.querySelector("#palette-list"),
  coreVisualList: document.querySelector("#core-visual-list"),
  lockList: document.querySelector("#lock-list"),
  urlSummaryList: document.querySelector("#url-summary-list"),
  referenceSummaryList: document.querySelector("#reference-summary-list"),
  refreshBrandPanelButton: document.querySelector("#refresh-brand-panel-button"),
  presetSelect: document.querySelector("#preset-select"),
  createRouteSelect: document.querySelector("#create-route-select"),
  draftCount: document.querySelector("#draft-count"),
  createDirection: document.querySelector("#create-direction"),
  generateCreateButton: document.querySelector("#generate-create-button"),
  createOneVariants: document.querySelector("#create-one-variants"),
  gridSizeSelect: document.querySelector("#grid-size-select"),
  groupingModeSelect: document.querySelector("#grouping-mode-select"),
  masterToneInput: document.querySelector("#master-tone-input"),
  gridRouteSelect: document.querySelector("#grid-route-select"),
  autoGridButton: document.querySelector("#auto-grid-button"),
  saveGridButton: document.querySelector("#save-grid-button"),
  generateGridButton: document.querySelector("#generate-grid-button"),
  regenerateUnlockedButton: document.querySelector("#regenerate-unlocked-button"),
  tripletEditor: document.querySelector("#triplet-editor"),
  gridWarningList: document.querySelector("#grid-warning-list"),
  feedGrid: document.querySelector("#feed-grid"),
  reviewTargetLabel: document.querySelector("#review-target-label"),
  reviewPreviewShell: document.querySelector("#review-preview-shell"),
  selectVariantButton: document.querySelector("#select-variant-button"),
  needsRevisionButton: document.querySelector("#needs-revision-button"),
  approveVariantButton: document.querySelector("#approve-variant-button"),
  commentAuthor: document.querySelector("#comment-author"),
  commentStatus: document.querySelector("#comment-status"),
  commentBody: document.querySelector("#comment-body"),
  pinReadout: document.querySelector("#pin-readout"),
  addCommentButton: document.querySelector("#add-comment-button"),
  commentList: document.querySelector("#comment-list"),
  exportProjectButton: document.querySelector("#export-project-button"),
  exportObsidianButton: document.querySelector("#export-obsidian-button"),
  exportLink: document.querySelector("#export-link"),
  obsidianLink: document.querySelector("#obsidian-link"),
  jobStatusBox: document.querySelector("#job-status-box"),
  settingsForm: document.querySelector("#settings-form"),
  googleKeyState: document.querySelector("#google-key-state"),
  projectName: document.querySelector("#project-name"),
  clientName: document.querySelector("#client-name"),
  brandName: document.querySelector("#brand-name"),
  industry: document.querySelector("#industry"),
  ownerName: document.querySelector("#owner-name"),
  budgetLimit: document.querySelector("#budget-limit"),
  goal: document.querySelector("#goal"),
  serviceSummary: document.querySelector("#service-summary"),
  targetAudience: document.querySelector("#target-audience"),
  homepageUrl: document.querySelector("#homepage-url"),
  instagramUrl: document.querySelector("#instagram-url"),
  requiredKeywords: document.querySelector("#required-keywords"),
  bannedKeywords: document.querySelector("#banned-keywords"),
  requiredColors: document.querySelector("#required-colors"),
  bannedColors: document.querySelector("#banned-colors"),
  settingBudgetDefault: document.querySelector("#setting-budget-default"),
  settingDailyLimit: document.querySelector("#setting-daily-limit"),
  settingAllowFinal: document.querySelector("#setting-allow-final"),
  settingObsidianVault: document.querySelector("#setting-obsidian-vault"),
  settingObsidianFolder: document.querySelector("#setting-obsidian-folder"),
  settingDraftProvider: document.querySelector("#setting-draft-provider"),
  settingDraftModel: document.querySelector("#setting-draft-model"),
  settingDraftCost: document.querySelector("#setting-draft-cost"),
  settingFinalProvider: document.querySelector("#setting-final-provider"),
  settingFinalModel: document.querySelector("#setting-final-model"),
  settingFinalCost: document.querySelector("#setting-final-cost"),
  settingPhotoProvider: document.querySelector("#setting-photo-provider"),
  settingPhotoModel: document.querySelector("#setting-photo-model"),
  settingPhotoCost: document.querySelector("#setting-photo-cost"),
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindEvents();
  await loadBootstrap();
}

function bindEvents() {
  els.refreshBootstrapButton.addEventListener("click", () => {
    loadBootstrap(true).catch(handleError);
  });

  els.newProjectButton.addEventListener("click", () => {
    prepareNewProject();
    setNotice("새 프로젝트 입력 상태로 전환했습니다.");
  });

  els.heroAnalyzeButton.addEventListener("click", () => {
    handleAnalyzeBrand().catch(handleError);
  });

  els.projectForm.addEventListener("submit", (event) => {
    event.preventDefault();
    persistProject().catch(handleError);
  });

  els.analyzeBrandButton.addEventListener("click", () => {
    handleAnalyzeBrand().catch(handleError);
  });

  els.referenceFiles.addEventListener("change", async (event) => {
    const input = event.target;
    const files = Array.from(input.files || []);
    if (!files.length) {
      return;
    }
    try {
      setNotice("참조 이미지를 정리하는 중입니다...", "info");
      const prepared = [];
      for (const file of files) {
        prepared.push(await prepareReferenceAsset(file));
      }
      state.referenceDrafts = [...state.referenceDrafts, ...prepared];
      renderReferenceDrafts();
      setNotice(`${prepared.length}개의 참조 이미지를 추가했습니다.`);
    } catch (error) {
      handleError(error);
    } finally {
      input.value = "";
    }
  });

  els.projectList.addEventListener("click", (event) => {
    const selectButton = event.target.closest("[data-project-select]");
    if (!selectButton) {
      return;
    }
    loadProject(selectButton.dataset.projectSelect).catch(handleError);
  });

  document.body.addEventListener("click", (event) => {
    const removeReference = event.target.closest("[data-remove-reference]");
    if (removeReference) {
      state.referenceDrafts = state.referenceDrafts.filter(
        (item) => item.assetId !== removeReference.dataset.removeReference
      );
      renderReferenceDrafts();
      return;
    }

    const reviewVariant = event.target.closest("[data-review-variant]");
    if (reviewVariant) {
      const variantId = reviewVariant.dataset.reviewVariant;
      focusReviewVariant(variantId);
      renderReviewPanel();
      return;
    }

    const selectVariant = event.target.closest("[data-select-variant]");
    if (selectVariant) {
      updateVariant(selectVariant.dataset.selectVariant, { selected: true }, "선택안을 반영했습니다.").catch(
        handleError
      );
      return;
    }

    const lockVariant = event.target.closest("[data-lock-variant]");
    if (lockVariant) {
      const variantId = lockVariant.dataset.lockVariant;
      const variant = findVariantById(variantId);
      updateVariant(variantId, { locked: !variant?.locked }, "잠금 상태를 변경했습니다.").catch(handleError);
      return;
    }

    const slotReview = event.target.closest("[data-slot-review]");
    if (slotReview) {
      const slotId = slotReview.dataset.slotReview;
      const variant = getSelectedSlotVariant(slotId);
      state.reviewScope = { type: "slot", key: slotId };
      state.selectedVariantId = variant?.id || "";
      renderReviewPanel();
      return;
    }

    const slotRegen = event.target.closest("[data-slot-regen]");
    if (slotRegen) {
      handleGenerateGrid({ slotIds: [slotRegen.dataset.slotRegen] }).catch(handleError);
      return;
    }

    const slotLock = event.target.closest("[data-slot-lock]");
    if (slotLock) {
      const slotId = slotLock.dataset.slotLock;
      toggleSlotLock(slotId).catch(handleError);
    }
  });

  els.generateCreateButton.addEventListener("click", () => {
    handleGenerateCreateOne().catch(handleError);
  });

  els.autoGridButton.addEventListener("click", () => {
    handleAutoGrid().catch(handleError);
  });

  els.saveGridButton.addEventListener("click", () => {
    saveGridPlan().catch(handleError);
  });

  els.generateGridButton.addEventListener("click", () => {
    handleGenerateGrid().catch(handleError);
  });

  els.regenerateUnlockedButton.addEventListener("click", () => {
    handleGenerateGrid().catch(handleError);
  });

  els.refreshBrandPanelButton.addEventListener("click", () => {
    renderBrandPanel();
  });

  els.reviewPreviewShell.addEventListener("click", (event) => {
    capturePin(event);
  });

  els.selectVariantButton.addEventListener("click", () => {
    if (!state.selectedVariantId) {
      setNotice("선택할 버전이 없습니다.", "warn");
      return;
    }
    updateVariant(state.selectedVariantId, { selected: true }, "선택 버전을 지정했습니다.").catch(handleError);
  });

  els.needsRevisionButton.addEventListener("click", () => {
    if (!state.selectedVariantId) {
      setNotice("상태를 바꿀 버전이 없습니다.", "warn");
      return;
    }
    updateVariant(state.selectedVariantId, { status: "Needs Revision" }, "수정 필요 상태로 변경했습니다.").catch(
      handleError
    );
  });

  els.approveVariantButton.addEventListener("click", () => {
    if (!state.selectedVariantId) {
      setNotice("승인할 버전이 없습니다.", "warn");
      return;
    }
    updateVariant(state.selectedVariantId, { selected: true, status: "Approved", locked: true }, "승인하고 잠금 처리했습니다.").catch(
      handleError
    );
  });

  els.addCommentButton.addEventListener("click", () => {
    handleAddComment().catch(handleError);
  });

  els.exportProjectButton.addEventListener("click", () => {
    handleExport().catch(handleError);
  });

  els.exportObsidianButton.addEventListener("click", () => {
    handleObsidianExport().catch(handleError);
  });

  els.settingsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveSettings().catch(handleError);
  });
}

async function api(url, options = {}) {
  const config = { ...options };
  config.headers = { ...(config.headers || {}) };
  if (config.body && !config.headers["Content-Type"]) {
    config.headers["Content-Type"] = "application/json; charset=utf-8";
  }
  const response = await fetch(url, config);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `요청 실패 (${response.status})`);
  }
  return payload;
}

function handleError(error) {
  const message = error instanceof Error ? error.message : String(error);
  setNotice(message, "warn");
  console.error(error);
}

function setNotice(message, tone = "info") {
  if (!message) {
    els.noticeBar.classList.add("is-hidden");
    els.noticeBar.textContent = "";
    return;
  }
  els.noticeBar.textContent = message;
  els.noticeBar.classList.remove("is-hidden");
  els.noticeBar.style.color = tone === "warn" ? "var(--orange)" : "var(--accent-strong)";
}

function splitList(value) {
  return String(value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  try {
    return new Date(value).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function formatCredits(value) {
  return `${Number(value || 0).toFixed(2)} cr`;
}

function randomId(prefix) {
  if (window.crypto?.randomUUID) {
    return `${prefix}-${window.crypto.randomUUID().slice(0, 8)}`;
  }
  return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
}

function emptyState(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

async function loadBootstrap(preserveSelection = true) {
  const data = await api("/api/bootstrap");
  state.bootstrap = data;
  fillSettingsForm(data.settings);
  renderHero(data);
  renderProjectList();

  const currentId = state.currentProject?.id;
  if (preserveSelection && currentId && data.projects.some((item) => item.id === currentId)) {
    await loadProject(currentId, { preserveExistingReview: true, quiet: true });
    return;
  }

  if (!state.currentProject && data.projects.length) {
    await loadProject(data.projects[0].id, { quiet: true });
    return;
  }

  if (!data.projects.length) {
    prepareNewProject();
    renderAll();
  }
}

async function loadProject(projectId, options = {}) {
  if (!projectId) {
    return;
  }
  const payload = await api(`/api/projects/${projectId}`);
  setCurrentProject(payload.project, options);
}

function setCurrentProject(project, options = {}) {
  state.currentProject = project;
  state.referenceDrafts = Array.isArray(project.brief?.references)
    ? project.brief.references.map((item) => ({ ...item }))
    : [];
  fillProjectForm(project);
  fillGeneratorControls(project);
  syncReviewSelection(project, options);
  renderAll();
}

function syncReviewSelection(project, options = {}) {
  const variants = project.variants || [];
  const preferred = options.preferredVariantId;
  if (preferred && variants.some((item) => item.id === preferred)) {
    state.selectedVariantId = preferred;
    const variant = variants.find((item) => item.id === preferred);
    state.reviewScope = { type: variant.scopeType, key: variant.scopeKey };
    return;
  }

  if (
    options.preserveExistingReview &&
    state.selectedVariantId &&
    variants.some((item) => item.id === state.selectedVariantId)
  ) {
    return;
  }

  const selectedSlot = variants.find((item) => item.scopeType === "slot" && item.selected);
  const selectedCreate = variants.find((item) => item.scopeType === "one" && item.selected);
  const fallback = selectedSlot || selectedCreate || variants[0];

  state.selectedVariantId = fallback?.id || "";
  if (fallback) {
    state.reviewScope = { type: fallback.scopeType, key: fallback.scopeKey };
  } else {
    state.reviewScope = { type: "project", key: project.id };
  }
  state.lastPin = { x: 50, y: 50 };
}

function prepareNewProject() {
  state.currentProject = null;
  state.referenceDrafts = [];
  state.selectedVariantId = "";
  state.reviewScope = { type: "project", key: "" };
  state.lastPin = { x: 50, y: 50 };
  fillProjectForm(null);
  fillGeneratorControls(null);
  renderAll();
}

function fillProjectForm(project) {
  const brief = project?.brief || {};
  els.projectName.value = brief.projectName || "";
  els.clientName.value = brief.client || "";
  els.brandName.value = brief.brandName || "";
  els.industry.value = brief.industry || "";
  els.ownerName.value = brief.owner || "";
  els.budgetLimit.value =
    project?.budgetLimit || state.bootstrap?.settings?.projectBudgetDefault || "";
  els.goal.value = brief.goal || "";
  els.serviceSummary.value = brief.serviceSummary || "";
  els.targetAudience.value = brief.targetAudience || "";
  els.homepageUrl.value = brief.homepageUrl || "";
  els.instagramUrl.value = brief.instagramUrl || "";
  els.requiredKeywords.value = (brief.requiredKeywords || []).join(", ");
  els.bannedKeywords.value = (brief.bannedKeywords || []).join(", ");
  els.requiredColors.value = (brief.requiredColors || []).join(", ");
  els.bannedColors.value = (brief.bannedColors || []).join(", ");
  renderReferenceDrafts();
}

function fillGeneratorControls(project) {
  const createOne = project?.createOne || {};
  const gridPlan = project?.gridPlan || {};
  els.presetSelect.value = createOne.lastPreset || "Hero";
  els.createRouteSelect.value = createOne.lastRoute || "draft";
  els.draftCount.value = String(createOne.lastCount || 4);
  els.createDirection.value = createOne.lastDirection || "";
  els.gridSizeSelect.value = String(gridPlan.gridSize || project?.gridSize || 9);
  els.groupingModeSelect.value = gridPlan.groupingMode || project?.groupingMode || "row";
  els.masterToneInput.value = gridPlan.masterTone || project?.brandPack?.masterTone || "";
  els.gridRouteSelect.value = "draft";
}

function fillSettingsForm(settings) {
  if (!settings) {
    return;
  }
  els.settingBudgetDefault.value = settings.projectBudgetDefault;
  els.settingDailyLimit.value = settings.dailyGenerationLimit;
  els.settingAllowFinal.checked = Boolean(settings.allowFinalOnlyForSelected);
  els.settingObsidianVault.value = settings.obsidian?.vaultPath || "";
  els.settingObsidianFolder.value = settings.obsidian?.ideaFolder || "MVP Ideas";
  fillRouteForm("draft", settings.routes.draft);
  fillRouteForm("final", settings.routes.final);
  fillRouteForm("photo", settings.routes.photo);
  els.googleKeyState.textContent = settings.hasGoogleApiKey
    ? "GOOGLE_API_KEY가 서버 환경에 설정되어 있습니다."
    : "GOOGLE_API_KEY가 없어 현재는 Mock 렌더러 중심으로 동작합니다.";
}

function fillRouteForm(route, config) {
  document.querySelector(`#setting-${route}-provider`).value = config.provider;
  document.querySelector(`#setting-${route}-model`).value = config.model;
  document.querySelector(`#setting-${route}-cost`).value = config.unitCost;
}

function collectProjectPayload() {
  return {
    budgetLimit: Number(els.budgetLimit.value || 0),
    gridSize: Number(els.gridSizeSelect.value || 9),
    groupingMode: els.groupingModeSelect.value,
    brief: {
      projectName: els.projectName.value.trim(),
      client: els.clientName.value.trim(),
      brandName: els.brandName.value.trim(),
      industry: els.industry.value.trim(),
      owner: els.ownerName.value.trim(),
      goal: els.goal.value.trim(),
      serviceSummary: els.serviceSummary.value.trim(),
      targetAudience: els.targetAudience.value.trim(),
      homepageUrl: els.homepageUrl.value.trim(),
      instagramUrl: els.instagramUrl.value.trim(),
      requiredKeywords: splitList(els.requiredKeywords.value),
      bannedKeywords: splitList(els.bannedKeywords.value),
      requiredColors: splitList(els.requiredColors.value),
      bannedColors: splitList(els.bannedColors.value),
      references: state.referenceDrafts.map((item) => ({ ...item })),
    },
  };
}

async function persistProject(options = {}) {
  const url = state.currentProject ? `/api/projects/${state.currentProject.id}` : "/api/projects";
  const payload = collectProjectPayload();
  const response = await api(url, { method: "POST", body: JSON.stringify(payload) });
  mergeProjectSummary(response.project);
  setCurrentProject(response.project, {
    preserveExistingReview: options.silent,
    preferredVariantId: state.selectedVariantId,
  });
  if (!options.silent) {
    setNotice(state.currentProject ? "프로젝트를 저장했습니다." : "프로젝트를 생성했습니다.");
  }
  return response.project;
}

function mergeProjectSummary(project) {
  if (!state.bootstrap) {
    return;
  }
  const summary = {
    id: project.id,
    projectName: project.projectName,
    client: project.client,
    brandName: project.brandName,
    industry: project.industry,
    owner: project.owner,
    goal: project.goal,
    status: project.status,
    budgetLimit: project.budgetLimit,
    spentCost: project.spentCost || 0,
    gridSize: project.gridSize,
    updatedAt: project.updatedAt,
    variantCount: project.variants?.length || 0,
  };
  const projects = state.bootstrap.projects || [];
  const existingIndex = projects.findIndex((item) => item.id === summary.id);
  if (existingIndex >= 0) {
    projects.splice(existingIndex, 1, summary);
  } else {
    projects.unshift(summary);
  }
  renderHero(state.bootstrap);
  renderProjectList();
}

async function ensureProjectSaved() {
  return persistProject({ silent: true });
}

async function handleAnalyzeBrand() {
  const project = await ensureProjectSaved();
  setNotice("Brand Pack을 분석하고 있습니다...", "info");
  const response = await api(`/api/projects/${project.id}/brand-pack/analyze`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  mergeProjectSummary(response.project);
  setCurrentProject(response.project, { preserveExistingReview: true });
  setNotice("Brand Pack 분석이 완료되었습니다.");
}

async function handleAutoGrid() {
  const project = await ensureProjectSaved();
  setNotice("그리드 역할과 Triplet tone을 다시 제안하고 있습니다...", "info");
  const response = await api(`/api/projects/${project.id}/grid-plan/auto`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  setCurrentProject(response.project, { preserveExistingReview: true });
  setNotice("그리드 제안을 다시 구성했습니다.");
}

function collectGridPlanPayload() {
  const current = state.currentProject;
  const triplets = Array.from(document.querySelectorAll("[data-triplet-card]")).map((card) => ({
    id: card.dataset.tripletCard,
    label: card.querySelector("[data-triplet-label]")?.value?.trim() || "",
    tone: card.querySelector("[data-triplet-tone]")?.value?.trim() || "",
    roles: splitList(card.querySelector("[data-triplet-roles]")?.value || ""),
  }));

  const slots = Array.from(document.querySelectorAll("[data-slot-card]")).map((card, index) => ({
    id: card.dataset.slotCard,
    index: index + 1,
    tripletId: card.dataset.tripletId,
    role: card.querySelector("[data-slot-role]")?.value?.trim() || "",
    tone: card.querySelector("[data-slot-tone]")?.value?.trim() || "",
    locked: Boolean(card.querySelector("[data-slot-locked]")?.checked),
    status: card.dataset.slotStatus || "Draft",
    selectedVariantId: card.dataset.selectedVariantId || "",
    notes: card.querySelector("[data-slot-notes]")?.value?.trim() || "",
  }));

  return {
    gridPlan: {
      gridSize: Number(els.gridSizeSelect.value || current?.gridSize || 9),
      groupingMode: els.groupingModeSelect.value,
      masterTone: els.masterToneInput.value.trim(),
      triplets,
      slots,
    },
  };
}

async function saveGridPlan(options = {}) {
  if (!state.currentProject) {
    throw new Error("먼저 프로젝트를 저장해주세요.");
  }
  const response = await api(`/api/projects/${state.currentProject.id}/grid-plan/save`, {
    method: "POST",
    body: JSON.stringify(collectGridPlanPayload()),
  });
  setCurrentProject(response.project, { preserveExistingReview: true });
  if (!options.silent) {
    setNotice("그리드 설정을 저장했습니다.");
  }
  return response.project;
}

async function handleGenerateCreateOne() {
  const project = await ensureProjectSaved();
  const payload = {
    preset: els.presetSelect.value,
    route: els.createRouteSelect.value,
    count: Number(els.draftCount.value || 4),
    direction: els.createDirection.value.trim(),
  };
  setNotice("단품 시안 생성을 시작했습니다...", "info");
  const response = await api(`/api/projects/${project.id}/create-one/generate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  trackJob(response.job);
}

async function handleGenerateGrid(extra = {}) {
  if (!state.currentProject) {
    throw new Error("먼저 프로젝트를 저장해주세요.");
  }
  await saveGridPlan({ silent: true });
  setNotice("그리드 생성을 시작했습니다...", "info");
  const response = await api(`/api/projects/${state.currentProject.id}/grid/generate`, {
    method: "POST",
    body: JSON.stringify({
      route: els.gridRouteSelect.value,
      direction: els.createDirection.value.trim(),
      ...extra,
    }),
  });
  trackJob(response.job);
}

function trackJob(job) {
  state.activeJob = job;
  renderJobPanel();
  if (state.jobTimer) {
    clearTimeout(state.jobTimer);
  }
  pollJob(job.id);
}

async function pollJob(jobId) {
  try {
    const payload = await api(`/api/jobs/${jobId}`);
    state.activeJob = payload.job;
    renderJobPanel();

    if (payload.job.status === "queued" || payload.job.status === "running") {
      state.jobTimer = window.setTimeout(() => {
        pollJob(jobId);
      }, 1200);
      return;
    }

    if (payload.job.status === "succeeded") {
      const preferredVariant = payload.job.result?.variants?.[0]?.id || state.selectedVariantId;
      await loadProject(payload.job.projectId, {
        preferredVariantId: preferredVariant,
      });
      await loadBootstrap(false);
      setNotice("백그라운드 작업이 완료되었습니다.");
      return;
    }

    setNotice(payload.job.errorMessage || "작업이 실패했습니다.", "warn");
  } catch (error) {
    handleError(error);
  }
}

function renderAll() {
  renderHero(state.bootstrap);
  renderProjectList();
  renderProjectSummary();
  renderBrandPanel();
  renderCreateOnePanel();
  renderGridPanel();
  renderReviewPanel();
  renderJobPanel();
}

function renderHero(data) {
  const current = state.currentProject;
  const warnings =
    (current?.brandPack?.warnings?.length || 0) + (current?.gridPlan?.warnings?.length || 0);
  const variantCount = current?.variants?.length || 0;
  const stats = [
    { label: "프로젝트", value: String(data?.projects?.length || 0) },
    { label: "현재 버전 수", value: String(variantCount) },
    { label: "예산 사용", value: current ? `${formatCredits(current.spentCost)} / ${formatCredits(current.budgetLimit)}` : "-" },
    { label: "경고", value: String(warnings) },
  ];
  els.heroStats.innerHTML = stats
    .map(
      (item) => `
        <article class="metric-card">
          <span>${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
        </article>
      `
    )
    .join("");

  const urls = data?.server?.accessUrls || [];
  els.accessUrlList.innerHTML = urls.length
    ? urls
        .map(
          (url) => `
            <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a>
          `
        )
        .join("")
    : emptyState("서버 접속 주소를 확인하지 못했습니다.");
}

function renderProjectList() {
  const projects = state.bootstrap?.projects || [];
  if (!projects.length) {
    els.projectList.innerHTML = emptyState("아직 저장된 프로젝트가 없습니다. 왼쪽 입력 폼에서 새 프로젝트를 만들어주세요.");
    return;
  }

  els.projectList.innerHTML = projects
    .map((project) => {
      const active = project.id === state.currentProject?.id ? "is-active" : "";
      return `
        <article class="project-card ${active}">
          <header>
            <div>
              <strong>${escapeHtml(project.projectName)}</strong>
              <div class="project-meta">${escapeHtml(project.client || project.brandName || "내부 프로젝트")}</div>
            </div>
            <span class="status-pill">${escapeHtml(project.status)}</span>
          </header>
          <div class="project-meta">${escapeHtml(project.industry || "업종 미입력")} · ${escapeHtml(project.owner || "담당자 미입력")}</div>
          <div class="project-meta">Grid ${project.gridSize} · ${project.variantCount} variants</div>
          <div class="project-meta">업데이트 ${escapeHtml(formatDate(project.updatedAt))}</div>
          <div class="project-actions">
            <button type="button" data-project-select="${escapeHtml(project.id)}">열기</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderReferenceDrafts() {
  if (!state.referenceDrafts.length) {
    els.referenceList.innerHTML = emptyState("참조 이미지를 추가하면 이곳에 팔레트와 미리보기가 표시됩니다.");
    return;
  }
  els.referenceList.innerHTML = state.referenceDrafts
    .map((item) => {
      const preview = item.assetUrl || item.dataUrl || "";
      const palette = (item.palette || [])
        .map((color) => `<span class="chip">${escapeHtml(color)}</span>`)
        .join("");
      return `
        <article class="reference-item">
          <header>
            <div>
              <strong>${escapeHtml(item.name || "reference")}</strong>
              <div class="project-meta">${escapeHtml(item.kind || "reference")}</div>
            </div>
            <button type="button" data-remove-reference="${escapeHtml(item.assetId)}">제거</button>
          </header>
          ${preview ? `<img src="${escapeHtml(preview)}" alt="${escapeHtml(item.name)}" />` : ""}
          <div class="chip-list">${palette || '<span class="project-meta">팔레트 준비 중</span>'}</div>
        </article>
      `;
    })
    .join("");
}

function renderProjectSummary() {
  const project = state.currentProject;
  if (!project) {
    els.projectStatusPill.textContent = "No Project";
    els.projectSummary.innerHTML = emptyState("프로젝트를 선택하면 예산, 버전 수, 승인 상태가 표시됩니다.");
    els.projectNotices.innerHTML = "";
    return;
  }

  const approvedSlots = project.variants.filter(
    (item) => item.scopeType === "slot" && item.selected && item.status.toLowerCase() === "approved"
  ).length;
  const cards = [
    { label: "Brand Match", value: project.brandPack.toneKeywords?.slice(0, 3).join(" · ") || "-" },
    { label: "Spent / Budget", value: `${formatCredits(project.spentCost)} / ${formatCredits(project.budgetLimit)}` },
    { label: "Grid Approval", value: `${approvedSlots} / ${project.gridPlan.gridSize}` },
    { label: "Updated", value: formatDate(project.updatedAt) },
  ];
  els.projectStatusPill.textContent = project.review?.projectStatus || project.status;
  els.projectSummary.innerHTML = cards
    .map(
      (item) => `
        <article class="metric-card">
          <span>${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
        </article>
      `
    )
    .join("");

  const notices = [...(project.brandPack.warnings || []), ...(project.gridPlan.warnings || [])];
  els.projectNotices.innerHTML = notices.length
    ? notices.map((item) => `<div>${escapeHtml(item)}</div>`).join("")
    : `<div class="empty-state">현재 경고 없이 안정적인 상태입니다.</div>`;
}

function renderBrandPanel() {
  const project = state.currentProject;
  if (!project) {
    els.brandOverview.textContent = "프로젝트를 저장하고 Brand Pack 분석을 실행하세요.";
    els.toneChipList.innerHTML = "";
    els.paletteList.innerHTML = "";
    els.coreVisualList.innerHTML = "";
    els.lockList.innerHTML = emptyState("브랜드 잠금 규칙이 아직 없습니다.");
    els.urlSummaryList.innerHTML = emptyState("URL 요약 결과가 아직 없습니다.");
    els.referenceSummaryList.innerHTML = emptyState("참조 이미지 요약이 아직 없습니다.");
    return;
  }

  const brandPack = project.brandPack || {};
  els.brandOverview.textContent = brandPack.overview || "분석 결과가 없습니다.";
  els.toneChipList.innerHTML = (brandPack.toneKeywords || [])
    .map((item) => `<span class="tone-chip">${escapeHtml(item)}</span>`)
    .join("");
  els.paletteList.innerHTML = (brandPack.palette || [])
    .map(
      (color) => `
        <div class="palette-swatch">
          <div class="palette-sample" style="background:${escapeHtml(color)}"></div>
          <span class="palette-swatch-label">${escapeHtml(color)}</span>
        </div>
      `
    )
    .join("");
  els.coreVisualList.innerHTML = (brandPack.coreVisuals || [])
    .map((item) => `<span class="tag">${escapeHtml(item)}</span>`)
    .join("");
  const locks = brandPack.locks || {};
  els.lockList.innerHTML = Object.entries(locks)
    .map(
      ([key, value]) => `
        <article class="lock-card">
          <strong>${escapeHtml(key)}</strong>
          <div class="project-meta">${escapeHtml(value || "미설정")}</div>
        </article>
      `
    )
    .join("");
  els.urlSummaryList.innerHTML = (brandPack.urlSummaries || []).length
    ? brandPack.urlSummaries
        .map(
          (item) => `
            <article class="url-card">
              <strong>${escapeHtml(item.title || item.url)}</strong>
              <div class="project-meta">${escapeHtml(item.description || "설명 없음")}</div>
              <div class="chip-list">${(item.keywords || [])
                .map((keyword) => `<span class="chip">${escapeHtml(keyword)}</span>`)
                .join("")}</div>
            </article>
          `
        )
        .join("")
    : emptyState("URL 요약이 아직 없습니다.");
  els.referenceSummaryList.innerHTML = (brandPack.referenceSummary || []).length
    ? brandPack.referenceSummary
        .map(
          (item) => `
            <article class="url-card">
              <strong>${escapeHtml(item.name)}</strong>
              <div class="project-meta">${escapeHtml(item.kind)}</div>
              <div class="chip-list">${(item.palette || [])
                .map((color) => `<span class="chip">${escapeHtml(color)}</span>`)
                .join("")}</div>
            </article>
          `
        )
        .join("")
    : emptyState("참조 이미지 분석 결과가 아직 없습니다.");
}

function renderCreateOnePanel() {
  const project = state.currentProject;
  if (!project) {
    els.createOneVariants.innerHTML = emptyState("프로젝트 저장 후 단품 시안을 생성할 수 있습니다.");
    return;
  }
  const variants = (project.variants || []).filter((item) => item.scopeType === "one");
  if (!variants.length) {
    els.createOneVariants.innerHTML = emptyState("아직 단품 시안이 없습니다.");
    return;
  }
  els.createOneVariants.innerHTML = variants
    .map(
      (variant) => `
        <article class="variant-card">
          <img src="${escapeHtml(variant.assetUrl)}" alt="${escapeHtml(variant.role)}" />
          <header>
            <div>
              <strong>${escapeHtml(variant.role)}</strong>
              <div class="variant-meta">v${variant.version} · ${escapeHtml(variant.route)}</div>
            </div>
            <span class="status-pill">${escapeHtml(variant.status)}</span>
          </header>
          <div class="variant-meta">score ${(variant.score || 0).toFixed(2)} · ${escapeHtml(variant.meta?.providerNotice || "")}</div>
          <div class="variant-actions">
            <button type="button" data-review-variant="${escapeHtml(variant.id)}">리뷰</button>
            <button type="button" data-select-variant="${escapeHtml(variant.id)}">
              ${variant.selected ? "선택됨" : "선택"}
            </button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderGridPanel() {
  const project = state.currentProject;
  if (!project) {
    els.tripletEditor.innerHTML = emptyState("프로젝트를 저장하면 Triplet 편집기가 표시됩니다.");
    els.gridWarningList.innerHTML = "";
    els.feedGrid.innerHTML = emptyState("그리드 프리뷰가 아직 없습니다.");
    return;
  }

  const gridPlan = project.gridPlan || {};
  els.feedGrid.classList.toggle("is-grid-12", Number(gridPlan.gridSize) === 12);
  els.tripletEditor.innerHTML = (gridPlan.triplets || [])
    .map((triplet) => {
      const roles = (gridPlan.slots || [])
        .filter((slot) => slot.tripletId === triplet.id)
        .map((slot) => slot.role)
        .join(", ");
      return `
        <article class="triplet-card" data-triplet-card="${escapeHtml(triplet.id)}">
          <strong>${escapeHtml(triplet.label)}</strong>
          <label>
            Label
            <input type="text" data-triplet-label value="${escapeHtml(triplet.label)}" />
          </label>
          <label>
            Tone
            <textarea rows="2" data-triplet-tone>${escapeHtml(triplet.tone)}</textarea>
          </label>
          <label>
            Roles
            <input type="text" data-triplet-roles value="${escapeHtml(roles)}" />
          </label>
        </article>
      `;
    })
    .join("");

  els.gridWarningList.innerHTML = (gridPlan.warnings || []).length
    ? (gridPlan.warnings || []).map((item) => `<div>${escapeHtml(item)}</div>`).join("")
    : "";

  els.feedGrid.innerHTML = (gridPlan.slots || [])
    .map((slot) => renderSlotCard(slot, project))
    .join("");
}

function renderSlotCard(slot, project) {
  const variants = getSlotVariants(slot.id);
  const selected = getSelectedSlotVariant(slot.id);
  const comments = getCommentsForScope("slot", slot.id);
  const commentPins = comments
    .map(
      (item) => `
        <span
          class="slot-pin"
          title="${escapeHtml(item.body)}"
          style="left:${Number(item.pinX || 50)}%; top:${Number(item.pinY || 50)}%;"
        ></span>
      `
    )
    .join("");

  return `
    <article
      class="slot-card ${slot.locked ? "is-locked" : ""}"
      data-slot-card="${escapeHtml(slot.id)}"
      data-triplet-id="${escapeHtml(slot.tripletId)}"
      data-slot-status="${escapeHtml(slot.status || "Draft")}"
      data-selected-variant-id="${escapeHtml(slot.selectedVariantId || selected?.id || "")}"
    >
      <header>
        <div>
          <strong>Slot ${String(slot.index).padStart(2, "0")}</strong>
          <div class="project-meta">${escapeHtml(slot.tripletId)}</div>
        </div>
        <span class="status-pill">${escapeHtml(slot.status || "Draft")}</span>
      </header>

      <div class="slot-preview">
        ${
          selected
            ? `<img src="${escapeHtml(selected.assetUrl)}" alt="${escapeHtml(slot.role)}" />`
            : `<div class="empty-state">아직 선택된 버전이 없습니다.</div>`
        }
        ${commentPins}
      </div>

      <label>
        Role
        <input type="text" data-slot-role value="${escapeHtml(slot.role)}" />
      </label>
      <label>
        Tone
        <input type="text" data-slot-tone value="${escapeHtml(slot.tone || "")}" />
      </label>
      <label>
        Notes
        <textarea rows="2" data-slot-notes placeholder="재생성 시 추가 디렉션">${escapeHtml(slot.notes || "")}</textarea>
      </label>
      <label class="checkbox-row">
        <input type="checkbox" data-slot-locked ${slot.locked ? "checked" : ""} />
        잠금 유지
      </label>

      <div class="mini-variants">
        ${
          variants.length
            ? variants
                .map(
                  (variant) => `
                    <button
                      type="button"
                      class="mini-variant ${variant.selected ? "is-selected" : ""}"
                      data-select-variant="${escapeHtml(variant.id)}"
                      title="${escapeHtml(variant.role)}"
                    >
                      <img src="${escapeHtml(variant.assetUrl)}" alt="${escapeHtml(variant.role)}" />
                    </button>
                  `
                )
                .join("")
            : `<div class="empty-state">버전 없음</div>`
        }
      </div>

      <div class="slot-actions">
        <button type="button" data-slot-review="${escapeHtml(slot.id)}">리뷰</button>
        <button type="button" data-slot-regen="${escapeHtml(slot.id)}">이 슬롯 재생성</button>
        <button type="button" data-slot-lock="${escapeHtml(slot.id)}">
          ${slot.locked ? "잠금 해제" : "잠금"}
        </button>
      </div>
    </article>
  `;
}

function renderReviewPanel() {
  const project = state.currentProject;
  const variant = getReviewVariant();
  const comments = getCurrentReviewComments();

  if (!project || !variant) {
    els.reviewTargetLabel.textContent = "리뷰 대상이 선택되지 않았습니다.";
    els.reviewPreviewShell.innerHTML =
      '<div class="preview-empty">슬롯이나 단품 시안을 선택하면 이곳에서 리뷰할 수 있습니다.</div>';
    els.commentList.innerHTML = emptyState("현재 범위에 달린 코멘트가 없습니다.");
    els.pinReadout.textContent = `핀 좌표: ${state.lastPin.x}%, ${state.lastPin.y}%`;
    els.exportLink.classList.add("is-hidden");
    return;
  }

  const pins = comments
    .map(
      (item) => `
        <span
          class="preview-pin"
          title="${escapeHtml(item.body)}"
          style="left:${Number(item.pinX || 50)}%; top:${Number(item.pinY || 50)}%;"
        ></span>
      `
    )
    .join("");

  els.reviewTargetLabel.textContent = `${variant.scopeType === "slot" ? variant.scopeKey : "Create One"} · ${
    variant.role
  } · ${variant.status}`;
  els.reviewPreviewShell.innerHTML = `
    <img src="${escapeHtml(variant.assetUrl)}" alt="${escapeHtml(variant.role)}" />
    ${pins}
  `;
  els.pinReadout.textContent = `핀 좌표: ${state.lastPin.x}%, ${state.lastPin.y}%`;
  els.commentList.innerHTML = comments.length
    ? comments
        .map(
          (item) => `
            <article class="comment-item">
              <header>
                <strong>${escapeHtml(item.author)}</strong>
                <span class="status-pill">${escapeHtml(item.status)}</span>
              </header>
              <p>${escapeHtml(item.body)}</p>
              <div class="project-meta">${escapeHtml(formatDate(item.createdAt))} · ${escapeHtml(
                `${Math.round(item.pinX)}%, ${Math.round(item.pinY)}%`
              )}</div>
            </article>
          `
        )
        .join("")
    : emptyState("현재 범위에 달린 코멘트가 없습니다.");
}

function renderJobPanel() {
  const job = state.activeJob;
  if (!job) {
    els.jobStatusBox.innerHTML = emptyState("진행 중인 작업이 없습니다.");
    return;
  }

  els.jobStatusBox.innerHTML = `
    <article class="job-card">
      <strong>${escapeHtml(job.jobType)}</strong>
      <div class="project-meta">${escapeHtml(job.status)}</div>
      <progress max="100" value="${Number(job.progress || 0)}"></progress>
      <div class="project-meta">${Number(job.progress || 0)}%</div>
      ${
        job.errorMessage
          ? `<div class="project-meta" style="color:var(--red)">${escapeHtml(job.errorMessage)}</div>`
          : ""
      }
    </article>
  `;
}

function findVariantById(variantId) {
  return state.currentProject?.variants?.find((item) => item.id === variantId) || null;
}

function getSlotVariants(slotId) {
  return (state.currentProject?.variants || []).filter(
    (item) => item.scopeType === "slot" && item.scopeKey === slotId
  );
}

function getSelectedSlotVariant(slotId) {
  const variants = getSlotVariants(slotId);
  return variants.find((item) => item.selected) || variants[0] || null;
}

function getReviewVariant() {
  if (!state.currentProject) {
    return null;
  }
  return findVariantById(state.selectedVariantId) || null;
}

function focusReviewVariant(variantId) {
  const variant = findVariantById(variantId);
  if (!variant) {
    return;
  }
  state.selectedVariantId = variant.id;
  state.reviewScope = { type: variant.scopeType, key: variant.scopeKey };
}

function getCommentsForScope(scopeType, scopeKey) {
  return (state.currentProject?.comments || []).filter(
    (item) => item.scopeType === scopeType && item.scopeKey === scopeKey
  );
}

function getCurrentReviewComments() {
  if (!state.reviewScope.key) {
    return [];
  }
  return getCommentsForScope(state.reviewScope.type, state.reviewScope.key);
}

async function updateVariant(variantId, patch, successMessage) {
  const response = await api(`/api/variants/${variantId}`, {
    method: "POST",
    body: JSON.stringify(patch),
  });
  await loadProject(response.variant.projectId, {
    preferredVariantId: variantId,
    preserveExistingReview: true,
  });
  await loadBootstrap(false);
  setNotice(successMessage);
}

async function toggleSlotLock(slotId) {
  const slot = state.currentProject?.gridPlan?.slots?.find((item) => item.id === slotId);
  if (!slot) {
    return;
  }
  const selectedVariant = getSelectedSlotVariant(slotId);
  if (selectedVariant) {
    await updateVariant(selectedVariant.id, { locked: !slot.locked }, "슬롯 잠금 상태를 변경했습니다.");
    return;
  }
  slot.locked = !slot.locked;
  await saveGridPlan({ silent: true });
  setNotice("선택 버전이 없는 슬롯의 잠금 상태를 저장했습니다.");
}

function capturePin(event) {
  const image = els.reviewPreviewShell.querySelector("img");
  if (!image) {
    return;
  }
  const rect = image.getBoundingClientRect();
  if (!rect.width || !rect.height) {
    return;
  }
  const x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100));
  const y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100));
  state.lastPin = { x: Math.round(x), y: Math.round(y) };
  els.pinReadout.textContent = `핀 좌표: ${state.lastPin.x}%, ${state.lastPin.y}%`;
}

async function handleAddComment() {
  if (!state.currentProject) {
    throw new Error("먼저 프로젝트를 저장해주세요.");
  }
  const body = els.commentBody.value.trim();
  if (!body) {
    throw new Error("코멘트 내용을 입력해주세요.");
  }

  const scope = state.reviewScope.key
    ? state.reviewScope
    : { type: "project", key: state.currentProject.id };
  await api(`/api/projects/${state.currentProject.id}/comments`, {
    method: "POST",
    body: JSON.stringify({
      author: els.commentAuthor.value.trim() || "내부 리뷰어",
      status: els.commentStatus.value,
      body,
      scopeType: scope.type,
      scopeKey: scope.key,
      pinX: state.lastPin.x,
      pinY: state.lastPin.y,
    }),
  });
  els.commentBody.value = "";
  await loadProject(state.currentProject.id, {
    preferredVariantId: state.selectedVariantId,
    preserveExistingReview: true,
  });
  setNotice("코멘트를 저장했습니다.");
}

async function handleExport() {
  if (!state.currentProject) {
    throw new Error("내보낼 프로젝트가 없습니다.");
  }
  setNotice("ZIP 패키지를 생성하는 중입니다...", "info");
  const response = await api(`/api/projects/${state.currentProject.id}/export`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  els.exportLink.href = response.export.zipUrl;
  els.exportLink.textContent = `ZIP 열기 (${response.export.selectedCount} assets)`;
  els.exportLink.classList.remove("is-hidden");
  setNotice("내보내기 패키지를 생성했습니다.");
}

async function handleObsidianExport() {
  if (!state.currentProject) {
    throw new Error("옵시디언으로 보낼 프로젝트가 없습니다.");
  }
  setNotice("Obsidian MVP 아이디어 노트를 생성하는 중입니다...", "info");
  const response = await api(`/api/projects/${state.currentProject.id}/export/obsidian`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  els.obsidianLink.href = response.obsidian.openUrl;
  els.obsidianLink.textContent = `옵시디언에서 열기 (${response.obsidian.notePath})`;
  els.obsidianLink.classList.remove("is-hidden");
  setNotice("Obsidian MVP 아이디어 노트를 생성했습니다.");
}

async function saveSettings() {
  const payload = {
    projectBudgetDefault: Number(els.settingBudgetDefault.value || 30),
    dailyGenerationLimit: Number(els.settingDailyLimit.value || 60),
    allowFinalOnlyForSelected: els.settingAllowFinal.checked,
    obsidian: {
      vaultPath: els.settingObsidianVault.value.trim(),
      ideaFolder: els.settingObsidianFolder.value.trim() || "MVP Ideas",
    },
    routes: {
      draft: collectRouteForm("draft"),
      final: collectRouteForm("final"),
      photo: collectRouteForm("photo"),
    },
  };
  const response = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  fillSettingsForm(response.settings);
  if (state.bootstrap) {
    state.bootstrap.settings = response.settings;
  }
  setNotice("관리자 설정을 저장했습니다.");
}

function collectRouteForm(route) {
  return {
    provider: document.querySelector(`#setting-${route}-provider`).value,
    model: document.querySelector(`#setting-${route}-model`).value.trim(),
    unitCost: Number(document.querySelector(`#setting-${route}-cost`).value || 0),
  };
}

async function prepareReferenceAsset(file) {
  const loaded = await loadImageFromFile(file);
  const maxSize = 1600;
  const scale = Math.min(1, maxSize / Math.max(loaded.width, loaded.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(loaded.width * scale));
  canvas.height = Math.max(1, Math.round(loaded.height * scale));
  const context = canvas.getContext("2d");
  context.drawImage(loaded, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL(
    file.type === "image/png" ? "image/png" : "image/jpeg",
    file.type === "image/png" ? undefined : 0.88
  );
  const palette = extractPalette(canvas);
  return {
    assetId: randomId("ref"),
    name: file.name,
    kind: guessReferenceKind(file.name),
    dataUrl,
    palette,
    notes: "",
  };
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function extractPalette(canvas) {
  const ctx = canvas.getContext("2d");
  const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const counter = new Map();
  for (let index = 0; index < data.length; index += 32) {
    const alpha = data[index + 3];
    if (alpha < 90) {
      continue;
    }
    const red = Math.round(data[index] / 32) * 32;
    const green = Math.round(data[index + 1] / 32) * 32;
    const blue = Math.round(data[index + 2] / 32) * 32;
    const key = [red, green, blue]
      .map((value) => Math.max(0, Math.min(255, value)).toString(16).padStart(2, "0"))
      .join("");
    counter.set(key, (counter.get(key) || 0) + 1);
  }
  return [...counter.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([key]) => `#${key}`);
}

function guessReferenceKind(name) {
  const value = String(name || "").toLowerCase();
  if (/(logo|로고)/.test(value)) {
    return "logo";
  }
  if (/(product|상품|제품)/.test(value)) {
    return "product";
  }
  if (/(model|person|인물|사람)/.test(value)) {
    return "person";
  }
  if (/(space|interior|공간)/.test(value)) {
    return "space";
  }
  if (/(feed|grid|instagram|피드)/.test(value)) {
    return "feed";
  }
  return "reference";
}
