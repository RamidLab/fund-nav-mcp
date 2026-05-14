__all__ = [
    "delete_fund", "delete_funds",
    "delete_fund_manager", "delete_fund_managers",
    "delete_fund_manager_person", "delete_fund_manager_persons",
    "delete_fund_category", "delete_fund_categories",
    "delete_fund_category_mapping", "delete_fund_category_mappings",
    "delete_fund_nav", "delete_fund_navs",
    "delete_fund_return", "delete_fund_returns",
    "delete_fund_holding", "delete_fund_holdings",
]

from typing import List, Type, Any

from fastmcp.tools import tool
from pydantic import BaseModel

from fund_nav_mcp.handlers import DeleteHandler
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import (
    Fund, FundManager, FundManagerPerson, FundCategory, FundCategoryMapping,
    FundNav, FundReturn, FundHolding,
)
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.models.pydantic.fund import (
    FundDelete, FundManagerDelete, FundManagerPersonDelete, FundCategoryDelete,
    FundCategoryMappingDelete, FundNavDelete, FundReturnDelete, FundHoldingDelete,
)


async def _handle_delete(
        orm_model: Type[Base], data: BaseModel, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """统一创建 Handler 并执行单条删除"""
    handler = DeleteHandler()
    return await handler.handle(orm_model, data, db_name)


async def _handle_delete_batch(
        orm_model: Type[Base], ids: List[int], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """统一创建 Handler 并执行批量删除"""
    handler = DeleteHandler()
    return await handler.handle_batch(orm_model, ids, db_name)


# ==================== Fund ====================


@tool(
    name="delete_fund",
    title="删除基金产品",
    description="删除单条基金产品记录，通过 record_id、fund_code 或 fund_name 定位记录",
    tags={"fund_tool"}
)
async def delete_fund(data: FundDelete, db_name: str = "default") -> UtilResponse[dict[str, int]]:
    """删除单条基金产品"""
    return await _handle_delete(Fund, data, db_name)


@tool(
    name="delete_funds",
    title="批量删除基金产品",
    description="批量删除多条基金产品记录",
    tags={"fund_tool"}
)
async def delete_funds(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金产品"""
    return await _handle_delete_batch(Fund, ids, db_name)


# ==================== FundManager ====================


@tool(
    name="delete_fund_manager",
    title="删除基金管理人（机构）",
    description="删除单条基金管理人（机构）记录，通过 record_id、amac_registration_number、company_name 或 unified_code 定位记录",
    tags={"fund_tool"}
)
async def delete_fund_manager(data: FundManagerDelete, db_name: str = "default") -> UtilResponse[dict[str, int]]:
    """删除单条基金管理人（机构）"""
    return await _handle_delete(FundManager, data, db_name)


@tool(
    name="delete_fund_managers",
    title="批量删除基金管理人（机构）",
    description="批量删除多条基金管理人（机构）记录",
    tags={"fund_tool"}
)
async def delete_fund_managers(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金管理人（机构）"""
    return await _handle_delete_batch(FundManager, ids, db_name)


# ==================== FundManagerPerson ====================


@tool(
    name="delete_fund_manager_person",
    title="删除基金管理人（个人）",
    description="删除单条基金管理人（个人）记录，通过 record_id、qualification_number 或 name 定位记录；同名时可额外提供 company_code 消除歧义",
    tags={"fund_tool"}
)
async def delete_fund_manager_person(
        data: FundManagerPersonDelete, db_name: str = "default"
) -> UtilResponse[dict[str, int]]:
    """删除单条基金管理人（个人）"""
    return await _handle_delete(FundManagerPerson, data, db_name)


@tool(
    name="delete_fund_manager_persons",
    title="批量删除基金管理人（个人）",
    description="批量删除多条基金管理人（个人）记录",
    tags={"fund_tool"}
)
async def delete_fund_manager_persons(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金管理人（个人）"""
    return await _handle_delete_batch(FundManagerPerson, ids, db_name)


# ==================== FundCategory ====================


@tool(
    name="delete_fund_category",
    title="删除基金分类",
    description="删除单条基金分类记录，通过 record_id、category_code 或 category_name 定位记录",
    tags={"fund_tool"}
)
async def delete_fund_category(data: FundCategoryDelete, db_name: str = "default") -> UtilResponse[dict[str, int]]:
    """删除单条基金分类"""
    return await _handle_delete(FundCategory, data, db_name)


@tool(
    name="delete_fund_categories",
    title="批量删除基金分类",
    description="批量删除多条基金分类记录",
    tags={"fund_tool"}
)
async def delete_fund_categories(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金分类"""
    return await _handle_delete_batch(FundCategory, ids, db_name)


# ==================== FundCategoryMapping ====================


@tool(
    name="delete_fund_category_mapping",
    title="删除基金分类映射",
    description="删除单条基金分类映射记录，通过 record_id，或 fund_code + category_code 定位记录",
    tags={"fund_tool"}
)
async def delete_fund_category_mapping(
        data: FundCategoryMappingDelete, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """删除单条基金分类映射"""
    return await _handle_delete(FundCategoryMapping, data, db_name)


@tool(
    name="delete_fund_category_mappings",
    title="批量删除基金分类映射",
    description="批量删除多条基金分类映射记录",
    tags={"fund_tool"}
)
async def delete_fund_category_mappings(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金分类映射"""
    return await _handle_delete_batch(FundCategoryMapping, ids, db_name)


# ==================== FundNav ====================


@tool(
    name="delete_fund_nav",
    title="删除基金净值",
    description="删除单条基金净值记录，通过 record_id，或 fund_code + nav_date 定位记录",
    tags={"fund_tool"}
)
async def delete_fund_nav(data: FundNavDelete, db_name: str = "default") -> UtilResponse[dict[str, int]]:
    """删除单条基金净值"""
    return await _handle_delete(FundNav, data, db_name)


@tool(
    name="delete_fund_navs",
    title="批量删除基金净值",
    description="批量删除多条基金净值记录",
    tags={"fund_tool"}
)
async def delete_fund_navs(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金净值"""
    return await _handle_delete_batch(FundNav, ids, db_name)


# ==================== FundReturn ====================


@tool(
    name="delete_fund_return",
    title="删除基金收益率",
    description="删除单条基金收益率记录，通过 record_id，或 fund_code + period_type + calculation_date 定位记录",
    tags={"fund_tool"}
)
async def delete_fund_return(data: FundReturnDelete, db_name: str = "default") -> UtilResponse[dict[str, int]]:
    """删除单条基金收益率"""
    return await _handle_delete(FundReturn, data, db_name)


@tool(
    name="delete_fund_returns",
    title="批量删除基金收益率",
    description="批量删除多条基金收益率记录",
    tags={"fund_tool"}
)
async def delete_fund_returns(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金收益率"""
    return await _handle_delete_batch(FundReturn, ids, db_name)


# ==================== FundHolding ====================


@tool(
    name="delete_fund_holding",
    title="删除基金持仓",
    description="删除单条基金持仓记录，通过 record_id，或 fund_code + report_date + stock_code 定位记录",
    tags={"fund_tool"}
)
async def delete_fund_holding(data: FundHoldingDelete, db_name: str = "default") -> UtilResponse[dict[str, int]]:
    """删除单条基金持仓"""
    return await _handle_delete(FundHolding, data, db_name)


@tool(
    name="delete_fund_holdings",
    title="批量删除基金持仓",
    description="批量删除多条基金持仓记录",
    tags={"fund_tool"}
)
async def delete_fund_holdings(ids: List[int], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量删除基金持仓"""
    return await _handle_delete_batch(FundHolding, ids, db_name)
