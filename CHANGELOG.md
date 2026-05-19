## [0.12.6] 2026-05-20

### Added

- **异常标记枚举**：新增 [`AbnormalType`](fund_nav_mcp/utils/enums.py) 枚举，包含 `Placeholder`（占位记录）、`ShortBaseCode`（私募基础编码不足6位）、`Orphaned`（关联记录已删除）、`NameMismatch`（父基金名称不一致）、`NavConflict`（净值数据冲突，需人工审核）。所有 ORM 模型新增 `abnormal` 字段，用于标记数据异常状态。

- **净值冲突自动升级**：[`AddHandler._detect_nav_conflict`](fund_nav_mcp/handlers/add_handlers.py)  方法检测到相同 `(fund_id, nav_date, data_source)` 已存在且数值不同时，自动将新记录的 `version` 设为 `max(version)+1`，并标记 `abnormal=NavConflict`，避免唯一约束冲突，同时保留历史版本供人工审核。

- **基金名称份额后缀自动补齐**：[`CodeResolveMixin._normalize_fund_codes`](fund_nav_mcp/handlers/base_handlers.py) 方法在写入前预处理：若 `fund_code` 无份额后缀但 `fund_name` 携带份额类别（如“某某稳健B类”），自动将 `fund_code` 补齐为 `fund_code + 后缀字母`（如 `000001B`），确保同一基金的不同份额拥有唯一编码。

- **父基金名称自动同步**：创建子基金占位记录时，若 `fund_name` 携带份额后缀，自动剥离后缀作为父基金名称；若已有父基金名称不一致，则标记 `abnormal=NameMismatch`。

- **删除标记孤儿记录**：[`DeleteHandler._mark_orphaned`](fund_nav_mcp/handlers/delete_handlers.py) 方法在删除父记录前，将关联子记录的 `abnormal` 字段设为 `Orphaned`（如删除基金时，其净值、收益率、持仓、分类映射均被标记；删除管理人时，关联基金和管理人员被标记）。原有关联级联删除（`cascade="all, delete"`）已全部移除，数据完整性通过标记而非物理删除维护。

- **分类映射外键可空**：[`FundCategoryMapping`](fund_nav_mcp/models/orm/fund.py) 的 `fund_id` 和 `category_id` 改为 `Optional[int]`，使得孤儿映射可以保留外键值但标记异常，便于事后追溯。

### Changed

- **CodeResolveMixin 增强**：
  - 新增 [`_strip_share_class_from_name`、`_parse_fund_name_for_share_class`](fund_nav_mcp/handlers/base_handlers.py) 方法，支持从基金名称中剥离/提取份额后缀字母。
  - [`_normalize_fund_codes`](fund_nav_mcp/handlers/base_handlers.py) 方法 作为公开方法，在 `AddHandler.handle` / `handle_batch` 中优先调用，实现 code 补齐。
  - 自动创建占位基金时，从请求中提取透传字段的同时，若发现父基金名称不一致则标记 `NameMismatch`；若基码长度小于6位则标记 `ShortBaseCode`。
  - `_build_placeholder` 自动设置 `abnormal=Placeholder`，区分正常创建与自动创建的记录。

- **ORM 模型级联策略调整**：
  - `Fund.nav_records`、`returns`、`holdings` 关系移除 `cascade="all, delete"`，改为由应用层标记孤儿。
  - `FundManagerPerson.current_company` 外键约束保留，但删除公司时不再自动删除人员，而是标记 `Orphaned`。
  - 所有模型 `abnormal` 字段默认 `None`（正常），非 `None` 表示异常状态。

- **Pydantic 响应模型更新**：`FundResponse`、`FundNavResponse`、`FundReturnResponse`、`FundHoldingResponse`、`FundManagerPersonResponse`、`FundCategoryMappingResponse` 均增加 `abnormal: Optional[AbnormalType]` 字段，供前端展示数据异常状态。

## [0.12.5] 2026-05-18

### Added

