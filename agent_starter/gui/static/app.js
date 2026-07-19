const pageIds = [
  "welcome",
  "project",
  "identity",
  "targets",
  "security",
  "codex",
  "sandbox",
  "stack",
  "quality",
  "task",
  "review",
  "generate",
  "result",
];

let index = 0;
let lastProjectPath = "";
let guidedDecisionIndex = 0;
let taskDefinitions = [];
let taskComposerInitialized = false;
let currentDraftId = "";
let pendingLaunchPreviewId = "";

function isGuided() {
  const selector = document.getElementById("entry-mode");
  return selector && selector.value === "guided";
}

function guidedDecisions(page) {
  return Array.from(page.querySelectorAll("label")).filter(
    (element) => !element.hasAttribute("data-advanced-only"),
  );
}

function renderGuidedDecision() {
  const page = document.querySelector(`.page[data-page="${pageIds[index]}"]`);
  const decisions = guidedDecisions(page);
  page.querySelectorAll("label:not([data-advanced-only])").forEach((element) => {
    element.hidden = isGuided() && element !== decisions[guidedDecisionIndex];
  });
  document.getElementById("next").textContent = isGuided() && decisions.length > 1
    ? "Next decision"
    : "Next";
}

function focusFirstControl(container) {
  const control = container && container.querySelector("input, select, textarea, button");
  if (control && !control.hidden && !control.disabled) control.focus();
}

function advanceGuidedDecision(direction) {
  const page = document.querySelector(`.page[data-page="${pageIds[index]}"]`);
  const decisions = guidedDecisions(page);
  if (isGuided() && direction > 0 && guidedDecisionIndex < decisions.length - 1) {
    guidedDecisionIndex += 1;
    renderGuidedDecision();
    focusFirstControl(decisions[guidedDecisionIndex]);
    return;
  }
  if (isGuided() && direction < 0 && guidedDecisionIndex > 0) {
    guidedDecisionIndex -= 1;
    renderGuidedDecision();
    focusFirstControl(decisions[guidedDecisionIndex]);
    return;
  }
  showPage(index + direction, direction < 0 ? "last" : "first");
}

function setEntryMode(mode) {
  const advanced = mode === "advanced";
  document.querySelectorAll("[data-advanced-only]").forEach((element) => {
    element.hidden = !advanced;
  });
  const explanation = document.getElementById("entry-mode-explanation");
  explanation.textContent = advanced
    ? "Advanced mode exposes every setting but uses the same validation, approvals, and safe generation boundaries."
    : "Guided mode explains consequences one decision at a time and uses conservative defaults for hidden implementation settings. You can switch to Advanced at any time.";
  guidedDecisionIndex = 0;
  renderGuidedDecision();
}

function api() {
  return window.pywebview && window.pywebview.api;
}

function confirmationText(value) {
  return String(value || "")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .trim()
    .slice(0, 300);
}

function resetLaunchReview() {
  pendingLaunchPreviewId = "";
  document.getElementById("launch-codex").textContent = "Review launch settings";
}

function formatLaunchPreview(preview) {
  const model = preview.model_policy;
  const exactModel = model.exact_model_id || "Inherited from global Codex configuration";
  const reasoning = model.reasoning_effort || "Inherited from global Codex configuration";
  return [
    "Launch review — no process has started",
    `Target project: ${preview.target_project}`,
    `Model provider: ${model.provider}`,
    `Model selection: ${model.selection}`,
    `Model display label: ${model.display_label}`,
    `Exact model ID: ${exactModel}`,
    `Reasoning effort: ${reasoning}`,
    `Task routing allowed: ${model.allow_task_routing ? "yes" : "no"}`,
    `Unavailable-model behavior: ${model.fallback_behavior}`,
    `Project sandbox: ${preview.sandbox.project_mode}`,
    `Codex sandbox mode: ${preview.sandbox.codex_mode}`,
    `Approval policy: ${preview.sandbox.approval_policy}`,
    `Execution location: ${preview.sandbox.execution_location}`,
    `Project requires network: ${preview.network.project_requires_network ? "yes" : "no"}`,
    `Command network access: ${preview.network.command_network_access}`,
    `Web search: ${preview.network.web_search}`,
    "Review every value above. Select Confirm and launch Codex only when it matches your intent.",
  ].join("\n");
}

