from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_starter import templates
from agent_starter.models import ProjectConfig


def config(**overrides: object) -> ProjectConfig:
    values: dict[str, object] = {
        "project_name": "Bootstrap Test",
        "project_slug": "bootstrap-test",
        "project_path": "/tmp/bootstrap-test",
        "description": "Test provider bootstrap planning.",
        "languages": ["python"],
        "database": "sqlite",
        "github_actions": False,
        "git_enabled": False,
    }
    values.update(overrides)
    return ProjectConfig(**values)


class BootstrapTemplateTests(unittest.TestCase):
    def test_script_has_provider_arrays_and_no_embedded_system_upgrade(self) -> None:
        rendered = templates.bootstrap_script(config(extra_packages_by_provider={
            "arch": ["arch-extra"],
            "debian": ["debian-extra"],
            "ubuntu": ["ubuntu-extra"],
        }))
        self.assertIn("ARCH_PACKAGES=(", rendered)
        self.assertIn("DEBIAN_PACKAGES=(", rendered)
        self.assertIn("UBUNTU_PACKAGES=(", rendered)
        self.assertIn("arch-extra", rendered)
        self.assertIn("debian-extra", rendered)
        self.assertIn("ubuntu-extra", rendered)
        self.assertIn(
            "ARCH_PACKAGES=(git curl jq ripgrep fd unzip base-devel python python-pip sqlite arch-extra)",
            rendered,
        )
        self.assertIn(
            "DEBIAN_PACKAGES=(git curl jq ripgrep fd-find unzip build-essential python3 python3-venv python3-pip sqlite3 debian-extra)",
            rendered,
        )
        self.assertIn("--provider", rendered)
        self.assertIn("--refresh", rendered)
        self.assertIn("--install", rendered)
        self.assertNotIn("pacman -Syu", rendered)
        self.assertNotIn("apt-get upgrade", rendered)
        self.assertNotIn("dist-upgrade", rendered)
        self.assertNotIn("source /etc/os-release", rendered)
        self.assertNotIn("eval ", rendered)
        self.assertNotIn("add-apt-repository", rendered)
        self.assertNotIn("apt-key", rendered)
        self.assertNotIn("/etc/apt/sources", rendered)
        self.assertNotIn("ppa:", rendered.lower())
        self.assertNotIn("curl |", rendered)
        self.assertNotIn("curl -", rendered)

    def test_arch_plan_and_install_never_embed_a_system_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "bootstrap-dev.sh"
            script.write_text(templates.bootstrap_script(config()), encoding="utf-8")
            script.chmod(0o755)
            syntax = subprocess.run(["bash", "-n", script], check=False, capture_output=True, text=True)
            self.assertEqual(syntax.returncode, 0, syntax.stderr)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            log = root / "mutation.log"
            self._write_command(
                bin_dir / "pacman",
                'if [[ "${1:-}" == "-Qq" && "${2:-}" == "git" ]]; then exit 0; fi\nexit 1',
            )
            self._write_command(bin_dir / "sudo", 'printf "%s\\n" "$*" >> "$BOOTSTRAP_LOG"')
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BOOTSTRAP_LOG": str(log)}
            plan = subprocess.run(
                [script, "--provider", "arch"], text=True, capture_output=True, check=False, env=env
            )
            self.assertEqual(plan.returncode, 0, plan.stderr)
            self.assertIn("installed: git", plan.stdout)
            self.assertIn("sudo pacman -S --needed", plan.stdout)
            self.assertNotIn("apt-get", plan.stdout)
            self.assertNotIn("-Syu", plan.stdout)
            self.assertFalse(log.exists())

            refresh = subprocess.run(
                [script, "--provider", "arch", "--refresh"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(refresh.returncode, 2)
            self.assertIn("No Arch system upgrade was run", refresh.stderr)
            self.assertFalse(log.exists())

            install = subprocess.run(
                [script, "--provider", "arch", "--install"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            mutation = log.read_text(encoding="utf-8")
            self.assertIn("pacman -S --needed", mutation)
            self.assertNotIn("-Syu", mutation)
            self.assertNotIn(" git", mutation)

    def test_ubuntu_plan_skips_installed_packages_and_never_mutates_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "bootstrap-dev.sh"
            script.write_text(templates.bootstrap_script(config()), encoding="utf-8")
            script.chmod(0o755)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            log = root / "mutation.log"
            self._write_command(bin_dir / "apt-get", "exit 97")
            self._write_command(
                bin_dir / "dpkg-query",
                'package="${@: -1}"\nif [[ "$package" == "git" ]]; then printf "%s" "install ok installed"; exit 0; fi\nexit 1',
            )
            self._write_command(bin_dir / "sudo", 'printf "%s\\n" "$*" >> "$BOOTSTRAP_LOG"')
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BOOTSTRAP_LOG": str(log)}
            result = subprocess.run(
                [script, "--provider", "ubuntu"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Provider: ubuntu", result.stdout)
            self.assertIn("installed: git", result.stdout)
            install_line = next(line for line in result.stdout.splitlines() if "apt-get install" in line)
            self.assertNotIn(" git", install_line)
            self.assertIn("python3", install_line)
            self.assertIn("sudo apt-get update", result.stdout)
            self.assertNotIn("pacman", result.stdout)
            self.assertFalse(log.exists())

            refresh = subprocess.run(
                [script, "--provider", "ubuntu", "--refresh"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(refresh.returncode, 0, refresh.stderr)
            self.assertEqual(log.read_text(encoding="utf-8").splitlines(), ["apt-get update"])

            log.write_text("", encoding="utf-8")
            install = subprocess.run(
                [script, "--provider", "ubuntu", "--install"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            mutations = log.read_text(encoding="utf-8")
            self.assertIn("apt-get install --yes", mutations)
            self.assertNotIn("update", mutations)
            self.assertNotIn(" git", mutations)

    def test_debian_requires_dpkg_query_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "bootstrap-dev.sh"
            script.write_text(templates.bootstrap_script(config()), encoding="utf-8")
            script.chmod(0o755)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._write_command(bin_dir / "apt-get", "exit 97")
            env = {**os.environ, "PATH": str(bin_dir)}
            result = subprocess.run(
                ["/bin/bash", script, "--provider", "debian"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires dpkg-query", result.stderr)
            self.assertIn("No package action was attempted", result.stderr)

    @staticmethod
    def _write_command(path: Path, body: str) -> None:
        path.write_text(f"#!/usr/bin/env bash\nset -eu\n{body}\n", encoding="utf-8")
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
