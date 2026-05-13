from typing import Any, Dict, List, Type, Union, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fund_nav_mcp.db.core import get_manager, DBManager
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import (
    Fund, FundCategory, FundCategoryMapping, FundHolding,
    FundManager, FundManagerPerson, FundNav, FundReturn, Base,
)
from fund_nav_mcp.models.pydantic import BaseFilter, BaseSearchByFields, BaseSearchByKeyword
from fund_nav_mcp.models.schemas import PageData, PaginationParams
from fund_nav_mcp.utils.enums import Errcode


class QueryHandler:
    """
    通用查询处理类

    负责分页查询、过滤、排序，并可选地将结果中的外键 ID 替换为关联对象的可读字段，
    使 API 响应直接呈现业务信息，避免暴露内部 ID。

    核心功能：
        1. 支持 BaseFilter / BaseSearchByKeyword / BaseSearchByFields 构建查询条件。
        2. 通过 PaginationParams 实现分页与排序。
        3. 根据字段映射配置，将外键 ID 转换为关联对象上的指定字段，
           支持嵌套关系预加载（select in load），避免 N+1 查询。

    配置方式：
        默认使用类属性 FIELD_MAPPING_CONFIG。实例化时也可通过参数 field_mapping
        动态覆盖，实现不同业务场景的复用。

    Usage:
        # 使用默认映射
        handler = QueryHandler()
        resp = await handler.handle(Fund, params, filter_, db_name)

        # 使用自定义映射
        custom_mapping = {...}
        handler = QueryHandler(field_mapping=custom_mapping)
    """

    # 模型级外键映射配置：
    # 结构：{ 主模型: { 外键字段名: (关联模型, [显示字段映射列表]) } }
    # 显示字段映射元素可为 str（同名字段）或 (源属性路径, 输出字段名) 元组
    FIELD_MAPPING_CONFIG: Dict[Type[Base], Dict[str, Tuple[Type[Base], List[Union[str, Tuple[str, str]]]]]] = {
        Fund: {
            # 基金管理公司（私募）
            'fund_manager_id': (FundManager, ['company_name', ('short_name', 'company_short_name')]),
            # 基金管理人（公募）
            'fund_manager_person_id': (
                FundManagerPerson,
                [
                    ('name', 'manager_person_name'),
                    ('current_company.company_name', 'manager_person_company_name'),
                    ('current_company.short_name', 'manager_person_company_short_name'),
                ],
            ),
        },
        FundNav: {
            'fund_id': (Fund, ['fund_name', 'fund_code']),
        },
        FundReturn: {
            'fund_id': (Fund, ['fund_name', 'fund_code']),
        },
        FundHolding: {
            'fund_id': (Fund, ['fund_name', 'fund_code']),
        },
        FundManagerPerson: {
            'current_company_id': (FundManager, ['company_name', ('short_name', 'company_short_name')]),
        },
        FundCategory: {
            'parent_id': (FundCategory, [('category_name', 'parent_category_name')]),
        },
        FundCategoryMapping: {
            'fund_id': (Fund, ['fund_name', 'fund_code']),
            'category_id': (FundCategory, ['category_name']),
        },
    }

    def __init__(
            self,
            field_mapping: Optional[
                Dict[Type[Base], Dict[str, Tuple[Type[Base], List[Union[str, Tuple[str, str]]]]]]
            ] = None,
    ):
        """
        初始化查询处理器。

        Args:
            field_mapping: 可选的外键映射配置，格式与 FIELD_MAPPING_CONFIG 相同。
                           若为 None，则使用类默认配置。
        """
        self.field_mapping = field_mapping or self.__class__.FIELD_MAPPING_CONFIG

    @staticmethod
    def _parse_field_mapping(mapping: Union[str, Tuple[str, str]]) -> Tuple[str, str]:
        """
        解析单个字段映射，统一为 (源属性路径, 输出字段名) 的元组。

        Args:
            mapping: 字段映射，可以是字符串（同名字段）或 (源属性, 输出字段) 元组。

        Returns:
            (source_attr, output_field) 元组，分别表示源属性路径和输出字段名。
        """
        if isinstance(mapping, str):
            return mapping, mapping
        if isinstance(mapping, tuple) and len(mapping) == 2:
            return mapping
        raise ValueError(f"无效的字段映射: {mapping}")

    @classmethod
    def _prepare_field_mappings(cls, model: Type[Base], config: Dict) -> Dict[
        str, Tuple[Type[Base], List[Tuple[str, str]], List[str]]]:
        """
        解析指定模型的字段映射配置。

        Args:
            model: ORM 模型类。
            config: 外键映射配置字典（完整，非仅当前模型）。

        Returns:
            该模型的解析后映射，便于后续批量查询和字段替换。
        """
        raw = config.get(model, {})
        result: Dict[str, Tuple[Type[Base], List[Tuple[str, str]], List[str]]] = {}
        for fk_field, (related_model, raw_mappings) in raw.items():
            parsed = [cls._parse_field_mapping(m) for m in raw_mappings]
            nested = list({src.split('.')[0] for src, _ in parsed if '.' in src})
            result[fk_field] = (related_model, parsed, nested)
        return result

    @staticmethod
    async def _fetch_related(
            items: List[Dict[str, Any]],
            mapping: Dict[str, Tuple[Type[Base], List[Tuple[str, str]], List[str]]],
            db_name: str,
    ) -> Dict[str, Dict[int, Base]]:
        """
        批量查询外键关联对象，返回 ID -> ORM 对象的缓存。

        Args:
            items: 结果字典列表。
            mapping: 当前模型的外键映射（已解析）。
            db_name: 数据库名称。

        Returns:
            外键字段名到 {ID: ORM对象} 的二级缓存。
        """
        if not mapping:
            return {}

        mgr: DBManager = (await get_manager("db", db_name))["mgr"]
        cache: Dict[str, Dict[int, Base]] = {}

        for fk_field, (related_model, _, nested_rels) in mapping.items():
            ids = {item[fk_field] for item in items if item.get(fk_field) is not None}
            if not ids:
                continue

            stmt = select(related_model)
            if nested_rels:
                options = [
                    selectinload(getattr(related_model, rel))
                    for rel in nested_rels
                    if hasattr(related_model, rel)
                ]
                stmt = stmt.options(*options)
            stmt = stmt.where(related_model.id.in_(ids))

            async with mgr.get_session() as session:
                rows = (await session.execute(stmt)).scalars().all()

            cache[fk_field] = {obj.id: obj for obj in rows}
        return cache

    @classmethod
    def _apply_mapping(
            cls,
            items: List[Dict[str, Any]],
            mapping: Dict[str, Tuple[Type[Base], List[Tuple[str, str]], List[str]]],
            cache: Dict[str, Dict[int, Base]],
    ) -> List[Dict[str, Any]]:
        """
        将 items 中的外键 ID 替换为关联对象的可读字段。

        Args:
            items: 原始结果列表。
            mapping: 已解析的外键映射。
            cache: 关联对象缓存。

        Returns:
            替换后的字典列表，外键列被移除。
        """
        if not mapping:
            return items

        converted = []
        for item in items:
            new_item = {}
            for key, value in item.items():
                if key in mapping:
                    ref_id = value
                    if ref_id is not None and key in cache:
                        obj = cache[key].get(ref_id)
                        if obj:
                            _, parsed_mappings, _ = mapping[key]
                            for src_path, out_field in parsed_mappings:
                                try:
                                    val = obj
                                    for attr in src_path.split('.'):
                                        val = getattr(val, attr)
                                    new_item[out_field] = val
                                except AttributeError:
                                    new_item[out_field] = None
                    # 不保留原始外键列
                    continue
                new_item[key] = value
            converted.append(new_item)
        return converted

    async def handle(
            self,
            model: Type[Base],
            params: PaginationParams,
            filter_or_search: Union[BaseFilter, BaseSearchByKeyword, BaseSearchByFields, None],
            db_name: str,
    ) -> UtilResponse:
        """
        执行分页查询并应用外键字段展开，返回统一响应。

        Args:
            model: 目标 ORM 模型类。
            params: 分页参数。
            filter_or_search: 过滤或搜索条件。
            db_name: 数据库配置名称。

        Returns:
            UtilResponse，data 为 PageData，其中 items 已展开外键字段。
        """
        mgr = (await get_manager("db", db_name))["mgr"]

        # 构建查询条件
        where = order_by = None
        if filter_or_search is not None:
            if isinstance(filter_or_search, BaseFilter):
                where = filter_or_search.to_where()
                order_by = filter_or_search.to_order_by()
            elif isinstance(filter_or_search, (BaseSearchByKeyword, BaseSearchByFields)):
                where = filter_or_search.to_where()
            else:
                raise TypeError(f"不支持的过滤器类型: {type(filter_or_search)}")

        # 分页查询
        page_data: PageData[Dict[str, Any]] = await mgr.paginate(model, params, where=where, order_by=order_by)

        # 准备字段映射（使用实例的 field_mapping 配置）
        prepared = self._prepare_field_mappings(model, self.field_mapping)

        # 批量获取关联对象并应用映射
        cache = await self._fetch_related(page_data.items, prepared, db_name)
        mapped_items = self._apply_mapping(page_data.items, prepared, cache)

        final_page = PageData.create(mapped_items, params, page_data.pagination.total)
        return UtilResponse(code=Errcode.SUCCESS, message="查询成功", data=final_page)
