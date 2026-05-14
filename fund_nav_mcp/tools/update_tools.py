__all__ = [
    "update_fund", "update_funds",
    "update_fund_manager", "update_fund_managers",
    "update_fund_manager_person", "update_fund_manager_persons",
    "update_fund_category", "update_fund_categories",
    "update_fund_nav", "update_fund_navs",
    "update_fund_return", "update_fund_returns",
    "update_fund_holding", "update_fund_holdings",
]

from typing import Any, List, Optional, Type

from fastmcp.tools import tool
from pydantic import BaseModel

from fund_nav_mcp.handlers import UpdateHandler
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import (
    Fund, FundManager, FundManagerPerson, FundCategory,
    FundNav, FundReturn, FundHolding,
)
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.models.pydantic.fund import (
    FundUpdate, FundManagerUpdate, FundManagerPersonUpdate, FundCategoryUpdate,
    FundNavUpdate, FundReturnUpdate, FundHoldingUpdate,
)


async def _handle_update(
        orm_model: Type[Base], data: BaseModel, record_id: Optional[int] = None, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """
    Update a single ORM record.

    Args:
        orm_model: Target ORM model class.
        data: Pydantic update model with fields to apply.
        record_id: Primary-key lookup.  Falls back to the model's unique
                   code field (e.g. fund_code) when omitted.
        db_name: Database configuration name.

    Returns:
        UtilResponse with the updated record id.
    """
    handler = UpdateHandler()
    return await handler.handle(orm_model, data, record_id, db_name)


async def _handle_update_batch(
        orm_model: Type[Base], ids: List[int], data_list: List[BaseModel], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """
    Batch-update ORM records.

    Args:
        orm_model: Target ORM model class.
        ids: Primary-key ids of the records to update (one per data item).
        data_list: List of Pydantic update models.
        db_name: Database configuration name.

    Returns:
        UtilResponse with ids and count.
    """
    handler = UpdateHandler()
    return await handler.handle_batch(orm_model, ids, data_list, db_name)


# ==================== Fund ====================


@tool(
    name="update_fund",
    title="更新基金产品",
    description="更新单条基金产品记录，通过 record_id 或 fund_code 定位记录",
    tags={"fund_tool"}
)
async def update_fund(
        data: FundUpdate, record_id: Optional[int] = None, db_name: str = "default"
) -> UtilResponse[dict[str, int]]:
    """更新单条基金产品"""
    return await _handle_update(Fund, data, record_id, db_name)


@tool(
    name="update_funds",
    title="批量更新基金产品",
    description="批量更新多条基金产品记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_funds(
        ids: List[int], data_list: List[FundUpdate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金产品"""
    return await _handle_update_batch(Fund, ids, data_list, db_name)


# ==================== FundManager ====================


@tool(
    name="update_fund_manager",
    title="更新基金管理人（机构）",
    description="更新单条基金管理人（机构）记录，通过 record_id 定位",
    tags={"fund_tool"}
)
async def update_fund_manager(
        data: FundManagerUpdate, record_id: Optional[int] = None, db_name: str = "default"
) -> UtilResponse[dict[str, int]]:
    """更新单条基金管理人（机构）"""
    return await _handle_update(FundManager, data, record_id, db_name)


@tool(
    name="update_fund_managers",
    title="批量更新基金管理人（机构）",
    description="批量更新多条基金管理人（机构）记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_fund_managers(
        ids: List[int], data_list: List[FundManagerUpdate], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金管理人（机构）"""
    return await _handle_update_batch(FundManager, ids, data_list, db_name)


# ==================== FundManagerPerson ====================


@tool(
    name="update_fund_manager_person",
    title="更新基金管理人（个人）",
    description="更新单条基金管理人（个人）记录，通过 record_id 定位",
    tags={"fund_tool"}
)
async def update_fund_manager_person(
        data: FundManagerPersonUpdate, record_id: Optional[int] = None, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """更新单条基金管理人（个人）"""
    return await _handle_update(FundManagerPerson, data, record_id, db_name)


@tool(
    name="update_fund_manager_persons",
    title="批量更新基金管理人（个人）",
    description="批量更新多条基金管理人（个人）记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_fund_manager_persons(
        ids: List[int], data_list: List[FundManagerPersonUpdate], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金管理人（个人）"""
    return await _handle_update_batch(FundManagerPerson, ids, data_list, db_name)


# ==================== FundCategory ====================


@tool(
    name="update_fund_category",
    title="更新基金分类",
    description="更新单条基金分类记录，通过 record_id 或 category_code 定位记录",
    tags={"fund_tool"}
)
async def update_fund_category(
        data: FundCategoryUpdate, record_id: Optional[int] = None, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """更新单条基金分类"""
    return await _handle_update(FundCategory, data, record_id, db_name)


@tool(
    name="update_fund_categories",
    title="批量更新基金分类",
    description="批量更新多条基金分类记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_fund_categories(
        ids: List[int], data_list: List[FundCategoryUpdate], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金分类"""
    return await _handle_update_batch(FundCategory, ids, data_list, db_name)


# ==================== FundNav ====================


@tool(
    name="update_fund_nav",
    title="更新基金净值",
    description="更新单条基金净值记录，通过 record_id 定位",
    tags={"fund_tool"}
)
async def update_fund_nav(
        data: FundNavUpdate, record_id: Optional[int] = None, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """更新单条基金净值"""
    return await _handle_update(FundNav, data, record_id, db_name)


@tool(
    name="update_fund_navs",
    title="批量更新基金净值",
    description="批量更新多条基金净值记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_fund_navs(
        ids: List[int], data_list: List[FundNavUpdate], db_name: str = "default"
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金净值"""
    return await _handle_update_batch(FundNav, ids, data_list, db_name)


# ==================== FundReturn ====================


@tool(
    name="update_fund_return",
    title="更新基金收益率",
    description="更新单条基金收益率记录，通过 record_id 定位",
    tags={"fund_tool"}
)
async def update_fund_return(
        data: FundReturnUpdate, record_id: Optional[int] = None, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """更新单条基金收益率"""
    return await _handle_update(FundReturn, data, record_id, db_name)


@tool(
    name="update_fund_returns",
    title="批量更新基金收益率",
    description="批量更新多条基金收益率记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_fund_returns(
        ids: List[int], data_list: List[FundReturnUpdate], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金收益率"""
    return await _handle_update_batch(FundReturn, ids, data_list, db_name)


# ==================== FundHolding ====================


@tool(
    name="update_fund_holding",
    title="更新基金持仓",
    description="更新单条基金持仓记录，通过 record_id 定位",
    tags={"fund_tool"}
)
async def update_fund_holding(
        data: FundHoldingUpdate, record_id: Optional[int] = None, db_name: str = "default",
) -> UtilResponse[dict[str, int]]:
    """更新单条基金持仓"""
    return await _handle_update(FundHolding, data, record_id, db_name)


@tool(
    name="update_fund_holdings",
    title="批量更新基金持仓",
    description="批量更新多条基金持仓记录，需提供 ids 与 data_list",
    tags={"fund_tool"}
)
async def update_fund_holdings(
        ids: List[int], data_list: List[FundHoldingUpdate], db_name: str = "default",
) -> UtilResponse[dict[str, Any]]:
    """批量更新基金持仓"""
    return await _handle_update_batch(FundHolding, ids, data_list, db_name)
