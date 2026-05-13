from typing import Any, Dict, List, Tuple, Type

from sqlalchemy import func, select

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.orm import Fund, FundCategory, FundManager, FundManagerPerson
from fund_nav_mcp.models.orm.base import Base


class CodeResolveMixin:
    """
    提供外键 code → id 解析和名称 → id 兜底解析的共享逻辑。

    该 Mixin 用于 AddHandler 和 UpdateHandler，避免解析逻辑重复。

    工作机制：
        - code 解析：通过业务编码（如 fund_code）查找对应记录的 id。
        - 名称解析：当 code 未提供时，通过唯一名称（如公司全称）查找对应记录的 id。
        - 自有 code 字段：某些模型自身的 code 字段（如 Fund.fund_code）不参与外键解析，
          但可用于唯一性校验（由添加处理器负责）。

    Attributes:
        _CODE_RESOLVE_MAP: code 字段 → (对应的 id 字段名, 参照的 ORM 模型, 用于查询的数据库列名)。
        _NAME_RESOLVE_MAP: 名称字段 → (对应的 code 字段, 对应的 id 字段, 参照的 ORM 模型, 用于查询的数据库名称列)。
        _OWN_CODE_FIELDS: 每个 ORM 模型自身的 code 字段集合。
        _NAME_FIELDS: 所有名称中间字段的集合（这些字段仅用于解析，最终不会写入数据库）。
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

    # 所有名称中间字段的集合（这些字段仅用于查找，不应持久化到数据库）
    _NAME_FIELDS: set = set(_NAME_RESOLVE_MAP.keys())

    # 每个 ORM 模型自身的 code 字段集合
    # 这些字段不会作为外键被解析，但可用于唯一性校验（在添加操作中）
    _OWN_CODE_FIELDS: Dict[Type[Base], set[str]] = {
        Fund: {"fund_code"},
        FundCategory: {"category_code"},
    }

    @staticmethod
    def _find_code_col(row: Any) -> str:
        """
        从数据库查询返回的行对象中提取可识别的业务编码字符串，用于错误提示。

        优先尝试 amac_registration_number，其次 qualification_number，
        都不可用时回退到记录 ID。

        Args:
            row: 查询结果行对象，具备对应 ORM 模型的属性。

        Returns:
            代表该行的编码字符串。
        """
        if hasattr(row, "amac_registration_number"):
            return row.amac_registration_number or "N/A"
        if hasattr(row, "qualification_number"):
            return row.qualification_number or "N/A"
        return str(row.id)

    @staticmethod
    def _merge_resolved(data: Dict[str, Any], resolved: Dict[str, Any], strip_fields: set) -> Dict[str, Any]:
        """
        合并原始数据与解析出的 ID 字段，并移除指定的中间字段。

        规则：
            - 若字段在 strip_fields 中，直接跳过（不保留）。
            - 若字段同时在 data 和 resolved 中出现，且 data 中的值非 None，
              则保留 data 中的值（显式提供的 ID 优先）。
            - 最后将 resolved 中的字段合并到结果中。

        Args:
            data: 原始数据字典（可能包含外键 code 和其他字段）。
            resolved: 由 code 解析出的 id 字典。
            strip_fields: 需要从最终结果中剔除的字段名集合（通常是那些作为外键的 code 字段）。

        Returns:
            合并并清理后的新字典。
        """
        out: Dict[str, Any] = {}
        for key, value in data.items():
            # 跳过分组定义为应移除的字段
            if key in strip_fields:
                continue
            # 如果该字段已经通过解析得到且原始值不为 None，则保留原始值（显式 ID 优先）
            if key in resolved and value is not None:
                continue
            out[key] = value
        out.update(resolved)
        return out

    def _fk_code_fields(self, orm_model: Type[Base]) -> set[str]:
        """
        返回对于给定 orm_model 应视为外键（需要解析并最终从数据中移除）的 code 字段集合。

        外键 code 字段 = _CODE_RESOLVE_MAP 中所有字段 - 该模型自身的 code 字段。

        Args:
            orm_model: 目标 ORM 模型类。

        Returns:
            外键 code 字段名的集合。
        """
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        return set(self._CODE_RESOLVE_MAP.keys()) - own

    async def _resolve_fk_codes(
            self, orm_model: Type[Base], data_list: List[Dict[str, Any]], db_name: str,
    ) -> List[Dict[str, Any]]:
        """
        批量将 data_list 中的外键 code 字段解析为对应的数据库 ID，自有 code 保留。

        处理流程：
        1. 收集所有需要解析且尚未提供 id 的外键 code 值。
        2. 批量查询对应参照表，构建 code → id 映射缓存。
        3. 遍历每条数据：
           - 若提供了 code 且未提供 id，则从缓存查找对应的 id 填入。
           - 若找不到匹配记录，抛出 ValueError。
        4. 移除所有分组的中间 code 字段（只保留解析出的 id 字段）。

        Args:
            orm_model: 目标 ORM 模型类，用于确定哪些 code 字段属于自己（不解析）。
            data_list: 待处理的原始数据字典列表（每条记录可能包含 code 字段）。
            db_name: 数据库连接名称。

        Returns:
            解析后的数据字典列表，其中外键 code 字段已被移除，并添加了对应的 id 字段。
        """
        if not data_list:
            return data_list

        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        mgr = (await get_manager("db", db_name))["mgr"]
        code_cache: Dict[str, Dict[str, int]] = {}

        # 第一步：按 code 字段分组收集需要解析的值
        for code_field, (id_field, model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field in own:
                continue  # 跳过模型自身的 code，不解析
            codes: set[str] = set()
            for d in data_list:
                cv = d.get(code_field)
                # 仅当提供字符串 code 且对应 id 尚未填写时才需要解析
                if isinstance(cv, str) and d.get(id_field) is None:
                    codes.add(cv.strip())
            if not codes:
                continue

            # 第二步：批量查询参照表，构建缓存
            stmt = select(model.id, getattr(model, lookup_col)).where(
                getattr(model, lookup_col).in_(codes)
            )
            rows = await mgr.fetch_all(stmt)
            code_cache[code_field] = {r[lookup_col]: r["id"] for r in rows}

        # 第三步：逐条数据处理
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
            # 合并解析结果并剔除中间 code 字段
            resolved_list.append(self._merge_resolved(d, resolved, strip))
        return resolved_list

    async def _resolve_names(self, data_list: List[Dict[str, Any]], db_name: str) -> List[Dict[str, Any]]:
        """
        批量将 data_list 中的名称字段兜底解析为对应的 ID 字段。

        触发条件：记录中既未提供外键 code，也未显式提供对应的 id。
        解析要求名称精确唯一（大小写不敏感），否则抛出异常。
        解析完成后，所有名称中间字段将从数据中移除。

        Args:
            data_list: 经过外键 code 解析后的数据字典列表。
            db_name: 数据库连接名称。

        Returns:
            解析并移除了名称中间字段后的数据字典列表。
        """
        if not data_list:
            return data_list

        mgr = (await get_manager("db", db_name))["mgr"]
        for name_field, (code_field, id_field, model, name_col) in self._NAME_RESOLVE_MAP.items():
            # 第一步：收集需要解析的名称
            names: set[str] = set()
            for d in data_list:
                nv = d.get(name_field)
                # 仅当名称存在，且对应的 code 和 id 均未提供时才解析
                if isinstance(nv, str) and not d.get(code_field) and not d.get(id_field):
                    s = nv.strip()
                    if s:
                        names.add(s)
            if not names:
                continue

            # 第二步：大小写不敏感精确匹配查询
            stmt = select(model.id, getattr(model, name_col)).where(
                func.lower(getattr(model, name_col)).in_(
                    [n.lower() for n in names]
                )
            )
            rows = await mgr.fetch_all(stmt)
            # 按小写名称分组，以便检测重名
            name_to_rows: Dict[str, List[Any]] = {}
            for r in rows:
                key = r[name_col].lower()
                name_to_rows.setdefault(key, []).append(r)

            # 第三步：逐条数据处理
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
                    # 名称不唯一，提示调用方使用 code 明确指定
                    candidates = ", ".join(
                        f"{r[name_col]} (code: {self._find_code_col(r)})"
                        for r in hits
                    )
                    raise ValueError(
                        f"名称 '{nv}' 匹配到 {len(hits)} 条记录，请使用 code 明确指定: "
                        f"{candidates}"
                    )
                # 将解析出的 id 填入数据
                d[id_field] = hits[0].id

        # 第四步：移除所有名称中间字段，这些字段不是 ORM 属性
        return [{k: v for k, v in d.items() if k not in self._NAME_FIELDS} for d in data_list]
