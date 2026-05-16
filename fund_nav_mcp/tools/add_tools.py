__all__ = [
    "add_fund", "add_funds",
    "add_fund_manager", "add_fund_managers",
    "add_fund_manager_person", "add_fund_manager_persons",
    "add_fund_category", "add_fund_categories",
    "add_fund_category_mapping", "add_fund_category_mappings",
    "add_fund_nav", "add_fund_navs",
    "add_fund_return", "add_fund_returns",
    "add_fund_holding", "add_fund_holdings",
]

from typing import Any, List, Type

from fastmcp.tools import tool
from pydantic import BaseModel

from fund_nav_mcp.handlers import AddHandler
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import (
    Fund, FundManager, FundManagerPerson, FundCategory, FundCategoryMapping,
    FundNav, FundReturn, FundHolding,
)
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.models.pydantic.fund import (
    FundCreate, FundManagerCreate, FundManagerPersonCreate, FundCategoryCreate,
    FundCategoryMappingCreate, FundNavCreate, FundReturnCreate, FundHoldingCreate,
)


async def _handle_add(
        orm_model: Type[Base], data: BaseModel, db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """
    添加单条 ORM 模型实例

    Args:
        orm_model: ORM 模型类
        data: 创建数据（Pydantic 模型实例）
        db_name: 数据库名称（可选）

    Returns:
        UtilResponse: 包含操作结果的响应
    """
    add_handler = AddHandler()
    return await add_handler.handle(orm_model, data, db_name)


async def _handle_add_batch(
        orm_model: Type[Base], data_list: List[BaseModel], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """
    批量添加多条 ORM 模型实例，支持部分失败。

    Args:
        orm_model: ORM 模型类
        data_list: 创建数据列表（Pydantic 模型实例列表）
        db_name: 数据库名称（可选）

    Returns:
        UtilResponse，data 包含 success_count、fail_count、ids 和 failures。
    """
    add_handler = AddHandler()
    return await add_handler.handle_batch(orm_model, data_list, db_name)


# ==================== Fund ====================

@tool(
    name="add_fund",
    title="添加基金产品",
    description="添加单条基金产品记录",
    tags={"fund_tool"}
)
async def add_fund(data: FundCreate, db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """添加单条基金产品"""
    return await _handle_add(Fund, data, db_name)


@tool(
    name="add_funds",
    title="批量添加基金产品",
    description="批量添加多条基金产品记录",
    tags={"fund_tool"}
)
async def add_funds(data_list: List[FundCreate], db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """批量添加基金产品"""
    return await _handle_add_batch(Fund, data_list, db_name)


# ==================== FundManager ====================

@tool(
    name="add_fund_manager",
    title="添加基金管理人（机构）",
    description="添加单条基金管理人（机构）记录",
    tags={"fund_tool"}
)
async def add_fund_manager(data: FundManagerCreate, db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """添加单条基金管理人（机构）"""
    return await _handle_add(FundManager, data, db_name)


@tool(
    name="add_fund_managers",
    title="批量添加基金管理人（机构）",
    description="批量添加多条基金管理人（机构）记录",
    tags={"fund_tool"}
)
async def add_fund_managers(
        data_list: List[FundManagerCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金管理人（机构）"""
    return await _handle_add_batch(FundManager, data_list, db_name)


# ==================== FundManagerPerson ====================

@tool(
    name="add_fund_manager_person",
    title="添加基金管理人（个人）",
    description="添加单条基金管理人（个人）记录",
    tags={"fund_tool"}
)
async def add_fund_manager_person(
        data: FundManagerPersonCreate, db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """添加单条基金管理人（个人）"""
    return await _handle_add(FundManagerPerson, data, db_name)


@tool(
    name="add_fund_manager_persons",
    title="批量添加基金管理人（个人）",
    description="批量添加多条基金管理人（个人）记录",
    tags={"fund_tool"}
)
async def add_fund_manager_persons(
        data_list: List[FundManagerPersonCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金管理人（个人）"""
    return await _handle_add_batch(FundManagerPerson, data_list, db_name)


# ==================== FundCategory ====================

@tool(
    name="add_fund_category",
    title="添加基金分类",
    description="添加单条基金分类记录",
    tags={"fund_tool"}
)
async def add_fund_category(data: FundCategoryCreate, db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """添加单条基金分类"""
    return await _handle_add(FundCategory, data, db_name)


@tool(
    name="add_fund_categories",
    title="批量添加基金分类",
    description="批量添加多条基金分类记录",
    tags={"fund_tool"}
)
async def add_fund_categories(
        data_list: List[FundCategoryCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金分类"""
    return await _handle_add_batch(FundCategory, data_list, db_name)


# ==================== FundCategoryMapping ====================

@tool(
    name="add_fund_category_mapping",
    title="添加基金分类映射",
    description="添加单条基金分类映射记录",
    tags={"fund_tool"}
)
async def add_fund_category_mapping(
        data: FundCategoryMappingCreate, db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """添加单条基金分类映射"""
    return await _handle_add(FundCategoryMapping, data, db_name)


@tool(
    name="add_fund_category_mappings",
    title="批量添加基金分类映射",
    description="批量添加多条基金分类映射记录",
    tags={"fund_tool"}
)
async def add_fund_category_mappings(
        data_list: List[FundCategoryMappingCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金分类映射"""
    return await _handle_add_batch(FundCategoryMapping, data_list, db_name)


# ==================== FundNav ====================

@tool(
    name="add_fund_nav",
    title="添加基金净值",
    description="添加单条基金净值记录",
    tags={"fund_tool"}
)
async def add_fund_nav(data: FundNavCreate, db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """添加单条基金净值"""
    return await _handle_add(FundNav, data, db_name)


@tool(
    name="add_fund_navs",
    title="批量添加基金净值",
    description="批量添加多条基金净值记录",
    tags={"fund_tool"}
)
async def add_fund_navs(
        data_list: List[FundNavCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金净值"""
    return await _handle_add_batch(FundNav, data_list, db_name)


# ==================== FundReturn ====================

@tool(
    name="add_fund_return",
    title="添加基金收益率",
    description="添加单条基金收益率记录",
    tags={"fund_tool"}
)
async def add_fund_return(data: FundReturnCreate, db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """添加单条基金收益率"""
    return await _handle_add(FundReturn, data, db_name)


@tool(
    name="add_fund_returns",
    title="批量添加基金收益率",
    description="批量添加多条基金收益率记录",
    tags={"fund_tool"}
)
async def add_fund_returns(
        data_list: List[FundReturnCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金收益率"""
    return await _handle_add_batch(FundReturn, data_list, db_name)


# ==================== FundHolding ====================

@tool(
    name="add_fund_holding",
    title="添加基金持仓",
    description="添加单条基金持仓记录",
    tags={"fund_tool"}
)
async def add_fund_holding(data: FundHoldingCreate, db_name: str = "default") -> UtilResponse[dict[str, Any]]:
    """添加单条基金持仓"""
    return await _handle_add(FundHolding, data, db_name)


@tool(
    name="add_fund_holdings",
    title="批量添加基金持仓",
    description="批量添加多条基金持仓记录",
    tags={"fund_tool"}
)
async def add_fund_holdings(
        data_list: List[FundHoldingCreate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量添加基金持仓"""
    return await _handle_add_batch(FundHolding, data_list, db_name)
