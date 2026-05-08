__all__ = ['FundSearchByKeyword', 'FundSearchByFields']

from typing import Optional, List, Tuple, Any

from pydantic import Field
from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson
from fund_nav_mcp.models.pydantic import BaseSearchByFields, BaseSearchByKeyword, SearchField


class FundSearchByKeyword(BaseSearchByKeyword):
    """基金关键词搜索"""

    def _or_conditions(self) -> List[ColumnElement[bool]]:
        fuzzy = self.match_mode == "fuzzy"
        expr = f"%{self.keyword}%" if fuzzy else self.keyword
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
    person_name: Optional[SearchField] = Field(default=None, title="基金管理人（个人）")
    fund_custodian: Optional[SearchField] = Field(default=None, title="基金托管人")

    @property
    def _column_mappings(self) -> list[Tuple[str, InstrumentedAttribute[Optional[str]]]]:
        return [
            ('fund_code', Fund.fund_code),
            ('fund_name', Fund.fund_name),
            ('fund_custodian', Fund.fund_custodian),
        ]

    @property
    def _relation_mappings(self) -> List[Tuple[str, str, Any, str]]:
        return [
            ('manager_name', 'manager', FundManager, 'company_name'),
            ('person_name', 'manager_person', FundManagerPerson, 'name'),
        ]

    @staticmethod
    def _model_class() -> type:
        return Fund
