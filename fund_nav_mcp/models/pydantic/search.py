__all__ = [
    'FundSearchByKeyword', 'FundSearchByFields', 'FundManagerSearchByKeyword', 'FundManagerSearchByFields',
    'FundManagerPersonSearchByKeyword', 'FundManagerPersonSearchByFields',
]

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson
from fund_nav_mcp.models.pydantic import BaseSearchByKeyword, BaseSearchByFields
from fund_nav_mcp.models.pydantic.builder import create_search_class

FundSearchByKeyword: type[BaseSearchByKeyword]
FundSearchByFields: type[BaseSearchByFields]
FundSearchByKeyword, FundSearchByFields = create_search_class(
    Fund,
    include=['fund_code', 'fund_name', 'fund_custodian'],
    relation_mappings={
        'manager_name': ('manager', FundManager, 'company_name'),
        'manager_person_name': ('manager_person', FundManagerPerson, 'name'),
    },
)

FundManagerSearchByFields: type[BaseSearchByFields]
FundManagerSearchByKeyword: type[BaseSearchByKeyword]
FundManagerSearchByKeyword, FundManagerSearchByFields = create_search_class(
    FundManager,
    include=[
        'company_name', 'english_name', 'short_name', 'unified_code',
        'amac_registration_number', 'legal_representative', 'actual_controller',
        'registered_address', 'office_address',
    ],
    relation_mappings={
        'fund_list': ('funds', Fund, 'fund_code'),
        'manager_person_list': ('manager_person', FundManagerPerson, 'name'),
    },
)

FundManagerPersonSearchByFields: type[BaseSearchByFields]
FundManagerPersonSearchByKeyword: type[BaseSearchByKeyword]
FundManagerPersonSearchByKeyword, FundManagerPersonSearchByFields = create_search_class(
    FundManagerPerson,
    include=['name', 'education', 'qualification_number', 'resume'],
    relation_mappings={
        'company_name': ('current_company', FundManager, 'company_name'),
        'fund_list': ('funds', Fund, 'fund_code'),
    },
)
