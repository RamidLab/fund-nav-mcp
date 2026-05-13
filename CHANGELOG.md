## [0.10.1] 2026-05-13

### Added

- **完整 ORM 模型测试套件**：新增 [`tests/test_orm_models.py`](tests/test_orm_fund.py) 测试文件，覆盖 `Fund`、`FundNav`、`FundReturn`、`FundHolding` 四张核心表的数据库层行为。
  - **表结构验证**：检查表的列完整性、索引存在性、外键约束目标及唯一约束（如 `fund_code` UNIQUE、基金+日期唯一等）。
  - **默认值测试**：验证 `share_class` 字段默认值为 `NotApplicable`。
  - **CRUD 操作**：
      - 最小字段插入、全字段插入、重复 code 唯一性冲突、更新、删除、按 code 查询、按份额类别筛选。
      - 可空字段接受 `None` 写入，超长字符串在严格数据库下的预期错误（`DataError`/`DBAPIError`）。
  - **关联表级联配置**：验证 `Fund.nav_records` 关系已配置 `delete` 级联。
  - **日期/数值范围查询**：净值按日期范围筛选、收益率按周期类型筛选、持仓按基金查询等场景。
  - **边界值测试**：持仓比例 0 和 1 的极端值写入。

  - **枚举全覆盖测试**：验证所有业务枚举值均可持久化到数据库：
      - `ShareClass`：公募 A/B/C/D/E 与私募 A/B/C/D/E 及 `NotApplicable` 写入。
      - `FundRegulatoryType`：公募、公募 REITs 及 9 种私募子类型写入。
      - `FundStatus`：所有状态值（Active / Suspended / Terminated 等）写入。
      - `FundNavStatus`：Valid / Estimated / Suspended / Missing 写入。
      - `FundDataSource`：Api / ManualImport / Calculated 等所有来源写入。
      - `PeriodType`（收益率周期）：Daily / Weekly / Monthly / Quarterly / Yearly 等全部写入。

## [0.10.0] 2026-05-13

### Added

- **通用数据添加处理器**：新增 [`handlers/add_handlers.py`](fund_nav_mcp/handlers/add_handlers.py) 中的 `AddHandler` 类，支持单条及批量记录添加。
  - 自动解析外键 `code` → `id`（如 `fund_code` → `fund_id`），调用方无需提供内部 ID。
  - 无 `code` 时支持名称字段兜底解析（如 `manager_name` → `manager_code` → `fund_manager_id`）。
  - 对模型自有 `code` 字段（如 `fund_code`）进行输入重复及数据库唯一性校验。
  - 提供 `handle` / `handle_batch` 方法，统一集成至现有数据库管理器。

- **MCP 添加工具集**：新增 [`tools/add_tools.py`](fund_nav_mcp/tools/add_tools.py)，为 `Fund`、`FundManager`、`FundManagerPerson`、`FundCategory`、`FundCategoryMapping`、`FundNav`、`FundReturn`、`FundHolding` 等 8 种实体生成添加工具。
  - 每个实体对应单条添加 `add_*` 和批量添加 `add_*s` 两个工具。
  - 所有工具均基于 `AddHandler` 实现，对外统一使用业务 `code` 字段。

- **数据库管理器批量插入能力**：在 [`db/core.py`](fund_nav_mcp/db/core.py) 的 `DBManager` 中新增：
  - `insert(obj: Base) -> Base`：插入单条 ORM 实例并刷新（获得自增 ID 等数据库生成值）。
  - `insert_batch(objs: List[Base]) -> List[Base]`：批量插入并逐个刷新实例。

- **份额类别模型及校验**：在 [`models/pydantic/fund.py`](fund_nav_mcp/models/pydantic/fund.py) 中增加：
  - `ShareClass` 枚举与 `ShareClassDescription` 描述类，支持按基金类型/监管类型返回份额类别详细说明。
  - `FundBase.share_class` 字段及 `share_class_description` 计算属性。
  - 根据监管类型（公募/私募）校验份额类别的合理性（如公募分级基金仅允许 A/B 类）。
  - `parent_fund_code` 字段，支持基金层级关系（母子基金）。

