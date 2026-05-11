__all__ = [
    "get_fund_list", "search_funds_by_keyword", "search_funds_by_fields",
    "get_fund_manager_list", "search_fund_manager_by_keyword", "search_fund_manager_by_fields",
    "get_fund_manager_person_list", "search_fund_manager_person_by_keyword", "search_fund_manager_person_by_fields",
    "get_fund_category_list", "search_fund_category_by_keyword", "search_fund_category_by_fields",
    "get_fund_category_mapping_list",
    "get_fund_nav_list", "search_fund_nav_by_keyword", "search_fund_nav_by_fields",
    "get_fund_return_list", "search_fund_return_by_keyword", "search_fund_return_by_fields",
    "get_fund_holding_list", "search_fund_holding_by_keyword", "search_fund_holding_by_fields",

]

from typing import Optional

from fastmcp.tools import tool

from fund_nav_mcp.handlers.query_handlers import ForeignKeyDisplayHandler
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson, FundCategory, FundCategoryMapping, FundNav, \
    FundReturn, FundHolding
from fund_nav_mcp.models.pydantic.filter import (
    FundFilter, FundManagerFilter, FundManagerPersonFilter, FundCategoryFilter, FundNavFilter,
    FundCategoryMappingFilter, FundReturnFilter, FundHoldingFilter)
from fund_nav_mcp.models.pydantic.search import (
    FundSearchByKeyword, FundSearchByFields, FundManagerSearchByKeyword, FundManagerSearchByFields,
    FundManagerPersonSearchByKeyword, FundManagerPersonSearchByFields, FundCategorySearchByKeyword,
    FundCategorySearchByFields, FundNavSearchByKeyword, FundNavSearchByFields, FundReturnSearchByKeyword,
    FundReturnSearchByFields, FundHoldingSearchByFields, FundHoldingSearchByKeyword)
from fund_nav_mcp.models.schemas import PaginationParams


async def _handle_query(model, params, filter_or_search, db_name: str = "default") -> UtilResponse:
    """统一创建 Handler 并执行查询"""
    query_handler = ForeignKeyDisplayHandler()
    return await query_handler.handle(model, params, filter_or_search, db_name)


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
    return await _handle_query(Fund, params, filters, db_name)


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
    return await _handle_query(Fund, params, keyword, db_name)


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
    return await _handle_query(Fund, params, search, db_name)


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
    return await _handle_query(FundManager, params, filters, db_name)


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
    return await _handle_query(FundManager, params, keyword, db_name)


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
    return await _handle_query(FundManager, params, search, db_name)


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
    return await _handle_query(FundManagerPerson, params, filters, db_name)


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
    return await _handle_query(FundManagerPerson, params, keyword, db_name)


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
    return await _handle_query(FundManagerPerson, params, search, db_name)


