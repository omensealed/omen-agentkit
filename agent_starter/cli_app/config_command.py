"""Parser registration and handler for non-destructive config migration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ..config_schema import migrate_config, parse_config


def command_config_migrate(args: argparse.Namespace) -> int:
    source = Path(args.input).expanduser()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read configuration {source}: {exc}") from exc
    migration = migrate_config(raw)
    parsed = parse_config(migration.data)
    rendered = json.dumps(parsed.config.to_dict(), indent=2, sort_keys=True) + "\n"
    if not args.output:
        print(rendered, end="")
        print(
            f"Migration preview only: schema v{migration.source_version} -> v{migration.target_version}; source was not changed.",
            file=sys.stderr,
        )
        return 0
    output = Path(args.output).expanduser()
    if output.resolve() == source.resolve():
        raise ValueError("Refusing to overwrite the source configuration; choose a separate --output path.")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"Refusing to replace existing migration output: {output}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    print(f"Wrote schema-v{migration.target_version} migration to {output}; source was not changed.")
    return 0


def register_config_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    config = subparsers.add_parser("config", help="Validate or migrate AgentKit answers/configuration.")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    migrate = config_sub.add_parser("migrate", help="Preview or separately write an ordered schema migration.")
    migrate.add_argument("--input", required=True, help="Source v1/v2 answers JSON; never modified.")
    migrate.add_argument("--output", help="Separate new file to create; omit for a stdout dry run.")
    migrate.set_defaults(func=command_config_migrate)
