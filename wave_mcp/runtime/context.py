#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""Who a request runs as.

wave-mcp runs as the OS account that started it, and that account is the one
owner every request belongs to. The server does not model tenants: a shared
host is served by one process per user (stdio, or HTTP bound to loopback or
protected by ``WAVE_MCP_TOKEN``), and what a user may read or write is decided
by the operating system, not re-implemented here.

``owner_id`` is kept on sessions and resources so the session layer has one
place to ask "whose is this" should a front door ever route requests to
per-user workers; today it is always ``LOCAL_OWNER``.
"""
from __future__ import annotations


class Principal:
    """The identity a request runs as."""

    __slots__ = ("owner_id",)

    def __init__(self, owner_id: str) -> None:
        self.owner_id = owner_id

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Principal(owner_id={self.owner_id!r})"


#: The owner every request runs as.
LOCAL_OWNER = "local"


def local_principal() -> Principal:
    """The single-user identity used by stdio, the CLI and HTTP alike."""
    return Principal(LOCAL_OWNER)
