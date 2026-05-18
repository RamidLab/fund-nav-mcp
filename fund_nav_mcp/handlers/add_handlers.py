import re
from typing import Any, List, Type

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.handlers.base_handlers import CodeResolveMixin
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.utils.enums import Errcode


class AddHandler(CodeResolveMixin):
    """
    通用数据添加处理类

    负责将 Pydantic 创建模型转换为 ORM 实例并持久化到数据库。
    支持单条及批量添加，并直接复用 CodeResolveMixin 提供的外键 code → id 解析和名称 → id 兜底解析。

    核心机制：
        1. 识别请求数据中的业务 code 字段（如 fund_code、manager_code 等），
           通过基类方法将它们转换为对应的外键 ID。
        2. 对于某些模型自身的 code 字段（如 Fund 的 fund_code），会进行唯一性校验，
           确保不会重复或与已有数据冲突。
        3. 如果没有提供 code，但提供了可读的名称字段（如 manager_name），
           则通过基类方法进行名称匹配并回填对应的 ID，要求名称精确唯一。

    Note:
        本类中的“code”泛指业务上的唯一标识字符串，不限于数据库主键，例如基金代码、管理人登记编号等。
    """

    @classmethod
    def _get_column_labels(cls, orm_model: Type[Base]) -> dict[str, str]:
        """从 ORM 模型列的 comment 中提取 列名→中文标签 映射."""
        labels: dict[str, str] = {}
        for col in orm_model.__table__.columns.values():
            comment = (col.comment or "").strip()
            if not comment:
                continue
            # comment 可能附带补充说明，取第一个逗号/顿号前的部分作为短标签
            label = re.split(r"[，,]", comment)[0]
            labels[col.name] = label
        return labels

    @classmethod
    def _parse_constraint_columns(cls, e: IntegrityError) -> tuple[str | None, list[str]]:
        """从 IntegrityError 中提取表名和冲突列名列表."""
        orig = str(getattr(e, "orig", e))
        match = re.search(r"UNIQUE constraint failed:\s*(\S.*)", orig)
        if not match:
            return None, []
        cols_part = match.group(1)
        table: str | None = None
        cols: list[str] = []
        for seg in cols_part.split(","):
            seg = seg.strip()
            if "." in seg:
                t, c = seg.split(".", 1)
                if table is None:
                    table = t
                cols.append(c)
            else:
                cols.append(seg)
        return table, cols

    @classmethod
    def _format_integrity_error(
            cls, e: IntegrityError, raw: dict | None = None, orm_model: Type[Base] | None = None,
    ) -> str:
        """将 IntegrityError 转换为用户可读的中文消息."""
        _table, cols = cls._parse_constraint_columns(e)
        if not cols:
            return f"数据重复：{getattr(e, 'orig', e)}"
        labels = cls._get_column_labels(orm_model) if orm_model else {}
        parts: list[str] = []
        for c in cols:
            label = labels.get(c, c)
            if raw and c in raw and raw[c] is not None:
                parts.append(f"「{label}={raw[c]}」")
            else:
                parts.append(f"「{label}」")
        return f"数据重复：{', '.join(parts)} 的组合已存在，请勿重复添加"

    @classmethod
    def _extract_conflict_key(cls, e: IntegrityError, raw: dict) -> dict[str, str]:
        """从 IntegrityError 中提取冲突列名，从 raw 中取出对应值组成 key."""
        _table, cols = cls._parse_constraint_columns(e)
        key: dict[str, str] = {}
        for c in cols:
            if c in raw and raw[c] is not None:
                key[c] = str(raw[c])
        if not key:
            key = {
                k: str(v) for k, v in raw.items()
                if k.endswith(("_code", "_date")) and v is not None
            }
        return key

    async def handle(
            self, orm_model: Type[Base], data: BaseModel, db_name: str = "default",
    ) -> UtilResponse[dict[str, Any]]:
        """
        添加单条 ORM 记录。

        Args:
            orm_model: 目标 ORM 模型类。
            data: 包含待添加字段的 Pydantic 创建模型。
            db_name: 数据库配置名称，默认为 "default"。

        Returns:
            UtilResponse，包含新记录的 id。
        """
        raw = data.model_dump()

        # 1) 检查自身 code 唯一性
        try:
            await self._check_own_codes_unique(orm_model, [raw], db_name)
        except ValueError as e:
            return UtilResponse(
                code=Errcode.UNIQUE_CONFLICT, message=str(e), data={"id": None},
            )

        # 2) 解析外键 code（由基类提供）
        try:
            raw = (await self._resolve_fk_codes(orm_model, [raw], db_name))[0]
        except ValueError as e:
            return UtilResponse(
                code=Errcode.FAIL, message=str(e), data={"id": None},
            )

        # 3) 名称兜底解析（由基类提供）
        try:
            raw = (await self._resolve_names([raw], db_name))[0]
        except ValueError as e:
            return UtilResponse(
                code=Errcode.FAIL, message=str(e), data={"id": None},
            )

        # 4) 时间字段处理
        raw = self._conv_date_fields([raw])[0]

        # 5) 插入记录
        mgr = (await get_manager("db", db_name))["mgr"]
        try:
            orm_instance = orm_model(**raw)
            await mgr.insert(orm_instance)
            return UtilResponse(code=Errcode.SUCCESS, message="添加成功", data={"id": orm_instance.id})
        except IntegrityError as e:
            return UtilResponse(
                code=Errcode.UNIQUE_CONFLICT,
                message=self._format_integrity_error(e, raw, orm_model),
                data={"id": None, "conflict_key": self._extract_conflict_key(e, raw)},
            )
        except Exception as e:
            return UtilResponse(
                code=Errcode.FAIL, message=f"添加失败: {e}", data={"id": None},
            )

    async def handle_batch(
            self, orm_model: Type[Base], data_list: List[BaseModel], db_name: str = "default"
    ) -> UtilResponse[dict[str, Any]]:
        """
        批量添加记录，支持部分失败——单条异常不影响其他记录。

        Args:
            orm_model: 目标 ORM 模型类。
            data_list: Pydantic 创建模型实例列表。
            db_name: 数据库连接名称，默认为 "default"。

        Returns:
            UtilResponse，data 中包含成功数量、失败数量、成功 ID 列表和失败详情。
        """
        total = len(data_list)
        raws = [d.model_dump() for d in data_list]

        # 1) 检查自身 code 唯一性（整批共享，失败则整体退出）
        try:
            await self._check_own_codes_unique(orm_model, raws, db_name)
        except ValueError as e:
            return UtilResponse(
                code=Errcode.UNIQUE_CONFLICT, message=str(e),
                data={"success_count": 0, "fail_count": total, "ids": [],
                      "failures": [{"index": 0, "key": {}, "error": str(e)}]},
            )

        # 2) 解析外键 code（整批共享）
        try:
            raws = await self._resolve_fk_codes(orm_model, raws, db_name)
        except ValueError as e:
            return UtilResponse(
                code=Errcode.FAIL, message=str(e),
                data={"success_count": 0, "fail_count": total, "ids": [],
                      "failures": [{"index": 0, "key": {}, "error": str(e)}]},
            )

        # 3) 名称兜底解析（整批共享）
        try:
            raws = await self._resolve_names(raws, db_name)
        except ValueError as e:
            return UtilResponse(
                code=Errcode.FAIL, message=str(e),
                data={"success_count": 0, "fail_count": total, "ids": [],
                      "failures": [{"index": 0, "key": {}, "error": str(e)}]},
            )

        # 4) 时间字段处理
        raws = self._conv_date_fields(raws)

        # 5) 逐条插入，单条异常不影响其他记录
        mgr = (await get_manager("db", db_name))["mgr"]
        success_ids: list[int] = []
        failures: list[dict] = []

        for i, raw in enumerate(raws):
            try:
                instance = orm_model(**raw)
                await mgr.insert(instance)
                success_ids.append(instance.id)
            except IntegrityError as e:
                failures.append({
                    "index": i,
                    "key": self._extract_conflict_key(e, raw),
                    "error": self._format_integrity_error(e, raw, orm_model),
                })
            except Exception as e:
                key = {k: str(v) for k, v in raw.items() if k.endswith(("_code", "_date")) and v is not None}
                failures.append({"index": i, "key": key, "error": str(e)})

        sc, fc = len(success_ids), len(failures)
        if fc == 0:
            return UtilResponse(code=Errcode.SUCCESS, message="批量添加成功", data={
                "success_count": sc, "fail_count": 0, "ids": success_ids, "failures": [],
            })
        if sc == 0:
            return UtilResponse(code=Errcode.FAIL, message=f"全部{fc}条失败", data={
                "success_count": 0, "fail_count": fc, "ids": [], "failures": failures,
            })
        return UtilResponse(code=Errcode.SUCCESS, message=f"成功{sc}条，失败{fc}条", data={
            "success_count": sc, "fail_count": fc, "ids": success_ids, "failures": failures,
        })