function setOutput(id, value) {
  const target = document.getElementById(id);
  const previousDiagnostic = document.getElementById(`${id}-diagnostic`);
  const previousRemediation = document.getElementById(`${id}-remediation`);
  if (previousDiagnostic) previousDiagnostic.remove();
  if (previousRemediation) previousRemediation.remove();
  target.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function renderDiagnostic(id, diagnostic) {
  setOutput(id, "");
  const target = document.getElementById(id);
  const panel = document.createElement("section");
  panel.id = `${id}-diagnostic`;
  panel.className = "diagnostic";
  panel.setAttribute("role", diagnostic.severity === "error" ? "alert" : "status");
  panel.tabIndex = -1;

  const title = document.createElement("h3");
  title.textContent = diagnostic.title;
  panel.appendChild(title);

  const severity = document.createElement("p");
  severity.textContent = `Severity: ${diagnostic.severity}`;
  panel.appendChild(severity);

  const explanation = document.createElement("p");
  explanation.textContent = diagnostic.explanation;
  panel.appendChild(explanation);

  const changed = document.createElement("p");
  changed.textContent = `Project files changed: ${diagnostic.project_changed ? "yes" : "no"}`;
  panel.appendChild(changed);

  const nextAction = document.createElement("p");
  nextAction.textContent = `Safe next action: ${diagnostic.safe_next_action}`;
  panel.appendChild(nextAction);

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Technical details";
  details.appendChild(summary);
  const technical = document.createElement("pre");
  technical.textContent = diagnostic.technical_details;
  details.appendChild(technical);
  panel.appendChild(details);
  target.insertAdjacentElement("afterend", panel);
  panel.focus();
}

function renderRemediationCommand(id, command) {
  if (typeof command !== "string" || !command.trim()) return;
  const target = document.getElementById(id);
  const previous = document.getElementById(`${id}-remediation`);
  if (previous) previous.remove();
  const panel = document.createElement("section");
  panel.id = `${id}-remediation`;
  panel.className = "remediation";
  panel.setAttribute("aria-label", "Reviewed remediation command");

  const heading = document.createElement("h3");
  heading.textContent = "Reviewed remediation command";
  panel.appendChild(heading);
  const explanation = document.createElement("p");
  explanation.textContent = "This command is displayed for review only. Copying it does not execute it.";
  panel.appendChild(explanation);
  const commandBlock = document.createElement("pre");
  const commandText = document.createElement("code");
  commandText.textContent = command;
  commandBlock.appendChild(commandText);
  panel.appendChild(commandBlock);
  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.textContent = "Copy remediation command";
  panel.appendChild(copyButton);
  const copyStatus = document.createElement("p");
  copyStatus.setAttribute("role", "status");
  copyStatus.setAttribute("aria-live", "polite");
  panel.appendChild(copyStatus);
  copyButton.addEventListener("click", async () => {
    if (!navigator.clipboard) {
      copyStatus.textContent = "Clipboard access is unavailable. Select and copy the command shown above.";
      commandBlock.focus();
      return;
    }
    try {
      await navigator.clipboard.writeText(command);
      copyStatus.textContent = "Remediation command copied. It has not been executed.";
    } catch (_error) {
      copyStatus.textContent = "The command was not copied. Select and copy the command shown above.";
      commandBlock.focus();
    }
  });
  commandBlock.tabIndex = 0;
  const anchor = document.getElementById(`${id}-diagnostic`) || target;
  anchor.insertAdjacentElement("afterend", panel);
}

function focusActivePage() {
  const heading = document.querySelector(`.page[data-page="${pageIds[index]}"] h2`);
  if (heading) heading.focus();
}

function showPage(nextIndex, guidedPosition = "first", shouldFocus = true) {
  index = Math.max(0, Math.min(pageIds.length - 1, nextIndex));
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.toggle("active", page.dataset.page === pageIds[index]);
  });
  document.querySelectorAll("#steps li").forEach((item, itemIndex) => {
    const current = itemIndex === index;
    item.classList.toggle("active", current);
    const button = item.querySelector("button");
    const state = item.querySelector(".step-state");
    if (current) {
      button.setAttribute("aria-current", "step");
      state.textContent = "Current step";
    } else {
      button.removeAttribute("aria-current");
      state.textContent = "";
    }
  });
  document.getElementById("back").disabled = index === 0;
  document.getElementById("next").disabled = index === pageIds.length - 1;
  const active = document.querySelector(`.page[data-page="${pageIds[index]}"]`);
  const decisions = guidedDecisions(active);
  guidedDecisionIndex = guidedPosition === "last" ? Math.max(0, decisions.length - 1) : 0;
  renderGuidedDecision();
  if (shouldFocus) focusActivePage();
}

