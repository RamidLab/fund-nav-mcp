__all__ = [
    'FundFilter', 'FundManagerFilter', 'FundManagerPersonFilter', 'FundCategoryFilter', 'FundCategoryMappingFilter',
    'FundNavFilter', 'FundReturnFilter', 'FundHoldingFilter',
]

from typing import Optional, Literal

from pydantic import Field

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson, FundCategory, FundCategoryMapping, FundNav, \
    FundReturn, FundHolding
from fund_nav_mcp.models.pydantic import BaseFilter
from fund_nav_mcp.models.pydantic.builder import create_filter_class

FundFilter: type[BaseFilter] = create_filter_class(
    model=Fund,
    exclude=["fund_manager_person_id", "fund_manager_id"],
    column_mappings={
        "manager_name": (Fund.manager, FundManager.company_name, Optional[str]),
        "manager_person_name": (Fund.manager_person, FundManagerPerson.name, Optional[str]),
        "category_name": (Fund.categories, FundCategory.category_name, Optional[str]),
    },
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "fund_code", "fund_name", "establishment_date", "registration_date", "created_at", "updated_at"
            ]],
            Field(default=None, title="排序字段", description="排序字段，可在 sort_order 字段选择升降序(acs,desc)")
        ),
        "sort_order": (Literal["asc", "desc"], Field(default="asc", title="排序方向", description="排序方向")),
    },
)
FundManagerFilter: type[BaseFilter] = create_filter_class(
    model=FundManager,
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "company_name", "unified_code", "amac_registration_number", "amac_registration_date",
                "registered_capital", "paid_up_capital", "capital_ratio", "employee_count",
                "fund_industry_count", "created_at", "updated_at"
            ]],
            Field(default=None)
        ),
        "sort_order": (Literal["asc", "desc"], Field("asc")),
    },
)

FundManagerPersonFilter: type[BaseFilter] = create_filter_class(
    model=FundManagerPerson,
    include=["gender", "education", "is_qualified"],
    column_mappings={
        "current_company_name": (FundManagerPerson.current_company, FundManager.company_name, Optional[str]),
    },
    extra_fields={
        "sort_by": (Optional[Literal[
            "name", "birth_date", "education", "qualification_number", "is_qualified"
        ]], Field(default=None, title="排序字段", description="排序字段，可在 sort_order 字段选择升降序(acs,desc)")),
        "sort_order": (Literal["asc", "desc"], Field(default="asc", title="排序方向", description="排序方向")),
    }
)

FundCategoryFilter: type[BaseFilter] = create_filter_class(
    model=FundCategory,
    exclude=["parent_id"],
    column_mappings={
        "parent_category_name": (FundCategory.parent, FundCategory.category_name, Optional[str]),
    },
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "category_code", "category_name", "level", "created_at", "updated_at",
            ]],
            Field(
                default=None,
                title="排序字段",
                description="排序字段，可在 sort_order 字段选择升降序(asc,desc)"
            ),
        ),
        "sort_order": (
            Literal["asc", "desc"],
            Field(default="asc", title="排序方向", description="排序方向"),
        ),
    },
)

FundCategoryMappingFilter: type[BaseFilter] = create_filter_class(
    model=FundCategoryMapping,
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "fund_id", "category_id", "created_at", "updated_at"
            ]], Field(default=None, title="排序字段", description="排序字段，可在 sort_order 字段选择升降序(acs,desc)")
        ),
        "sort_order": (Literal["asc", "desc"], Field(default="asc", title="排序方向", description="排序方向")),
    },
)

FundNavFilter: type[BaseFilter] = create_filter_class(
    model=FundNav,
    exclude=["id", "fund_id"],
    column_mappings={
        "fund_code": (FundNav.fund, Fund.fund_code, Optional[str]),
        "fund_name": (FundNav.fund, Fund.fund_name, Optional[str]),
    },
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "nav_date", "created_at", "updated_at"
            ]],
            Field(default=None, title="排序字段", description="排序字段，可在 sort_order 字段选择升降序(asc,desc)"),
        ),
        "sort_order": (Literal["asc", "desc"], Field(default="asc", title="排序方向", description="排序方向")),
    },
)

FundReturnFilter: type[BaseFilter] = create_filter_class(
    model=FundReturn,
    exclude=["id", "fund_id"],
    column_mappings={
        "fund_code": (FundReturn.fund, Fund.fund_code, Optional[str]),
        "fund_name": (FundReturn.fund, Fund.fund_name, Optional[str]),
    },
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "calculation_date", "return_rate", "rank", "created_at", "updated_at",
            ]],
            Field(default=None, title="排序字段", description="排序字段，可在 sort_order 字段选择升降序(asc,desc)"),
        ),
        "sort_order": (Literal["asc", "desc"], Field(default="asc", title="排序方向", description="排序方向")),
    },
)

FundHoldingFilter: type[BaseFilter] = create_filter_class(
    model=FundHolding,
    exclude=["fund_id"],
    column_mappings={
        "fund_code": (FundHolding.fund, Fund.fund_code, Optional[str]),
        "fund_name": (FundHolding.fund, Fund.fund_name, Optional[str]),
    },
    extra_fields={
        "sort_by": (
            Optional[Literal[
                "report_date", "holding_ratio", "market_value", "shares_held", "stock_code", "stock_name",
                "created_at", "updated_at",
            ]], Field(default=None, title="排序字段", description="排序字段，可在 sort_order 字段选择升降序(asc,desc)"),
        ),
        "sort_order": (Literal["asc", "desc"], Field(default="asc", title="排序方向", description="排序方向")),
    },
)
