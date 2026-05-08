from __future__ import annotations

__all__ = ["create_filter_class", "create_search_class"]

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union

from pydantic import Field, create_model
from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute
from sqlalchemy.sql.sqltypes import Enum as SQLEnum

from fund_nav_mcp.models.pydantic import BaseFilter, BaseSearchByKeyword, SearchField, BaseSearchByFields


def _safe_column_python_type(col: InstrumentedAttribute) -> type:
    """
    安全获取列对应的 Python 类型。
    - 枚举返回枚举类
    - 常见 SQLAlchemy 类型做显式映射
    - 失败返回 Any
    """
    col_type = getattr(col, "type", None)
    if col_type is None:
        return Any

    try:
        if isinstance(col_type, SQLEnum):
            enum_class = getattr(col_type, "enum_class", None)
            if isinstance(enum_class, type):
                return enum_class

        type_map = {
            Integer: int,
            String: str,
            Text: str,
            Date: date,
            DateTime: datetime,
            Boolean: bool,
        }
        for sa_type, py_type in type_map.items():
            if isinstance(col_type, sa_type):
                return py_type

        py_type = getattr(col_type, "python_type", None)
        if isinstance(py_type, type):
            return py_type
    except (AttributeError, NotImplementedError):
        pass

    return Any


def _selected_model_columns(
        model: Type[DeclarativeBase],
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        *,
        text_only: bool = False,
) -> Dict[str, InstrumentedAttribute]:
    """
    从模型中选择列：
    - include 不为空时：只取白名单
    - include 为空时：取全部列，排除 exclude 和自增主键
    - text_only=True 时：只保留 String/Text 列
    """
    selected: Dict[str, InstrumentedAttribute] = {}
    table_columns = list(getattr(model.__table__, "columns", []))

    for col in table_columns:
        col_name = col.name

        if include is not None:
            if col_name not in include:
                continue
        else:
            if (col.primary_key and col.autoincrement) or (exclude and col_name in exclude):
                continue

        if text_only and not isinstance(col.type, (String, Text)):
            continue

        attr: InstrumentedAttribute | None = getattr(model, col_name, None)
        if attr is not None:
            selected[col_name] = attr

    return selected


def _bind_property_value(cls: type, name: str, value: Any) -> None:
    """
    给类绑定一个只读 property，避免可变默认值问题。
    """
    setattr(cls, name, property(lambda self, v=value: v))


def _drop_abstract_methods(cls: type, *method_names: str) -> None:
    """移除指定方法名。"""
    abstract_name = "__abstractmethods__"  # noqa
    abstract_methods = frozenset(getattr(cls, abstract_name, frozenset()))
    setattr(cls, abstract_name, abstract_methods - frozenset(method_names))


def create_filter_class(
        model: Type[DeclarativeBase],
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        column_mappings: Optional[Dict[str, Union[InstrumentedAttribute, Tuple[InstrumentedAttribute, type]]]] = None,
        date_range_mappings: Optional[Dict[str, Tuple[str, str]]] = None,
        extra_fields: Optional[Dict[str, Tuple[type, Any]]] = None,
        class_name: Optional[str] = None,
) -> Type[BaseFilter]:
    """
    动态创建 Filter 子类（零类型警告、自动推断字段、全字段可选）。

    Args:
        model: ORM 模型类
        include: 白名单，只包含这些列（优先级高于exclude）
        exclude: 黑名单，排除这些列（include 为 None 时生效）
        column_mappings: 额外/覆盖的列映射，可指定类型
        date_range_mappings: 日期区间映射
        extra_fields: 额外字段，如 sort_by
        class_name: 类名，默认 {ModelName}Filter
    """
    class_name = class_name or f"{model.__name__}Filter"
    date_range_mappings = date_range_mappings or {}
    extra_fields = extra_fields or {}
    column_mappings = column_mappings or {}

    selected_columns = _selected_model_columns(model, include=include, exclude=exclude)

    # 合并 column_mappings 中的字段（类型优先）
    for field_name, entry in column_mappings.items():
        if isinstance(entry, tuple):
            col, _ = entry
        else:
            col = entry
        selected_columns[field_name] = col

    # 构造字段定义
    fields_def: Dict[str, Tuple[type, Any]] = {}
    filter_mappings: List[Tuple[str, InstrumentedAttribute]] = []

    for field_name, col in selected_columns.items():
        if field_name in column_mappings:
            entry = column_mappings[field_name]
            if isinstance(entry, tuple):
                _, py_type = entry
            else:
                py_type = _safe_column_python_type(col)
                py_type = py_type | None
        else:
            py_type = _safe_column_python_type(col)
            py_type = py_type | None

        if not isinstance(py_type, type):
            py_type = Any

        comment = getattr(col, 'comment', '') or ''
        fields_def[field_name] = (py_type, Field(default=None, description=comment))
        filter_mappings.append((field_name, col))

    # 日期区间字段
    for col_name, (start_field, end_field) in date_range_mappings.items():
        fields_def[start_field] = (Optional[date], Field(default=None, description=f"{col_name}起始"))
        fields_def[end_field] = (Optional[date], Field(default=None, description=f"{col_name}截止"))

    # 额外字段
    fields_def.update(extra_fields)

    # 创建动态类
    new_filter = create_model(class_name, __base__=BaseFilter, **fields_def)

    # 绑定只读属性，避免 mutable default warning
    _bind_property_value(new_filter, "_filter_mappings", tuple(filter_mappings))
    _bind_property_value(new_filter, "_date_ranges", tuple(
        (start_field, end_field, getattr(model, col_name))
        for col_name, (start_field, end_field) in date_range_mappings.items()))
    new_filter._model_class = staticmethod(lambda: model)

    _drop_abstract_methods(new_filter, "_filter_mappings", "_model_class")

    return new_filter