- **完整字段校验器**：为所有 Pydantic Create 模型添加字段级与模型级校验器：
  - 基金代码格式校验（公募 6 位数字，私募允许特定模式）。
  - 日期逻辑校验（成立日≤备案日，净值/计算/报告日期不晚于今日）。
  - 数值范围校验（单位净值>0，持仓比例 0~1，排名≤同类总数，实缴比例 0~100）。
  - 统一社会信用代码、中基协登记编号格式校验。
  - 名称字段自动去除首尾空白，空值统一处理为 `None`。

### Changed

- **外键字段改为业务 code**：将所有 Pydantic Create 模型中的外键 ID 字段（如 `fund_id`、`manager_id`）替换为对应的业务 code 字段（如 `fund_code`、`manager_code`），并增加名称字段（`manager_name`、`manager_person_name`）用于兜底解析。
  - 受影响的模型：[`FundCreate`、`FundNavCreate`、`FundReturnCreate`、`FundHoldingCreate`、`FundCategoryCreate`、`FundCategoryMappingCreate`、`FundManagerPersonCreate`](fund_nav_mcp/models/pydantic/fund.py)。
  - 响应模型（`*Response`）同时保留 ID 和 code 字段，并通过 `computed_field` 增加份额类别说明。
- **DBManager 扩展现有接口**：[`DBManager`](fund_nav_mcp/db/core.py) 新增 `insert`/`insert_batch` 提供更便捷的 ORM 持久化方式。

- **份额描述缓存优化**：[`ShareClassDescription._descriptions`](fund_nav_mcp/models/pydantic/fund.py) 中 使用 `@lru_cache` 确保全量定义仅构造一次，`get_description` 实现精确匹配 → 私募匹配 → 公募类型匹配 → 通用匹配的四级降级策略。

## [0.9.3] 2026-05-12

### Added

- **Fund ORM 模型字段增加**: 为 [`Fund`](fund_nav_mcp/models/orm/fund.py) ORM 模型增加 share_class 与 parent_fund_id 字段，分别用于表示基金的份额类和父基金 ID。

### Changed

- **完善处理类和工具方法注释**：完善 [`ForeignKeyDisplayHandler`](fund_nav_mcp/handlers/query_handlers.py) 类的注释，添加外键字段映射关系的说明。

## [0.9.2] 2026-05-11

### Added

- **外键显示处理**：新增 [`ForeignKeyDisplayHandler`](fund_nav_mcp/handlers/query_handlers.py) 类，实现配置化的外键字段自动替换。通过 `FIELD_MAPPING_CONFIG` 声明外键与目标显示字段的映射关系，分页查询后自动将外键 ID 替换为关联对象的可读字段，并移除原始外键列，使 API 响应更友好。

### Changed

- **查询工具统一重构**：所有 MCP 工具函数（基金/净值/收益等）不再独立调用 `_execute_paginated_query`，改为统一使用 `ForeignKeyDisplayHandler` 执行分页查询与外键展开。

### Removed

- 移除旧版 `_execute_paginated_query` 辅助函数及相关直接操作数据库管理器的代码，其职责已并入 `ForeignKeyDisplayHandler`。

## [0.9.1] 2026-05-11

### Changed

- **ORM 基类统一**：在 [`Base`](fund_nav_mcp/models/orm/base.py) 类集中定义 `id`、`created_at`、`updated_at` 公共字段。所有 ORM 模型（Fund、FundNav、FundReturn 等）均已切换为继承该 `Base`，并将项目中所有原有的独立 `DeclarativeBase` 引用替换为统一的 `Base`。

### Removed

- 移除各模型类中原有的 `id`、`created_at`、`updated_at` 字段重复声明。

## [0.9.0] 2026-05-10

### Added

