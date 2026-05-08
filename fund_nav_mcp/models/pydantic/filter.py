__all__ = ['FundFilter']

from datetime import date
from typing import Optional, Literal, List, Any

from pydantic import BaseModel, Field
from sqlalchemy import desc, asc

from fund_nav_mcp.models.orm import Fund
from fund_nav_mcp.utils.enums import FundType, FundRegulatoryType, FundStatus, FundManagementType


class FundFilter(BaseModel):
    """基金列表过滤器"""
    fund_type: Optional[FundType] = Field(
        default=None, title="基金投资类型", description="基金投资类型")
    fund_regulatory_type: Optional[FundRegulatoryType] = Field(
        default=None, title="监管类型")
    fund_management_type: Optional[FundManagementType] = Field(
        default=None, title="基金管理类型", description="基金管理类型")
    establishment_date_start: Optional[date] = Field(
        default=None, title="成立日期起始", description="成立日期起始，含当日")
    establishment_date_end: Optional[date] = Field(
        default=None, title="成立日期截止", description="成立日期截止，含当日")
    registration_date_start: Optional[date] = Field(
        default=None, title="备案日期起始", description="备案日期起始，含当日")
    registration_date_end: Optional[date] = Field(
        default=None, title="备案日期截止", description="备案日期截止，含当日")
    sort_by: Optional[Literal[
        "fund_code", "fund_name", "fund_type", "fund_regulatory_type", "fund_management_type",
        "status", "establishment_date", "establishment_date", "update_time"
    ]] = Field(
        default=None, title="排序字段", description="排序字段，支持 '-field' 降序")
    status: Optional[FundStatus] = Field(
        default=None, title="基金状态")

    @staticmethod
    def _add_date_range(column, start, end, conditions):
        if start and end:
            conditions.append(column.between(start, end))
        elif start:
            conditions.append(column >= start)
        elif end:
            conditions.append(column <= end)

    def to_where(self, model: type[Fund]) -> List[Any]:
        """
        转换为 SQLAlchemy where 条件列表

        Args:
            model: 基金模型类
        Returns:
            SQLAlchemy where 条件列表
        """
        conditions = []

        # 枚举字段精确匹配
        for value, col in [
            (self.fund_type, model.fund_type),
            (self.fund_regulatory_type, model.fund_regulatory_type),
            (self.fund_management_type, model.fund_management_type),
            (self.status, model.status),
        ]:
            if value is not None:
                conditions.append(col == value)

        # 日期区间
        self._add_date_range(
            model.establishment_date,
            self.establishment_date_start,
            self.establishment_date_end,
            conditions
        )
        self._add_date_range(
            model.registration_date,
            self.registration_date_start,
            self.registration_date_end,
            conditions
        )
        return conditions

    def to_order_by(self, model: type[Fund]) -> List[Any]:
        """
        转换为 SQLAlchemy order by 条件列表

        Args:
            model: 基金模型类
        Returns:
            SQLAlchemy order by 条件列表
        """
        if not self.sort_by:
            return []

        direction = desc if self.sort_by.startswith('-') else asc
        field_name = self.sort_by.lstrip('-')

        try:
            col = model.__table__.c[field_name]
        except KeyError:
            raise ValueError(f"无效的排序字段: {field_name}")

        return [direction(col)]