function formPayload() {
  const form = document.getElementById("wizard");
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    payload[key] = value;
  }
  for (const checkbox of form.querySelectorAll('input[type="checkbox"]')) {
    payload[checkbox.name] = checkbox.checked;
  }
  return payload;
}

function renderTaskQuestions() {
  const kind = document.getElementById("task-kind").value;
  const definition = taskDefinitions.find((item) => item.kind === kind);
  const container = document.getElementById("task-composer");
  container.replaceChildren();
  if (!definition) return;
  definition.questions.forEach((question) => {
    const label = document.createElement("label");
    label.textContent = question.prompt;
    let control;
    if (question.choices.length) {
      control = document.createElement("select");
      question.choices.forEach((choice) => {
        const option = document.createElement("option");
        option.value = choice.value;
        option.textContent = choice.label;
        option.selected = choice.value === question.default;
        control.appendChild(option);
      });
    } else {
      control = document.createElement("textarea");
      control.rows = 3;
      control.value = question.default;
    }
    control.required = question.required;
    control.dataset.taskKey = question.key;
    control.dataset.taskPrompt = question.prompt;
    control.id = `task-${kind}-${question.key}`;
    const answerChanged = () => {
      control.removeAttribute("aria-invalid");
      updateComposeAvailability();
    };
    control.addEventListener("input", answerChanged);
    control.addEventListener("change", answerChanged);
    label.htmlFor = control.id;
    label.appendChild(control);
    container.appendChild(label);
  });
  document.getElementById("edit-task").hidden = true;
  document.getElementById("approve-task").hidden = true;
  setOutput("task-output", "");
  guidedDecisionIndex = 0;
  renderGuidedDecision();
  updateComposeAvailability();
}

async function initializeTaskComposer() {
  if (taskComposerInitialized || !api()) return;
  const definitions = await api().task_composer_schema();
  if (!Array.isArray(definitions) || !definitions.length) {
    throw new Error("The task composer returned no starting choices.");
  }
  taskDefinitions = definitions;
  const selector = document.getElementById("task-kind");
  selector.replaceChildren();
  taskDefinitions.forEach((definition) => {
    const option = document.createElement("option");
    option.value = definition.kind;
    option.textContent = definition.label;
    selector.appendChild(option);
  });
  selector.addEventListener("change", renderTaskQuestions);
  taskComposerInitialized = true;
  renderTaskQuestions();
  selector.disabled = false;
  updateComposeAvailability();
}

function taskPayload() {
  const answers = {};
  document.querySelectorAll("#task-composer [data-task-key]").forEach((control) => {
    answers[control.dataset.taskKey] = control.value;
  });
  return {kind: document.getElementById("task-kind").value, answers};
}

function updateComposeAvailability() {
  const selector = document.getElementById("task-kind");
  const controls = Array.from(document.querySelectorAll("#task-composer [data-task-key]"));
  const complete = taskComposerInitialized
    && selector
    && !selector.disabled
    && Boolean(selector.value)
    && controls.every((control) => !control.required || control.value.trim());
  document.getElementById("compose-task").disabled = !complete;
}

