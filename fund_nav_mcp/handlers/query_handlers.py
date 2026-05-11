from typing import Any, Dict, List, Type, Union, Tuple

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fund_nav_mcp.db.core import get_manager
from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.orm import (
    Fund,
    FundCategory,
    FundCategoryMapping,
    FundHolding,
    FundManager,
    FundManagerPerson,
    FundNav,
    FundReturn, Base,
)
from fund_nav_mcp.models.pydantic import BaseFilter, BaseSearchByFields, BaseSearchByKeyword
from fund_nav_mcp.models.schemas import PageData, PaginationParams
from fund_nav_mcp.utils.enums import Errcode


class ForeignKeyDisplayHandler:
    """
    外键显示处理类

    负责在分页查询后将数据中的外键 ID 列替换为关联对象的可读字段，
    并移除原始外键列，使 API 响应直接展示关联信息。
    """
    # 模型级外键映射配置：
    # { 主模型: { 外键字段名: (关联模型, [显示字段映射列表]) } }
    # 显示字段映射元素可为 str（同名字段）或 (源字段, 输出字段) 元组
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

    @staticmethod
    def _parse_field_mapping(mapping: Union[str, Tuple[str, str]]) -> Tuple[str, str]:
        """
        解析单个字段映射，统一为 (源属性路径, 输出字段名) 的元组

        Args:
            mapping: 字段映射，可以是字符串（同名字段）或 (源属性, 输出字段) 元组

        Returns:
            (source_attr, output_field) 元组
        """
        if isinstance(mapping, str):
            return mapping, mapping
        if isinstance(mapping, tuple) and len(mapping) == 2:
            return mapping
        raise ValueError(f"无效的字段映射: {mapping}")

    @classmethod
    def _prepare_field_mappings(cls, model: Type[Base]) -> Dict[str, Tuple[Type[Base], Tuple[str, str], List[str]]]:
        """
        解析指定模型的字段映射配置，返回：
        {外键字段名: (关联模型, 解析后的映射列表, 需要预加载的 relationship 名列表)}

        Args:
            model: 模型类，用于获取映射配置

        Returns:
            解析后的映射字典
        """
        raw = cls.FIELD_MAPPING_CONFIG.get(model, {})
        result = {}
        for fk_field, (related_model, raw_mappings) in raw.items():
            parsed = [cls._parse_field_mapping(m) for m in raw_mappings]
            # 收集点号路径第一段的 relationship 名称
            nested = list({src.split('.')[0] for src, _ in parsed if '.' in src})
            result[fk_field] = (related_model, parsed, nested)
        return result

    @staticmethod
    async def _fetch_related(
            items: List[Dict[str, Any]],
            mapping: Dict[str, Tuple[Type[Base], Tuple[str, str], List[str]]],
            db_name: str,
    ) -> Dict[str, Dict[int, Base]]:
        """
        批量查询外键关联对象，返回 {外键字段名: {ID: ORM对象}}。

        Args:
            items: 包含外键ID的字典列表。
            mapping: 外键字段名到 (关联模型, 解析后的映射列表, 需要预加载的 relationship 名列表) 的映射字典。
            db_name: 数据库连接名称。

        Returns:
            外键字段名到 {ID: ORM对象} 的缓存字典。
        """
        if not mapping:
            return {}

        mgr = (await get_manager("db", db_name))["mgr"]
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
            mapping: Dict[str, Tuple[Type[Base], Tuple[str, str], List[str]]],
            cache: Dict[str, Dict[int, Base]],
    ) -> List[Dict[str, Any]]:
        """
        替换外键ID为关联对象的显示字段，并删除原始外键列。

        Args:
            items: 包含外键ID的字典列表。
            mapping: 外键字段名到 (关联模型, 解析后的映射列表, 需要预加载的 relationship 名列表) 的映射字典。
            cache: 外键字段名到 {ID: ORM对象} 的缓存字典。

        Returns:
            替换后的字典列表。
        """
        if not mapping:
            return items

        converted = []
        for item in items:
            new_item = {}
            for key, value in item.items():
                # 如果该字段是外键且有映射，则展开关联对象字段
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
                        # 外键列本身不写入 new_item
                    continue  # 跳过原始外键列
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
        分页查询并将外键ID替换为可读字段，返回统一响应。

        Args:
            model: 要查询的模型类。
            params: 分页参数。
            filter_or_search: 过滤器或搜索参数，用于构建查询条件。
            db_name: 数据库名称。

        Returns:
            UtilResponse: 包含分页数据的统一响应。
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

        # 准备字段映射
        prepared_mapping = self._prepare_field_mappings(model)

        # 批量获取关联对象并应用映射
        cache = await self._fetch_related(page_data.items, prepared_mapping, db_name)
        mapped_items = self._apply_mapping(page_data.items, prepared_mapping, cache)

        final_page = PageData.create(mapped_items, params, page_data.pagination.total)
        return UtilResponse(code=Errcode.SUCCESS, message="成功", data=final_page)
