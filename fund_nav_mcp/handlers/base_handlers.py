from typing import Any, Dict, List, Tuple, Type, Optional

from sqlalchemy import func, select

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.orm import Fund, FundCategory, FundManager, FundManagerPerson
from fund_nav_mcp.models.orm.base import Base


class CodeResolveMixin:
    """
    提供外键 code → id 解析和名称 → id 兜底解析的共享逻辑。

    该 Mixin 用于 AddHandler、UpdateHandler 和 DeleteHandler，避免解析逻辑重复。

    工作机制：
        - code 解析：当请求数据中包含业务编码（如 ``fund_code``）时，
          通过数据库查询将其转换为对应记录的主键 ID，并移除原始 code 字段。
        - 名称解析：当 code 未提供但给出了可读名称（如 ``manager_name``）时，
          通过大小写不敏感精确匹配查找对应记录的 ID，要求名称唯一。
        - 自有 code 字段：某些模型自身包含具有唯一约束的 code 字段
          （如 ``Fund.fund_code``），这些字段不参与外键解析，
          但可用于唯一性校验（主要在 AddHandler 中使用）以及通过 code 定位记录。

    Attributes:
        _CODE_RESOLVE_MAP (Dict[str, tuple]): code 字段到 (目标 id 字段, 参照 ORM 模型, 参照表查询列) 的映射。
        _NAME_RESOLVE_MAP (Dict[str, tuple]): 名称字段到 (对应 code 字段, 目标 id 字段, 参照 ORM 模型, 参照表名称列) 的映射。
        _OWN_CODE_FIELDS (Dict[type, set[str]]): 每个 ORM 模型自身的 code 字段集合，这些字段不会被当作外键处理。
        _NAME_FIELDS (set[str]): 所有名称中间字段的集合，这些字段仅用于解析，不应持久化到数据库。
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

    # 每个 ORM 模型自身的 code 字段集合（在这里统一定义，可被子类覆盖）
    _OWN_CODE_FIELDS: Dict[Type[Base], set[str]] = {
        Fund: {"fund_code"},
        FundCategory: {"category_code"},
    }

    @staticmethod
    def _find_code_col(row: Any) -> str:
        """
        从查询结果行对象中提取一个可读的业务编码，用于构造错误提示。

        遍历几个常见的编码字段（中基协登记编号、从业资格证号），
        若都不存在则回退到记录的主键 ID。

        Args:
            row: 数据库查询返回的 ORM 实例或行对象。

        Returns:
            字符串形式的编码或 ID。
        """
        if isinstance(row, dict):
            return str(row.get("amac_registration_number") or row.get("qualification_number") or row.get("id", "N/A"))
        if hasattr(row, "amac_registration_number"):
            return row.amac_registration_number or "N/A"
        if hasattr(row, "qualification_number"):
            return row.qualification_number or "N/A"
        return str(row.id)

    @staticmethod
    def _merge_resolved(data: Dict[str, Any], resolved: Dict[str, Any], strip_fields: set) -> Dict[str, Any]:
        """
        合并原始数据与解析出的 ID 字段，并移除指定的中间字段。

        合并策略：
            1. 若字段名在 ``strip_fields`` 中，则丢弃该字段（通常是外键 code 字段）。
            2. 若字段名同时出现在 ``data`` 和 ``resolved`` 中，且 ``data`` 中的值不是 ``None``，
               则保留 ``data`` 中的值（显式提供的 ID 优先于解析出的 ID）。
            3. 其他字段直接从 ``data`` 复制。
            4. 最后将 ``resolved`` 中的所有键值对合并到结果中。

        Args:
            data: 原始请求数据字典，可能包含外键 code 字段。
            resolved: 由 code 解析出的 id 字典，例如 ``{"fund_id": 42}``。
            strip_fields: 需要移除的字段名集合（通常为外键 code 字段名）。

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
        获取对于指定 ORM 模型来说需要作为外键处理的 code 字段集合。

        外键 code 字段 = 全部 code 映射字段 - 该模型自身的 code 字段。
        这些字段在解析完成后应当从数据中移除。

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
        批量将请求数据中的外键 code 字段解析为对应的数据库 ID，并移除这些 code 字段。

        处理流程：
            1. 遍历全局 code 映射，筛选出属于当前模型外键的字段。
            2. 收集所有需要解析的 code 值（仅当字符串提供且对应 id 未填写）。
            3. 执行一次批量 IN 查询，构建 ``code → id`` 的字典缓存。
            4. 对于每条数据，用缓存中的 id 填充对应的 id 字段；
               若某个 code 在数据库中找不到，抛出 ValueError。
            5. 通过 ``_merge_resolved`` 合并并移除中间 code 字段。

        Args:
            orm_model: 目标 ORM 模型类，用于区分自有 code 和外键 code。
            data_list: 待处理的原始数据字典列表。
            db_name: 数据库连接名称。

        Returns:
            解析后的数据字典列表，外键 code 字段已被移除，只包含解析后的 id 字段。
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
        批量将请求数据中的名称字段兜底解析为对应的 ID 字段。

        仅当记录中既未提供外键 code，也未显式提供对应 id 时，才尝试通过名称匹配。
        匹配规则：大小写不敏感精确匹配，且要求名称唯一；若匹配到多条记录或找不到记录则抛出异常。
        解析成功后，所有名称中间字段会从数据中移除，因为这些字段不属于 ORM 属性。

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
                    # 名称不唯一，列出候选项的 code 以便调用方明确指定
                    candidates = ", ".join(
                        f"{r[name_col]} (code: {self._find_code_col(r)})"
                        for r in hits
                    )
                    raise ValueError(
                        f"名称 '{nv}' 匹配到 {len(hits)} 条记录，请使用 code 明确指定: "
                        f"{candidates}"
                    )
                # 将解析出的 id 填入数据
                d[id_field] = hits[0]["id"]

        # 第四步：移除所有名称中间字段，这些字段不是 ORM 属性
        return [{k: v for k, v in d.items() if k not in self._NAME_FIELDS} for d in data_list]

    async def _check_own_codes_unique(
            self,
            orm_model: Type[Base],
            data_list: List[Dict[str, Any]],
            db_name: str,
            exclude_id: Optional[int] = None,
    ) -> None:
        """
        检查 data_list 中模型自身 code 字段的唯一性，防止重复。

        遍历该模型的自有 code 字段（如 Fund 的 ``fund_code``），
        首先校验输入数据内部是否有重复值，然后查询数据库是否已存在相同的 code。
        若指定了 ``exclude_id``，则数据库查重时会排除该 ID（用于更新操作的自引用排除）。

        Args:
            orm_model: 目标 ORM 模型类。
            data_list: 待检查的数据字典列表。
            db_name: 数据库连接名称。
            exclude_id: 可选，要排除的记录主键 ID，用于更新时忽略自身。
        """
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        if not own:
            return
        mgr = (await get_manager("db", db_name))["mgr"]

        for code_field, (_, model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field not in own:
                continue
            # 收集所有非空字符串 code
            codes: List[str] = [
                d[code_field].strip()
                for d in data_list
                if isinstance(d.get(code_field), str)
            ]
            if not codes:
                continue

            # 输入内部重复检查
            seen = set()
            dup = None
            for c in codes:
                if c in seen:
                    dup = c
                    break
                seen.add(c)
            if dup is not None:
                raise ValueError(
                    f"操作失败：{code_field}='{dup}' 在输入数据中重复。"
                )

            # 数据库冲突检查
            stmt = select(model.id, getattr(model, lookup_col)).where(
                getattr(model, lookup_col).in_(codes)
            )
            if exclude_id is not None:
                stmt = stmt.where(model.id != exclude_id)
            rows = await mgr.fetch_all(stmt)
            if rows:
                existing = {r[lookup_col]: r["id"] for r in rows}
                conflicts = [
                    f"{code_field}='{c}' 已存在 (id={existing[c]})"
                    for c in codes if c in existing
                ]
                raise ValueError(
                    "失败：以下 code 已存在，请使用不同的 code。\n"
                    + "\n".join(conflicts)
                )

    async def _resolve_record_id(
            self,
            orm_model: Type[Base],
            record_id: Optional[int],
            raw: Dict[str, object],
            db_name: str,
    ) -> int:
        """
        解析待操作记录的主键 ID。

        优先使用显式提供的 ``record_id``；若未提供，则尝试从 ``raw`` 中获取模型的自有
        code 字段值（例如 ``fund_code``），通过查询数据库定位对应的 ID。

        Args:
            orm_model: 目标 ORM 模型类。
            record_id: 直接指定的主键 ID，可为 None。
            raw: 从请求数据中提取的字段字典，可能包含 model 的自有 code。
            db_name: 数据库配置名称。

        Returns:
            解析出的整数主键 ID。
        """
        if record_id is not None:
            mgr = (await get_manager("db", db_name))["mgr"]
            stmt = select(orm_model.id).where(orm_model.id == record_id)
            row = await mgr.fetch_one(stmt)
            if row is None:
                raise ValueError(f"{orm_model.__tablename__} 表中未找到 id={record_id} 的记录。")
            return record_id

        # 尝试通过模型自身的 code 字段解析
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        for code_field, (_, _model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field not in own:
                continue
            cv = raw.get(code_field)
            if not isinstance(cv, str):
                continue
            mgr = (await get_manager("db", db_name))["mgr"]
            stmt = select(orm_model.id).where(
                getattr(orm_model, lookup_col) == cv.strip()
            )
            row = await mgr.fetch_one(stmt)
            if row is None:
                raise ValueError(
                    f"{orm_model.__tablename__} 表中未找到 {code_field}='{cv}' 的记录。"
                )
            return row["id"]

        raise ValueError(
            f"无法识别 {orm_model.__tablename__} 记录：请提供 `record_id` 或唯一的业务编码字段。"
        )
