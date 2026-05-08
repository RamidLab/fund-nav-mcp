__all__ = [
    'FundSearchByKeyword', 'FundSearchByFields', 'FundManagerSearchByKeyword', 'FundManagerSearchByFields',
    'FundManagerPersonSearchByKeyword', 'FundManagerPersonSearchByFields',
]

from typing import Optional, List, Tuple, Any

from pydantic import Field
from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson
from fund_nav_mcp.models.pydantic import BaseSearchByFields, BaseSearchByKeyword, SearchField


class FundSearchByKeyword(BaseSearchByKeyword):
    """基金关键词搜索"""

    def _or_conditions(self) -> List[ColumnElement[bool]]:
        expr, fuzzy = self._get_search_params()
        return [
            Fund.fund_code.ilike(expr) if fuzzy else Fund.fund_code == expr,
            Fund.fund_name.ilike(expr) if fuzzy else Fund.fund_name == expr,
            Fund.fund_custodian.ilike(expr) if fuzzy else Fund.fund_custodian == expr,
            Fund.manager.has(
                FundManager.company_name.ilike(expr) if fuzzy else FundManager.company_name == expr
            ),
            Fund.manager_person.has(
                FundManagerPerson.name.ilike(expr) if fuzzy else FundManagerPerson.name == expr
            ),
        ]


class FundSearchByFields(BaseSearchByFields):
    """基金产品列表搜索字段参数"""
    fund_code: Optional[SearchField] = Field(default=None, title="基金代码")
    fund_name: Optional[SearchField] = Field(default=None, title="基金名称")
    manager_name: Optional[SearchField] = Field(default=None, title="基金管理人（机构）")
    manager_person_name: Optional[SearchField] = Field(default=None, title="基金管理人（个人）")
    fund_custodian: Optional[SearchField] = Field(default=None, title="基金托管人")

    @property
    def _column_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        return [
            ('fund_code', Fund.fund_code),
            ('fund_name', Fund.fund_name),
            ('fund_custodian', Fund.fund_custodian),
        ]

    @property
    def _relation_mappings(self) -> List[Tuple[str, str, Any, str]]:
        return [
            ('manager_name', 'manager', FundManager, 'company_name'),
            ('manager_person_name', 'manager_person', FundManagerPerson, 'name'),
        ]

    @staticmethod
    def _model_class() -> type:
        return Fund


class FundManagerSearchByKeyword(BaseSearchByKeyword):
    """基金管理人关键词搜索"""

    def _or_conditions(self) -> List[ColumnElement[bool]]:
        expr, fuzzy = self._get_search_params()
        return [
            FundManager.company_name.ilike(expr) if fuzzy else FundManager.company_name == expr,
            FundManager.english_name.ilike(expr) if fuzzy else FundManager.english_name == expr,
            FundManager.short_name.ilike(expr) if fuzzy else FundManager.short_name == expr,
            FundManager.unified_code.ilike(expr) if fuzzy else FundManager.unified_code == expr,
            FundManager.amac_registration_number.ilike(expr) if fuzzy else FundManager.amac_registration_number == expr,
            FundManager.legal_representative.ilike(expr) if fuzzy else FundManager.legal_representative == expr,
            FundManager.actual_controller.ilike(expr) if fuzzy else FundManager.actual_controller == expr,
            FundManager.registered_address.ilike(expr) if fuzzy else FundManager.registered_address == expr,
            FundManager.office_address.ilike(expr) if fuzzy else FundManager.office_address == expr,
        ]


class FundManagerSearchByFields(BaseSearchByFields):
    """基金管理人字段搜索"""
    company_name: Optional[SearchField] = Field(default=None, title="公司全称")
    english_name: Optional[SearchField] = Field(default=None, title="英文名称")
    short_name: Optional[SearchField] = Field(default=None, title="公司简称")
    unified_code: Optional[SearchField] = Field(default=None, title="统一社会信用代码")
    amac_registration_number: Optional[SearchField] = Field(default=None, title="中基协登记编号")
    legal_representative: Optional[SearchField] = Field(default=None, title="法定代表人")
    actual_controller: Optional[SearchField] = Field(default=None, title="实际控制人")
    registered_address: Optional[SearchField] = Field(default=None, title="注册地址")
    office_address: Optional[SearchField] = Field(default=None, title="办公地址")
    fund_list: Optional[SearchField] = Field(default=None, title="管理基金代码列表")
    manager_person_list: Optional[SearchField] = Field(default=None, title="基金管理人（个人）列表")

    @property
    def _column_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        return [
            ('company_name', FundManager.company_name),
            ('english_name', FundManager.english_name),
            ('short_name', FundManager.short_name),
            ('unified_code', FundManager.unified_code),
            ('amac_registration_number', FundManager.amac_registration_number),
            ('legal_representative', FundManager.legal_representative),
            ('actual_controller', FundManager.actual_controller),
            ('registered_address', FundManager.registered_address),
            ('office_address', FundManager.office_address),
        ]

    @property
    def _relation_mappings(self) -> List[Tuple[str, str, Any, str]]:
        return [
            ('fund_list', 'funds', Fund, 'fund_code'),
            ('manager_person_list', 'manager_person', FundManagerPerson, 'name'),
        ]

    @staticmethod
    def _model_class() -> type:
        return FundManager


class FundManagerPersonSearchByKeyword(BaseSearchByKeyword):
    """基金经理关键词搜索"""

    def _or_conditions(self) -> List[ColumnElement[bool]]:
        expr, fuzzy = self._get_search_params()
        return [
            FundManagerPerson.name.ilike(expr) if fuzzy else FundManagerPerson.name == expr,
            FundManagerPerson.education.ilike(expr) if fuzzy else FundManagerPerson.education == expr,
            FundManagerPerson.qualification_number.ilike(
                expr) if fuzzy else FundManagerPerson.qualification_number == expr,
            FundManagerPerson.resume.ilike(expr) if fuzzy else FundManagerPerson.resume == expr,
            # 通过关联公司名称搜索
            FundManagerPerson.current_company.has(
                FundManager.company_name.ilike(expr) if fuzzy else FundManager.company_name == expr
            ),
        ]


class FundManagerPersonSearchByFields(BaseSearchByFields):
    """基金经理字段搜索"""
    name: Optional[SearchField] = None
    education: Optional[SearchField] = None
    qualification_number: Optional[SearchField] = None
    resume: Optional[SearchField] = None
    company_name: Optional[SearchField] = None
    fund_list: Optional[SearchField] = Field(default=None, title="管理基金名称列表")

    @property
    def _column_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        return [
            ('name', FundManagerPerson.name),
            ('education', FundManagerPerson.education),
            ('qualification_number', FundManagerPerson.qualification_number),
            ('resume', FundManagerPerson.resume),
        ]

    @property
    def _relation_mappings(self) -> List[Tuple[str, str, Any, str]]:
        return [
            ('company_name', 'current_company', FundManager, 'company_name'),
            ('fund_list', 'funds', Fund, 'fund_code'),
        ]

    @staticmethod
    def _model_class() -> type:
        return FundManagerPerson
