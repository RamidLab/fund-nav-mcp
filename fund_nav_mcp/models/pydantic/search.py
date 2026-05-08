__all__ = ['FundSearchByKeyword', 'FundSearchByFields']

from typing import Optional, List, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_, ColumnElement, Column

from fund_nav_mcp.models.orm import Fund, FundManager, FundManagerPerson


class FundSearchByKeyword(BaseModel):
    """基金产品列表搜索关键词参数"""
    keyword: str = Field(
        title="搜索关键词", description="搜索关键词，同时匹配代码/名称/托管人/管理人/经理")
    match_mode: Literal["exact", "fuzzy"] = Field(
        default="fuzzy", title="匹配模式", description="exact=精确，fuzzy=模糊")

    def to_where(self) -> List[ColumnElement[bool]]:
        """转换为 SQLAlchemy where 条件列表"""
        conditions = []
        fuzzy = self.match_mode == "fuzzy"
        expr = f"%{self.keyword}%" if fuzzy else self.keyword

        conditions.append(
            or_(
                Fund.fund_code.ilike(expr) if fuzzy else Fund.fund_code == expr,
                Fund.fund_name.ilike(expr) if fuzzy else Fund.fund_name == expr,
                Fund.fund_custodian.ilike(expr) if fuzzy else Fund.fund_custodian == expr,
                Fund.manager.has(
                    FundManager.company_name.ilike(expr) if fuzzy else FundManager.company_name == expr
                ),
                Fund.manager_person.has(
                    FundManagerPerson.name.ilike(expr) if fuzzy else FundManagerPerson.name == expr
                ),
            )
        )
        return conditions


class FundSearchField(BaseModel):
    """
    单个搜索字段，可以是纯字符串（默认模糊匹配）或包含匹配模式的对象。

    示例：
        纯字符串： "XXX" -> 模糊匹配
        对象：    {"value": "001", "mode": "exact"}  -> 精确匹配
    """
    value: Optional[str] = Field(default=None, title="搜索值")
    mode: Optional[Literal["exact", "fuzzy"]] = Field(
        default=None, title="匹配模式", description="exact=精确，fuzzy=模糊")

    @model_validator(mode="before")
    @classmethod
    def coerce_string_to_value(cls, data):
        """
        如果传入的是普通字符串，自动转换为 {'value': data, 'mode': None}
        这样后续会继承全局 match_mode（默认模糊）。
        """
        if isinstance(data, str):
            return {"value": data, "mode": None}
        return data


class FundSearchByFields(BaseModel):
    """基金产品列表搜索字段参数"""
    fund_code: Optional[FundSearchField] = Field(default=None, title="基金代码")
    fund_name: Optional[FundSearchField] = Field(default=None, title="基金名称")
    manager_name: Optional[FundSearchField] = Field(default=None, title="基金管理人（机构）")
    person_name: Optional[FundSearchField] = Field(default=None, title="基金管理人（个人）")
    fund_custodian: Optional[FundSearchField] = Field(default=None, title="基金托管人")
    match_mode: Literal["exact", "fuzzy"] = Field(
        default="fuzzy", title="匹配模式", description="exact=精确，fuzzy=模糊")
    logic: Literal["and", "or"] = Field(
        default="and", title="条件连接方式", description="条件连接方式：and 表示同时满足，or 表示任一满足")

    def _like_or_eq(self, column: Column, field: FundSearchField) -> Optional[ColumnElement[bool]]:
        """
        根据匹配模式返回 SQLAlchemy 条件表达式

        Args:
            column: SQLAlchemy 列对象
            field: 搜索字段

        Returns:
            SQLAlchemy 条件表达式
        """
        if field.value is None:
            return None
        mode = field.mode if field.mode else self.match_mode
        return column.ilike(f"%{field.value}%") if mode == "fuzzy" else column == field.value

    def _relation_cond(self, relation_attr: str, field: FundSearchField) -> Optional[ColumnElement[bool]]:
        if field.value is None:
            return None
        target_model = {
            'manager': FundManager,
            'manager_person': FundManagerPerson,
        }[relation_attr]
        target_col = getattr(target_model, 'company_name' if relation_attr == 'manager' else 'name')
        rel = getattr(Fund, relation_attr)
        mode = field.mode if field.mode else self.match_mode
        if mode == "fuzzy":
            return rel.has(target_col.ilike(f"%{field.value}%"))
        return rel.has(target_col == field.value)

    def to_where(self) -> List[ColumnElement[bool]]:
        """转换为 SQLAlchemy where 条件列表"""
        conditions = []

        # 字段组合搜索（AND）
        for field, col in [
            ('fund_code', Fund.fund_code),
            ('fund_name', Fund.fund_name),
            ('fund_custodian', Fund.fund_custodian),
        ]:
            value = getattr(self, field)
            if value:
                conditions.append(self._like_or_eq(col, value))

        for field, rel_attr in [
            ('manager_name', 'manager'),
            ('person_name', 'manager_person'),
        ]:
            value = getattr(self, field)
            if value:
                conditions.append(self._relation_cond(rel_attr, value))

        return [or_(*conditions)] if self.logic == "or" and conditions else conditions