def create_search_class(
        model: Type[DeclarativeBase],
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        column_overrides: Optional[Dict[str, Tuple[InstrumentedAttribute, type]]] = None,
        relation_mappings: Optional[Dict[str, Tuple[str, Type[DeclarativeBase], str]]] = None,
) -> Tuple[Type["BaseSearchByKeyword"], Type["BaseSearchByFields"]]:
    """
    根据 ORM 模型自动生成关键词搜索和字段搜索两个 Pydantic 类。

    Args:
        model: ORM 模型类
        include: 参与搜索的文本列白名单（若为 None 则自动包含所有 String/Text 列）
        exclude: 黑名单（include 为 None 时生效）
        column_overrides: 覆盖列类型，例如 {'fund_code': (Fund.fund_code, str)}
        relation_mappings: 跨表关系搜索，例如
            {'manager_name': ('manager', FundManager, 'company_name')}
    """
    column_overrides = column_overrides or {}

    # 选择文本列
    search_columns = _selected_model_columns(
        model,
        include=include,
        exclude=exclude,
        text_only=True,
    )

    # 覆盖列
    for name, (col, _) in column_overrides.items():
        search_columns[name] = col

    # 生成关键词搜索类
    class_name_kw = f"{model.__name__}SearchByKeyword"
    keyword_search_class = create_model(
        class_name_kw,
        __base__=BaseSearchByKeyword,
        keyword=(str, Field(..., description="搜索关键词")),
        match_mode=(Literal["exact", "fuzzy"], Field("fuzzy", description="匹配模式")),
    )

    def _or_conditions(self) -> List[Any]:
        fuzzy = self.match_mode == "fuzzy"
        expr = f"%{self.keyword}%" if fuzzy else self.keyword

        conditions: List[Any] = []
        for col_attr in search_columns.values():
            conditions.append(col_attr.ilike(expr) if fuzzy else col_attr == expr)

        if relation_mappings:
            for _, (rel_attr, target_model, target_col_name) in relation_mappings.items():
                target_col = getattr(target_model, target_col_name)
                rel = getattr(model, rel_attr)
                if rel.property.uselist:
                    cond = rel.any(target_col.ilike(expr)) if fuzzy else rel.any(target_col == expr)
                else:
                    cond = rel.has(target_col.ilike(expr)) if fuzzy else rel.has(target_col == expr)
                conditions.append(cond)
        return conditions

    setattr(keyword_search_class, "_or_conditions", _or_conditions)
    _drop_abstract_methods(keyword_search_class, "_or_conditions")

    # 生成字段搜索类
    class_name_fs = f"{model.__name__}SearchByFields"
    fields_fs: Dict[str, Tuple[type, Any]] = {
        col_name: (Optional[SearchField], None) for col_name in search_columns
    }

    if relation_mappings:
        for field_name in relation_mappings:
            fields_fs[field_name] = (Optional[SearchField], None)

    fields_fs["match_mode"] = (Literal["exact", "fuzzy"], Field("fuzzy"))
    fields_fs["logic"] = (Literal["and", "or"], Field("and"))

    field_search_class = create_model(class_name_fs, __base__=BaseSearchByFields, **fields_fs)

    _bind_property_value(
        field_search_class,
        "_column_mappings",
        [(name, getattr(model, name)) for name in search_columns],
    )

    if relation_mappings:
        _bind_property_value(
            field_search_class,
            "_relation_mappings",
            [
                (field_name, rel_attr, target_model, target_col_name)
                for field_name, (rel_attr, target_model, target_col_name) in relation_mappings.items()
            ],
        )

    def _relation_cond(self, relation_attr: str, target_model: Type[DeclarativeBase], target_col_name: str,
                       field: SearchField) -> Optional[Any]:
        if not field or field.value is None:
            return None
        rel = getattr(self._model_class(), relation_attr)
        target_col = getattr(target_model, target_col_name)
        mode = field.mode or self.match_mode
        fuzzy = (mode == "fuzzy")
        if fuzzy:
            if rel.property.uselist:
                return rel.any(target_col.ilike(f"%{field.value}%"))
            else:
                return rel.has(target_col.ilike(f"%{field.value}%"))
        else:
            if rel.property.uselist:
                return rel.any(target_col == field.value)
            else:
                return rel.has(target_col == field.value)

    setattr(field_search_class, "_relation_cond", _relation_cond)

    field_search_class._model_class = staticmethod(lambda: model)
    _drop_abstract_methods(field_search_class, "_column_mappings", "_model_class", "_relation_cond")

    return keyword_search_class, field_search_class
