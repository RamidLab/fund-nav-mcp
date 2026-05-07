__all__ = [
    "get_fund_list",
]

from typing import Optional

from fastmcp.tools import tool

from fund_nav_mcp.db.core import get_manager, DBManager
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import Fund
from fund_nav_mcp.models.pydantic.filter import FundFilter
from fund_nav_mcp.models.schemas import PaginationParams
from fund_nav_mcp.utils.enums import Errcode


@tool(
    name="get_fund_list",
    title="获取基金列表",
    description="获取基金列表",
    tags={"fund_tool"}
)
async def get_fund_list(
        params: PaginationParams, filters: Optional[FundFilter] = None, db_name: str = "default"
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
    try:
        mgr_info = await get_manager("db", db_name)
        mgr = mgr_info["mgr"]
        if not isinstance(mgr, DBManager):
            return UtilResponse(code=Errcode.DB_QUERY_FAILED, message="该数据库不支持分页查询")
        if not await mgr.health_check():
            return UtilResponse(code=Errcode.DB_CONNECTION_FAILED, message="数据库连接失败")

        where = filters.to_where(Fund) if filters else None
        order_by = filters.to_order_by(Fund) if filters else None

        page_data = await mgr.paginate(
            model=Fund,
            params=params,
            where=where,
            order_by=order_by
        )
        return UtilResponse(code=Errcode.SUCCESS, message="成功", data=page_data)
    except Exception as e:
        return UtilResponse(code=Errcode.DB_QUERY_FAILED, message=str(e))