@tool(
    name="get_fund_category_list",
    title="获取基金分类列表",
    description="获取基金分类列表，支持筛选和排序",
    tags={"fund_tool"}
)
async def get_fund_category_list(
        params: PaginationParams = PaginationParams(),
        filters: Optional[FundCategoryFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """获取基金分类列表"""
    return await _handle_query(FundCategory, params, filters, db_name)


@tool(
    name="search_fund_category_by_keyword",
    title="搜索基金分类",
    description="根据关键词搜索基金分类",
    tags={"fund_tool"}
)
async def search_fund_category_by_keyword(
        keyword: FundCategorySearchByKeyword,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """关键词搜索基金分类"""
    return await _handle_query(FundCategory, params, keyword, db_name)


@tool(
    name="search_fund_category_by_fields",
    title="高级搜索基金分类",
    description="根据基金分类字段进行高级搜索，支持字段级匹配模式控制",
    tags={"fund_tool"}
)
async def search_fund_category_by_fields(
        search: FundCategorySearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """高级搜索基金分类"""
    return await _handle_query(FundCategory, params, search, db_name)


@tool(
    name="get_fund_category_mapping_list",
    title="获取基金分类映射列表",
    description="获取基金分类映射列表，支持筛选和排序",
    tags={"fund_tool"}
)
async def get_fund_category_mapping_list(
        params: PaginationParams = PaginationParams(),
        filters: Optional[FundCategoryMappingFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """获取基金分类映射列表"""
    return await _handle_query(FundCategoryMapping, params, filters, db_name)


@tool(
    name="get_fund_nav_list",
    title="获取基金净值列表",
    description="获取基金净值列表，支持筛选和排序",
    tags={"fund_tool"}
)
async def get_fund_nav_list(
        params: PaginationParams = PaginationParams(),
        filters: Optional[FundNavFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """获取基金净值列表"""
    return await _handle_query(FundNav, params, filters, db_name)


@tool(
    name="search_fund_nav_by_keyword",
    title="搜索基金净值",
    description="根据关键词搜索基金净值",
    tags={"fund_tool"}
)
async def search_fund_nav_by_keyword(
        keyword: FundNavSearchByKeyword,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """关键词搜索基金分类"""
    return await _handle_query(FundNav, params, keyword, db_name)


@tool(
    name="search_fund_nav_by_fields",
    title="高级搜索基金净值",
    description="根据基金净值字段进行高级搜索，支持字段级匹配模式控制",
    tags={"fund_tool"}
)
async def search_fund_nav_by_fields(
        search: FundNavSearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """高级搜索基金净值"""
    return await _handle_query(FundNav, params, search, db_name)


@tool(
    name="get_fund_return_list",
    title="获取基金收益率列表",
    description="获取基金收益率列表，支持筛选和排序",
    tags={"fund_tool"}
)
async def get_fund_return_list(
        params: PaginationParams = PaginationParams(),
        filters: Optional[FundReturnFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """获取基金收益率列表"""
    return await _handle_query(FundReturn, params, filters, db_name)


@tool(
    name="search_fund_return_by_keyword",
    title="搜索基金收益率",
    description="根据关键词搜索基金收益率",
    tags={"fund_tool"}
)
async def search_fund_return_by_keyword(
        keyword: FundReturnSearchByKeyword,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """关键词搜索基金收益率"""
    return await _handle_query(FundReturn, params, keyword, db_name)


@tool(
    name="search_fund_return_by_fields",
    title="高级搜索基金收益率",
    description="根据基金收益率字段进行高级搜索，支持字段级匹配模式控制",
    tags={"fund_tool"}
)
async def search_fund_return_by_fields(
        search: FundReturnSearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """高级搜索基金收益率"""
    return await _handle_query(FundReturn, params, search, db_name)


@tool(
    name="get_fund_holding_list",
    title="获取基金持仓列表",
    description="获取基金持仓列表，支持筛选和排序",
    tags={"fund_tool"}
)
async def get_fund_holding_list(
        params: PaginationParams = PaginationParams(),
        filters: Optional[FundHoldingFilter] = None,
        db_name: str = "default"
) -> UtilResponse:
    """获取基金持仓列表"""
    return await _handle_query(FundHolding, params, filters, db_name)


@tool(
    name="search_fund_holding_by_keyword",
    title="搜索基金持仓",
    description="根据关键词搜索基金持仓",
    tags={"fund_tool"}
)
async def search_fund_holding_by_keyword(
        keyword: FundHoldingSearchByKeyword,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """关键词搜索基金持仓"""
    return await _handle_query(FundHolding, params, keyword, db_name)


@tool(
    name="search_fund_holding_by_fields",
    title="高级搜索基金持仓",
    description="根据基金持仓字段进行高级搜索，支持字段级匹配模式控制",
    tags={"fund_tool"}
)
async def search_fund_holding_by_fields(
        search: FundHoldingSearchByFields,
        params: PaginationParams = PaginationParams(),
        db_name: str = "default"
) -> UtilResponse:
    """高级搜索基金持仓"""
    return await _handle_query(FundHolding, params, search, db_name)
