## [0.1.0] - 2026-05-02

### Added
- **Docker Compose 支持**：
  - 提供 [`compose.yml`](docker/compose.yml)，可一键启动开发所需服务。
  - 附带 [`.env.example`](docker/.env.example) 和覆盖配置示例 [`compose.override.example.yml`](docker/compose.override.example.yml)。
- **统一工具调用机制**：
  - 新增工具注册表，支持全局工具（跨应用）与私有工具的动态加载。
  - 调用时根据上下文自动路由，无需手动区分。
  - 核心逻辑入口：[`fund_nav_mcp/tools/__init__.py`](fund_nav_mcp/tools/__init__.py)。
- **配置工具 UI 界面**：[`fund_nav_mcp/apps/config_app.py`](fund_nav_mcp/apps/config_app.py) 提供首个可视化配置页面，可实时编辑与校验参数。
- **项目文档**：补充 [`README.md`](./README.md)、[`LICENSE`](./LICENSE) 和 [`CHANGELOG.md`](./CHANGELOG.md)。
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