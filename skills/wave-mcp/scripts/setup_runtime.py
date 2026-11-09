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

"""Install this skill's project snapshot into a private virtual environment."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import venv


SKILL_DIR = Path(__file__).resolve().parents[1]


def find_source(explicit: str | None) -> Path:
    if explicit:
        source = Path(explicit).expanduser().resolve()
        if not source.exists():
            raise ValueError(f"source does not exist: {source}")
        return source
    bundled = SKILL_DIR / "assets" / "wave-mcp-source.zip"
    if bundled.is_file():
        return bundled
    for parent in SKILL_DIR.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "wave_mcp/server.py").is_file():
            return parent
    raise ValueError("no bundled source or checkout found; use --source /path/to/dv365-wave-mcp "
                     "or install the complete skill distribution")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="local project directory or source archive; "
                        "defaults to bundled source, then the enclosing checkout")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        print("error: use Python 3.10+ (3.10-3.13 are project-tested)", file=sys.stderr)
        return 2
    try:
        source = find_source(args.source)
        environment = SKILL_DIR / ".venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(interpreter), "-m", "pip", "--disable-pip-version-check",
                        "install", str(source)], check=True)
        subprocess.run([str(interpreter), "-m", "wave_mcp.cli.main", "query", "--list"], check=True)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("See references/setup.md. Linux x86_64 has prebuilt dependencies; "
              "other platforms may need native build tools for pylibfst.", file=sys.stderr)
        return 1
    print(f"Ready: {SKILL_DIR / 'scripts' / 'wave.py'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
