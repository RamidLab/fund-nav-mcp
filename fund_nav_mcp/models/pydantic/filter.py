__all__ = ['FundFilter', 'FundManagerFilter', 'FundManagerPersonFilter']

from datetime import date
from typing import Optional, Literal, List, Tuple

from pydantic import Field
from sqlalchemy.orm import InstrumentedAttribute

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson
from fund_nav_mcp.models.pydantic import BaseFilter
from fund_nav_mcp.utils.enums import FundType, FundRegulatoryType, FundStatus, FundManagementType, ManagementScaleRange

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
PERSON_SORT_FIELDS = Literal[
    "name", "gender", "birth_date", "education",
    "qualification_number", "is_qualified", "current_company_id",
    "created_at", "updated_at"
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

    @property
    def _filter_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        return [
            ('fund_type', Fund.fund_type),
            ('fund_regulatory_type', Fund.fund_regulatory_type),
            ('fund_management_type', Fund.fund_management_type),
            ('status', Fund.status),
        ]

    @property
    def _date_ranges(self) -> List[Tuple[str, str, InstrumentedAttribute]]:
        return [
            ('establishment_date_start', 'establishment_date_end', Fund.establishment_date),
            ('registration_date_start', 'registration_date_end', Fund.registration_date),
        ]

    @staticmethod
    def _model_class():
        return Fund


class FundManagerFilter(BaseFilter):
    """基金管理人（机构）列表过滤器"""
    management_scale_range: Optional[ManagementScaleRange] = Field(default=None, title="管理规模区间")
    is_member: Optional[bool] = Field(default=None, title="是否为会员")
    amac_registration_date_start: Optional[date] = Field(
        default=None, title="登记时间起始", description="登记时间起始，含当日")
    amac_registration_date_end: Optional[date] = Field(
        default=None, title="登记时间截止", description="登记时间截止，含当日")
    sort_by: Optional[MANAGER_SORT_FIELDS] = Field(
        default=None, title="排序字段", description="排序字段，支持 '-field' 降序")

    @property
    def _filter_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        return [
            ('management_scale_range', FundManager.management_scale_range),
            ('is_member', FundManager.is_member),
        ]

    @property
    def _date_ranges(self) -> List[Tuple[str, str, InstrumentedAttribute]]:
        return [
            ('amac_registration_date_start', 'amac_registration_date_end', FundManager.amac_registration_date),
        ]

    @staticmethod
    def _model_class():
        return FundManager


class FundManagerPersonFilter(BaseFilter):
    """基金经理/投资经理列表过滤器"""
    gender: Optional[Literal["男", "女"]] = Field(default=None, title="性别")
    education: Optional[Literal["本科", "硕士", "博士"]] = Field(default=None, title="学历")
    is_qualified: Optional[bool] = Field(default=None, title="是否具有从业资格")
    birth_date_start: Optional[date] = Field(default=None, title="出生日期起始", description="出生日期起始，含当日")
    birth_date_end: Optional[date] = Field(default=None, title="出生日期截止", description="出生日期截止，含当日")
    current_company_id: Optional[int] = Field(default=None, title="当前任职公司 ID", description="当前任职公司 ID")
    sort_by: Optional[PERSON_SORT_FIELDS] = Field(
        default=None, title="排序字段", description="排序字段，支持 '-field' 降序")

    @property
    def _filter_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        return [
            ('gender', FundManagerPerson.gender),
            ('education', FundManagerPerson.education),
            ('is_qualified', FundManagerPerson.is_qualified),
            ('current_company_id', FundManagerPerson.current_company_id),
        ]

    @property
    def _date_ranges(self) -> List[Tuple[str, str, InstrumentedAttribute]]:
        return [
            ('birth_date_start', 'birth_date_end', FundManagerPerson.birth_date),
        ]

    @staticmethod
    def _model_class():
        return FundManagerPerson
