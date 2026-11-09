#===========================================================================
#  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
#---------------------------------------------------------------------------
#  公众号 / 视频号：芯片验证日记
#  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
#
#  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
#  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
#===========================================================================

"""``wave-mcp`` entrypoint dispatch.

``wave-mcp query ...`` routes to the CLI surface for all MCP tools;
``wave-mcp gc ...`` shows / reclaims session and cache disk usage;
anything else starts the MCP server exactly as before.
"""
from __future__ import annotations

import sys


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "query":
        from .query import main as query_main
        sys.exit(query_main(argv[1:]))
    if argv and argv[0] == "gc":
        from .gc import main as gc_main
        sys.exit(gc_main(argv[1:]))
    from ..server import main as server_main
    sys.exit(server_main())


if __name__ == "__main__":
    main()
