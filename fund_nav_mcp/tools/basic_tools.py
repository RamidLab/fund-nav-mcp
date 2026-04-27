__all__ = ["health"]

from fastmcp.tools import tool

from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.utils.enums import Errcode


@tool(
    name="health",
    title="健康检查",
    description="检查MCP服务器健康状态，返回服务是否正常"
)
def health() -> UtilResponse:
    # TODO: 检查系统服务是否正常
    return UtilResponse(code=Errcode.SUCCESS, message="服务正常")

# TODO: 添加配置增删改查工具
