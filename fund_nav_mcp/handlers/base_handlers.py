from typing import Any, Dict, List, Tuple, Type

from sqlalchemy import func, select

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.orm import Fund, FundCategory, FundManager, FundManagerPerson
from fund_nav_mcp.models.orm.base import Base


class CodeResolveMixin:
    """
    共享的外键 code → id 解析和名称 → id 兜底解析逻辑。

    供 AddHandler / UpdateHandler 复用，避免重复代码。

    Attributes:
        _CODE_RESOLVE_MAP: code 字段 → (id 字段, 参照 ORM, 查询列)
        _NAME_RESOLVE_MAP: 名称字段 → (code 字段, id 字段, 参照 ORM, 名称列)
        _OWN_CODE_FIELDS: 每个 ORM 模型自身的 code 字段集合
        _NAME_FIELDS: 所有名称中间字段的集合
    """

    # code 字段 → (对应的 id 字段名, 参照的 ORM 模型, 用于查询的数据库列名)
    _CODE_RESOLVE_MAP: Dict[str, Tuple[str, Type[Base], str]] = {
        "fund_code": ("fund_id", Fund, "fund_code"),
        "parent_fund_code": ("parent_fund_id", Fund, "fund_code"),
        "category_code": ("category_id", FundCategory, "category_code"),
        "parent_category_code": ("parent_id", FundCategory, "category_code"),
        "manager_code": ("fund_manager_id", FundManager, "amac_registration_number"),
        "manager_person_code": (
            "fund_manager_person_id", FundManagerPerson, "qualification_number",
        ),
        "company_code": ("current_company_id", FundManager, "amac_registration_number"),
    }

    # 名称字段 → (对应的 code 字段, 对应的 id 字段, 参照的 ORM 模型, 用于查询的数据库名称列)
    _NAME_RESOLVE_MAP: Dict[str, Tuple[str, str, Type[Base], str]] = {
        "manager_name": ("manager_code", "fund_manager_id", FundManager, "company_name"),
        "manager_person_name": (
            "manager_person_code", "fund_manager_person_id", FundManagerPerson, "name",
        ),
    }

    _NAME_FIELDS: set = set(_NAME_RESOLVE_MAP.keys())

    # 每个 ORM 模型自身的 code 字段
    _OWN_CODE_FIELDS: Dict[Type[Base], set[str]] = {
        Fund: {"fund_code"},
        FundCategory: {"category_code"},
    }

    @staticmethod
    def _find_code_col(row: Any) -> str:
        if hasattr(row, "amac_registration_number"):
            return row.amac_registration_number or "N/A"
        if hasattr(row, "qualification_number"):
            return row.qualification_number or "N/A"
        return str(row.id)

    @staticmethod
    def _merge_resolved(
            data: Dict[str, Any],
            resolved: Dict[str, Any],
            strip_fields: set,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in data.items():
            if key in strip_fields:
                continue
            if key in resolved and value is not None:
                continue
            out[key] = value
        out.update(resolved)
        return out

    def _fk_code_fields(self, orm_model: Type[Base]) -> set[str]:
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        return set(self._CODE_RESOLVE_MAP.keys()) - own


    async def _resolve_fk_codes(
            self,
            orm_model: Type[Base],
            data_list: List[Dict[str, Any]],
            db_name: str,
    ) -> List[Dict[str, Any]]:
        if not data_list:
            return data_list

        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        mgr = (await get_manager("db", db_name))["mgr"]
        code_cache: Dict[str, Dict[str, int]] = {}

        for code_field, (id_field, model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field in own:
                continue
            codes: set[str] = set()
            for d in data_list:
                cv = d.get(code_field)
                if isinstance(cv, str) and d.get(id_field) is None:
                    codes.add(cv.strip())
            if not codes:
                continue

            stmt = select(model.id, getattr(model, lookup_col)).where(
                getattr(model, lookup_col).in_(codes)
            )
            rows = await mgr.fetch_all(stmt)
            code_cache[code_field] = {r[lookup_col]: r["id"] for r in rows}

        strip = self._fk_code_fields(orm_model)
        resolved_list: List[Dict[str, Any]] = []
        for d in data_list:
            resolved: Dict[str, Any] = {}
            for code_field, (id_field, model, _) in self._CODE_RESOLVE_MAP.items():
                if code_field in own:
                    continue
                code_val = d.get(code_field)
                if isinstance(code_val, str) and d.get(id_field) is None:
                    cache = code_cache.get(code_field, {})
                    cv = code_val.strip()
                    if cv not in cache:
                        raise ValueError(
                            f"无法解析 {code_field}='{cv}'："
                            f"在 {model.__tablename__} 中未找到匹配记录，请先创建对应的 {model.__tablename__}。"
                        )
                    resolved[id_field] = cache[cv]
            resolved_list.append(self._merge_resolved(d, resolved, strip))
        return resolved_list


    async def _resolve_names(
            self,
            data_list: List[Dict[str, Any]],
            db_name: str,
    ) -> List[Dict[str, Any]]:
        if not data_list:
            return data_list

        mgr = (await get_manager("db", db_name))["mgr"]
        for name_field, (code_field, id_field, model, name_col) in self._NAME_RESOLVE_MAP.items():
            names: set[str] = set()
            for d in data_list:
                nv = d.get(name_field)
                if isinstance(nv, str) and not d.get(code_field) and not d.get(id_field):
                    s = nv.strip()
                    if s:
                        names.add(s)
            if not names:
                continue

            stmt = select(model.id, getattr(model, name_col)).where(
                func.lower(getattr(model, name_col)).in_(
                    [n.lower() for n in names]
                )
            )
            rows = await mgr.fetch_all(stmt)
            name_to_rows: Dict[str, List[Any]] = {}
            for r in rows:
                key = r[name_col].lower()
                name_to_rows.setdefault(key, []).append(r)

            for d in data_list:
                nv = d.get(name_field)
                if not isinstance(nv, str) or d.get(code_field) or d.get(id_field):
                    continue
                key = nv.strip().lower()
                if not key:
                    continue
                hits = name_to_rows.get(key, [])
                if not hits:
                    raise ValueError(
                        f"无法通过名称 '{nv}' 找到匹配的 {model.__tablename__} 记录，"
                        f"请先创建或提供对应的 code。"
                    )
                if len(hits) > 1:
                    candidates = ", ".join(
                        f"{r[name_col]} (code: {self._find_code_col(r)})"
                        for r in hits
                    )
                    raise ValueError(
                        f"名称 '{nv}' 匹配到 {len(hits)} 条记录，请使用 code 明确指定: "
                        f"{candidates}"
                    )
                d[id_field] = hits[0].id

        return [{k: v for k, v in d.items() if k not in self._NAME_FIELDS} for d in data_list]
