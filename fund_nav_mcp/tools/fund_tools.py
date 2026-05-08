__all__ = [
    "get_fund_list",
]

from typing import Optional

from fastmcp.tools import tool

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import Fund
from fund_nav_mcp.models.pydantic.filter import FundFilter
from fund_nav_mcp.models.pydantic.search import FundSearchByKeyword, FundSearchByFields
from fund_nav_mcp.models.schemas import PaginationParams
from fund_nav_mcp.utils.enums import Errcode


@tool(
    name="get_fund_list",
    title="获取基金列表",
    description="获取基金列表",
    tags={"fund_tool"}
)
async def get_fund_list(
        params: PaginationParams,
        filters: Optional[FundFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """
    获取基金列表

    Args:
        params: 分页参数
        filters: 过滤参数
        db_name: 数据库名称
    Returns:
        通用响应
    """
    mgr = (await get_manager("db", db_name))["mgr"]
    where = filters.to_where(Fund) if filters else None
    order_by = filters.to_order_by(Fund) if filters else None

    page_data = await mgr.paginate(
        model=Fund,
        params=params,
        where=where,
        order_by=order_by
    )
    return UtilResponse(code=Errcode.SUCCESS, message="成功", data=page_data)


@tool(
    name="search_funds_by_keyword",
    title="搜索基金产品",
    description="根据关键词搜索基金产品（支持名称/代码/管理人/经理人/托管人的模糊查询）",
    tags={"fund_tool"}
)
async def search_funds_by_keyword(
        keyword: FundSearchByKeyword,
        params: PaginationParams,
        db_name: str = "default"
) -> UtilResponse:
    """
    根据关键词搜索基金产品

    Args:
        keyword: 搜索关键词
        params: 分页参数
        db_name: 数据库名称

    Returns:
        通用响应，包含分页的基金列表
    """
    mgr = (await get_manager("db", db_name))["mgr"]
    page_data = await mgr.paginate(Fund, params, where=keyword.to_where())
    return UtilResponse(code=Errcode.SUCCESS, message="成功", data=page_data)


@tool(
    name="search_funds_by_fields",
    title="高级搜索基金",
    description="根据基金产品字段进行高级搜索，字段值支持字符或者对象类型，"
                "字符串类型可由全局搜索模式字段指定，"
                "对象类型支持自定义字段搜索模式，格式为{'value': '', 'mode': 'exact or fuzzy'}",
    tags={"fund_tool"}
)
async def search_funds_by_fields(
        search: FundSearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """
    根据基金产品字段进行高级搜索

    Args:
        search: 搜索参数
        params: 分页参数
        db_name: 数据库名称

    Returns:
        通用响应，包含分页的基金列表
    """
    mgr = (await get_manager("db", db_name))["mgr"]
    page_data = await mgr.paginate(Fund, params, where=search.to_where())
    return UtilResponse(code=Errcode.SUCCESS, message="成功", data=page_data)
