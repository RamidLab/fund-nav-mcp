from typing import Any, Dict, List, Type, Union, Tuple

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fund_nav_mcp.db.core import get_manager, DBManager
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

    核心配置：
        类属性 FIELD_MAPPING_CONFIG 定义了各模型的外键映射规则。
        其结构为：{ 主模型类: { 外键字段名: (关联模型类, 字段映射列表) } }
        字段映射列表中的元素可以是：
            - 字符串：表示关联对象上的属性名，输出时使用相同字段名。
            - 二元组 (源属性路径, 输出字段名)：源属性路径支持点号访问嵌套关系
              （例如 'current_company.company_name'），对应的嵌套关系会在查询时
              通过 select in load 预加载，避免 N+1 查询问题。

    Attributes：
        FIELD_MAPPING_CONFIG: 模型级外键映射配置字典，详细格式见类说明。

    Usage：
        handler = ForeignKeyDisplayHandler()
        response = await handler.handle(Fund, pagination_params, filter_or_search, db_name)
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

    @staticmethod
    def _parse_field_mapping(mapping: Union[str, Tuple[str, str]]) -> Tuple[str, str]:
        """
        解析单个字段映射，统一为 (源属性路径, 输出字段名) 的元组。

        Args:
            mapping: 字段映射，可以是字符串（同名字段）或 (源属性, 输出字段) 元组。
                     源属性支持点号访问嵌套对象，如 'current_company.company_name'。

        Returns:
            (source_attr, output_field) 元组，分别表示源属性路径和输出字段名。

        Raises:
            ValueError: 如果 mapping 格式无效（既不是字符串也不是长度为2的元组）。
        """
        if isinstance(mapping, str):
            return mapping, mapping
        if isinstance(mapping, tuple) and len(mapping) == 2:
            return mapping
        raise ValueError(f"无效的字段映射: {mapping}")

    @classmethod
    def _prepare_field_mappings(cls, model: Type[Base]) -> Dict[
        str, Tuple[Type[Base], List[Tuple[str, str]], List[str]]]:
        """
        解析指定模型的字段映射配置，返回便于后续处理的结构。

        对 FIELD_MAPPING_CONFIG 中定义的原始配置进行解析，将字段映射统一为
        (源属性, 输出字段) 元组列表，并提取需要预加载的 relationship 名称。

        Args:
            model: 模型类，用于从 FIELD_MAPPING_CONFIG 中查找映射配置。

        Returns:
            解析后的映射字典，格式为：
            {外键字段名: (关联模型, 解析后的映射列表, 需要预加载的 relationship 名列表)}
            其中映射列表元素为 (源属性路径, 输出字段名) 元组。
        """
        raw = cls.FIELD_MAPPING_CONFIG.get(model, {})
        result: Dict[str, Tuple[Type[Base], List[Tuple[str, str]], List[str]]] = {}
        for fk_field, (related_model, raw_mappings) in raw.items():
            parsed = [cls._parse_field_mapping(m) for m in raw_mappings]
            # 收集点号路径第一段的 relationship 名称
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
        批量查询外键关联对象，返回 {外键字段名: {ID: ORM对象}} 的缓存字典。

        遍历 items 中所有不为空的外键 ID，构造 IN 查询，同时通过 select in load
        预加载 mapping 中声明的嵌套关系，避免后续属性访问产生额外查询。

        Args:
            items: 包含外键ID的字典列表（通常为分页查询结果）。
            mapping: 外键字段名到 (关联模型, 解析后的映射列表, 预加载关系列表) 的映射字典，
                     由 _prepare_field_mappings 生成。
            db_name: 数据库连接名称，用于获取对应的 DBManager。

        Returns:
            外键字段名到 {ID: ORM对象} 的缓存字典，方便按 ID 快速查找关联对象。
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
        替换外键ID为关联对象的显示字段，并删除原始外键列。

        遍历 items 中的每个字典，若某个键在外键映射 mapping 中，则根据缓存中的
        关联对象，将源属性路径的值写入对应的输出字段，同时移除原始外键键。

        Args:
            items: 包含外键ID的字典列表。
            mapping: 外键字段名到 (关联模型, 解析后的映射列表, 预加载关系列表) 的映射字典。
            cache: 外键字段名到 {ID: ORM对象} 的缓存字典，由 _fetch_related 生成。

        Returns:
            替换后的字典列表。每个字典中的外键列已被展开为可读字段，不再包含原始外键键。
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

        该方法整合了分页查询、外键关联预加载以及字段映射替换的全流程。
        支持通过过滤器或搜索参数构建查询条件，最终返回包含处理后数据的 UtilResponse。

        Args:
            model: 要查询的模型类（必须为 ORM 模型，且在 FIELD_MAPPING_CONFIG 中配置了映射）。
            params: 分页参数，包含页码和每页条数。
            filter_or_search: 过滤器或搜索参数，用于构建 WHERE 和 ORDER BY 条件；
                              可以是 BaseFilter、BaseSearchByKeyword、BaseSearchByFields 或 None。
            db_name: 数据库名称，用于获取对应的数据库连接管理器。

        Returns:
            UtilResponse: 统一响应对象，其中的 data 为 PageData，items 列表中的每条记录已
                          将外键 ID 替换为关联对象的可读字段。

        Raises:
            TypeError: 如果 filter_or_search 的类型不在支持范围内。
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