function revealTaskControl(control) {
  const page = document.querySelector('.page[data-page="task"]');
  const label = control.closest("label");
  const decisions = guidedDecisions(page);
  const decisionIndex = decisions.indexOf(label);
  if (isGuided() && decisionIndex >= 0) {
    guidedDecisionIndex = decisionIndex;
    renderGuidedDecision();
  }
  control.focus();
}

function validatedTaskPayload() {
  const selector = document.getElementById("task-kind");
  if (!taskComposerInitialized || selector.disabled || !selector.value) {
    setOutput("task-output", "Task choices are still loading. Wait a moment, then try again.");
    return null;
  }
  const controls = Array.from(document.querySelectorAll("#task-composer [data-task-key]"));
  const missing = controls.find((control) => control.required && !control.value.trim());
  if (missing) {
    missing.setAttribute("aria-invalid", "true");
    setOutput("task-output", `Answer required: ${missing.dataset.taskPrompt}`);
    revealTaskControl(missing);
    return null;
  }
  return taskPayload();
}

function selectedDraftId() {
  return document.getElementById("draft-list").value;
}

function draftPayload() {
  const payload = {project: formPayload(), task: taskPayload()};
  if (currentDraftId) payload.draft_id = currentDraftId;
  return payload;
}

function applyDraftProject(project) {
  const form = document.getElementById("wizard");
  Object.entries(project).forEach(([key, value]) => {
    const control = form.elements.namedItem(key);
    if (!control) return;
    if (control.type === "checkbox") {
      control.checked = value === true;
    } else {
      control.value = String(value);
    }
  });
  const entryMode = document.getElementById("entry-mode");
  setEntryMode(entryMode.value);
}

function applyDraftTask(task) {
  if (!task) return;
  const selector = document.getElementById("task-kind");
  selector.value = task.kind;
  renderTaskQuestions();
  Object.entries(task.answers).forEach(([key, value]) => {
    const control = document.querySelector(`#task-composer [data-task-key="${key}"]`);
    if (control) control.value = value;
  });
  updateComposeAvailability();
}

async function refreshDrafts(preferredId = "") {
  const result = await safeCall("draft-status", () => api().list_drafts());
  if (!result || !result.ok) return;
  const selector = document.getElementById("draft-list");
  selector.replaceChildren();
  result.drafts.forEach((draft) => {
    const option = document.createElement("option");
    option.value = draft.draft_id;
    option.textContent = `${draft.selected_project} — updated ${draft.updated_at}`;
    selector.appendChild(option);
  });
  if (preferredId && result.drafts.some((draft) => draft.draft_id === preferredId)) {
    selector.value = preferredId;
  }
  setOutput("draft-status", result.drafts.length
    ? `${result.drafts.length} saved draft session(s). Select one to resume, export, or discard.`
    : "No saved draft sessions.");
}

async function safeCall(outputId, fn) {
  if (!api()) {
    setOutput(outputId, "GUI bridge is not ready yet.");
    return null;
  }
  try {
    const result = await fn();
    if (result && result.diagnostic) {
      renderDiagnostic(outputId, result.diagnostic);
    } else {
      setOutput(outputId, result);
    }
    if (result && result.install_command) {
      renderRemediationCommand(outputId, result.install_command);
    }
    return result;
  } catch (error) {
    setOutput(outputId, String(error));
    return null;
  }
}

async function initializeBridgeFeatures() {
  if (!api()) return;
  try {
    await initializeTaskComposer();
    await refreshDrafts();
  } catch (_error) {
    taskComposerInitialized = false;
    setOutput("task-output", "Task choices could not be loaded. Close and reopen Agent Kit, then try again.");
  }
}

window.addEventListener("pywebviewready", initializeBridgeFeatures);

