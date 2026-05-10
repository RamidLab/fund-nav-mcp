__all__ = [
    'FundSearchByKeyword', 'FundSearchByFields',
    'FundManagerSearchByKeyword', 'FundManagerSearchByFields',
    'FundManagerPersonSearchByKeyword', 'FundManagerPersonSearchByFields',
]

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson, FundCategory
from fund_nav_mcp.models.pydantic import BaseSearchByKeyword, BaseSearchByFields
from fund_nav_mcp.models.pydantic.builder import create_search_class

FundSearchByKeyword: type[BaseSearchByKeyword]
FundSearchByFields: type[BaseSearchByFields]
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

FundManagerSearchByKeyword: type[BaseSearchByKeyword]
FundManagerSearchByFields: type[BaseSearchByFields]
FundManagerSearchByKeyword, FundManagerSearchByFields = create_search_class(
    model=FundManager,
    include=[
        "company_name", "english_name", "short_name", "registered_address", "office_address",
        "actual_controller", "legal_representative",
    ]
)

FundManagerPersonSearchByKeyword: type[BaseSearchByKeyword]
FundManagerPersonSearchByFields: type[BaseSearchByFields]
FundManagerPersonSearchByKeyword, FundManagerPersonSearchByFields = create_search_class(
    model=FundManagerPerson,
    include=["name", "resume"],
    relation_mappings={
        "current_company_name": ("current_company", FundManager, "company_name"),
    },
)
