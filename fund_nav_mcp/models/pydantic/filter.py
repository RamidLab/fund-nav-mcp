__all__ = ['FundFilter']

from datetime import date
from typing import Optional, Literal, List, Any

from pydantic import Field
from sqlalchemy import ColumnElement

from fund_nav_mcp.models.orm import Fund
from fund_nav_mcp.models.pydantic import BaseFilter
from fund_nav_mcp.utils.enums import FundType, FundRegulatoryType, FundStatus, FundManagementType

# 排序字段常量
FUND_SORT_FIELDS = Literal[
    "fund_code", "fund_name", "fund_type", "fund_regulatory_type",
    "fund_management_type", "status", "establishment_date", "registration_date", "updated_at"
]
MANAGER_SORT_FIELDS = Literal[
    "company_name", "english_name", "unified_code", "amac_registration_number",
    "amac_registration_date", "organization_type", "business_type",
    "registered_capital", "paid_up_capital", "capital_ratio",
    "office_address", "employee_count", "fund_industry_count",
    "management_scale_range", "actual_controller", "is_member",
    "legal_representative", "updated_at"
]


class FundFilter(BaseFilter):
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
    status: Optional[FundStatus] = Field(
        default=None, title="基金状态")
    sort_by: Optional[FUND_SORT_FIELDS] = Field(
        default=None, title="排序字段", description="排序字段，支持 '-field' 降序")

    def to_where(self, model: type[Fund]) -> List[ColumnElement[bool]]:
        conditions: List[ColumnElement[bool]] = []

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
        self._add_date_range(model.establishment_date,
                             self.establishment_date_start,
                             self.establishment_date_end, conditions)
        self._add_date_range(model.registration_date,
                             self.registration_date_start,
                             self.registration_date_end, conditions)
        return conditions

    def to_order_by(self, model: type[Fund]) -> List[ColumnElement[Any]]:
        return self._build_order_by(model, self.sort_by)
