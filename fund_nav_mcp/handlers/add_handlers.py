from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel
from sqlalchemy import func, select

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import Fund, FundCategory, FundManager, FundManagerPerson
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.utils.enums import Errcode


class AddHandler:
    """
    通用数据添加处理类

    负责将 Pydantic 创建模型转换为 ORM 实例并持久化到数据库。
    支持单条及批量添加，并内置了外键 code → id 解析和名称 → id 兜底解析逻辑。

    核心机制：
        1. 识别请求数据中的业务 code 字段（如 fund_code、manager_code 等），
           通过数据库查询将它们转换为对应的外键 ID，从而避免调用方直接接触内部 ID。
        2. 对于某些模型自身的 code 字段（如 Fund 的 fund_code），会进行唯一性校验，
           确保不会重复或与已有数据冲突。
        3. 如果没有提供 code，但提供了可读的名称字段（如 manager_name），
           则尝试通过名称去重匹配并回填对应的 ID，要求名称精确唯一。

    Attributes:
        _CODE_RESOLVE_MAP: 定义 code 字段到外键 ID 的映射规则。
        _NAME_RESOLVE_MAP: 定义名称字段兜底解析的映射规则。
        _OWN_CODE_FIELDS: 指定每个 ORM 模型自身的 code 字段集合。
        _NAME_FIELDS: 所有名称中间字段的集合。

    Note:
        本类中的“code”泛指业务上的唯一标识字符串，不限于数据库主键，例如基金代码、管理人登记编号等。
    """

    # code 字段 → (对应的 id 字段名, 参照的 ORM 模型, 用于查询的数据库列名)
    # 用于将前端的 code 字段转换为数据库中的外键 ID。
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

    # 名称字段 → (对应的 code 字段, 对应的 id 字段, 参照的 ORM 模型, 用于模糊查询的数据库名称列)
    # 当请求中没有提供 code 但提供了可读名称时，用于兜底解析并回填 ID。
    _NAME_RESOLVE_MAP: Dict[str, Tuple[str, str, Type[Base], str]] = {
        "manager_name": ("manager_code", "fund_manager_id", FundManager, "company_name"),
        "manager_person_name": (
            "manager_person_code", "fund_manager_person_id", FundManagerPerson, "name",
        ),
    }

    # 所有名称中间字段的集合，这些字段在解析完成后会被从数据中移除，
    # 因为它们不是 ORM 模型的直接属性。
    _NAME_FIELDS: set = set(_NAME_RESOLVE_MAP.keys())

    # 每个 ORM 模型自身的 code 字段，这些字段不会被当作外键解析，
    # 而是保留在数据中直接传给 ORM。同时，在创建记录前会检查这些 code 的唯一性。
    _OWN_CODE_FIELDS: Dict[Type[Base], set[str]] = {
        Fund: {"fund_code"},
        FundCategory: {"category_code"},
    }

    async def _check_own_codes_unique(
            self,
            orm_model: Type[Base],
            data_list: List[Dict[str, Any]],
            db_name: str,
    ) -> None:
        """
        检查 data_list 中属于 orm_model 自身的 code 是否在输入内重复或已在数据库中存在。

        遍历 _OWN_CODE_FIELDS 中定义的该模型的自有 code 字段，
        首先在传入的 data_list 中检测重复值，然后查询数据库确认是否已有相同 code 的记录。
        如发现冲突则抛出 ValueError。

        Args:
            orm_model: 目标 ORM 模型类。
            data_list: 待添加的数据字典列表，来源于 Pydantic 模型。
            db_name: 数据库连接名称。

        Raises:
            ValueError: 当检测到 code 在输入内重复或与数据库现有记录冲突时。
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

            # 检查输入中是否存在重复
            seen = set()
            dup = None
            for c in codes:
                if c in seen:
                    dup = c
                    break
                seen.add(c)
            if dup is not None:
                raise ValueError(
                    f"添加失败：{code_field}='{dup}' 在输入数据中重复。"
                )

            # 查询数据库中是否已存在这些 code
            stmt = select(model.id, getattr(model, lookup_col)).where(
                getattr(model, lookup_col).in_(codes)
            )
            rows = await mgr.fetch_all(stmt)
            if rows:
                existing = {r[lookup_col]: r["id"] for r in rows}
                conflicts = [
                    f"{code_field}='{c}' 已存在 (id={existing[c]})"
                    for c in codes if c in existing
                ]
                raise ValueError(
                    "添加失败：以下 code 已存在，请使用不同的 code。\n"
                    + "\n".join(conflicts)
                )

    def _fk_code_fields(self, orm_model: Type[Base]) -> set[str]:
        """
        返回对于给定 orm_model 需视为外键（需要解析并最终从数据中移除）的 code 字段集合。

        外键 code 字段指的是 _CODE_RESOLVE_MAP 中不属于该模型自身 code 的那些字段，
        这些字段仅用于解析对应的 ID，解析完成后会被删除，不会写入 ORM。

        Args:
            orm_model: 目标 ORM 模型类。

        Returns:
            外键 code 字段名的集合。
        """
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        return set(self._CODE_RESOLVE_MAP.keys()) - own

    async def _resolve_fk_codes(
            self,
            orm_model: Type[Base],
            data_list: List[Dict[str, Any]],
            db_name: str,
    ) -> List[Dict[str, Any]]:
        """
        批量将 data_list 中的外键 code 字段解析为对应的数据库 ID，自有 code 保留。

        对于每一条数据，将其中的外键 code（如 fund_code）通过数据库查询找到对应记录的 ID，
        并填充到对应的 id 字段（如 fund_id）。同时，将这些外键 code 字段从数据中删除。
        属于模型自身的 code（如 Fund.fund_code）不会被解析，而是原样保留。

        Args:
            orm_model: 目标 ORM 模型类。
            data_list: 待处理的原始数据字典列表。
            db_name: 数据库连接名称。

        Returns:
            解析后的数据字典列表，其中外键 code 字段已被移除，并添加了对应的 id 字段。

        Raises:
            ValueError: 若某个 code 在数据库中找不到对应记录。
        """
        if not data_list:
            return data_list

        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        mgr = (await get_manager("db", db_name))["mgr"]
        code_cache: Dict[str, Dict[str, int]] = {}

        # 按 code 字段分组批量查询
        for code_field, (id_field, model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field in own:
                continue
            # 收集所有需要解析且尚未提供 id 的 code 值
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

        # 需要从数据中剔除的外键 code 字段
        strip = self._fk_code_fields(orm_model)
        resolved_list: List[Dict[str, Any]] = []
        for d in data_list:
            resolved: Dict[str, Any] = {}
            for code_field, (id_field, model, _) in self._CODE_RESOLVE_MAP.items():
                if code_field in own:
                    continue
                code_val = d.get(code_field)
                # 仅当提供了 code 且未提供对应 id 时才进行解析
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
            data_list: List[Dict[str, Any]], db_name: str,
    ) -> List[Dict[str, Any]]:
        """
        批量将 data_list 中的名称字段兜底解析为对应的 ID 字段。

        当记录中没有提供外键 code 且未显式提供 id 时，尝试通过可读名称（如 manager_name）
        去数据库匹配。要求名称精确唯一，若匹配到多条或找不到则抛出异常。
        解析完成后，会从数据中移除所有名称中间字段。

        Args:
            data_list: 经过外键 code 解析后的数据字典列表。
            db_name: 数据库连接名称。

        Returns:
            解析并移除了名称中间字段后的数据字典列表。

        Raises:
            ValueError: 若名称找不到匹配记录或匹配到多条记录。
        """
        if not data_list:
            return data_list

        mgr = (await get_manager("db", db_name))["mgr"]
        for name_field, (code_field, id_field, model, name_col) in self._NAME_RESOLVE_MAP.items():
            # 收集需要解析的名称（没有 code 且没有 id）
            names: set[str] = set()
            for d in data_list:
                nv = d.get(name_field)
                if isinstance(nv, str) and not d.get(code_field) and not d.get(id_field):
                    s = nv.strip()
                    if s:
                        names.add(s)
            if not names:
                continue

            # 大小写不敏感精确匹配
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
                    # 列出所有候选项供调用方明确指定
                    candidates = ", ".join(
                        f"{r[name_col]} (code: {self._find_code_col(r)})"
                        for r in hits
                    )
                    raise ValueError(
                        f"名称 '{nv}' 匹配到 {len(hits)} 条记录，请使用 code 明确指定: "
                        f"{candidates}"
                    )
                d[id_field] = hits[0].id

        # 移除所有名称中间字段，因为这些字段不属于 ORM 属性
        return [{k: v for k, v in d.items() if k not in self._NAME_FIELDS} for d in data_list]

    @staticmethod
    def _find_code_col(row: Any) -> str:
        """
        从数据库查询返回的行对象中提取一个可识别的 code 字符串，用于错误提示。

        优先尝试 amac_registration_number，其次 qualification_number，
        都不存在时回退到记录 ID。

        Args:
            row: 查询结果行对象，具有列属性。

        Returns:
            代表该行的 code 字符串。
        """
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
        """
        合并解析后的 ID 字段与原始数据，并移除指定的中间字段。

        将 resolved 字典中的新 id 合并到 data 中，同时跳过 strip_fields 指定的字段。
        如果 data 中某字段已经有值且 resolved 中也有（例如同时提供了 id 和 code），
        则保留 data 中原有的值，不进行覆盖，以保证显式提供的 id 优先。

        Args:
            data: 原始数据字典。
            resolved: 由 code 解析出的 id 字典。
            strip_fields: 需要从结果中剔除的中间字段名集合。

        Returns:
            合并并清理后的数据字典。
        """
        out: Dict[str, Any] = {}
        for key, value in data.items():
            if key in strip_fields:
                continue
            # 如果该字段已被解析且原始值不是 None，则保留原始值（显式提供的 id 优先）
            if key in resolved and value is not None:
                continue
            out[key] = value
        out.update(resolved)
        return out

    async def handle(
            self,
            orm_model: Type[Base],
            data: BaseModel,
            db_name: str = "default",
    ) -> UtilResponse:
        """
        添加单条记录。

        完整流程：
        1. 检查数据中模型自身的 code 字段在输入及数据库中的唯一性。
        2. 解析传入的 FK code 字段，转换为对应的数据库 ID。
        3. 如果没有提供 code，则尝试通过名称进行兜底 ID 解析。
        4. 使用最终数据创建 ORM 对象并持久化到数据库。

        Args:
            orm_model: 目标 ORM 模型类。
            data: Pydantic 创建模型实例，包含待添加的字段。
            db_name: 数据库连接名称，默认为 "default"。

        Returns:
            UtilResponse 统一响应，data 中包含新记录的 ID。

        Raises:
            ValueError: 当 code 重复、无法解析或名称匹配失败时。
        """
        data_list = [data.model_dump()]
        await self._check_own_codes_unique(orm_model, data_list, db_name)
        data_list = await self._resolve_fk_codes(orm_model, data_list, db_name)
        data_list = await self._resolve_names(data_list, db_name)

        raw = data_list[0]
        mgr = (await get_manager("db", db_name))["mgr"]
        orm_instance = orm_model(**raw)
        await mgr.insert(orm_instance)
        return UtilResponse(code=Errcode.SUCCESS, message="添加成功", data={"id": orm_instance.id})

    async def handle_batch(
            self,
            orm_model: Type[Base],
            data_list: List[BaseModel],
            db_name: str = "default",
    ) -> UtilResponse:
        """
        批量添加记录。

        与单条添加流程相同，但对传入的整个列表统一进行 code 唯一性校验、
        外键 code 解析和名称解析，最后批量插入数据库。

        Args:
            orm_model: 目标 ORM 模型类。
            data_list: Pydantic 创建模型实例列表。
            db_name: 数据库连接名称，默认为 "default"。

        Returns:
            UtilResponse 统一响应，data 中包含新记录的 ID 列表和数量。

        Raises:
            ValueError: 当 code 重复、无法解析或名称匹配失败时。
        """
        raws = [d.model_dump() for d in data_list]
        await self._check_own_codes_unique(orm_model, raws, db_name)
        raws = await self._resolve_fk_codes(orm_model, raws, db_name)
        raws = await self._resolve_names(raws, db_name)

        mgr = (await get_manager("db", db_name))["mgr"]
        orm_instances = [orm_model(**d) for d in raws]
        await mgr.insert_batch(orm_instances)
        ids = [obj.id for obj in orm_instances]
        return UtilResponse(
            code=Errcode.SUCCESS, message="批量添加成功",
            data={"ids": ids, "count": len(ids)},
        )
