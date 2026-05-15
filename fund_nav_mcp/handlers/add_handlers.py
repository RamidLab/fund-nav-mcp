from typing import List, Type

from pydantic import BaseModel

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

    async def handle(
            self, orm_model: Type[Base], data: BaseModel, db_name: str = "default",
    ) -> UtilResponse[dict[str, int]]:
        """
        添加单条 ORM 记录。

        Args:
            orm_model: 目标 ORM 模型类。
            data: 包含待添加字段的 Pydantic 创建模型。
            db_name: 数据库配置名称，默认为 "default"。

        Returns:
            UtilResponse，包含新记录的 id。
        """
        data_list = [data.model_dump()]
        # 1) 检查自身 code 唯一性
        await self._check_own_codes_unique(orm_model, data_list, db_name)
        # 2) 解析外键 code（由基类提供）
        data_list = await self._resolve_fk_codes(orm_model, data_list, db_name)
        # 3) 名称兜底解析（由基类提供）
        data_list = await self._resolve_names(data_list, db_name)
        # 4) 时间字段处理
        data_list = self._conv_date_fields(data_list)

        raw = data_list[0]
        mgr = (await get_manager("db", db_name))["mgr"]
        orm_instance = orm_model(**raw)
        await mgr.insert(orm_instance)
        return UtilResponse(code=Errcode.SUCCESS, message="添加成功", data={"id": orm_instance.id})

    async def handle_batch(
            self, orm_model: Type[Base], data_list: List[BaseModel], db_name: str = "default"
    ) -> UtilResponse[dict[str, list[int]]]:
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
        """
        raws = [d.model_dump() for d in data_list]
        # 1) 检查自身 code 唯一性
        await self._check_own_codes_unique(orm_model, raws, db_name)
        # 2) 解析外键 code（基类提供）
        raws = await self._resolve_fk_codes(orm_model, raws, db_name)
        # 3) 名称兜底解析（基类提供）
        raws = await self._resolve_names(raws, db_name)

        mgr = (await get_manager("db", db_name))["mgr"]
        orm_instances = [orm_model(**d) for d in raws]
        await mgr.insert_batch(orm_instances)
        ids = [obj.id for obj in orm_instances]
        return UtilResponse(code=Errcode.SUCCESS, message="批量添加成功", data={"ids": ids, "count": len(ids)})
