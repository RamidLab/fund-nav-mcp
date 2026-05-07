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

## Changed

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