- **份额后缀自动创建父基金**：[`CodeResolveMixin._resolve_fk_codes`](fund_nav_mcp/handlers/base_handlers.py) 在自动创建占位基金时，识别 `fund_code` 中的份额后缀（A/B/C/D/E），提取基码后先创建主份额基金（若无），并为当前记录自动填充 `share_class` 与 `parent_fund_id`，实现份额体系静默补齐。
- **唯一冲突友好提示**：[`AddHandler`](fund_nav_mcp/handlers/add_handlers.py) 新增 `_parse_constraint_columns`、`_format_integrity_error`、`_extract_conflict_key` 方法，从 `IntegrityError` 中解析冲突列与值，返回中文错误信息（如“数据重复：基金代码=‘000001’ 的组合已存在”）；单条与批量响应的 `data` 中增加 `conflict_key` 字段，便于前端精确定位重复项。
- **基金代码查询自动前缀匹配**：[`create_filter_class`](fund_nav_mcp/handlers/base_handlers.py) 生成的过滤器对 `fund_code` 字段的 `eq` 条件，若值为无后缀基码（不以 A-E 结尾），自动转换为 `like 'value%'`，一次查询可匹配该基金的所有份额变体（如 S12345 → S12345A、S12345B），提升查询便利性。
- **数据来源追溯字段**：[`FundNav`](fund_nav_mcp/models/orm/fund.py)  ORM 新增 `source_reference: Optional[str]` 列（String 200），Pydantic 模型同步增加该字段，用于记录邮件 Message-ID、文件路径+哈希、API 请求 ID 等来源标识。

### Changed

- **自动创建占位逻辑增强**：[`_build_placeholder`](fund_nav_mcp/handlers/base_handlers.py) 构建占位基金时，优先从请求中提取透传字段；份额后缀检测逻辑复用正则 `_SHARE_CLASS_SUFFIX_PATTERN`，支持大小写敏感。私募基金代码正则同步更新，允许末尾带份额后缀。
- **Pydantic 日期字段类型调整**：`FundBase`、`FundUpdate`、`FundNavBase`、`FundReturnBase`、`FundHoldingBase` 等模型中的日期字段（`establishment_date`、`registration_date`、`nav_date`、`calculation_date`、`report_date`、`amac_registration_date`、`birth_date`）从 `date` 改为 `Optional[str]`，允许接收更多格式的日期字符串，由 `_conv_date_fields` 统一调用 `to_date_flexible` 转换，提升前端兼容性。
- **枚举字段默认值统一**：[`FundBase`](fund_nav_mcp/models/pydantic/fund.py) 中 `fund_type`、`fund_management_type`、`status` 的默认值分别设为 `FundType.Unknown`、`FundManagementType.Unknown`、`FundStatus.Unknown`，确保非空且语义清晰。
- **正则校验增强**：[`FundBase._validate_fund_code`](fund_nav_mcp/models/pydantic/fund.py) 中对私募代码的匹配模式增加可选后缀 `[A-Ea-e]?`，允许私募代码后跟份额类别字母。
- **模型字段注释完善**：[`FundNavBase`](fund_nav_mcp/models/pydantic/fund.py) 添加 `source_reference` 字段说明；`fund_code` 校验注释更新。

## [0.12.4] 2026-05-16

### Added

- **外键缺失自动创建占位记录**：[`add_handlers`](fund_nav_mcp/handlers/add_handlers.py)在批量添加净值/收益率/持仓时，若 `fund_code` 对应的基金记录不存在，系统自动创建一条占位基金记录。
  - 占位基金名称默认格式 `未知fund-{code}`，其余字段根据 ORM 列类型自动填充类型感知的兜底值（如 `""`、`0`、`date.today()` 等）。
  - 若请求中同时传入了 `fund_name`、`fund_type` 等 `Fund` 模型字段，优先使用传入值填充占位记录。
  - 通过 `AddHandler._AUTO_CREATE_MODELS` 集合控制哪些关系支持自动创建，便于扩展至其他模型（如基金管理人）。
  - 占位构造逻辑 `_build_placeholder` 与透传字段推导 `_ref_passthrough_columns` 均基于 ORM 列内省实现，不再硬编码 `Fund` 特有逻辑。