- **新增实体筛选与搜索类**：为 `FundCategory`、`FundCategoryMapping`、`FundNav`、`FundReturn`、`FundHolding` 共 5 个模型新增对应的 `Filter` 和 `SearchByKeyword` / `SearchByFields` 类，实现全部主要实体的筛选与搜索能力覆盖。所有类均基于工厂函数自动生成，支持排序（`sort_by` / `sort_order`）和跨表关联过滤（如按父分类名称查分类、按基金代码查净值记录等）。

## [0.8.2] 2026-05-10

### Added

- **多操作符过滤支持**：新增 [`FilterField`](fund_nav_mcp/models/pydantic/__init__.py) 类型及 `ScalarValue`、`FilterValue` 联合类型，支持 `eq`/`ne`/`gt`/`gte`/`lt`/`lte`/`in`/`like`/`between` 九种比较操作符，取代此前单一的等值过滤，过滤能力大幅增强。
- **跨表关联列过滤**：`create_filter_class` 的 `column_mappings` 新增三元组形式 `(relation_attr, target_column, python_type)`，自动生成基于 `has()`/`any()` 的跨表过滤条件（例如通过基金查询管理人或分类名称）。
- **枚举类型推断增强**：`_safe_column_python_type` 引入 `_extract_py_type_from_annotation`，优先从 `Mapped[]` 注解中提取真实 Python 枚举类型，使生成的筛选字段直接使用枚举类而非 `int`。
- **`exclude_comparable_fields` 参数**：`create_filter_class` 新增该参数，允许指定部分字段不转换为 `FilterField` 而保留原始类型等值比较，满足特殊场景需求。

### Changed

- **筛选基类重构**：`BaseFilter` 移除 `_date_ranges` 与 `_add_date_range`，统一使用静态方法 `_build_condition` 根据 `FilterField` 生成 SQL 条件（日期区间改用 `between` 操作符实现），`to_where` 逻辑大幅简化。
- **搜索字段统一命名**：`SearchField.mode` 重命名为 `condition`，与 `FilterField` 命名风格一致；`BaseSearchByFields._like_or_eq`、`_relation_cond` 及所有生成方法同步使用 `field.condition`。
- **工厂函数接口升级**：
  - `create_filter_class`：移除 `date_range_mappings` 参数，日期/数值区间改为由 `column_mappings` 配置；新增 `exclude_comparable_fields`；`column_mappings` 支持关联列三元组。
  - `create_search_class`：统一使用 `model=` 关键字参数，移除部分冗余校验。
- **所有 Filter/Search 类重构**：`filter_classes.py` 与 `search_classes.py` 中的类全部改用新的工厂参数生成，增加 `sort_order` 字段，并对 `Fund`、`FundManager`、`FundManagerPerson` 的关系映射进行优化（如补充 `category_name` 搜索、调整经理名称映射）。
- **ORM 模型字段注释与时间戳完善**：
  - `FundCategoryMapping` 新增 `updated_at` 字段。
  - `FundNav`、`FundReturn`、`FundHolding` 的外键字段注释细化（如“基金产品ID，关联fund表的ID”），移除部分不必要的 `nullable=False` 约束。
  - 所有时间戳字段统一使用 `server_default=text("CURRENT_TIMESTAMP")`。

### Fixed

- **枚举解析安全性**：`_BaseIntEnum._resolver` 由直接构造 `cls(value)` 改为 `_value2member_map_.get(value, default)`，避免传入无效值时抛出异常。
- **字段搜索条件回退**：修复 `_relation_cond` 中 `field.mode` 引用错误（已改为 `field.condition`），确保字段级匹配模式可正确回退到全局 `match_mode`。

### Removed

- 移除 `BaseFilter._date_ranges` 属性及其配套的 `_add_date_range` 静态方法。
- 移除 `create_filter_class` 的 `date_range_mappings` 参数及相关的冲突检测逻辑。
- 删除旧版 Filter/Search 类中手动绑定的部分方法，全部逻辑已由工厂函数自动注入。

## [0.8.1] 2026-05-09

### Added

