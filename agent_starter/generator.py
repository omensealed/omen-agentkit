"""Compatibility facade for safe project generation and validation.

Generation treats an existing repository as valuable user data. Implementations
live in ``agent_starter.generation``; established imports remain available here.
"""

from .generation.registry import (
    EXECUTABLE_FILES,
    REQUIRED_FILES,
    _codex_scripts,
    _manifest,
    _new_note_script,
    _redacted_config_dict,
    _sha256,
    build_file_map,
)
from .generation.service import (
    GenerationReport,
    _assert_no_symlink_parent,
    _assert_safe_root,
    _atomic_write,
    _reuse_existing_generation_timestamps,
    _safe_relative,
    _timestamp,
    generate_project,
)
from .generation.validation import ValidationReport, _shell_files, validate_project

__all__ = [
    "EXECUTABLE_FILES",
    "GenerationReport",
    "REQUIRED_FILES",
    "ValidationReport",
    "build_file_map",
    "generate_project",
    "validate_project",
]