- **批量添加部分失败隔离**：[`add_handlers.handle_batch`](fund_nav_mcp/handlers/add_handlers.py) 方法改为逐条插入，单条记录的异常不会影响其他记录的添加。
  - 响应数据结构扩展为：`{success_count, fail_count, ids, failures}`。
  - `failures` 列表包含失败记录的 `index`（序号）、`key`（自动提取的 `_code`/`_date` 等定位字段）、`error`（异常信息）。
  - 全部成功 → `code=SUCCESS`；部分成功 → `code=SUCCESS` 并返回明细；全部失败 → `code=FAIL` 并返回明细。

- **净值校验强化**：
  - `unit_nav` 在创建模型中已是必填字段（`Field(...)`），并新增 `validator` 拦截 ≤ 0 的值。
  - `acc_nav` / `adj_nav` 若传入 `0`，自动转换为 `None`，避免写入无意义的零值。

### Changed

- **批量添加响应类型**：[`handle_batch`](fund_nav_mcp/handlers/add_handlers.py) 方法返回类型从 `dict[str, list[int]]` 调整为 `dict[str, Any]`，解决了 `count` 字段与 FastMCP output schema 要求 `array` 类型的冲突。
- **Pydantic 模型增加 `extra="allow"`**：[`models/pydantic/fund`](fund_nav_mcp/models/pydantic/fund.py) 为 `FundNavCreate`、`FundReturnCreate`、`FundHoldingCreate` 添加 `model_config = {"extra": "allow"}`，允许在请求中透传 `Fund` 模型的字段（如 `fund_name`），供 handler 层自动创建占位基金时使用。

### Fixed

- 修复 [`add_handlers.handle_batch`](fund_nav_mcp/handlers/add_handlers.py) 方法 内部遗漏调用 `_conv_date_fields` 的问题，该问题导致日期字符串直接传入 SQLite 时引发 `TypeError`。

## [0.12.4] 2026-05-15

### Added

- **日期字段转换**：新增日期字段转换功能，支持将字符串日期转换为 datetime.date 对象。

### Changed

- **修改净值字段名称**：将净值字段从 `unit_nav`、`acc_nav`、`adj_nav` 改为 `nav_unit`、`nav_acc`、`nav_adj`，以符合数据库设计规范。

##### [0.12.2] 2026-05-14

### Added

- **删除模型基类**：新增 [`BaseDeleteModel`](fund_nav_mcp/models/pydantic/__init__.py)，定义抽象基类，包含 `record_id: Optional[int]` 公共字段，所有实体删除模型统一继承，消除重复代码。

### Changed

- **批量删除支持多策略定位**：[`DeleteHandler.handle_batch`](fund_nav_mcp/handlers/delete_handlers.py) 方法签名由 `(orm_model, ids, db_name)` 改为 `(orm_model, data_list, db_name)`，每条删除数据独立使用与单条删除相同的定位逻辑（record_id / 编码 / 复合字段 / 名称），大幅提升批量删除的灵活性。
- **删除工具批量接口升级**：[`tools/delete_tools.py`](fund_nav_mcp/tools/delete_tools.py) 中所有 `delete_*s` 工具参数从 `ids: List[int]` 改为 `data_list: List[对应Delete模型]`，调用方可通过多种方式定位每条待删除记录，而不仅限于主键 ID。
- **Pydantic 删除模型简化**：[`models/pydantic/fund.py`](fund_nav_mcp/models/pydantic/fund.py) 中所有 `*Delete` 类改为继承 `BaseDeleteModel`，移除各自重复定义的 `record_id` 字段及相应的校验器，代码量显著减少。

## [0.12.1] 2026-05-14

### Added

- **动态类存根生成**：新增 [`models/pydantic/generate.py`](fund_nav_mcp/models/pydantic/generate.py)，提供 `register_pyi_class()` 函数，在创建动态 Filter/Search 类时自动注册，并生成 `.pyi` 存根文件，解决动态类在 IDE 中无类型提示的问题。
- **存根刷新脚本**：新增 [`refresh_stubs.py`](scripts/refresh_stub.py)，调用 `clean_registry()` 清空注册表后重新加载 `filter` 和 `search` 模块，重新生成所有存根文件，便于开发时手动刷新类型提示。

