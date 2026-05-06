__all__ = [
    "health",
    "get_all_config",
    "add_database", "add_cache",
    "update_database", "update_cache",
    "delete_database", "delete_cache"
]

from typing import Any, Dict

from fastmcp.server.context import Context
from fastmcp.tools import tool

from fund_nav_mcp.config import get_settings, MCPSettings
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.schemas import DatabaseConfig, CacheConfig
from fund_nav_mcp.tools import global_tool
from fund_nav_mcp.utils.common import check_result
from fund_nav_mcp.utils.enums import NodeStatus, Errcode


@tool(
    name="health",
    title="健康检查",
    description="检查MCP服务器健康状态，返回服务是否正常",
    tags={"sys_tool"}
)
def health() -> UtilResponse:
    # TODO: 检查系统服务是否正常
    return UtilResponse(code=Errcode.SUCCESS, message="服务正常")


@tool(
    name="get_tools_by_tag",
    title="根据标签查询工具",
    description="获取当前MCP服务器中所有带有指定标签的工具列表，返回工具名称、描述和标签信息。",
    tags={"sys_tool"}
)
async def get_tools_by_tag(tag: str, ctx: Context) -> UtilResponse:
    """
    根据标签筛选已注册的工具。

    Args:
        tag: 需要筛选的标签，例如 "sys_tool", "config_tool" 等。
        ctx: FastMCP 上下文对象，包含 FastMCP 服务器实例等信息。

    Returns:
        工具信息列表，每个工具包含：
        - name: 工具名称
        - description: 工具描述
        - tags: 该工具的所有标签列表
        - input_schema: 输入参数的 JSON Schema（可选）
    """
    mcp_server = ctx.fastmcp  # 获取 FastMCP 服务器实例
    all_tools = await mcp_server.list_tools()  # 异步获取所有工具
    matched = [item.name for item in all_tools if tag in item.tags]
    return UtilResponse(code=Errcode.SUCCESS, message="获取指定标签工具成功", data=matched)


@global_tool
@tool(
    name="get_all_config",
    title="获取所有配置",
    description="获取所有配置",
    tags={"config_tool"}
)
def get_all_config(reload: bool = False) -> MCPSettings:
    """
    获取所有配置

    Returns:
        所有配置
    """
    return get_settings(reload)


@global_tool
@tool(
    name="add_database",
    title="添加数据库配置",
    description="添加数据库配置",
    tags={"config_tool"}
)
def add_database(db_name: str, db_config: Dict[str, Any]) -> UtilResponse:
    """
    添加数据库配置

    Args:
        db_name: 数据库名称
        db_config: 数据库配置字典

    Returns:
        通用响应
    """
    settings = get_settings()
    result = settings.add_database(db_name, DatabaseConfig.model_validate(db_config))
    settings.store()
    return check_result(result)


@global_tool
@tool(
    name="add_cache",
    title="添加缓存配置",
    description="添加缓存配置",
    tags={"config_tool"}
)
def add_cache(cache_name: str, cache_config: Dict[str, Any]) -> UtilResponse:
    """
    添加缓存配置

    Args:
        cache_name: 缓存名称
        cache_config: 缓存配置字典

    Returns:
        通用响应
    """
    settings = get_settings()
    result = settings.add_cache(cache_name, CacheConfig.model_validate(cache_config))
    settings.store()
    return check_result(result)


@global_tool
@tool(
    name="update_database",
    title="更新数据库配置",
    description="更新数据库配置",
    tags={"config_tool"}
)
def update_database(db_name: str, db_config: Dict[str, Any]) -> UtilResponse:
    """
    更新数据库配置

    Args:
        db_name: 数据库名称
        db_config: 数据库配置字典

    Returns:
        通用响应
    """
    settings = get_settings()
    db_config["status"] = db_config.get("status", NodeStatus.Unknown)
    new_db_name = db_config["db_name"]
    result = settings.update_database(
        db_name, DatabaseConfig.model_validate(db_config),
        new_db_name=new_db_name if db_name != new_db_name else None
    )
    settings.store()
    return check_result(result)


@global_tool
@tool(
    name="update_cache",
    title="更新缓存配置",
    description="更新缓存配置",
    tags={"config_tool"}
)
def update_cache(cache_name: str, cache_config: Dict[str, Any]) -> UtilResponse:
    """
    更新缓存配置

    Args:
        cache_name: 缓存名称
        cache_config: 缓存配置字典

    Returns:
        通用响应
    """
    settings = get_settings()
    cache_config["status"] = cache_config.get("status", NodeStatus.Unknown)
    new_cache_name = cache_config["cache_name"]
    result = settings.update_cache(
        cache_name, CacheConfig.model_validate(cache_config),
        new_cache_name=new_cache_name if cache_name != new_cache_name else None
    )
    settings.store()
    return check_result(result)


@global_tool
@tool(
    name="delete_database",
    title="删除数据库配置",
    description="删除数据库配置",
    tags={"config_tool"}
)
def delete_database(db_name: str, db_config: Dict[str, Any]) -> UtilResponse:
    """
    删除数据库配置

    Args:
        db_name: 数据库名称
        db_config: 数据库配置字典

    Returns:
        通用响应
    """
    settings = get_settings()
    result = settings.delete_database(db_name, DatabaseConfig.model_validate(db_config))
    settings.store()
    return check_result(result)


@global_tool
@tool(
    name="delete_cache",
    title="删除缓存配置",
    description="删除缓存配置",
    tags={"config_tool"}
)
def delete_cache(cache_name: str, cache_config: Dict[str, Any]) -> UtilResponse:
    """
    删除缓存配置

    Args:
        cache_name: 缓存名称
        cache_config: 缓存配置字典

    Returns:
        通用响应
    """
    settings = get_settings()
    result = settings.delete_cache(cache_name, CacheConfig.model_validate(cache_config))
    settings.store()
    return check_result(result)
