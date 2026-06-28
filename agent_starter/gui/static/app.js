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
  "review",
  "generate",
  "result",
];

let index = 0;
let lastProjectPath = "";

function api() {
  return window.pywebview && window.pywebview.api;
}

function setOutput(id, value) {
  const target = document.getElementById(id);
  target.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function showPage(nextIndex) {
  index = Math.max(0, Math.min(pageIds.length - 1, nextIndex));
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.toggle("active", page.dataset.page === pageIds[index]);
  });
  document.querySelectorAll("#steps li").forEach((item, itemIndex) => {
    item.classList.toggle("active", itemIndex === index);
  });
  document.getElementById("back").disabled = index === 0;
  document.getElementById("next").disabled = index === pageIds.length - 1;
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

async function safeCall(outputId, fn) {
  if (!api()) {
    setOutput(outputId, "GUI bridge is not ready yet.");
    return null;
  }
  try {
    const result = await fn();
    setOutput(outputId, result);
    return result;
  } catch (error) {
    setOutput(outputId, String(error));
    return null;
  }
}

function installSteps() {
  const list = document.getElementById("steps");
  pageIds.forEach((id) => {
    const item = document.createElement("li");
    item.textContent = id.replaceAll("-", " ");
    list.appendChild(item);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  installSteps();
  showPage(0);

  document.getElementById("back").addEventListener("click", () => showPage(index - 1));
  document.getElementById("next").addEventListener("click", () => showPage(index + 1));

  document.getElementById("codex-status").addEventListener("click", () => {
    safeCall("codex-output", () => api().codex_status());
  });

  document.getElementById("preview").addEventListener("click", () => {
    safeCall("preview-output", () => api().preview_config(formPayload()));
  });

  document.getElementById("generate").addEventListener("click", async () => {
    const result = await safeCall("generate-output", () => api().generate(formPayload()));
    if (result && result.root) {
      lastProjectPath = result.root;
      showPage(pageIds.indexOf("result"));
      setOutput("result-output", result);
    }
  });

  document.getElementById("open-folder").addEventListener("click", () => {
    safeCall("result-output", () => api().open_project_folder(lastProjectPath));
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

  document.getElementById("launch-codex").addEventListener("click", () => {
    setOutput("result-output", "Closing Agent Kit and launching Codex...");
    api().launch_codex(lastProjectPath);
  });
});
