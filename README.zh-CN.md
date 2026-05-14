# 基金净值管理 MCP

🌐 [English](./README.md) | 中文

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-blueviolet)](https://spec.modelcontextprotocol.io/)

一个基于 MCP (Model Context Protocol) 协议的基金净值管理服务器，提供基金净值查询、计算、存储和分析功能。

## 功能特性

### 🔧 核心功能

- **基金净值查询**: 支持多种数据源的基金净值实时查询
- **净值计算引擎**: 提供复杂的净值计算和验证逻辑
- **多数据源支持**: 支持数据库、缓存、API 等多种数据源
- **配置化管理**: 灵活的配置文件和环境变量管理

### 🚀 技术特性

- **MCP 协议兼容**: 完全兼容 Model Context Protocol 标准
- **异步高性能**: 基于 FastMCP 框架，支持高并发处理
- **类型安全**: 使用 Pydantic 进行数据验证和类型检查
- **结构化日志**: 完整的日志记录和监控支持

### 📊 数据管理

- **数据库支持**: PostgreSQL、MySQL 等多种数据库
- **缓存支持**: Redis 缓存集成
- **时序数据**: InfluxDB 时序数据库支持
- **配置持久化**: TOML 格式配置文件管理

## 快速开始

### 环境要求

- Python 3.12 或更高版本
- 支持的数据库: PostgreSQL, MySQL
- 可选缓存: Redis
- 可选时序数据库: InfluxDB

### 安装

#### 方法一：使用 UV 包管理器（推荐）

详情可见：[UV 安装文档](https://docs.astral.sh/uv/getting-started/installation/)

1. **安装 UV**（如果尚未安装）
    ```bash
    # Windows
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    # Linux/macOS
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # 或者
    wget -qO- https://astral.sh/uv/install.sh | sh
    ```

2. **克隆项目**

    ```bash
    git clone https://github.com/RamidLab/fund-nav-mcp.git
    cd fund-nav-mcp
    ```

3. **创建虚拟环境**
   
   详情可见：[UV 虚拟环境文档](https://docs.astral.sh/uv/pip/environments/)

    ```bash
    uv venv
    # 或者自定义名称
    uv venv my-name
    # 或者指定 Python 版本
    uv venv --python 3.12
    ```
   
4. **激活虚拟环境**

    ```bash
    # Windows
    {venv-name}\Scripts\activate

    # Linux/Mac
    source {venv-name}/bin/activate
    ```

5. **安装依赖**

    ```bash
    # 安装项目依赖
    uv sync
    
    # 或者使用开发模式（包含开发依赖）
    uv sync --dev
    ```

#### 方法二：使用传统 pip

1. **克隆项目**

   ```bash
   git clone https://github.com/RamidLab/fund-nav-mcp.git
   cd fund-nav-mcp
   ```

2. **创建虚拟环境**

   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **安装依赖**
   
   ```bash
   pip install -e .
   ```

### 配置环境变量

**配置说明**: 项目采用分层配置系统，`.env` 文件用于系统级配置，环境特定配置使用 `.env.local` 文件。

#### 系统级配置 (.env)
创建或编辑 `.env` 文件，配置系统级参数：

```env
MCP_ENV=dev                          # 环境标识: dev, prod, test
MCP_NAME=fund_nav_mcp                # 应用名称

MCP_CONFIG_PRIORITY=init_first       # 该部分可详见下方配置源优先级

MCP_TRANSPORT=streamable-http        # 传输协议: stdio, sse, streamable-http

MCP_CACHE_ENABLED=true               # 是否启用缓存
MCP_TIMEZONE=Asia/Shanghai           # 系统时区
MCP_DEFAULT_CURRENCY=CNY             # 默认货币
```

#### 环境特定配置

（可选）根据 `MCP_ENV` 设置，复制对应的环境配置文件：
```bash
# 开发环境 (MCP_ENV=dev)
cp .env.dev .env.local
# 生产环境 (MCP_ENV=prod)  
cp .env.prod .env.local
# 测试环境 (MCP_ENV=test)
cp .env.test .env.local
# 或使用示例文件
cp .env.example .env.local
```
环境特定配置示例（.env.dev）：

```env
# 服务器配置
MCP_HOST=0.0.0.0                   # 服务器监听地址
MCP_PORT=8000                      # 服务器端口
# UI 开发界面配置
MCP_UI_PORT=8080                   # UI 开发端口
MCP_UI_RELOAD=true                 # 是否启用热重载

# 日志中间件配置
MCP_LOG_MID_INCLUDE_PAYLOADS=true          # 是否在日志中包含请求/响应负载
MCP_LOG_MID_INCLUDE_PAYLOADS_LENGTH=true   # 是否包含负载长度
MCP_LOG_MID_ESTIMATE_PAYLOAD_TOKENS=true   # 是否估算负载token数量

# 日志配置
MCP_LOGGING_LEVEL="WARNING"                # 日志级别: DEBUG, INFO, WARNING, ERROR
MCP_LOGGING_CONSOLE=false                  # 是否输出到控制台
MCP_LOGGING_FILE=true                      # 是否输出到文件
MCP_LOGGING_FILE_PATH="dev_logs"           # 日志文件路径
MCP_LOGGING_FILE_BASE_NAME="fund_nav_mcp"  # 日志文件名
MCP_LOGGING_BACKUP_COUNT=100               # 日志备份文件数量
MCP_LOGGING_MAX_FILE_SIZE=104857600        # 单个日志文件最大大小（字节）
MCP_LOGGING_JSON_FORMAT=true               # 是否使用JSON格式
MCP_LOGGING_SEPARATE_ERROR_FILE=true       # 是否分离错误日志
MCP_LOGGING_ERROR_FILE_BASE_NAME="fund_nav_mcp_error"  # 错误日志文件名

# 数据库配置（示例）
MCP_DATABASES__DEFAULT__DB_TYPE=sqlite
MCP_DATABASES__DEFAULT__DB_HOST=.cache/sqlite/default.db

# 缓存配置（示例）
MCP_CACHES__DEFAULT__CACHE_TYPE=memory
```

**配置文件说明**：
- `.env`: 系统级配置（环境标识、应用名称、配置优先级等）
- `.env.local`: 环境特定配置（服务器、日志、数据库等）
- `.env.dev`: 开发环境配置模板
- `.env.prod`: 生产环境配置模板  
- `.env.test`: 测试环境配置模板
- `.env.example`: 配置示例文件

**配置加载顺序**：
1. `.env` 文件（系统级配置）
2. `.env.local` 文件（环境特定配置）
3. 环境变量（覆盖文件配置）
4. 代码传参（最高优先级）

### 配置源优先级

通过环境变量 `MCP_CONFIG_PRIORITY` 控制配置源优先级：

- `toml_first`: TOML > 环境变量 > 显式参数（TOML文件覆盖一切）
- `env_first`: 环境变量 > TOML > 显式参数（环境变量优先于文件）
- `init_first`: 显式参数 > 环境变量 > TOML（代码传参优先，默认行为）
- `env_only`: 环境变量 > 显式参数（忽略TOML文件）
- `toml_only`: TOML > 显式参数（只读文件，忽略环境变量）

### TOML 配置文件

项目支持 TOML 格式的配置文件，配置文件位于 `configs/` 目录下，按环境命名（如 `config.dev.toml`）。

#### 方式一：使用 UI 界面配置（推荐）

项目启动时会自动检测并生成默认配置，直接启动 UI 界面进行配置即可：
```bash
uv run fund-nav-mcp ui --dev-port 8080 --mcp-port 8000 --reload
```
首次运行后，系统会创建：
- `configs/config.dev.toml`（开发环境）
- `configs/config.prod.toml`（生产环境）
- `configs/config.test.toml`（测试环境）

访问 `http://localhost:8080` 进行可视化配置管理。

#### 方式二：手动创建配置文件

您也可以手动创建配置文件，参考 `configs/config.dev.toml` 示例：
```toml
# configs/config.dev.toml
cache_enabled = true
timezone = "Asia/Shanghai"
default_currency = "CNY"

[databases.default]
db_type = "postgresql"
db_host = "127.0.0.1"
db_port = 5432
db_username = "postgres"
db_password = "postgres"
db_sql_echo = "close"
db_pool_size = 5
status = "已启动"

[caches.default]
cache_host = "127.0.0.1"
cache_port = 6379
cache_pass = ""
timeout = 5
main_db = 0
databases = 16
ttl_seconds = 300
max_size = 1024
cache_pool_size = 5
cache_type = "redis"
status = "已启动"
```

#### 配置项说明

##### 数据库配置
支持多种数据库类型，完整配置参数参考 `fund_nav_mcp/models/schemas.py`：
```toml
[databases.default]
db_type = "sqlite"           # 数据库类型: sqlite, mysql, postgresql, influxdb
db_host = "memory"           # 数据库主机，默认 memory（内存数据库）
db_port = 0                  # 数据库端口，SQLite 为 0
db_username = ""             # 数据库用户名，默认 null
db_password = ""             # 数据库密码，默认 null
db_sql_echo = "close"        # SQL命令输出: open/close
db_pool_size = 5             # 连接池大小，默认 5
status = "Unknown"           # 数据库状态: Unknown, Active, Inactive, Error, AuthFailed
```
**数据库类型说明**：
- **sqlite**: 本地文件数据库，`db_host` 可为文件路径或 "memory"（内存数据库）
- **mysql**: MySQL 数据库，需要设置 host、port、username、password
- **postgresql**: PostgreSQL 数据库，配置同 MySQL
- **influxdb**: InfluxDB 时序数据库

##### 缓存配置
缓存配置支持 Redis，完整参数参考 `fund_nav_mcp/models/schemas.py`：
```toml
[caches.default]
cache_host = "127.0.0.1"     # 缓存主机，默认 127.0.0.1
cache_port = 6379            # 缓存端口，默认 6379
cache_pass = ""              # 缓存密码，默认 null
timeout = 5                  # 连接超时时间（秒），默认 5
main_db = 0                  # 主数据库索引，默认 0
databases = 16               # 逻辑数据库数量，默认 16
key_prefix = ""              # 键前缀，默认 null
ttl_seconds = 300            # 缓存过期时间（秒），默认 300
max_size = 1024              # 缓存最大大小（MB），默认 1024
cache_pool_size = 5          # 连接池大小，默认 5
cache_type = "redis"         # 缓存类型，目前仅支持 redis
status = "Unknown"           # 缓存状态: Unknown, Active, Inactive, Error, AuthFailed
```

### 运行服务器

#### 使用 UV 运行（推荐）

详情可见：[UV 运行文档](https://docs.astral.sh/uv/guides/scripts/)

```bash
# 标准输入输出模式 (推荐用于开发)
uv run fund-nav-mcp stdio

# SSE 服务器模式 (用于生产环境)
uv run fund-nav-mcp sse --host 0.0.0.0 --port 8000

# Streamable HTTP 模式
uv run fund-nav-mcp streamable-http --host 0.0.0.0 --port 8000

# UI 开发模式（启动 Apps 预览界面）
uv run fund-nav-mcp ui --dev-port 8080 --mcp-port 8000 --reload
```

#### 使用传统方式运行

```bash
# 标准输入输出模式
python -m fund_nav_mcp.server stdio

# SSE 服务器模式
python -m fund_nav_mcp.server sse --host 0.0.0.0 --port 8000

# Streamable HTTP 模式
python -m fund_nav_mcp.server streamable-http --host 0.0.0.0 --port 8000

# UI 开发模式
python -m fund_nav_mcp.server ui --dev-port 8080 --mcp-port 8000 --reload
```

### 运行模式说明

- **stdio 模式**: 标准输入输出，适合与 MCP 客户端集成
- **sse 模式**: Server-Sent Events 模式，支持 Web 客户端连接
- **streamable-http 模式**: HTTP 流式传输模式
- **ui 模式**: 启动开发界面，便于调试和测试

## MCP 工具

### 系统工具

#### 健康检查工具
- `health`: 检查MCP服务器健康状态，返回服务是否正常

### 配置工具

#### 配置管理工具
- `get_all_config`: 获取所有配置信息
- `add_database`: 添加数据库配置
- `add_cache`: 添加缓存配置
- `update_database`: 更新数据库配置
- `update_cache`: 更新缓存配置
- `delete_database`: 删除数据库配置
- `delete_cache`: 删除缓存配置

#### 配置应用工具（UI界面）
- `config_app`: 配置应用，提供可视化配置界面

### 工具使用示例

正在完善中...

### 工具标签分类

- `sys_tool`: 系统级工具（如健康检查）
- `config_tool`: 配置管理工具
- 目前处于开发阶段，其他标签将会逐渐完善

## 开发指南

### 添加新的 MCP 工具

1. 在 `fund_nav_mcp/tools/` 目录下创建新的工具文件
2. 定义工具函数并使用 `@tool()` 装饰器
3. 若是全局工具，需要添加 `@global_tool()` 装饰器

示例：

```python
from typing import Dict, Any

from fastmcp.tools import tool

from fund_nav_mcp.tools import global_tool


@global_tool
@tool(
    name="get_fund_data",
    title="获取基金数据",
    description="获取基金数据，根据基金代码和日期查询基金净值数据",
    tags={"fund_tool"}
)
async def get_fund_data(fund_code: str, date: str) -> Dict[str, Any]:
    """
    获取基金数据   
    
    Args:
        fund_code: 基金代码
        date: 日期
        
    Returns:
        dict: 基金净值数据
    """
    # 实现逻辑...
    return {"fund_code": fund_code, "date": date, "nav": 1.2345}
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_config.py

# 带详细输出
pytest -v
```

## 部署说明

### Docker 部署

正在完善中...

## 故障排除

### 常见问题

#### 1. Windows 下 FastMCP Apps UI 空白或控制台报 404 / `t.custom is not a function`

**原因**：FastMCP 缓存了某次失败的前端资源下载（如 esm.sh 临时不可用）。  
**解决**：删除缓存文件，重启服务即可。

- **Windows (PowerShell)**：
  ```powershell
  Get-ChildItem -Path "$env:TEMP" -Filter "fastmcp-ext-apps-*bundle.json" | Remove-Item -Force
  ```

### 日志查看

日志文件默认位于 `logs` 目录。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 作者: ramid
- 邮箱: ramid@qq.com
- 项目地址: [GitHub Repository](https://github.com/RamidLab/fund-nav-mcp)

## 更新日志

详细更新见 [CHANGELOG.md](CHANGELOG.md)