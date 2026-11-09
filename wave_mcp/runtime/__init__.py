#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""Runtime infrastructure for the MCP server.

Kept apart from the analysis code on purpose: the data plane (waveform and
netlist readers) should not grow deployment concerns, and the deployment layer
should not reach into the readers. This package is where request identity and
resource lifetime live.
"""
from __future__ import annotations

from .context import LOCAL_OWNER, Principal, local_principal
from .identity import (cache_key, dataset_identity, dataset_version, file_version,
                       question_digest, request_signature)
from .request import API_SCHEMA_VERSION, RequestSnapshot, current, digest_of
from .resources import ResourceLease, ResourceRegistry

__all__ = ["LOCAL_OWNER", "Principal", "local_principal",
           "cache_key", "dataset_identity", "dataset_version", "file_version",
           "question_digest", "request_signature",
           "API_SCHEMA_VERSION", "RequestSnapshot", "current", "digest_of",
           "ResourceLease", "ResourceRegistry"]
