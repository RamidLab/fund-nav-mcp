from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import TypeVar, Optional, List, Any, Literal, Tuple, Dict, Union

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import desc, asc, ColumnElement, or_
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

T = TypeVar("T", bound=DeclarativeBase)

ScalarValue = Union[int, float, str, bool, date, datetime]
FilterValue = Union[
    ScalarValue,
    List[ScalarValue],  # in 操作符的值
    Tuple[Optional[ScalarValue], Optional[ScalarValue]],  # between 操作符
]


class FilterField(BaseModel):
    value: Optional[FilterValue] = Field(default=None, title="搜索值")
    condition: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "like", "between"] = "eq"

    @model_validator(mode="before")
    @classmethod
    def coerce_plain_value(cls, data):
        if not isinstance(data, dict):
            return {"value": data, "condition": "eq"}
        return data


class BaseFilter(BaseModel, ABC):
    """过滤器基类，提供排序和日期区间辅助方法"""

    @property
    @abstractmethod
    def _filter_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        """返回 [(字段名, 对应模型列)] 列表，用于等值筛选"""
        ...

    @staticmethod
    @abstractmethod
    def _model_class() -> type[T]:
        """返回过滤器对应的 ORM 模型类"""
        ...

    @staticmethod
    def _build_condition(col: InstrumentedAttribute, value: Optional[FilterField]) -> Optional[ColumnElement[bool]]:
        """统一构造 SQL 条件，支持普通值和 FilterField"""
        if value is None:
            return None
        if not isinstance(value, FilterField):
            # 普通值 → 等值（向后兼容）
            return col == value
        # FilterField 对象
        op = value.condition
        val = value.value
        if op == "eq":
            return col == val
        elif op == "ne":
            return col != val
        elif op == "gt":
            return col > val
        elif op == "gte":
            return col >= val
        elif op == "lt":
            return col < val
        elif op == "lte":
            return col <= val
        elif op == "in":
            return col.in_(val if isinstance(val, (list, tuple)) else [val])
        elif op == "like":
            return col.like(f"%{val}%")
        elif op == "between":
            if isinstance(val, (list, tuple)) and len(val) == 2:
                start, end = val
                if start is not None and end is not None:
                    return col.between(start, end)
                elif start is not None:
                    return col >= start
                elif end is not None:
                    return col <= end
                else:
                    return None
            raise ValueError("between 的 value 必须是 (start, end) 二元组")
        else:
            raise ValueError(f"不支持的运算符: {op}")

    def to_order_by(self) -> List[ColumnElement[Any]]:
        """
        转换为 SQLAlchemy order by 条件列表
        子类可重写排序，默认调用 _build_order_by(self, model, self.sort_by)

        Returns:
            SQLAlchemy order by 条件列表
        """
        field_name: Optional[str] = getattr(self, 'sort_by', None)
        order = getattr(self, 'sort_order', "asc")
        if field_name is None:
            return []
        if order not in ["asc", "desc"]:
            raise ValueError(f"无效的排序方向: {order}")
        direction = desc if order == "desc" else asc
        model = self._model_class()
        try:
            col = model.__table__.c[field_name]
        except KeyError:
            raise ValueError(f"无效的排序字段: {field_name}")
        return [direction(col)]

    def to_where(self) -> List[ColumnElement[bool]]:
        """
        转换为 SQLAlchemy where 条件列表
        子类实现具体的条件生成

        Returns:
            SQLAlchemy where 条件列表
        """
        conditions: List[ColumnElement[bool]] = []
        for field_name, col in self._filter_mappings:
            value = getattr(self, field_name, None)
            cond = self._build_condition(col, value)
            if cond is not None:
                conditions.append(cond)
        return conditions


class BaseSearchByKeyword(BaseModel, ABC):
    keyword: str = Field(..., description="搜索关键词")
    match_mode: Literal["exact", "fuzzy"] = Field("fuzzy", description="匹配模式")

    @abstractmethod
    def _or_conditions(self) -> List[ColumnElement[bool]]:
        """
        转换为 SQLAlchemy where 条件列表
        子类实现：返回需要 OR 搜索的条件列表

        Returns:
            SQLAlchemy where 条件列表
        """
        ...

    def to_where(self) -> List[ColumnElement[bool]]:
        return [or_(*self._or_conditions())]


