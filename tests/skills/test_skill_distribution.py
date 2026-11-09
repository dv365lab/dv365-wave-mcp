#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""Portable skill distribution checks; no native waveform dependencies needed."""
from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "wave-mcp"


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DistributionTests(unittest.TestCase):
    def test_archive_is_relocatable_and_contains_installable_source(self):
        with tempfile.TemporaryDirectory(prefix="wave skill test ") as directory:
            output = Path(directory) / "output"
            result = subprocess.run(
                [sys.executable, str(ROOT / "deploy" / "build_skill.py"),
                 "--output-dir", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archive, = output.glob("*.zip")
            companion, = output.glob("*.skill")
            self.assertEqual(archive.read_bytes(), companion.read_bytes())
            with zipfile.ZipFile(archive) as outer:
                names = outer.namelist()
                self.assertTrue(all(name.startswith("wave-mcp/") for name in names))
                self.assertIn("wave-mcp/SKILL.md", names)
                self.assertIn("wave-mcp/LICENSE", names)
                self.assertIn("wave-mcp/.gitignore", names)
                self.assertIn("/.venv/", outer.read("wave-mcp/.gitignore").decode())
                self.assertFalse(any(".venv" in name or "__pycache__" in name
                                     for name in names))
                with zipfile.ZipFile(io.BytesIO(outer.read(
                        "wave-mcp/assets/wave-mcp-source.zip"))) as source:
                    members = source.namelist()
                    for needed in ("pyproject.toml", "LICENSE", "README.md",
                                   "wave_mcp/server.py", "wave_mcp/cli/query.py",
                                   "wave_mcp/viewer/web/shell.html",
                                   "deploy/build_fsdb2fst.sh",
                                   "third_party/fsdb2fst/fsdb2fst.cpp",
                                   "docs/licenses/TraceWeave-MIT.txt"):
                        self.assertIn(needed, members)
                    self.assertEqual(source.read("wave_mcp/convert.py"),
                                     (ROOT / "wave_mcp/convert.py").read_bytes())
                    self.assertFalse(any(name.startswith((".git/", "tests/",
                                                          "skills/", "dist/"))
                                         or name.endswith((".so", ".dll", ".fst", ".vcd"))
                                         for name in members))
                moved = Path(directory) / "moved skill"
                outer.extractall(moved)
            result = subprocess.run(
                [sys.executable, str(moved / "wave-mcp/scripts/setup_runtime.py"),
                 "--help"], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--source", result.stdout)


class RuntimeSetupTests(unittest.TestCase):
    def test_explicit_source_overrides_bundled_snapshot(self):
        setup = load_script("skill_setup_explicit", SKILL / "scripts/setup_runtime.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "assets/wave-mcp-source.zip"
            bundle.parent.mkdir()
            bundle.touch()
            checkout = root / "checkout"
            checkout.mkdir()
            with mock.patch.object(setup, "SKILL_DIR", root):
                self.assertEqual(setup.find_source(str(checkout)), checkout.resolve())

    def test_setup_installs_bundled_source_into_skill_venv(self):
        setup = load_script("skill_setup", SKILL / "scripts/setup_runtime.py")
        with tempfile.TemporaryDirectory(prefix="wave setup ") as directory:
            skill = Path(directory)
            source = skill / "assets/wave-mcp-source.zip"
            source.parent.mkdir()
            source.write_bytes(b"test source")
            with mock.patch.object(setup, "SKILL_DIR", skill), \
                    mock.patch.object(setup.venv, "EnvBuilder") as builder, \
                    mock.patch.object(setup.subprocess, "run") as run:
                self.assertEqual(setup.main([]), 0)
            builder.return_value.create.assert_called_once_with(skill / ".venv")
            install = run.call_args_list[0]
            self.assertIn(str(source), install.args[0])
            self.assertIn("pip", install.args[0])
            self.assertTrue(Path(install.args[0][0]).is_relative_to(skill / ".venv"))
            self.assertTrue(install.kwargs["check"])

    def test_missing_source_fails_before_creating_environment(self):
        setup = load_script("skill_setup_missing", SKILL / "scripts/setup_runtime.py")
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(setup, "SKILL_DIR", Path(directory)), \
                    mock.patch.object(setup.venv, "EnvBuilder") as builder:
                self.assertNotEqual(setup.main([]), 0)
            builder.assert_not_called()

    def test_dependency_install_failure_is_not_reported_as_ready(self):
        setup = load_script("skill_setup_failure", SKILL / "scripts/setup_runtime.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.zip"
            source.touch()
            with mock.patch.object(setup, "SKILL_DIR", root), \
                    mock.patch.object(setup.venv, "EnvBuilder"), \
                    mock.patch.object(setup.subprocess, "run", side_effect=
                                      subprocess.CalledProcessError(1, ["pip", "install"])), \
                    mock.patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertNotEqual(setup.main(["--source", str(source)]), 0)
                self.assertNotIn("Ready:", output.getvalue())


class LauncherTests(unittest.TestCase):
    def test_forwards_arguments_cwd_and_exit_code_to_selected_runtime(self):
        with tempfile.TemporaryDirectory(prefix="wave cli ") as directory:
            root = Path(directory)
            package = root / "wave_mcp/cli"
            package.mkdir(parents=True)
            for path in (package.parent / "__init__.py", package / "__init__.py"):
                path.write_text("", encoding="utf-8")
            (package / "main.py").write_text(
                "import json, os, sys\n"
                "print(json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd()}))\n"
                "sys.exit(17)\n", encoding="utf-8")
            arguments = ["query", "signal_values", "--json-args",
                         json.dumps({"paths": ["tb.u_dut.data[7:0]"], "time": "15ns"})]
            result = subprocess.run(
                [sys.executable, str(SKILL / "scripts/wave.py"), *arguments],
                cwd=root, env={**os.environ, "WAVE_MCP_PYTHON": sys.executable,
                               "PYTHONPATH": str(root)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 17, result.stderr)
            reply = json.loads(result.stdout)
            self.assertEqual(reply["args"], arguments)
            self.assertEqual(Path(reply["cwd"]), root)

    def test_missing_runtime_has_actionable_error(self):
        result = subprocess.run(
            [sys.executable, str(SKILL / "scripts/wave.py"), "query", "--list"],
            env={**os.environ, "WAVE_MCP_PYTHON": str(SKILL / "not-installed/python")},
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("setup_runtime.py", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