### Changed

- **`create_filter_class` 增强**：在 [`models/pydantic/builder.py`](fund_nav_mcp/models/pydantic/builder.py) 中，创建动态 Filter 类后自动调用 `register_pyi_class` 注册至 `filter.pyi`，使生成的类具备类型提示支持。
- **`create_search_class` 增强**：同样在 `builder.py` 中，创建关键词搜索类和字段搜索类后分别调用 `register_pyi_class` 注册至 `search.pyi`。
- **`filter_classes.py` 简化**：移除所有显式的 `: type[BaseFilter]` 类型注解，改为直接赋值，依赖自动生成的 `.pyi` 文件提供类型信息，代码更简洁。
- **`search_classes.py` 简化**：同样移除 `: type[BaseSearchByKeyword]` 和 `: type[BaseSearchByFields]` 类型注解，直接赋值。

## [0.12.0] 2026-05-13

### Added

- **DeleteHandler 通用删除处理器**：新增 [`DeleteHandler`](fund_nav_mcp/handlers/delete_handlers.py)，实现 ORM 删除逻辑，支持单条及批量删除。定位策略丰富：`record_id`、自有编码字段、额外编码（如统一社会信用代码）、复合字段（`fund_code`+`nav_date` 等）、名称多策略定位。包含同名记录歧义检测与候选项提示。

- **MCP 删除工具集**：新增 [`delete_tools`](fund_nav_mcp/tools/delete_tools.py)，提供 18 个删除工具，覆盖 `Fund`、`FundManager`、`FundManagerPerson`、`FundCategory`、`FundCategoryMapping`、`FundNav`、`FundReturn`、`FundHolding` 各模型，均提供单条和批量删除接口。

- **DBManager 删除方法**：在 [`core`](fund_nav_mcp/db/core.py) 的 `DBManager` 中新增 `delete_by_id()`（按主键删除单条）和 `delete_batch_by_ids()`（按主键列表批量删除）。

- **Pydantic 删除模型**：新增 [`FundDelete`、`FundNavDelete`、`FundReturnDelete`、`FundHoldingDelete`、`FundManagerDelete`、`FundManagerPersonDelete`、`FundCategoryDelete`、`FundCategoryMappingDelete`](fund_nav_mcp/models/pydantic/fund.py)，均包含联合必填校验（如多个定位字段至少提供一个）及字符串自动去空白。

- **FundCategoryMappingValidators**：新增 [`fund_validators`](fund_nav_mcp/models/pydantic/fund_validators.py) 中的校验 Mixin，统一处理分类映射相关代码字段的空白校验。

### Changed

- **CodeResolveMixin 增强**：在 [`base_handlers`](fund_nav_mcp/handlers/base_handlers.py) 中提升 `_check_own_codes_unique`（新增 `exclude_id` 参数，支持更新时排除自身 ID）和 `_resolve_record_id` 为共享方法；`_find_code_col` 增加对字典类型行的支持，完善文档注释。

- **AddHandler 简化**：移除内联的 `_check_own_codes_unique` 方法，改为继承 `CodeResolveMixin` 的共享实现。

- **UpdateHandler 简化**：移除内联的 `_check_own_codes_unique_for_update` 和 `_resolve_record_id` 方法，改为继承 `CodeResolveMixin` 的共享实现。

- **FundCategoryMappingBase 重构**：将字段校验逻辑从 `FundCategoryMappingBase` 迁移至 `FundCategoryMappingValidators` Mixin，保持校验行为不变。

### Removed

- 移除 `handlers/add_handlers.py` 中重复的 `_check_own_codes_unique` 方法。
- 移除 `handlers/update_handlers.py` 中重复的 `_check_own_codes_unique_for_update` 和 `_resolve_record_id` 方法。

## [0.11.0] 2026-05-13

### Added

