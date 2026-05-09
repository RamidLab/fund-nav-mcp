__all__ = [
    "get_fund_list", "search_funds_by_keyword", "search_funds_by_fields",
    "get_fund_manager_list", "search_fund_manager_by_keyword", "search_fund_manager_by_fields",
    "get_fund_manager_person_list", "search_fund_manager_person_by_keyword", "search_fund_manager_person_by_fields",
]

from typing import Optional, Type, Union

from fastmcp.tools import tool
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson
from fund_nav_mcp.models.pydantic import BaseFilter, BaseSearchByKeyword, BaseSearchByFields
from fund_nav_mcp.models.pydantic.filter import FundFilter, FundManagerFilter, FundManagerPersonFilter
from fund_nav_mcp.models.pydantic.search import (
    FundSearchByKeyword, FundSearchByFields, FundManagerSearchByKeyword, FundManagerSearchByFields,
    FundManagerPersonSearchByKeyword, FundManagerPersonSearchByFields)
from fund_nav_mcp.models.schemas import PaginationParams
from fund_nav_mcp.utils.enums import Errcode


async def _execute_paginated_query(
        model: Type[DeclarativeBase],
        params: PaginationParams,
        filter_or_search: Union[BaseFilter, BaseSearchByKeyword, BaseSearchByFields, None],
        db_name: str
) -> UtilResponse:
    mgr = (await get_manager("db", db_name))["mgr"]

    where = None
    order_by = None

    if filter_or_search is not None:
        if isinstance(filter_or_search, BaseFilter):
            where = filter_or_search.to_where()
            order_by = filter_or_search.to_order_by()

            for field_name in dir(filter_or_search):
                if field_name.endswith("_list"):
                    column_name = field_name[:-5]
                    col: InstrumentedAttribute | None = getattr(model, column_name, None)
                    if col is not None:
                        values = getattr(filter_or_search, field_name, None)
                        if isinstance(values, list) and len(values) > 0:
                            where = (where or []) + [col.in_(values)]

        elif isinstance(filter_or_search, (BaseSearchByKeyword, BaseSearchByFields)):
            where = filter_or_search.to_where()
        else:
            raise TypeError(f"不支持的过滤器类型: {type(filter_or_search)}")

    page_data = await mgr.paginate(model, params, where=where, order_by=order_by)
    return UtilResponse(code=Errcode.SUCCESS, message="成功", data=page_data)


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
    return await _execute_paginated_query(Fund, params, filters, db_name)


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
    return await _execute_paginated_query(Fund, params, keyword, db_name)


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
    return await _execute_paginated_query(Fund, params, search, db_name)


@tool(
    name="get_fund_manager_list",
    title="获取基金管理人列表",
    description="获取基金管理人（机构）列表，支持筛选、排序与分页",
    tags={"fund_tool"}
)
async def get_fund_manager_list(
        params: PaginationParams,
        filters: Optional[FundManagerFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """
    获取基金管理人（机构）列表

    Args:
        params: 分页参数
        filters: 过滤参数
        db_name: 数据库名称

    Returns:
        通用响应，包含分页的基金管理人（机构）列表
    """
    return await _execute_paginated_query(FundManager, params, filters, db_name)


@tool(
    name="search_fund_manager_by_keyword",
    title="搜索基金管理人（机构）",
    description="根据关键词搜索基金管理人（机构）（支持代码/管理人/经理人/托管人等模糊查询）",
    tags={"fund_tool"}
)
async def search_fund_manager_by_keyword(
        keyword: FundManagerSearchByKeyword,
        params: PaginationParams,
        db_name: str = "default"
) -> UtilResponse:
    """
    根据关键词搜索基金管理人（机构）

    Args:
        keyword: 搜索关键词
        params: 分页参数
        db_name: 数据库名称

    Returns:
        通用响应，包含分页的基金管理人（机构）列表
    """
    return await _execute_paginated_query(FundManager, params, keyword, db_name)


@tool(
    name="search_fund_manager_by_fields",
    title="高级搜索基金管理人（机构）",
    description="根据基金管理人（机构）字段进行高级搜索，字段值支持字符或者对象类型，"
                "字符串类型可由全局搜索模式字段指定，"
                "对象类型支持自定义字段搜索模式，格式为{'value': '', 'mode': 'exact or fuzzy'}",
    tags={"fund_tool"}
)
async def search_fund_manager_by_fields(
        search: FundManagerSearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """
    根据基金管理人（机构）字段进行高级搜索

    Args:
        search: 搜索参数
        params: 分页参数
        db_name: 数据库名称

    Returns:
        通用响应，包含分页的基金列表
    """
    return await _execute_paginated_query(FundManager, params, search, db_name)


@tool(
    name="get_fund_manager_person_list",
    title="获取基金管理人（个人）列表",
    description="获取基金管理人（个人）列表，支持筛选和排序",
    tags={"fund_tool"}
)
async def get_fund_manager_person_list(
        params: PaginationParams = PaginationParams(),
        filters: Optional[FundManagerPersonFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """获取基金经理列表"""
    return await _execute_paginated_query(FundManagerPerson, params, filters, db_name)


@tool(
    name="search_fund_manager_person_by_keyword",
    title="搜索基金管理人（个人）",
    description="根据关键词搜索基金管理人（个人），支持姓名、学历、资格证号、履历及所属公司",
    tags={"fund_tool"}
)
async def search_fund_manager_person_by_keyword(
        keyword: FundManagerPersonSearchByKeyword,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """关键词搜索基金经理"""
    return await _execute_paginated_query(FundManagerPerson, params, keyword, db_name)


@tool(
    name="search_fund_manager_person_by_fields",
    title="高级搜索基金管理人（个人）",
    description="根据基金管理人（个人）字段进行高级搜索，支持字段级匹配模式控制",
    tags={"fund_tool"}
)
async def search_fund_manager_person_by_fields(
        search: FundManagerPersonSearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """高级搜索基金经理"""
    return await _execute_paginated_query(FundManagerPerson, params, search, db_name)
