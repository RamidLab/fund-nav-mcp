from typing import Any, Dict, List, Optional, Type

from sqlalchemy import func, select, update

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.handlers.base_handlers import CodeResolveMixin
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import (
    Fund, FundManager, FundManagerPerson, FundCategory, FundCategoryMapping,
    FundNav, FundReturn, FundHolding,
)
from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.models.pydantic import BaseDeleteModel
from fund_nav_mcp.utils.enums import AbnormalType, Errcode


class DeleteHandler(CodeResolveMixin):
    """
    通用 ORM 模型删除处理器。

    支持通过多种方式定位待删除记录：
        1. record_id — 直接主键
        2. 自有编码字段（fund_code、category_code）— 唯一业务编码
        3. 额外编码字段（amac_registration_number、unified_code 等）
        4. 复合字段（fund_code + nav_date 等）— 联合唯一键
        5. 名称字段（fund_name、company_name 等）— 含同名检测

    名称查找时若匹配到多条记录，会列出所有候选项的编码与 ID，
    供调用方添加编码字段以消除歧义。
    """

    # 额外编码查找：ORM 模型 → [(pydantic 字段名, ORM 列属性)]
    _DELETE_EXTRA_CODE: Dict[Type[Base], list] = {
        FundManager: [
            ("amac_registration_number", FundManager.amac_registration_number),
            ("unified_code", FundManager.unified_code),
        ],
        FundManagerPerson: [
            ("qualification_number", FundManagerPerson.qualification_number),
        ],
    }

    # 名称查找：ORM 模型 → [(pydantic 字段名, ORM 名称列属性, ORM 编码列属性)]
    _DELETE_NAME_LOOKUP: Dict[Type[Base], list] = {
        Fund: [("fund_name", Fund.fund_name, Fund.fund_code)],
        FundManager: [("company_name", FundManager.company_name, FundManager.amac_registration_number)],
        FundManagerPerson: [("name", FundManagerPerson.name, FundManagerPerson.qualification_number)],
        FundCategory: [("category_name", FundCategory.category_name, FundCategory.category_code)],
    }

    async def _resolve_compound_target(
            self, orm_model: Type[Base], data_dict: Dict[str, Any], db_name: str,
    ) -> Optional[int]:
        """为需要通过复合外键定位的模型解析目标 ID。"""
        mgr = (await get_manager("db", db_name))["mgr"]

        if orm_model is FundCategoryMapping:
            fund_code = data_dict.get("fund_code")
            category_code = data_dict.get("category_code")
            if isinstance(fund_code, str) and isinstance(category_code, str):
                fund_code = fund_code.strip()
                category_code = category_code.strip()
                fk_data = [{"fund_code": fund_code, "category_code": category_code}]
                resolved = await self._resolve_fk_codes(orm_model, fk_data, db_name)
                fd = resolved[0]
                stmt = select(orm_model.id).where(
                    getattr(orm_model, "fund_id") == fd.get("fund_id"),
                    getattr(orm_model, "category_id") == fd.get("category_id"),
                )
                row = await mgr.fetch_one(stmt)
                if row is None:
                    raise ValueError(
                        f"未找到 fund_code='{fund_code}' 与 category_code='{category_code}' 的映射记录。"
                    )
                return row["id"]

        elif orm_model is FundNav:
            fund_code = data_dict.get("fund_code")
            nav_date = data_dict.get("nav_date")
            if isinstance(fund_code, str) and nav_date is not None:
                fund_code = fund_code.strip()
                fk_data = [{"fund_code": fund_code}]
                resolved = await self._resolve_fk_codes(FundNav, fk_data, db_name)
                fund_id = resolved[0].get("fund_id")
                stmt = select(orm_model.id).where(
                    getattr(orm_model, "fund_id") == fund_id,
                    getattr(orm_model, "nav_date") == nav_date,
                )
                row = await mgr.fetch_one(stmt)
                if row is None:
                    raise ValueError(
                        f"未找到 fund_code='{fund_code}' 且 nav_date={nav_date} 的净值记录。"
                    )
                return row["id"]

        elif orm_model is FundReturn:
            fund_code = data_dict.get("fund_code")
            period_type = data_dict.get("period_type")
            calculation_date = data_dict.get("calculation_date")
            if isinstance(fund_code, str) and period_type is not None and calculation_date is not None:
                fund_code = fund_code.strip()
                fk_data = [{"fund_code": fund_code}]
                resolved = await self._resolve_fk_codes(FundReturn, fk_data, db_name)
                fund_id = resolved[0].get("fund_id")
                stmt = select(FundReturn.id).where(  # type: ignore[reportArgumentType]
                    getattr(orm_model, "fund_id") == fund_id,
                    getattr(orm_model, "period_type") == period_type,
                    getattr(orm_model, "calculation_date") == calculation_date,
                )
                row = await mgr.fetch_one(stmt)
                if row is None:
                    raise ValueError(
                        f"未找到 fund_code='{fund_code}'、period_type={period_type} 且 "
                        f"calculation_date={calculation_date} 的收益率记录。"
                    )
                return row["id"]

        elif orm_model is FundHolding:
            fund_code = data_dict.get("fund_code")
            report_date = data_dict.get("report_date")
            stock_code = data_dict.get("stock_code")
            if isinstance(fund_code, str) and report_date is not None and isinstance(stock_code, str):
                fund_code = fund_code.strip()
                stock_code = stock_code.strip()
                fk_data = [{"fund_code": fund_code}]
                resolved = await self._resolve_fk_codes(FundHolding, fk_data, db_name)
                fund_id = resolved[0].get("fund_id")
                stmt = select(orm_model.id).where(
                    getattr(orm_model, "fund_id") == fund_id,
                    getattr(orm_model, "report_date") == report_date,
                    getattr(orm_model, "stock_code") == stock_code,
                )
                row = await mgr.fetch_one(stmt)
                if row is None:
                    raise ValueError(
                        f"未找到 fund_code='{fund_code}'、report_date={report_date} 且 "
                        f"stock_code='{stock_code}' 的持仓记录。"
                    )
                return row["id"]

        return None

    async def _resolve_delete_target(
            self, orm_model: Type[Base], record_id: Optional[int],
            data_dict: Dict[str, Any], db_name: str,
    ) -> int:
        """按优先级依次尝试各种定位方式，返回目标记录的主键 ID。"""
        mgr = (await get_manager("db", db_name))["mgr"]

        # ── 1. record_id ──
        if record_id is not None:
            stmt = select(orm_model.id).where(orm_model.id == record_id)
            row = await mgr.fetch_one(stmt)
            if row is None:
                raise ValueError(f"{orm_model.__tablename__} 表中未找到 id={record_id} 的记录。")
            return record_id

        # ── 2. 自有编码字段（fund_code、category_code）──
        own = self._OWN_CODE_FIELDS.get(orm_model, set())
        for code_field, (_, _model, lookup_col) in self._CODE_RESOLVE_MAP.items():
            if code_field not in own:
                continue
            cv = data_dict.get(code_field)
            if isinstance(cv, str):
                raw = {code_field: cv.strip()}
                return await self._resolve_record_id(orm_model, None, raw, db_name)

        # ── 3. 额外编码字段 ──
        extra_codes = self._DELETE_EXTRA_CODE.get(orm_model, [])
        for field_name, col_attr in extra_codes:
            cv = data_dict.get(field_name)
            if cv is None:
                continue
            value = cv.strip() if isinstance(cv, str) else cv
            stmt = select(orm_model.id, col_attr).where(col_attr == value)
            rows = await mgr.fetch_all(stmt)
            if not rows:
                raise ValueError(
                    f"{orm_model.__tablename__} 表中未找到 {field_name}='{value}' 的记录。"
                )
            if len(rows) > 1:
                candidates = ", ".join(
                    f"id={r['id']} ({field_name}={r[col_attr.name]})"
                    for r in rows
                )
                raise ValueError(
                    f"{field_name}='{value}' 匹配到 {len(rows)} 条记录，"
                    f"请使用 record_id 明确指定: {candidates}"
                )
            return rows[0]["id"]

        # ── 4. 复合字段查找 ──
        target_id = await self._resolve_compound_target(orm_model, data_dict, db_name)
        if target_id is not None:
            return target_id

        # ── 5. 名称字段（含同名检测）──
        name_lookups = self._DELETE_NAME_LOOKUP.get(orm_model, [])
        for field_name, col_attr, code_col in name_lookups:
            nv = data_dict.get(field_name)
            if not isinstance(nv, str):
                continue
            name = nv.strip()
            stmt = select(orm_model.id, col_attr, code_col).where(
                func.lower(col_attr) == name.lower()
            )

            # FundManagerPerson 支持通过 company_code 缩小名称查找范围
            if orm_model is FundManagerPerson:
                company_code = data_dict.get("company_code")
                if isinstance(company_code, str):
                    cc = company_code.strip()
                    company_stmt = select(FundManager.id).where(
                        FundManager.amac_registration_number == cc
                    )
                    company_row = await mgr.fetch_one(company_stmt)
                    if company_row is None:
                        raise ValueError(
                            f"未找到 company_code='{cc}' 的基金管理人（机构）记录，"
                            f"无法用于缩小 {field_name} 查找范围。"
                        )
                    stmt = stmt.where(FundManagerPerson.current_company_id == company_row["id"])

            rows = await mgr.fetch_all(stmt)
            if not rows:
                hint = ""
                if orm_model is FundManagerPerson and "company_code" in data_dict:
                    hint = "（已应用 company_code 筛选）"
                raise ValueError(
                    f"{orm_model.__tablename__} 表中未找到 {field_name}='{name}' 的记录。{hint}"
                )
            if len(rows) > 1:
                candidates = ", ".join(
                    f"{r[col_attr.name]} "
                    f"(code: {r[code_col.name] or 'N/A'}, id: {r['id']})"
                    for r in rows
                )
                raise ValueError(
                    f"{field_name}='{name}' 匹配到 {len(rows)} 条记录，"
                    f"请使用编码或 record_id 明确指定，或提供额外编码以缩小范围: "
                    f"{candidates}"
                )
            return rows[0]["id"]

        raise ValueError(
            f"无法定位 {orm_model.__tablename__} 记录：请提供 record_id、编码字段或名称字段。"
        )

    @staticmethod
    async def _mark_orphaned(
            orm_model: Type[Base], target_id: int, db_name: str,
    ) -> None:
        """将关联到此记录的从属记录标记为异常（关联记录已删除）。

        删除父记录前，找到所有引用它的子记录，标记 abnormal=Orphaned，
        不再级联删除关联数据。外键值保留，便于事后追溯。
        """
        mgr = (await get_manager("db", db_name))["mgr"]
        async with mgr.get_session() as session:
            if orm_model is Fund:
                for child_model, fk_col in [
                    (FundNav, FundNav.fund_id),
                    (FundReturn, FundReturn.fund_id),
                    (FundHolding, FundHolding.fund_id),
                    (FundCategoryMapping, FundCategoryMapping.fund_id),
                ]:
                    stmt = (
                        update(child_model)
                        .where(fk_col == target_id)
                        .values(abnormal=AbnormalType.Orphaned)
                    )
                    await session.execute(stmt)
            elif orm_model is FundManager:
                stmt = (
                    update(Fund)
                    .where(Fund.fund_manager_id == target_id)
                    .values(abnormal=AbnormalType.Orphaned)
                )
                await session.execute(stmt)
                stmt = (
                    update(FundManagerPerson)
                    .where(FundManagerPerson.current_company_id == target_id)
                    .values(abnormal=AbnormalType.Orphaned)
                )
                await session.execute(stmt)
            elif orm_model is FundCategory:
                stmt = (
                    update(FundCategoryMapping)
                    .where(FundCategoryMapping.category_id == target_id)
                    .values(abnormal=AbnormalType.Orphaned)
                )
                await session.execute(stmt)
            elif orm_model is FundManagerPerson:
                stmt = (
                    update(Fund)
                    .where(Fund.fund_manager_person_id == target_id)
                    .values(abnormal=AbnormalType.Orphaned)
                )
                await session.execute(stmt)
            await session.commit()

    async def handle(
            self, orm_model: Type[Base], data: BaseDeleteModel, db_name: str = "default",
    ) -> UtilResponse[dict[str, int]]:
        """
        删除单条 ORM 记录。

        定位优先级：
            1. record_id
            2. 自有编码字段（如 fund_code）
            3. 额外编码字段（如 amac_registration_number）
            4. 复合字段（如 fund_code + nav_date）
            5. 名称字段（如 fund_name），同名时报错并列出候选项

        Args:
            orm_model: 目标 ORM 模型类。
            data: Pydantic 删除模型，包含定位字段。
            db_name: 数据库配置名称，默认为 "default"。

        Returns:
            UtilResponse，包含已删除记录的 id。
        """
        data_dict = data.model_dump(exclude_none=True)
        record_id = data_dict.pop("record_id", None)

        target_id = await self._resolve_delete_target(orm_model, record_id, data_dict, db_name)

        # 不再级联删除关联数据，改为标记异常
        await self._mark_orphaned(orm_model, target_id, db_name)

        mgr = (await get_manager("db", db_name))["mgr"]
        await mgr.delete_by_id(orm_model, target_id)
        return UtilResponse(code=Errcode.SUCCESS, message="删除成功。", data={"id": target_id})

    async def handle_batch(
            self, orm_model: Type[Base], data_list: List[BaseDeleteModel], db_name: str = "default"
    ) -> UtilResponse[dict[str, Any]]:
        """
        批量删除 ORM 记录。

        每条数据使用与单条删除相同的定位逻辑（record_id / 编码 / 复合字段 / 名称），
        解析出目标 ID 后统一批量删除。重名检测等校验与单条删除行为一致。

        Args:
            orm_model: 目标 ORM 模型类。
            data_list: Pydantic 删除模型列表，每项包含定位字段。
            db_name: 数据库配置名称，默认为 "default"。

        Returns:
            UtilResponse，data 中包含已删除的 id 列表与总数量。
            若 data_list 为空，直接返回成功但 count 为 0。
        """
        if not data_list:
            return UtilResponse(code=Errcode.SUCCESS, message="没有需要删除的记录。", data={"count": 0})

        target_ids: List[int] = []
        for data in data_list:
            data_dict = data.model_dump(exclude_none=True)
            record_id = data_dict.pop("record_id", None)
            target_id = await self._resolve_delete_target(orm_model, record_id, data_dict, db_name)
            target_ids.append(target_id)

        unique_ids = list(dict.fromkeys(target_ids))

        # 不再级联删除关联数据，改为标记异常
        for tid in unique_ids:
            await self._mark_orphaned(orm_model, tid, db_name)

        mgr = (await get_manager("db", db_name))["mgr"]
        count = await mgr.delete_batch_by_ids(orm_model, unique_ids)
        return UtilResponse(
            code=Errcode.SUCCESS,
            message="批量删除成功。",
            data={"ids": unique_ids, "count": count},
        )
