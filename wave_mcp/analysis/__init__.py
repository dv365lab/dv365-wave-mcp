#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""Waveform analysis primitives built on the FST data source.

These modules answer *what the dump contains*: activity statistics, time-window
pattern search, value reads, clock-edge sampling and transaction folding. They
never judge why a design failed and never suggest a fix: root-causing belongs to
the agent that calls them.
"""
from .activity import signal_activity
from .clocking import clock_edges, sample_at, sample_table
from .fsm import fsm_transitions
from .predicate import find_time_windows
from .transactions import fold_transactions
from .values import read_point, read_values

__all__ = ["signal_activity", "find_time_windows", "read_values", "read_point",
           "clock_edges", "sample_at", "sample_table", "fold_transactions",
           "fsm_transitions"]
