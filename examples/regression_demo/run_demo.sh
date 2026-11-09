#!/usr/bin/env bash

#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

# One command for the whole demo: run the regression, then triage it.
#
#   ./run_demo.sh              # regression + triage + report
#   ./run_demo.sh --no-shots   # skip screenshots (no browser needed)
#   ./run_demo.sh --hold       # keep the viewer alive to click around
#
# Requires: iverilog, vvp, vcd2fst on PATH; wave-mcp importable.
# Screenshots additionally need playwright + chromium + viewer assets.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${WAVE_MCP_PYTHON:-python3}"
cd "$HERE"

echo "=============================================="
echo " 1/3  running the regression suite"
echo "=============================================="
"$PY" run_regression.py

echo
echo "=============================================="
echo " 2/3  building the netlist session"
echo "=============================================="
# Pick any passing case's waveform: the netlist comes from the RTL, so which
# case it is attached to does not matter. triage.py re-points the session per
# case anyway; this one just proves the filelist elaborates.
REF_WAVE="$(ls runs/seed_*/wave.fst 2>/dev/null | head -1 || true)"
if [[ -z "$REF_WAVE" ]]; then
  echo "no waveform produced; cannot continue" >&2
  exit 1
fi
"$PY" -m wave_mcp.cli.build_session \
  --fst "$REF_WAVE" \
  --filelist rtl/crc_regress.f \
  --top crc_regress_tb \
  --out runs/session

echo
echo "=============================================="
echo " 3/3  triaging the failures with wave-mcp"
echo "=============================================="
"$PY" triage.py "$@"

echo
echo "open the report:  $HERE/report/index.html"