- **显式升降序选择**：在 [`BaseFilter`](fund_nav_mcp/models/pydantic/filter.py) 中新增 `sort_by` 字段，支持显式指定排序字段和方向。
- **枚举解析增强**：在 [`_BaseIntEnum`](fund_nav_mcp/utils/enums.py) 基类中新增 `_resolver` 方法，支持通过整数值、`label` 或大小写不敏感的名称查找枚举成员。`FundStatus` 等枚举的 `_missing_` 方法已采用该解析器，提高对字符串输入的兼容性。
- **列表筛选支持**：[`_execute_paginated_query`](fund_nav_mcp/tools/query_tools.py) 新增对 Filter 中 `*_list` 后缀字段的自动处理，字段值若为列表则生成 `IN` 查询条件，方便批量筛选。
- **字段冲突检测**：新增 [`_check_field_conflicts`](fund_nav_mcp/models/pydantic/builder.py)，自动检测 Filter/Search 生成时的字段名冲突，并支持 `suppress_warnings` 参数控制警告输出。

### Changed

- **工厂重命名与增强**：`create_search_classes` 更名为 `create_search_class`（返回值不变）；`create_filter_class` 和 `create_search_class` 均增加 `suppress_warnings` 参数，方便调用方按需静默冲突警告。

## [0.8.0] 2026-05-09

### Added

- **模型工厂**：新增 [`builder.py`](fund_nav_mcp/models/pydantic/builder.py) 模块，提供 `create_filter_class` 与 `create_search_class` 两个动态模型工厂函数，以及配套的列选择、类型推断、抽象方法清理等内部辅助函数。从此可根据 ORM 模型一键生成完整的 Filter / Search 类，无需手写任何字段或查询方法。

### Changed

- **Filter / Search 全面工厂化**：所有实体（Fund、FundManager、FundManagerPerson）的筛选和搜索类全部改为调用工厂生成，支持通过 `include` / `exclude` / `date_range_mappings` / `relation_mappings` 等参数灵活配置，字段类型自动推断，调用侧代码量减少超过 60%。

### Fixed

- **关系搜索修正**：修复在关键词搜索和字段搜索中，当关系为一对多（集合）时错误使用 `has()` 导致的运行时异常。现在工厂内部根据 `uselist` 自动选用 `any()`，确保搜索功能正常。

### Removed

- 移除了手写的 `FundFilter`、`FundManagerFilter`、`FundManagerPersonFilter` 类定义。
- 移除了手写的 `FundSearchByKeyword`、`FundSearchByFields`、`FundManagerSearchByKeyword`、`FundManagerSearchByFields`、`FundManagerPersonSearchByKeyword`、`FundManagerPersonSearchByFields` 类定义。
- 以上手写类中的 `to_where`、`to_order_by`、`_or_conditions`、`_column_mappings`、`_relation_mappings` 等方法全部删除，相应逻辑已由工厂自动注入。

## [0.7.0] - 2026-05-08

### Added

