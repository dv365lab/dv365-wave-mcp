#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""Static RTL netlist extraction + trace engine.

Built from a pyslang-elaborated design (no Surelog/UHDM, no Verible), persisted
as JSON maps:
  * DriverMap : signal -> [driver records {kind, rhs, control, file, line, snippet}]
  * FanInMap  : signal -> signals that can affect it
  * LoadMap   : signal -> signals it affects (fan-out)
  * LocMap    : signal -> declaration {file, line}
  * instance_tree : hierarchical path -> module definition

The trace engine combines these static maps with FST values to determine the
active driver at a time and to reverse-traverse value / X propagation.
"""
from .slang_netlist import build_netlist, NetlistError  # noqa: F401
from .trace_engine import TraceEngine  # noqa: F401