- **通用更新处理器**：新增 [`handlers/update.py`](fund_nav_mcp/handlers/update_handlers.py)，实现 `UpdateHandler` 类，支持单条及批量更新。
  - 通过 `record_id` 或模型自有编码字段（如 `fund_code`）精确定位记录。
  - 仅更新请求中显式提供的非 `None` 字段，自动跳过空值。
  - 复用 `CodeResolveMixin` 解析外键 `code` 和名称字段，更新前自动设置 `updated_at`。
  - 提供 `handle` / `handle_batch` 方法，统一集成至数据库管理器。

- **MCP 更新工具集**：新增 [`tools/update.py`](fund_nav_mcp/tools/update_tools.py)，为 `Fund`、`FundManager`、`FundManagerPerson`、`FundCategory`、`FundNav`、`FundReturn`、`FundHolding` 等 7 个实体生成更新工具。
  - 每个实体对应单条更新 `update_*` 和批量更新 `update_*s` 两个工具。
  - 支持通过 `record_id` 或业务 `code` 字段（如 `fund_code`）定位记录，对外隐藏内部主键 ID。

- **数据库管理器更新能力**：在 [`db/core.py`](fund_nav_mcp/db/core.py) 的 `DBManager` 中新增：
  - `update_by_id(model, record_id, values)`：按主键更新单条 ORM 记录，提交后刷新实例并返回。
  - `update_batch_by_ids(model, ids, values_list)`：按主键列表批量更新，顺序匹配，返回成功更新的 ID 列表。

- **字段校验器 Mixin 抽取**：新增 [`models/pydantic/fund_validators.py`](fund_nav_mcp/models/pydantic/fund_validators.py)，为各模型定义独立的校验器 Mixin 类：
  - `FundValidators`：基金代码、名称、可选字段修剪。
  - `FundNavValidators`：净值日期、单位净值正数、累计净值不小于单位净值。
  - `FundReturnValidators`：排名与总数正数校验、排名不超过总数。
  - `FundHoldingValidators`：持仓比例 0~1、金额/股数非负、日期不晚于今天。
  - `FundManagerValidators`：统一信用代码、中基协编号格式、资本及人数逻辑校验。
  - `FundManagerPersonValidators`：姓名、性别、出生日期校验。
  - `FundCategoryValidators`：分类层级 ≥ 1，一级分类禁止父级代码。

### Changed

- **Pydantic 模型重构**：重构 [`models/pydantic/fund.py`](fund_nav_mcp/models/pydantic/fund.py)，所有 Create/Update 模型改为继承对应的 Mixin 类，移除原有的内联校验器定义，代码重复率显著降低，维护性提升。所有业务校验逻辑保持不变。

- **模块导出更新**：`handlers/__init__.py` 增加 `UpdateHandler` 导出，与 `AddHandler`、`QueryHandler` 并列。

## [0.10.2] 2026-05-13

### Added

- **共享解析基类**：新增 [`handlers/base_handlers.py`](fund_nav_mcp/handlers/base_handlers.py)，提供 `CodeResolveMixin`，统一封装外键 `code → id` 解析和名称兜底解析逻辑，供 `AddHandler` 及后续 `UpdateHandler` 复用。

### Changed

- **AddHandler 重构**：[`AddHandler`](fund_nav_mcp/handlers/add_handlers.py) 继承 `CodeResolveMixin`，移除类内部重复的 `_CODE_RESOLVE_MAP`、`_NAME_RESOLVE_MAP` 等映射定义，直接复用基类方法。
- **查询处理器重命名与增强**：`ForeignKeyDisplayHandler` 重命名为 [`QueryHandler`](fund_nav_mcp/handlers/query_handlers.py)，新增 `__init__(field_mapping=None)` 支持实例级自定义字段映射，不再强制使用类默认配置；`handle` 方法内部使用实例的 `field_mapping`，提升不同业务场景的复用性。

### Fixed

- **模拟数据插入字段过滤**：修复 [`scripts/mock_data.py`](mock/mock_fund_data.py) 中向关系数据库写入 `fund_category_mapping` 等表时，因字典包含 `id` 字段（自增主键）导致 SQLAlchemy 插入失败的问题。现在插入前会过滤仅保留 ORM 模型实际定义的列，确保兼容 PostgreSQL/MySQL 等严格数据库。

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