- **基金经理/投资经理查询维度**：
  - 新增 [`FundManagerPersonFilter`](fund_nav_mcp/models/pydantic/filter.py) 筛选模型，支持性别、学历、从业资格、出生日期区间、所属公司等精确筛选及排序。
  - 新增 [`FundManagerPersonSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 关键词搜索模型，一键搜索姓名、学历、资格证号、履历及关联公司名称。
  - 新增 [`FundManagerPersonSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 高级字段搜索模型，支持字段级精确/模糊控制与 AND/OR 切换。
  - 新增 [`get_fund_manager_person_list`](fund_nav_mcp/tools/query_tools.py)、[`search_persons_by_keyword`](fund_nav_mcp/tools/query_tools.py)、[`search_persons_by_fields`](fund_nav_mcp/tools/query_tools.py) 三个工具，覆盖基金经理个人维度的列表、关键词搜索及高级组合搜索。

- **通用查询辅助函数**：
  - 新增 `_execute_paginated_query` 内部函数，统一处理筛选、搜索模型的分页查询逻辑，消除工具函数间的重复代码。

### Changed

- **查询体系全面重构**：
  - 抽象基类 [`BaseFilter`](fund_nav_mcp/models/pydantic/__init__.py) 的 `to_where` 与 `to_order_by` 改为无参方法，由子类声明 `_filter_mappings`（字段→列映射）与 `_date_ranges`（日期区间映射）自动生成条件。
  - 所有筛选子类（`FundFilter`、`FundManagerFilter`、`FundManagerPersonFilter`）移除了手写的查询生成代码，仅保留字段定义与映射属性，极简化子类实现。
  - 抽象基类 [`BaseSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 与 [`BaseSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 引入，彻底消除基金、管理人、经理人员搜索模型间的重复逻辑，使新实体扩展仅需定义 OR 条件或字段映射。
  - 工具层通过 `_execute_paginated_query` 实现统一调用，每个工具函数降为一行核心业务调用，维护性显著提升。

## [0.6.0] - 2026-05-08

### Added

- **管理人筛选与搜索**：
  - 新增 [`FundManagerFilter`](fund_nav_mcp/models/pydantic/filter.py) 筛选模型，支持规模区间、会员状态、登记日期区间及排序。
  - 新增 [`FundManagerSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 关键词搜索模型，一键搜索公司全称、简称、统一代码、登记编号等文本字段。
  - 新增 [`FundManagerSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 高级字段搜索模型，支持字段级精确/模糊控制和 AND/OR 切换。
  - 新增 [`get_manager_list`](fund_nav_mcp/tools/query_tools.py)、[`search_managers_by_keyword`](fund_nav_mcp/tools/query_tools.py)、[`search_managers_by_fields`](fund_nav_mcp/tools/query_tools.py) 三个工具，提供管理人维度的查询能力。

### Changed

- **模型字段优化**：将 `FundManager.management_scale_range` 字段类型从普通字符串改为 `ManagementScaleRange` 枚举，增强数据约束与语义。

## [0.5.1] - 2026-05-08

### Changed

- **搜索模型重构**：
  - 抽取 [`BaseSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 和 [`BaseSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 抽象基类，统一关键词搜索和字段搜索的核心逻辑。
  - [`FundSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 和 [`FundSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 重构为继承基类，代码量大幅减少。
  - [`FundManagerSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 和 [`FundManagerSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 基于基类实现，补全管理人维度的搜索功能。
  - 所有子类仅需定义字段映射或 OR 条件列表，消除重复的 `_like_or_eq`、`_relation_cond` 和 `to_where` 实现。

## [0.5.0] - 2026-05-08

### Added

- **基金筛选与搜索模型分离**：
  - 新增 [`FundFilter`](fund_nav_mcp/models/pydantic/filter.py) 筛选模型，支持基金类型、监管类型、状态、日期区间等精确过滤及自定义排序。
  - 新增 [`FundSearchByKeyword`](fund_nav_mcp/models/pydantic/search.py) 关键词搜索模型，一键 OR 搜索基金代码、名称、托管人、管理人、经理。
  - 新增 [`FundSearchByFields`](fund_nav_mcp/models/pydantic/search.py) 字段组合搜索模型，支持 AND/OR 逻辑切换、全局及字段级精确/模糊匹配。
  - 新增 [`SearchField`](fund_nav_mcp/models/pydantic/search.py) 通用搜索字段，允许客户端传入简写字符串（默认模糊）或完整对象（自定义模式）。
- **基金列表工具**：
  - [`get_fund_list`](fund_nav_mcp/tools/query_tools.py) 作为筛选工具，配合 `FundFilter` 使用。
  - [`search_funds_by_keyword`](fund_nav_mcp/tools/query_tools.py) 和 [`search_funds_by_fields`](fund_nav_mcp/tools/query_tools.py) 分别处理关键词与高级组合搜索。

### Changed

- **数据库管理器增强**：`get_manager` 内建连接与健康检查，确保返回的管理器始终可用，工具层不再做重复检查。
- **Fund 模型精简**：移除冗余字段，保持模型简洁。

## [0.4.0] - 2026-05-08

### Added

- **分页模型与通用查询**：
  - 新增 [`PaginationParams`](fund_nav_mcp/models/schemas.py)、[`PaginationMetadata`](fund_nav_mcp/models/schemas.py)、[`PageData`](fund_nav_mcp/models/schemas.py) 分页模型，支持请求参数校验、响应元数据自动计算及便捷构造方法。
  - [`DBManager`](fund_nav_mcp/db/core.py) 新增 `paginate` 通用分页查询方法，与分页模型、过滤条件及排序无缝集成，支持 PostgreSQL、MySQL 及 SQLite 多种数据库。
- **基金过滤器**：
  - 新增 [`FundFilter`](fund_nav_mcp/models/pydantic/filter.py) 过滤器，支持按基金代码、名称、类型、状态、管理人等条件筛选，包含日期区间及自定义排序。

### Changed

- **基金模型优化**：
  - 精简 [`Fund`](fund_nav_mcp/models/orm/fund.py) 模型字段，移除冗余、未使用的属性，保持模型简洁清晰。

## [0.3.1] - 2026-05-07

### Changed

- **数据库/缓存管理器获取异步化**：
  - 将 [`get_manager`](fund_nav_mcp/db/core.py) 由同步函数改为 `async def`，在创建 `InfluxDBManager` 或 `DBManager` 实例后立即执行 `await manager.connect()`，确保调用方获取到的管理器已完成连接初始化，避免后续手动调用 `connect` 的遗漏风险。
  - 该改动为破坏性变更，所有 `get_manager` 调用处改为 `await get_manager(...)` 以适应异步上下文。
- **配置删除接口优化**：
  - 重命名 `get_config_path` 为 `get_toml_config`，更清晰地表达获取 TOML 配置路径的用途。
  - 重构 [`_delete_config`](fund_nav_mcp/config.py) 方法，参数从 `(name, config)` 改为 `(_class, name)`，直接通过 `_class` 文本区分 `"db"` 或 `"cache"`，不再依赖传入完整配置对象推断类型。
  - 相应地，[`delete_database`](fund_nav_mcp/config.py) 和 [`delete_cache`](fund_nav_mcp/config.py) 公共方法移除多余的 `db_config` / `cache_config` 参数，仅保留名称参数，简化了 MCP 工具调用时的传参要求。

## [0.3.0] - 2026-05-07

### Added

- **Mock 数据生成器**：
  - 新增 [`mock_fund_data.py`](mock/mock_fund_data.py)，支持全量异步生成与批量插入8张核心业务表（基金管理人、经理、分类、基金、净值、收益率、持仓、映射）。
  - 同时支持 PostgreSQL、MySQL、InfluxDB 三种数据库，自动处理外键依赖和数据类型转换。

### Changed

- **数据库配置模型优化**：
  - [`SQLiteConfig`](fund_nav_mcp/models/schemas.py) 文件路径统一收敛至 `.cache/sqlite/` 子目录，避免项目根目录散落 db 文件。
  - [`MySQLConfig`](fund_nav_mcp/models/schemas.py)、[`PostgresqlConfig`](fund_nav_mcp/models/schemas.py)、[`InfluxDBConfig`](fund_nav_mcp/models/schemas.py) 的 `db_main` 字段改为必填并提供默认值 `"fund_nav_mcp"`，防止遗漏数据库名导致运行时错误。

## [0.2.0] - 2026-05-06

### Added

- **日志配置优化**：
  - 支持使用 [`log_libraries.json`](configs/log_libraries.json) 配置文件统一静默第三方库日志（如 asyncio、faker）
  - 新增应用方法 [`_apply_library_log_levels`](fund_nav_mcp/utils/log.py)，用于在应用中统一日志记录。
- **数据库层完整实现**：
  - 基于 SQLAlchemy 的异步 ORM 模型（基金、净值、持仓、基金经理等表，见 [`models/orm/fund.py`](fund_nav_mcp/models/orm/fund.py)、[`models/orm/manager.py`](fund_nav_mcp/models/orm/manager.py)、[`models/orm/category.py`](fund_nav_mcp/models/orm/category.py)）。
  - Pydantic API 模型，用于请求/响应校验（见 [`models/pydantic/fund.py`](fund_nav_mcp/models/pydantic/fund.py)）。
  - [`DBManager`](fund_nav_mcp/db/core.py)：异步连接池、事务、CRUD 及健康检查。
  - [`InfluxDBManager`](fund_nav_mcp/db/core.py)：时序数据库支持（同步 API + 线程池，规避官方异步 bug）。
  - 完整测试覆盖，包含关系型数据库与时序数据库的 CRUD 及并发场景，测试文件 [`tests/test_rdbms_db.py`](tests/test_rdbms_db.py)、[`tests/test_timeseries_db.py`](tests/test_timeseries_db.py)。

### Changed

- **数据库管理器缓存与接口重构**：
  - [`get_manager`](fund_nav_mcp/db/core.py) 增加 `_class` 参数（`"db"` / `"cache"`），引入按类别隔离的多级缓存，实现同一数据库实例在全局范围内的单例模式，避免连接池重复创建。
  - 使用 `dict.setdefault` 自动构建二级缓存结构，无需显式初始化，简化缓存管理逻辑。
  - 返回类型从直接实例更改为 `Dict[str, Any]`（包含 `mgr` 和 `db_type` 键），统一不同数据库管理器的获取接口。
- **会话获取方式改进**：
  - [`DBManager.get_session`](fund_nav_mcp/db/core.py) 改用 `@asynccontextmanager` 装饰器，返回 `AsyncIterator[AsyncSession]`，修正静态类型检查中的 `AbstractAsyncContextManager` 兼容问题，同时保持原有 `async with` 用法不变。

### Fixed

- **修复 InfluxDB 写入与数据库管理器获取中的问题**：
  - 在 [`InfluxDBManager.write`](fund_nav_mcp/db/core.py) 中增加空列表判断，避免向 InfluxDB 写入空点集导致的潜在异常；同时移除不必要的 `write_precision` 参数，简化写入逻辑。
  - 修复 `get_manager` 中缺失的 `else` 分支，防止 InfluxDB 管理器配置被后续通用 DBManager 配置错误覆盖，确保按数据库类型正确实例化。
- **修复异步程序无法正常退出**：
  - 修复异步程序退出时进程卡死的问题（由日志监听进程未退出及第三方库 DEBUG 日志清理阻塞引起）
  - 优化 [`LoggingManager._shutdown`](fund_nav_mcp/utils/log.py)，监听进程超时后强制终止，确保主进程优雅退出

## [0.1.1] - 2026-05-06

### Added

- **Compose 配置优化**：
  - 将 mysql 和 influxdb 服务定义以注释形式加入，方便按需启用 [`compose.yml`](docker/compose.yml)。
  - 更新环境变量文件及相关字段，适配多数据库后端配置。

### Changed

- **多态配置模型**：
  - 新增 [`StorageConfigBase`](fund_nav_mcp/models/__init__.py) 抽象基类，定义 `url`、`_do_test`、`_classify_error` 等核心接口。
  - 将原单一 [`DatabaseConfig`](fund_nav_mcp/models/schemas.py)  拆分为多态继承体系：
      - `DatabaseConfig` 作为数据库配置根类，负责多态分发。
      - 具体实现：`SQLiteConfig`、`MySQLConfig`、`PostgresqlConfig`、`InfluxDBConfig`。
  - 将原单一 [`CacheConfig`](fund_nav_mcp/models/schemas.py)  拆分为 `CacheConfig`（根类）+ `RedisConfig`。
  - 使用 `@lru_cache` 单例管理 `TypeAdapter`，实现根据 `db_type` / `cache_type` 字段自动反序列化为具体子类。

### Fixed

- **修复多进程日志队列 pickle 序列化错误**：
  - 将 [`MPQueueHandler.emit`](fund_nav_mcp/utils/log.py) 中放入队列的日志记录转为仅含基础类型的字典，自动将 `sqlite3.Connection`、局部函数等不可序列化对象转为字符串，彻底消除跨进程日志时的 `TypeError` 与 `AttributeError`。
- **修复 Windows 下导入配置模块导致的 pickle 序列化错误**：
  - 将日志初始化从模块顶层移至显式的调用，避免在 import 阶段触发 `multiprocessing` 内部队列及后台线程的创建。
  - 彻底消除了程序退出时 `cannot pickle 'sqlite3.Connection'` 等一系列无害但干扰性的异常输出。
- **修复由于在 server 初始化日志导致其他文件使用时出现的重复初始化问题**：
  - 将 [`server`](fund_nav_mcp/server.py) 中的日志初始化逻辑限定在 [`init`](fund_nav_mcp/__init__.py) 中执行，避免被其他模块在导入阶段触发多次初始化，确保全局日志配置仅生效一次。

## [0.1.0] - 2026-05-02

### Added

- **Docker Compose 支持**：
  - 提供 [`compose.yml`](docker/compose.yml)，可一键启动开发所需服务。
  - 附带 [`.env.example`](docker/.env.example) 和覆盖配置示例 [`compose.override.example.yml`](docker/compose.override.example.yml)。
- **统一工具调用机制**：
  - 新增工具注册表，支持全局工具（跨应用）与私有工具的动态加载。
  - 调用时根据上下文自动路由，无需手动区分。
  - 核心逻辑入口：[`fund_nav_mcp/tools/__init__.py`](fund_nav_mcp/tools/__init__.py)。
- **配置工具 UI 界面**：
  - [`fund_nav_mcp/apps/config_app.py`](fund_nav_mcp/apps/config_app.py) 提供首个可视化配置页面，可实时编辑与校验参数。
- **项目文档**：
  - 补充 [`README.md`](./README.md)、[`LICENSE`](./LICENSE) 和 [`CHANGELOG.md`](./CHANGELOG.md)。

### Changed

- **类型安全与代码质量**：消除 PyCharm 静态检查告警。
  - 合并重复的条件判断与工具函数，减少冗余分支。
  - 强化类型收窄，移除不必要的注释。
  - 对可能为 `None` 的变量增加提前返回或显式默认值，提升空值安全性。
  - 所有改动均适应 PyCharm 2026.1+ 更严格的类型检查规则。
- **环境变量体系优化**：
  - 增/删/改 `.env` 部分变量，优化命名与默认值（[`.env.dev`](.env.dev)、[`.env.prod`](.env.prod)、[`.env.test`](.env.test)）。
  - 新增 `.env.local` 最高优先级加载，方便本地开发覆盖且不进入版本控制（[`load_env`](fund_nav_mcp/utils/path_utils.py)）。
- **代码格式与类型注解**：统一代码风格，补充 `Union[DatabaseConfig, CacheConfig]` 等联合类型注解，为核心逻辑添加注释，提升可读性。

### Fixed

- **测试用例字段对齐**（[`test_config.py`](tests/test_config.py)）：测试字段与 `DatabaseConfig`/`CacheConfig` 模型定义不一致的问题。
  - 将已废弃的 `url`/`pool_size` 替换为 `db_type`、`db_host`、`db_port`、`db_pool_size` 等实际字段。
  - 构造 `DatabaseConfig` 时不再使用 `DatabaseConfig(url=...)`，改为传入真实字段。
  - 环境变量嵌套测试中的变量名调整为 `MCP_DATABASES__<name>__DB_HOST` 等合法写法。
  - TOML 存储后的内容断言改为校验实际持久化的键名。
  - 更新了 `test_env_var_loading`、`test_toml_file_loading` 等用例的字段引用。

## [0.0.1] - 2026-04-17

### Added

- **初始版本**：构建项目框架。
