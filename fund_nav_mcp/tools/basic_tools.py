__all__ = [
    "health",
    "get_all_config",
    "add_database", "add_cache",
    "update_database", "update_cache",
    "delete_database", "delete_cache"
]

from typing import Any, Dict

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


@global_tool
@tool(
    name="get_all_config",
    title="获取所有配置",
    description="获取所有配置",
    tags={"config_tool"}
)
def get_all_config() -> MCPSettings:
    """
    获取所有配置

    Returns:
        所有配置
    """
    return get_settings()


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
    db_config = DatabaseConfig.model_validate(db_config)
    result = settings.add_database(db_name, db_config)
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
    cache_config = CacheConfig.model_validate(cache_config)
    result = settings.add_cache(cache_name, cache_config)
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
    db_config = DatabaseConfig.model_validate(db_config)
    result = settings.update_database(db_name, db_config, new_db_name=new_db_name if db_name != new_db_name else None)
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
    cache_config = CacheConfig.model_validate(cache_config)
    result = settings.update_cache(
        cache_name, cache_config,
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
def delete_database(db_name: str) -> UtilResponse:
    """
    删除数据库配置

    Args:
        db_name: 数据库名称

    Returns:
        通用响应
    """
    settings = get_settings()
    result = settings.delete_database(db_name)
    settings.store()
    return check_result(result)


@global_tool
@tool(
    name="delete_cache",
    title="删除缓存配置",
    description="删除缓存配置",
    tags={"config_tool"}
)
def delete_cache(cache_name: str) -> UtilResponse:
    """
    删除缓存配置

    Args:
        cache_name: 缓存名称

    Returns:
        通用响应
    """
    settings = get_settings()
    result = settings.delete_cache(cache_name)
    settings.store()
    return check_result(result)
