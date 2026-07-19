"""Assessment-only local-model handoff command and presentation."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..model_policy import DEFAULT_CODEX_MODEL_POLICY
from ..models import ProjectConfig
from ..task_composer import TASK_SECRET_RE
from .project_runtime import load_generated_config
from .prompt_commands import render_continuation_prompt


@dataclass(slots=True)
class OllamaModelAssessment:
    name: str
    context_length: int | None
    coding_score: int
    assessment: str
    reasons: list[str]

    @property
    def suitable(self) -> bool:
        return self.assessment == "suitable"


def _parse_ollama_list(output: str) -> list[str]:
    models: list[str] = []
    for index, line in enumerate(output.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if index == 0 and stripped.lower().startswith("name "):
            continue
        parts = stripped.split()
        if parts:
            models.append(parts[0])
    return models


def _find_context_length(value: object) -> int | None:
    found: list[int] = []

    def walk(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                key_text = str(key).lower()
                if any(marker in key_text for marker in ("context_length", "num_ctx", "n_ctx")):
                    if isinstance(nested, int):
                        found.append(nested)
                    elif isinstance(nested, str) and nested.isdigit():
                        found.append(int(nested))
                walk(nested)
        elif isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return max(found) if found else None


def _coding_score(model_name: str) -> int:
    name = model_name.lower()
    score = 0
    strong_markers = ("coder", "code", "deepseek-coder", "qwen2.5-coder", "qwen3-coder", "devstral")
    capable_markers = ("gpt-oss", "llama3.3", "llama3.1", "mixtral", "mistral-large")
    weak_markers = ("tiny", "mini", "1b", "3b", "7b")
    if any(marker in name for marker in strong_markers):
        score += 3
    if any(marker in name for marker in capable_markers):
        score += 2
    if "70b" in name or "72b" in name or "120b" in name:
        score += 2
    elif "32b" in name or "34b" in name:
        score += 1
    if any(marker in name for marker in weak_markers):
        score -= 2
    return score


def _show_ollama_model(model: str) -> dict[str, object]:
    try:
        result = subprocess.run(
            ["ollama", "show", model, "--json"],
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def assess_ollama_model(model: str) -> OllamaModelAssessment:
    details = _show_ollama_model(model)
    context_length = _find_context_length(details)
    coding_score = _coding_score(model)
    reasons: list[str] = []

    if context_length is None:
        reasons.append("Context length could not be confirmed from `ollama show --json`.")
    elif context_length >= 131_072:
        reasons.append(f"Confirmed context length is {context_length:,} tokens, suitable for larger project handoff.")
    elif context_length >= 32_768:
        reasons.append(f"Confirmed context length is {context_length:,} tokens, enough only for focused project slices.")
    else:
        reasons.append(f"Confirmed context length is {context_length:,} tokens, too small for safe project-wide handoff.")

    if coding_score >= 3:
        reasons.append("Model name indicates a code-focused or large general model.")
    elif coding_score >= 1:
        reasons.append("Model name indicates some coding/general capability, but not a strong code-handoff signal.")
    else:
        reasons.append("Model name does not indicate strong coding capability.")

    if context_length is not None and context_length >= 131_072 and coding_score >= 3:
        assessment = "suitable"
    elif context_length is not None and context_length >= 32_768 and coding_score >= 3:
        assessment = "borderline"
        reasons.append("Use only for narrow tasks with explicit file lists and compact handoff context.")
    else:
        assessment = "inadvisable"
        reasons.append("Do not switch this project to the local model unless a human explicitly overrides the warning.")
    return OllamaModelAssessment(
        name=model,
        context_length=context_length,
        coding_score=coding_score,
        assessment=assessment,
        reasons=reasons,
    )


def _best_ollama_assessment(models: list[str]) -> OllamaModelAssessment:
    assessments = [assess_ollama_model(model) for model in models]
    if not assessments:
        raise ValueError("No Ollama models were found. Run `ollama list` locally after installing a model.")

    def rank(item: OllamaModelAssessment) -> tuple[int, int, int]:
        status = {"suitable": 2, "borderline": 1, "inadvisable": 0}[item.assessment]
        return status, item.context_length or 0, item.coding_score

    return max(assessments, key=rank)


def render_local_model_handoff_prompt(
    config: ProjectConfig,
    *,
    request: str,
    assessment: OllamaModelAssessment,
    override: bool,
) -> str:
    continuation = render_continuation_prompt(
        config,
        request=request or "Continue the next documented project phase using the local model cautiously.",
        phase="local-model handoff",
    )
    warning = (
        "Manual override accepted: this model did not meet the starter kit's normal handoff threshold.\n"
        if override and not assessment.suitable
        else "Local model passed the starter kit's normal handoff threshold.\n"
    )
    reasons = "\n".join(f"- {reason}" for reason in assessment.reasons)
    context = f"{assessment.context_length:,}" if assessment.context_length is not None else "unknown"
    return (
        "## Local Model Handoff Prompt\n\n"
        f"Target local model: `{assessment.name}`\n"
        f"Codex quality baseline: `{DEFAULT_CODEX_MODEL_POLICY.model_id}` "
        f"({DEFAULT_CODEX_MODEL_POLICY.display_label}) with "
        f"{DEFAULT_CODEX_MODEL_POLICY.reasoning_effort} reasoning.\n"
        f"Assessment: {assessment.assessment}\n"
        f"Confirmed context length: {context}\n"
        f"{warning}\n"
        "Assessment reasons:\n"
        f"{reasons}\n\n"
        "Use this local model only for a focused, reviewable continuation. If the model loses project context, stop, "
        "return to Codex, or generate a narrower prompt with explicit files and requirements.\n\n"
        + continuation
    )


def command_ollama_check(args: argparse.Namespace) -> int:
    config = load_generated_config(Path(args.project))
    request = args.request or "Continue the next documented project phase."
    if TASK_SECRET_RE.search(request):
        raise ValueError("The prompt request appears to contain a credential or private key. Remove it and rotate it if it was real.")
    if shutil.which("ollama") is None:
        print("Ollama is not installed or is not on PATH. No local-model handoff was generated.")
        return 3
    if args.model:
        assessment = assess_ollama_model(args.model)
    else:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"Could not inspect Ollama models: {exc}")
            return 3
        if result.returncode != 0:
            print(f"Could not inspect Ollama models: {(result.stderr or result.stdout).strip()}")
            return 3
        assessment = _best_ollama_assessment(_parse_ollama_list(result.stdout))

    print(f"Model: {assessment.name}")
    print(
        f"Codex quality baseline: {DEFAULT_CODEX_MODEL_POLICY.model_id} "
        f"({DEFAULT_CODEX_MODEL_POLICY.display_label}), "
        f"{DEFAULT_CODEX_MODEL_POLICY.reasoning_effort} reasoning"
    )
    print(f"Assessment: {assessment.assessment}")
    for reason in assessment.reasons:
        print(f"- {reason}")
    if not assessment.suitable and not args.override:
        print("")
        print("Refusing to generate a local-model handoff prompt. Re-run with --override only after accepting the risk.")
        return 2

    prompt = render_local_model_handoff_prompt(
        config,
        request=request,
        assessment=assessment,
        override=args.override,
    )
    if args.output:
        path = Path(args.output)
        if path.exists() and not args.force:
            print(f"Refusing to replace {path}; add --force.")
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt, encoding="utf-8")
        print(f"Wrote {path}")
    else:
        print("")
        sys.stdout.write(prompt)
    return 0


def register_local_model_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    ollama = subparsers.add_parser(
        "ollama-check",
        help="Assess installed Ollama models before generating a local-model handoff prompt.",
    )
    ollama.add_argument("project", nargs="?", default=".")
    ollama.add_argument("--model", help="Specific Ollama model to assess; defaults to the best installed candidate.")
    ollama.add_argument("--request", "-r", default="", help="Feature, fix, or next-step request for the handoff prompt.")
    ollama.add_argument("--output", "-o", help="Write the handoff prompt to a file instead of stdout.")
    ollama.add_argument("--force", action="store_true", help="Replace an existing --output file.")
    ollama.add_argument(
        "--override",
        action="store_true",
        help="Generate the handoff prompt even when the local model is inadvisable or borderline.",
    )
    ollama.set_defaults(func=command_ollama_check)
