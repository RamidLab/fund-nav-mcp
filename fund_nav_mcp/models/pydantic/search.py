__all__ = [
    'FundSearchByKeyword', 'FundSearchByFields',
    'FundManagerSearchByKeyword', 'FundManagerSearchByFields',
    'FundManagerPersonSearchByKeyword', 'FundManagerPersonSearchByFields',
    'FundCategorySearchByKeyword', 'FundCategorySearchByFields',
    'FundNavSearchByKeyword', 'FundNavSearchByFields',
    'FundReturnSearchByKeyword', 'FundReturnSearchByFields',
    'FundHoldingSearchByKeyword', 'FundHoldingSearchByFields',

]

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson, FundCategory, FundNav, FundReturn, FundHolding
from fund_nav_mcp.models.pydantic.builder import create_search_class

FundSearchByKeyword, FundSearchByFields = create_search_class(
    model=Fund,
    include=[
        "fund_code", "fund_name", "fund_short_name",
        "fund_custodian", "fund_registration_address"
    ],
    relation_mappings={
        "manager_name": ("manager", FundManager, "name"),
        "manager_person_name": ("manager_person", FundManagerPerson, "name"),
        "category_name": ("categories", FundCategory, "category_name"),
    },
)

FundManagerSearchByKeyword, FundManagerSearchByFields = create_search_class(
    model=FundManager,
    include=[
        "company_name", "english_name", "short_name", "registered_address", "office_address",
        "actual_controller", "legal_representative",
    ]
)

FundManagerPersonSearchByKeyword, FundManagerPersonSearchByFields = create_search_class(
    model=FundManagerPerson,
    include=["name", "resume"],
    relation_mappings={
        "current_company_name": ("current_company", FundManager, "company_name"),
    },
)

FundCategorySearchByKeyword, FundCategorySearchByFields = create_search_class(
    model=FundCategory,
    include=["category_name", "description"],
    relation_mappings={
        "parent_category_name": ("parent", FundCategory, "category_name"),
        "child_category_name": ("children", FundCategory, "category_name"),
        "fund_name": ("funds", Fund, "fund_name"),
        "fund_code": ("funds", Fund, "fund_code"),
    },
)

FundNavSearchByKeyword, FundNavSearchByFields = create_search_class(
    model=FundNav,
    relation_mappings={
        "fund_name": ("fund", Fund, "fund_name"),
        "fund_code": ("fund", Fund, "fund_code"),
    },
)

FundReturnSearchByKeyword, FundReturnSearchByFields = create_search_class(
    model=FundReturn,
    relation_mappings={
        "fund_code": ("fund", Fund, "fund_code"),
        "fund_name": ("fund", Fund, "fund_name"),
    },
)

FundHoldingSearchByKeyword, FundHoldingSearchByFields = create_search_class(
    model=FundHolding,
    include=["stock_code", "stock_name"],
    relation_mappings={
        "fund_code": ("fund", Fund, "fund_code"),
        "fund_name": ("fund", Fund, "fund_name"),
    },
)