class SearchField(BaseModel):
    """
    单个搜索字段，可以是纯字符串（默认模糊匹配）或包含匹配模式的对象。

    示例：
        纯字符串： "XXX" -> 模糊匹配
        对象：    {"value": "001", "mode": "exact"}  -> 精确匹配
    """
    value: Optional[str] = Field(default=None, title="搜索值")
    condition: Optional[Literal["exact", "fuzzy"]] = Field(
        default=None, title="匹配模式", description="exact=精确，fuzzy=模糊")

    @model_validator(mode="before")
    @classmethod
    def coerce_string_to_value(cls, data) -> Union[Dict[str, Optional[str]], str]:
        """
        如果传入的是普通字符串，自动转换为 {'value': data, 'mode': None}
        这样后续会继承全局 match_mode（默认模糊）。
        """
        if isinstance(data, str):
            return {"value": data, "condition": None}
        return data


class BaseSearchByFields(BaseModel, ABC):
    """
    高级字段搜索抽象基类
    子类只需定义 `_field_mappings`（列字段）和可选的 `_relation_mappings`（关系字段）
    """
    match_mode: Literal["exact", "fuzzy"] = Field("fuzzy", description="全局匹配模式（字段级可覆盖）")
    logic: Literal["and", "or"] = Field("and", description="多条件组合方式")

    @property
    @abstractmethod
    def _column_mappings(self) -> List[Tuple[str, InstrumentedAttribute]]:
        """返回 [(字段名, 模型列)] 列表，用于普通列搜索"""
        ...

    @property
    def _relation_mappings(self) -> List[Tuple[str, str, type[T], str]]:
        """
        返回 [(字段名, 关系属性名, 目标模型, 目标列名)] 列表
        默认空列表，子类按需重写
        """
        return []

    def _like_or_eq(self, column: InstrumentedAttribute, field: SearchField) -> Optional[ColumnElement[bool]]:
        """
        根据匹配模式返回 SQLAlchemy 条件表达式

        Args:
            column: SQLAlchemy 列对象
            field: 搜索字段

        Returns:
            SQLAlchemy 条件表达式
        """
        if not field or field.value is None:
            return None
        mode = field.condition or self.match_mode
        return column.ilike(f"%{field.value}%") if mode == "fuzzy" else column == field.value

    def _relation_cond(
            self, relation_attr: str, target_model: Any, target_col_name: str, field: SearchField
    ) -> Optional[ColumnElement[bool]]:
        """
        根据匹配模式返回 SQLAlchemy 条件表达式

        Args:
            relation_attr: 关系属性名
            target_model: 目标模型类
            target_col_name: 目标列名
            field: 搜索字段

        Returns:
            SQLAlchemy 条件表达式
        """
        if not field or field.value is None:
            return None
        target_col = getattr(target_model, target_col_name)
        rel = getattr(self._model_class(), relation_attr)
        mode = field.condition or self.match_mode
        if mode == "fuzzy":
            return rel.has(target_col.ilike(f"%{field.value}%"))
        return rel.has(target_col == field.value)

    @staticmethod
    @abstractmethod
    def _model_class() -> type:
        """返回搜索的目标模型类"""
        ...

    def to_where(self) -> List[ColumnElement[bool]]:
        """转换为 SQLAlchemy where 条件列表"""
        conditions: List[ColumnElement[bool]] = []

        # 普通列字段
        for field_name, col in self._column_mappings:
            field = getattr(self, field_name, SearchField())
            cond = self._like_or_eq(col, field)
            if cond is not None:
                conditions.append(cond)

        # 关系字段
        for field_name, rel_attr, target_model, target_col_name in self._relation_mappings:
            field = getattr(self, field_name, SearchField())
            cond = self._relation_cond(rel_attr, target_model, target_col_name, field)
            if cond is not None:
                conditions.append(cond)

        if self.logic == "or" and conditions:
            return [or_(*conditions)]
        return conditions


__all__ = ["FilterField", "BaseFilter", "BaseSearchByKeyword", "SearchField", "BaseSearchByFields"]
