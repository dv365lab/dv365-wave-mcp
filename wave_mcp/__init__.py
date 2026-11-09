#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""wave_mcp — open-source MCP server for RTL waveform debug.

A license-free alternative to Cadence Indago / Verisium Debug MCP.

Data sources aggregated by the server:
  * FST waveform (pylibfst) -> hierarchy, signals, values
  * RTL static analysis    -> connectivity / driver / trace (pyslang netlist)
"""

__version__ = "1.1.1"
