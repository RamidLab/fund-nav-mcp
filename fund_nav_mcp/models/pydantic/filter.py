__all__ = ['FundFilter', 'FundManagerFilter', 'FundManagerPersonFilter']

from typing import Optional, Literal

from pydantic import Field

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson
from fund_nav_mcp.models.pydantic import BaseFilter
from fund_nav_mcp.models.pydantic.builder import create_filter_class

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
    "name", "gender", "birth_date", "education", "qualification_number", "is_qualified",
    "current_company_id", "updated_at"
]

FundFilter: type[BaseFilter] = create_filter_class(
    Fund,
    include=['fund_type', 'fund_regulatory_type', 'fund_management_type', 'status'],
    date_range_mappings={
        'establishment_date': ('establishment_date_start', 'establishment_date_end'),
        'registration_date': ('registration_date_start', 'registration_date_end'),
    },
    extra_fields={
        'sort_by': (Optional[FUND_SORT_FIELDS], Field(default=None, description="排序字段，支持 '-field' 降序")),
    },
)

FundManagerFilter: type[BaseFilter] = create_filter_class(
    FundManager,
    include=['management_scale_range', 'is_member'],
    date_range_mappings={
        'amac_registration_date': ('amac_registration_date_start', 'amac_registration_date_end'),
    },
    extra_fields={
        'sort_by': (Optional[MANAGER_SORT_FIELDS], Field(default=None, description="排序字段，支持 '-field' 降序")),
    },
)

FundManagerPersonFilter: type[BaseFilter] = create_filter_class(
    FundManagerPerson,
    include=['gender', 'education', 'is_qualified', 'current_company_id'],
    date_range_mappings={
        'birth_date': ('birth_date_start', 'birth_date_end'),
    },
    extra_fields={
        'sort_by': (Optional[PERSON_SORT_FIELDS], Field(default=None, description="排序字段，支持 '-field' 降序")),
    },
)
