from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel
from sqlalchemy import select

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.handlers.base_handlers import CodeResolveMixin
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.utils.enums import Errcode


class UpdateHandler(CodeResolveMixin):
    """
    通用的 ORM 模型更新处理器。

    通过 `record_id`（主键）或模型的唯一业务编码字段定位记录，
    然后仅将更新 Pydantic 模型中非 None 的字段应用到数据库。
    外键编码 → id 以及名称 → id 的解析能力继承自 CodeResolveMixin。
    """

    async def _check_own_codes_unique_for_update(
            self,
            orm_model: Type[Base],
            target_id: int,
            update_fields: Dict[str, Any],
            db_name: str,
    ) -> None:
        """
        检查更新数据中的自有编码字段是否与其他记录冲突（排除当前记录）。

        参照 AddHandler._check_own_codes_unique，但将当前记录 ID 排除在外，
        允许将记录编码更新为与自身相同的值（幂等更新）。

        Args:
            orm_model: 目标 ORM 模型类。
            target_id: 当前待更新记录的主键 id。
            update_fields: 待更新的字段字典（已完成外键/名称解析）。
            db_name: 数据库配置名称。

        Raises:
            ValueError: 当编码与数据库中其他记录冲突时。
        """
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        if not own:
            return
        mgr = (await get_manager("db", db_name))["mgr"]

        for code_field, (_, model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field not in own:
                continue
            new_val = update_fields.get(code_field)
            if not isinstance(new_val, str):
                continue

            # 查询是否有其他记录已使用此编码
            stmt = select(model.id, getattr(model, lookup_col)).where(
                getattr(model, lookup_col) == new_val.strip(),
                model.id != target_id,
            )
            row = await mgr.fetch_one(stmt)
            if row:
                raise ValueError(
                    f"更新失败：{code_field}='{new_val}' 已被其他记录使用 (id={row['id']})。"
                )

    async def _resolve_record_id(
            self,
            orm_model: Type[Base],
            record_id: Optional[int],
            raw: Dict[str, Any],
            db_name: str,
    ) -> int:
        """
        解析待更新记录的主键 id。

        解析顺序：
        1. 直接使用 *record_id*。
        2. 使用 *raw* 中包含的自身编码字段（例如 ``fund_code``）。

        Args:
            orm_model: 目标 ORM 模型类。
            record_id: 主键 id，可直接指定。
            raw: 从请求数据中提取的字段字典（可能包含编码字段）。
            db_name: 数据库配置名称。

        Returns:
            解析出的整数主键 id。
        """
        if record_id is not None:
            mgr = (await get_manager("db", db_name))["mgr"]
            stmt = select(orm_model.id).where(orm_model.id == record_id)
            row = await mgr.fetch_one(stmt)
            if row is None:
                raise ValueError(f"{orm_model.__tablename__} 表中未找到 id={record_id} 的记录。")
            return record_id

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

    async def handle(
            self,
            orm_model: Type[Base],
            data: BaseModel,
            record_id: Optional[int],
            db_name: str = "default",
    ) -> UtilResponse:
        """
        更新单条 ORM 记录。

        Args:
            orm_model: 目标 ORM 模型类。
            data: 包含待应用字段的 Pydantic 更新模型。
            record_id: 主键定位；若未提供，则回退到模型的唯一编码字段（例如 fund_code）进行定位。
            db_name: 数据库配置名称。

        Returns:
            UtilResponse，包含更新后的记录 id。
        """
        raw = data.model_dump()

        # 若未提供 record_id，则从数据中提取自有编码字段用于定位
        # 若已提供 record_id，则自有编码字段保留在更新数据中，允许修改
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        identifying_codes: Dict[str, str] = {}
        if record_id is None:
            for cf in own:
                if isinstance(raw.get(cf), str):
                    identifying_codes[cf] = raw.pop(cf)

        # 解析主键 id
        lookup = {**raw, **identifying_codes}
        target_id = await self._resolve_record_id(orm_model, record_id, lookup, db_name)

        # 剔除值为 None 的字段 —— 只应用明确给出的值
        update_fields = {k: v for k, v in raw.items() if v is not None}
        if not update_fields:
            return UtilResponse(code=Errcode.SUCCESS, message="没有需要更新的字段。", data={"id": target_id})

        # 外键与名称解析
        resolved_list = await self._resolve_fk_codes(orm_model, [update_fields], db_name)
        resolved_list = await self._resolve_names(resolved_list, db_name)
        final = resolved_list[0]

        # 校验自有编码不与数据库中其他记录冲突
        await self._check_own_codes_unique_for_update(orm_model, target_id, final, db_name)

        final["updated_at"] = datetime.now()

        mgr = (await get_manager("db", db_name))["mgr"]
        instance = await mgr.update_by_id(orm_model, target_id, final)
        return UtilResponse(
            code=Errcode.SUCCESS, message="更新成功。", data={"id": instance.id}
        )

    async def handle_batch(
            self,
            orm_model: Type[Base],
            ids: List[int],
            data_list: List[BaseModel],
            db_name: str = "default",
    ) -> UtilResponse:
        """
        批量更新 ORM 记录。

        Args:
            orm_model: 目标 ORM 模型类。
            ids: 要更新的记录主键 id 列表。
            data_list: 与 ids 顺序对应的 Pydantic 更新模型列表。
            db_name: 数据库配置名称。

        Returns:
            UtilResponse，包含更新成功的 id 列表及数量。
        """
        if not data_list:
            return UtilResponse(code=Errcode.SUCCESS, message="没有需要更新的记录。", data={"count": 0})
        if len(ids) != len(data_list):
            raise ValueError(
                f"数量不匹配：{len(ids)} 个 ID 与 {len(data_list)} 条数据不一致。"
            )

        raws = [d.model_dump() for d in data_list]
        cleaned: List[Dict[str, Any]] = [
            {k: v for k, v in r.items() if v is not None} for r in raws
        ]

        # 外键与名称解析
        resolved = await self._resolve_fk_codes(orm_model, cleaned, db_name)
        resolved = await self._resolve_names(resolved, db_name)

        # 校验自有编码不与数据库中其他记录冲突
        for rid, fields in zip(ids, resolved):
            await self._check_own_codes_unique_for_update(orm_model, rid, fields, db_name)

        now = datetime.now()
        for fields in resolved:
            fields["updated_at"] = now

        mgr = (await get_manager("db", db_name))["mgr"]
        updated_ids = await mgr.update_batch_by_ids(orm_model, ids, resolved)

        return UtilResponse(
            code=Errcode.SUCCESS,
            message="批量更新成功。",
            data={"ids": updated_ids, "count": len(updated_ids)},
        )