function installSteps() {
  const list = document.getElementById("steps");
  pageIds.forEach((id, itemIndex) => {
    const item = document.createElement("li");
    const stepButton = document.createElement("button");
    stepButton.type = "button";
    stepButton.className = "step-button";
    const label = document.createElement("span");
    label.textContent = id.replaceAll("-", " ");
    stepButton.appendChild(label);
    const state = document.createElement("span");
    state.className = "step-state";
    stepButton.appendChild(state);
    stepButton.addEventListener("click", () => showPage(itemIndex));
    item.appendChild(stepButton);
    list.appendChild(item);
  });
}

function installPageAccessibility() {
  document.querySelectorAll(".page").forEach((page) => {
    const heading = page.querySelector("h2");
    if (!heading) return;
    heading.id = `page-heading-${page.dataset.page}`;
    heading.tabIndex = -1;
    page.setAttribute("aria-labelledby", heading.id);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  installPageAccessibility();
  installSteps();
  showPage(0, "first", false);
  const entryMode = document.getElementById("entry-mode");
  setEntryMode(entryMode.value);
  entryMode.addEventListener("change", () => setEntryMode(entryMode.value));
  initializeBridgeFeatures();

  document.getElementById("back").addEventListener("click", () => advanceGuidedDecision(-1));
  document.getElementById("next").addEventListener("click", () => advanceGuidedDecision(1));

  document.getElementById("codex-status").addEventListener("click", () => {
    safeCall("codex-output", () => api().codex_status());
  });

  document.getElementById("preview").addEventListener("click", () => {
    safeCall("preview-output", () => api().preview_config(formPayload()));
  });

  document.getElementById("compose-task").addEventListener("click", async () => {
    const payload = validatedTaskPayload();
    if (!payload) return;
    const result = await safeCall("task-output", () => api().compose_task(payload));
    if (result && result.ok) {
      setOutput("task-output", result.contract_text);
      document.getElementById("edit-task").hidden = false;
      document.getElementById("approve-task").hidden = false;
    }
  });

  document.getElementById("edit-task").addEventListener("click", () => {
    document.getElementById("approve-task").hidden = true;
    document.getElementById("edit-task").hidden = true;
    setOutput("task-output", "Edit the answers, then compose a new contract. Nothing is approved or launched.");
    const first = document.querySelector("#task-composer [data-task-key]");
    if (first) first.focus();
  });

  document.getElementById("approve-task").addEventListener("click", async () => {
    const payload = validatedTaskPayload();
    if (!payload) return;
    if (!window.confirm(
      "Approve this prompt? This releases prompt text in the GUI only. It does not launch Codex, run commands, or change project files.",
    )) return;
    const result = await safeCall("task-output", () => api().approve_task(payload));
    if (result && result.ok) {
      setOutput("task-output", `Prompt approved. Codex has not been launched.\n\n${result.request}`);
      document.getElementById("approve-task").hidden = true;
    }
  });

  document.getElementById("save-draft").addEventListener("click", async () => {
    const result = await safeCall("draft-status", () => api().save_draft(draftPayload()));
    if (result && result.ok) {
      currentDraftId = result.draft.draft_id;
      setOutput(
        "draft-status",
        `Draft saved. Selected project: ${result.draft.selected_project}. Last updated: ${result.draft.updated_at}.`,
      );
      await refreshDrafts(currentDraftId);
    }
  });

  document.getElementById("refresh-drafts").addEventListener("click", () => refreshDrafts(selectedDraftId()));

  document.getElementById("resume-draft").addEventListener("click", async () => {
    const draftId = selectedDraftId();
    if (!draftId) {
      setOutput("draft-status", "Select a saved draft to resume.");
      return;
    }
    const result = await safeCall("draft-status", () => api().load_draft(draftId));
    if (result && result.ok) {
      applyDraftProject(result.draft.project);
      applyDraftTask(result.draft.task);
      currentDraftId = result.draft.draft_id;
      setOutput(
        "draft-status",
        `Draft resumed. Selected project: ${result.draft.selected_project}. Last updated: ${result.draft.updated_at}.`,
      );
    }
  });

  document.getElementById("discard-draft").addEventListener("click", async () => {
    const draftId = selectedDraftId();
    if (!draftId) {
      setOutput("draft-status", "Select a saved draft to discard.");
      return;
    }
    if (!window.confirm(
      `Discard saved draft ${confirmationText(draftId)}? This permanently deletes only the selected local draft file. It does not change project files and cannot be undone.`,
    )) return;
    const result = await safeCall("draft-status", () => api().discard_draft(draftId));
    if (result && result.ok) {
      if (currentDraftId === draftId) currentDraftId = "";
      await refreshDrafts();
    }
  });

  document.getElementById("export-draft").addEventListener("click", async () => {
    const draftId = selectedDraftId();
    const destination = document.getElementById("draft-export-path").value.trim();
    if (!draftId || !destination) {
      setOutput("draft-status", "Select a saved draft and enter a new export file path.");
      return;
    }
    const result = await safeCall("draft-status", () => api().export_draft(draftId, destination));
    if (result && result.ok) {
      setOutput("draft-status", `Draft exported to ${result.path}. The saved draft remains available.`);
    }
  });

  document.getElementById("generate").addEventListener("click", async () => {
    const payload = formPayload();
    const selectedRoot = typeof payload.project_path === "string" && payload.project_path.trim()
      ? confirmationText(payload.project_path)
      : "the project folder entered above";
    if (!window.confirm(
      `Generate this workspace? This writes Agent Kit files under "${selectedRoot}". Existing conflicts become proposals, and local Git may be initialized when selected. It does not install packages or launch Codex.`,
    )) return;
    const result = await safeCall("generate-output", () => api().generate(payload));
    if (result && result.root) {
      resetLaunchReview();
      lastProjectPath = result.root;
      showPage(pageIds.indexOf("result"));
      setOutput("result-output", result);
    }
  });

  document.getElementById("open-folder").addEventListener("click", () => {
    safeCall("result-output", () => api().open_project_folder(lastProjectPath));
  });

  document.getElementById("start-here").addEventListener("click", () => {
    safeCall("result-output", () => api().read_text_file(lastProjectPath, "START_HERE.md"));
  });

  document.getElementById("next-steps").addEventListener("click", () => {
    safeCall("result-output", () => api().read_text_file(lastProjectPath, "NEXT_STEPS.md"));
  });

  document.getElementById("first-prompt").addEventListener("click", async () => {
    const result = await safeCall("result-output", () => api().read_text_file(lastProjectPath, "FIRST_PROMPT.md"));
    if (result && result.ok && navigator.clipboard) {
      await navigator.clipboard.writeText(result.text);
      setOutput("result-output", `Copied FIRST_PROMPT.md from ${result.path}`);
    }
  });

  document.getElementById("validate").addEventListener("click", () => {
    safeCall("result-output", () => api().validate(lastProjectPath));
  });

  document.getElementById("launch-codex").addEventListener("click", async () => {
    const launchButton = document.getElementById("launch-codex");
    if (!pendingLaunchPreviewId) {
      const result = await safeCall("result-output", () => api().launch_preview(lastProjectPath));
      if (result && result.ok) {
        pendingLaunchPreviewId = result.preview_id;
        setOutput("result-output", formatLaunchPreview(result.preview));
        launchButton.textContent = "Confirm and launch Codex";
        document.getElementById("result-output").focus();
      } else {
        resetLaunchReview();
      }
      return;
    }
    if (!window.confirm(
      `Launch Codex in "${confirmationText(lastProjectPath)}" using the exact reviewed settings above? This closes Agent Kit and starts Codex, which may modify project files subject to its displayed sandbox, approval, and network policy.`,
    )) return;
    const previewId = pendingLaunchPreviewId;
    resetLaunchReview();
    setOutput("result-output", "Revalidating the reviewed project before closing Agent Kit and launching Codex...");
    const result = await safeCall(
      "result-output",
      () => api().launch_codex(lastProjectPath, previewId),
    );
    if (result && !result.ok) resetLaunchReview();
  });
});
