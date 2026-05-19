import re
from datetime import date
from typing import Any, Dict, List, Tuple, Type, Optional, Set

from sqlalchemy import Integer, String, Date, DECIMAL, func, select

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.orm import Fund, FundCategory, FundManager, FundManagerPerson
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.utils.common import to_date_flexible
from fund_nav_mcp.utils.enums import AbnormalType, ShareClass


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
        _CODE_RESOLVE_MAP: code 字段到 (目标 id 字段, 参照 ORM 模型, 参照表查询列) 的映射。
        _NAME_RESOLVE_MAP: 名称字段到 (对应 code 字段, 目标 id 字段, 参照 ORM 模型, 参照表名称列) 的映射。
        _OWN_CODE_FIELDS: 每个 ORM 模型自身的 code 字段集合，这些字段不会被当作外键处理。
        _NAME_FIELDS: 所有名称中间字段的集合，这些字段仅用于解析，不应持久化到数据库。
        _AUTO_CREATE_MODELS: FK 解析失败时自动创建占位记录的参照模型集合。
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

    # FK 解析失败时自动创建占位记录的参照模型集合
    _AUTO_CREATE_MODELS: Set[Type[Base]] = {Fund}

    # ORM 自动管理的列，透传和占位构造时需跳过
    _AUTO_MANAGED_COLUMNS: Set[str] = {"id", "created_at", "updated_at"}

    # fund_code 份额后缀检测：S12345A → base=S12345, share_class=A
    _SHARE_CLASS_SUFFIX_PATTERN: re.Pattern = re.compile(r'^(.+?)([A-Ea-e])$')
    _SHARE_CLASS_SUFFIX_MAP: Dict[str, ShareClass] = {
        "A": ShareClass.A, "B": ShareClass.B, "C": ShareClass.C,
        "D": ShareClass.D, "E": ShareClass.E,
    }
    # fund_name 份额后缀剥离/提取：某某稳健A类 → (某某稳健, A)
    _SHARE_CLASS_NAME_PATTERN: re.Pattern = re.compile(
        r'^(.+?)([A-Ea-e])(类(份额)?|份额)?$'
    )

    _DATE_FIELDS: set = {
        "establishment_date", "registration_date", "nav_date", "calculation_date",
        "report_date", "amac_registration_date", "birth_date"
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

    @classmethod
    def _ref_passthrough_columns(cls, ref_model: Type[Base], lookup_col: str) -> Set[str]:
        """
        从 ``ref_model`` 的 ORM 列推导可透传的字段集合。

        排除主键、自动管理列、lookup_col，以及属于其他 code→id 映射目标的列。
        """
        pk_cols = {c.name for c in ref_model.__table__.primary_key.columns}
        id_target_cols = {
            id_field
            for code_field, (id_field, m, _) in cls._CODE_RESOLVE_MAP.items()
            if m is ref_model and code_field != lookup_col
        }
        return {
            c.name for c in ref_model.__table__.columns.values()
            if c.name not in pk_cols
               and c.name not in cls._AUTO_MANAGED_COLUMNS
               and c.name != lookup_col
               and c.name not in id_target_cols
        }

    @classmethod
    def _parse_fund_code_for_share_class(cls, fund_code: str) -> Tuple[str, Optional[ShareClass]]:
        """从 fund_code 中提取基码和份额类别。

        S12345A → (S12345, ShareClass.A)
        S12345  → (S12345, None)
        """
        m = cls._SHARE_CLASS_SUFFIX_PATTERN.match(fund_code.strip())
        if not m:
            return fund_code, None
        base = m.group(1)
        suffix = m.group(2).upper()
        return base, cls._SHARE_CLASS_SUFFIX_MAP.get(suffix)

    @classmethod
    def _strip_share_class_from_name(cls, fund_name: str) -> str:
        """从基金名称中剥离份额类别后缀。

        某某A类 → 某某
        某某A份额 → 某某
        某某A → 某某
        """
        m = cls._SHARE_CLASS_NAME_PATTERN.match(fund_name.strip())
        if m:
            return m.group(1).strip()
        return fund_name.strip()

    @classmethod
    def _parse_fund_name_for_share_class(cls, fund_name: str) -> Tuple[str, Optional[ShareClass]]:
        """从基金名称中提取基名和份额类别。

        某某稳健A类 → (某某稳健, ShareClass.A)
        某某稳健A份额 → (某某稳健, ShareClass.A)
        某某稳健A → (某某稳健, ShareClass.A)
        某某稳健 → (某某稳健, None)
        """
        if not fund_name:
            return fund_name, None
        m = cls._SHARE_CLASS_NAME_PATTERN.match(fund_name.strip())
        if not m:
            return fund_name.strip(), None
        base_name = m.group(1).strip()
        suffix_letter = m.group(2).upper()
        return base_name, cls._SHARE_CLASS_SUFFIX_MAP.get(suffix_letter)

    @classmethod
    def _normalize_fund_codes(cls, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """写入前预处理：当 fund_code 无份额后缀但 fund_name 携带份额类别时，自动补齐 code。

        场景：fund_code="000001", fund_name="某某稳健B类" → fund_code 补齐为 "000001B"。
        这样每条记录在后续 FK 解析阶段拥有唯一 code，避免多条不同份额的记录
        被错误映射到第一个自动创建的占位子基金上。
        """
        for d in data_list:
            code = d.get("fund_code")
            name = d.get("fund_name")
            if not isinstance(code, str) or not isinstance(name, str):
                continue
            base_code, code_sc = cls._parse_fund_code_for_share_class(code.strip())
            if code_sc is not None:
                continue
            _, name_sc = cls._parse_fund_name_for_share_class(name.strip())
            if name_sc is None:
                continue
            d["fund_code"] = f"{code.strip()}{name_sc.name}"
            if "share_class" in d and d.get("share_class") in (None, ShareClass.NotApplicable):
                d["share_class"] = name_sc
        return data_list

    @classmethod
    def _build_placeholder(
            cls, ref_model: Type[Base], lookup_col: str, code_val: str, extras: Dict[str, Any],
    ) -> Base:
        """用内省构建占位记录：无默认值的列用类型感知兜底值填充，extras 覆盖。"""
        kwargs: Dict[str, Any] = {lookup_col: code_val}

        for c in ref_model.__table__.columns.values():
            cn = c.name
            if cn in kwargs or cn in extras or cn in cls._AUTO_MANAGED_COLUMNS:
                continue
            if c.server_default is not None or c.primary_key:
                continue
            col_type = getattr(c.type, 'impl', c.type)
            if cn == f"{ref_model.__tablename__}_name" and isinstance(col_type, String):
                kwargs[cn] = f"未知{ref_model.__tablename__}-{code_val}"
            elif isinstance(col_type, Date):
                kwargs[cn] = date.today()
            elif isinstance(col_type, (Integer, DECIMAL)):
                kwargs[cn] = 0
            else:
                kwargs[cn] = None

        kwargs["abnormal"] = AbnormalType.Placeholder
        kwargs.update(extras)
        return ref_model(**kwargs)

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
               若某个 code 在数据库中找不到：_AUTO_CREATE_MODELS 中的模型自动创建占位记录，其余抛出 ValueError。
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

            # 若参照模型支持自动创建且 code 不存在，构建占位记录
            if model in self._AUTO_CREATE_MODELS and codes:
                cache = code_cache[code_field]
                missing = [c for c in codes if c not in cache]
                if missing:
                    passthrough = self._ref_passthrough_columns(model, lookup_col)
                    for mc in missing:
                        # 可能已被前面迭代（如父基金创建时）加入缓存，跳过避免重复插入
                        if mc in cache:
                            continue
                        # 从请求数据中提取该参照模型的透传字段
                        extras: Dict[str, Any] = {}
                        for d in data_list:
                            if d.get(code_field, "").strip() == mc:
                                for fn in passthrough:
                                    if fn in d and d[fn] is not None and fn not in extras:
                                        extras[fn] = d[fn]
                        # 日期字段统一转换
                        for date_fn in self._DATE_FIELDS & passthrough:
                            if date_fn in extras:
                                extras[date_fn] = to_date_flexible(extras[date_fn])
                        # 检测 fund_code 中的份额后缀，自动创建父子关系
                        if model is Fund:
                            base_code, code_sc = self._parse_fund_code_for_share_class(mc)
                            child_name: Optional[str] = extras.get("fund_name")

                            share_class = code_sc
                            if share_class is not None and child_name:
                                # code 有后缀但 name 没有 → 同步丰富 name
                                _, name_sc = self._parse_fund_name_for_share_class(child_name)
                                if name_sc is None:
                                    extras["fund_name"] = f"{child_name}{share_class.name}类"

                            if share_class is not None:
                                # 创建 / 定位父基金
                                if base_code not in cache:
                                    parent_extras: Dict[str, Any] = {}
                                    if child_name:
                                        parent_name = self._strip_share_class_from_name(child_name)
                                        if parent_name != child_name:
                                            parent_extras["fund_name"] = parent_name
                                        parent_extras.setdefault("share_class", ShareClass.NotApplicable)
                                    parent = self._build_placeholder(
                                        model, lookup_col, base_code, parent_extras,
                                    )
                                    await mgr.insert(parent)
                                    cache[base_code] = parent.id
                                else:
                                    if child_name:
                                        expected_parent_name = self._strip_share_class_from_name(child_name)
                                        parent_stmt = select(Fund.fund_name).where(
                                            Fund.id == cache[base_code],
                                        )
                                        parent_row = await mgr.fetch_one(parent_stmt)
                                        if parent_row and parent_row["fund_name"] != expected_parent_name:
                                            extras.setdefault("abnormal", AbnormalType.NameMismatch)

                                extras.setdefault("share_class", share_class)
                                extras.setdefault("parent_fund_id", cache[base_code])
                                if len(base_code) < 6:
                                    extras.setdefault("abnormal", AbnormalType.ShortBaseCode)

                        placeholder = self._build_placeholder(model, lookup_col, mc, extras)
                        await mgr.insert(placeholder)
                        cache[mc] = placeholder.id

        # 第三步：逐条数据处理
        strip = self._fk_code_fields(orm_model)
        # 非参照自身的模型需移除所有自动创建模型的透传字段
        for ref_model in self._AUTO_CREATE_MODELS:
            if orm_model is not ref_model:
                for _code_field, (_, m, _lookup) in self._CODE_RESOLVE_MAP.items():
                    if m is ref_model:
                        strip |= self._ref_passthrough_columns(ref_model, _lookup)
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

    def _conv_date_fields(self, data_list: List[dict]) -> List[dict]:
        """
        转换日期字段为数据库支持的格式。

        Args:
            data_list: 待处理的数据字典列表。

        Returns:
            处理后的数据字典列表，其中日期字段已转换为数据库支持的格式。
        """
        for row in data_list:
            for field, value in row.items():
                if field in self._DATE_FIELDS:
                    row[field] = to_date_flexible(value)
        return data_list
