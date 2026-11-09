#!/usr/bin/env python3

#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""Build portable .zip/.skill packages with this checkout's tracked source."""
from __future__ import annotations

import argparse
import ast
import io
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {"pyproject.toml", "requirements.txt", "MANIFEST.in", "LICENSE",
              "README.md", "README.en.md", "CHANGELOG.md"}
SOURCE_SUFFIXES = {
    "wave_mcp": {".py", ".html", ".js"},
    "docs": {".md", ".txt", ".json", ".png", ".jpg", ".LICENSE", ".NOTICE"},
    "examples": {".py", ".sv", ".f", ".sh", ".md"},
    "third_party/fsdb2fst": {".cpp", ".c", ".h", ".sh"},
    "third_party/fstdumper": {".patch"},
    "deploy": {".py", ".sh", ".md", ".template", ".example", ".sv"},
}


def project_version(root: Path) -> str:
    tree = ast.parse((root / "wave_mcp/__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str) and value and all(c.isalnum() or c in ".-+" for c in value):
                return value
    raise ValueError("cannot find a safe project version in wave_mcp/__init__.py")


def source_files(root: Path) -> list[Path]:
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    selected = []
    for raw in tracked.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8")
        path = PurePosixPath(name)
        if name not in ROOT_FILES and not any(
                name.startswith(prefix + "/") and path.suffix in suffixes
                for prefix, suffixes in SOURCE_SUFFIXES.items()):
            continue
        local = root / name
        if local.is_symlink() or not local.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"source must be a regular file inside the checkout: {name}")
        if not local.is_file():
            raise ValueError(f"tracked source is missing: {name}")
        selected.append(local)
    needed = ROOT_FILES | {"wave_mcp/server.py", "wave_mcp/cli/query.py"}
    missing = needed - {path.relative_to(root).as_posix() for path in selected}
    if missing:
        raise ValueError(f"missing project source: {sorted(missing)}")
    return sorted(selected)


def build_skill(root: Path, output_dir: Path) -> tuple[Path, Path]:
    skill = root / "skills/wave-mcp"
    source = io.BytesIO()
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files(root):
            archive.write(path, path.relative_to(root).as_posix())
    # Restrict the outer package to authored instructions and helpers. Never
    # package the private venv, generated assets, caches, or local simulations.
    resources = [skill / "SKILL.md", skill / ".gitignore"]
    for folder, suffixes in (("scripts", {".py"}), ("references", {".md"}),
                             ("agents", {".yaml"})):
        resources.extend(path for path in (skill / folder).glob("*")
                         if path.is_file() and path.suffix in suffixes)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"wave-mcp-{project_version(root)}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(resources):
            archive.write(path, "wave-mcp/" + path.relative_to(skill).as_posix())
        archive.write(root / "LICENSE", "wave-mcp/LICENSE")
        archive.writestr("wave-mcp/assets/wave-mcp-source.zip", source.getvalue())
    companion = target.with_suffix(".skill")
    shutil.copyfile(target, companion)
    return target, companion


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/skills")
    args = parser.parse_args()
    for path in build_skill(ROOT, args.output_dir.resolve()):
        print(f"{path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
