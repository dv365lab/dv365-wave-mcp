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

"""Forward the wave-mcp CLI to this skill's runtime, preserving the caller's cwd."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    skill = Path(__file__).resolve().parents[1]
    override = os.environ.get("WAVE_MCP_PYTHON")
    interpreter = (Path(override).expanduser() if override else
                   skill / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    if not interpreter.is_file():
        print(f"error: runtime Python not found: {interpreter}\n"
              f"Run: python \"{skill / 'scripts' / 'setup_runtime.py'}\"\n"
              "Or set WAVE_MCP_PYTHON to an absolute Python executable with wave-mcp installed.",
              file=sys.stderr)
        return 2
    try:
        return subprocess.call([str(interpreter), "-m", "wave_mcp.cli.main", *sys.argv[1:]])
    except OSError as exc:
        print(f"error: cannot start runtime: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
