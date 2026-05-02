# Fund NAV Management MCP

🌐 [中文](./README.zh-CN.md) | English

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-blueviolet)](https://spec.modelcontextprotocol.io/)

A fund NAV management server based on the MCP (Model Context Protocol) protocol, providing fund NAV query, calculation, storage and analysis capabilities.

## Features

### 🔧 Core Features

- **Fund NAV Query**: Real-time fund NAV querying from multiple data sources
- **NAV Calculation Engine**: Complex NAV calculation and validation logic
- **Multi-source Support**: Supports databases, caches, APIs and other data sources
- **Configurable Management**: Flexible configuration file and environment variable management

### 🚀 Technical Features

- **MCP Protocol Compatible**: Fully compliant with Model Context Protocol standards
- **Asynchronous High Performance**: Built on the FastMCP framework, supporting high concurrency
- **Type Safety**: Data validation and type checking using Pydantic
- **Structured Logging**: Comprehensive logging and monitoring support

### 📊 Data Management

- **Database Support**: PostgreSQL, MySQL and other databases
- **Cache Support**: Redis cache integration
- **Time-series Data**: InfluxDB time-series database support
- **Configuration Persistence**: TOML format configuration file management

## Quick Start

### Prerequisites

- Python 3.12 or higher
- Supported databases: PostgreSQL, MySQL
- Optional cache: Redis
- Optional time-series database: InfluxDB

### Installation

#### Method 1: Using UV Package Manager (Recommended)

For details, see: [UV Installation Documentation](https://docs.astral.sh/uv/getting-started/installation/)

1. **Install UV** (if not already installed)
    ```bash
    # Windows
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    # Linux/macOS
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Or
    wget -qO- https://astral.sh/uv/install.sh | sh
    ```

2. **Clone the repository**

    ```bash
    git clone https://github.com/RamidLab/fund-nav-mcp.git
    cd fund-nav-mcp
    ```

3. **Create a virtual environment**
   
   For details, see: [UV Virtual Environment Documentation](https://docs.astral.sh/uv/pip/environments/)

    ```bash
    uv venv
    # Or with a custom name
    uv venv my-name
    # Or specify a Python version
    uv venv --python 3.12
    ```
   
4. **Activate the virtual environment**

    ```bash
    # Windows
    {venv-name}\Scripts\activate

    # Linux/Mac
    source {venv-name}/bin/activate
    ```

5. **Install dependencies**

    ```bash
    # Install project dependencies
    uv sync
    
    # Or use development mode (includes dev dependencies)
    uv sync --dev
    ```

#### Method 2: Using Traditional pip

1. **Clone the repository**

   ```bash
   git clone https://github.com/RamidLab/fund-nav-mcp.git
   cd fund-nav-mcp
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   
   ```bash
   pip install -e .
   ```

### Configure Environment Variables

**Configuration Description**: The project uses a layered configuration system, with `.env` files for system-level configuration and environment-specific configuration in `.env.local` files.

#### System-level Configuration (.env)
Create or edit the `.env` file and configure system-level parameters:

```env
MCP_ENV=dev                          # Environment identifier: dev, prod, test
MCP_NAME=fund_nav_mcp                # Application name

MCP_CONFIG_PRIORITY=init_first       # See configuration source priority below

MCP_TRANSPORT=streamable-http        # Transport protocol: stdio, sse, streamable-http

MCP_CACHE_ENABLED=true               # Whether to enable caching
MCP_TIMEZONE=Asia/Shanghai           # System timezone
MCP_DEFAULT_CURRENCY=CNY             # Default currency
```

#### Environment-specific Configuration

(Optional) Copy the corresponding environment configuration file according to the `MCP_ENV` setting:
```bash
# Development environment (MCP_ENV=dev)
cp .env.dev .env.local
# Production environment (MCP_ENV=prod)  
cp .env.prod .env.local
# Test environment (MCP_ENV=test)
cp .env.test .env.local
# Or use the example file
cp .env.example .env.local
```
Example environment-specific configuration (.env.dev):

```env
# Server configuration
MCP_HOST=0.0.0.0                   # Server listen address
MCP_PORT=8000                      # Server port
# UI development interface configuration
MCP_UI_PORT=8080                   # UI development port
MCP_UI_RELOAD=true                 # Whether to enable hot reload

# Log middleware configuration
MCP_LOG_MID_INCLUDE_PAYLOADS=true          # Whether to include request/response payloads in logs
MCP_LOG_MID_INCLUDE_PAYLOADS_LENGTH=true   # Whether to include payload lengths
MCP_LOG_MID_ESTIMATE_PAYLOAD_TOKENS=true   # Whether to estimate payload token count

# Logging configuration
MCP_LOGGING_LEVEL="WARNING"                # Log level: DEBUG, INFO, WARNING, ERROR
MCP_LOGGING_CONSOLE=false                  # Whether to output to console
MCP_LOGGING_FILE=true                      # Whether to output to file
MCP_LOGGING_FILE_PATH="dev_logs"           # Log file path
MCP_LOGGING_FILE_BASE_NAME="fund_nav_mcp"  # Log file name
MCP_LOGGING_BACKUP_COUNT=100               # Number of log backup files
MCP_LOGGING_MAX_FILE_SIZE=104857600        # Maximum size of a single log file (bytes)
MCP_LOGGING_JSON_FORMAT=true               # Whether to use JSON format
MCP_LOGGING_SEPARATE_ERROR_FILE=true       # Whether to separate error logs
MCP_LOGGING_ERROR_FILE_BASE_NAME="fund_nav_mcp_error"  # Error log file name

# Database configuration (example)
MCP_DATABASES__DEFAULT__DB_TYPE=sqlite
MCP_DATABASES__DEFAULT__DB_HOST=.cache/sqlite/default.db

# Cache configuration (example)
MCP_CACHES__DEFAULT__CACHE_TYPE=memory
```

**Configuration File Descriptions**:
- `.env`: System-level configuration (environment identifier, app name, configuration priority, etc.)
- `.env.local`: Environment-specific configuration (server, log, database, etc.)
- `.env.dev`: Development environment configuration template
- `.env.prod`: Production environment configuration template  
- `.env.test`: Test environment configuration template
- `.env.example`: Configuration example file

**Configuration Loading Order**:
1. `.env` file (system-level configuration)
2. `.env.local` file (environment-specific configuration)
3. Environment variables (override file configuration)
4. Code arguments (highest priority)

### Configuration Source Priority

Control the configuration source priority via the `MCP_CONFIG_PRIORITY` environment variable:

- `toml_first`: TOML > Environment variables > Explicit parameters (TOML file overrides everything)
- `env_first`: Environment variables > TOML > Explicit parameters (environment variables take precedence over files)
- `init_first`: Explicit parameters > Environment variables > TOML (code arguments take precedence, default behavior)
- `env_only`: Environment variables > Explicit parameters (ignore TOML file)
- `toml_only`: TOML > Explicit parameters (read from file only, ignore environment variables)

### TOML Configuration

The project supports TOML format configuration files, located in the `configs/` directory and named according to the environment (e.g., `config.dev.toml`).

#### Option 1: Using the UI Configuration Interface (Recommended)

The project automatically detects and generates default configurations at startup. Simply launch the UI interface to configure:
```bash
uv run fund-nav-mcp ui --dev-port 8080 --mcp-port 8000 --reload
```
After the first run, the system will create:
- `configs/config.dev.toml` (development environment)
- `configs/config.prod.toml` (production environment)
- `configs/config.test.toml` (test environment)

Visit `http://localhost:8080` for visual configuration management.

#### Option 2: Manual Creation of Configuration Files

You can also manually create configuration files, referring to the `configs/config.dev.toml` example:
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

#### Configuration Item Details

##### Database Configuration
Supports multiple database types. Full configuration parameters can be found in `fund_nav_mcp/models/schemas.py`:
```toml
[databases.default]
db_type = "sqlite"           # Database type: sqlite, mysql, postgresql, influxdb
db_host = "memory"           # Database host, default memory (in-memory database)
db_port = 0                  # Database port, 0 for SQLite
db_username = ""             # Database username, default null
db_password = ""             # Database password, default null
db_sql_echo = "close"        # SQL echo output: open/close
db_pool_size = 5             # Connection pool size, default 5
status = "Unknown"           # Database status: Unknown, Active, Inactive, Error, AuthFailed
```
**Database Type Descriptions**:
- **sqlite**: Local file database, `db_host` can be a file path or "memory" (in-memory database)
- **mysql**: MySQL database, requires host, port, username, password
- **postgresql**: PostgreSQL database, configuration similar to MySQL
- **influxdb**: InfluxDB time-series database

##### Cache Configuration
Cache configuration supports Redis. Full parameters can be found in `fund_nav_mcp/models/schemas.py`:
```toml
[caches.default]
cache_host = "127.0.0.1"     # Cache host, default 127.0.0.1
cache_port = 6379            # Cache port, default 6379
cache_pass = ""              # Cache password, default null
timeout = 5                  # Connection timeout (seconds), default 5
main_db = 0                  # Main database index, default 0
databases = 16               # Number of logical databases, default 16
key_prefix = ""              # Key prefix, default null
ttl_seconds = 300            # Cache expiration time (seconds), default 300
max_size = 1024              # Maximum cache size (MB), default 1024
cache_pool_size = 5          # Connection pool size, default 5
cache_type = "redis"         # Cache type, currently only supports redis
status = "Unknown"           # Cache status: Unknown, Active, Inactive, Error, AuthFailed
```

### Running the Server

#### Using UV (Recommended)

For details, see: [UV Run Documentation](https://docs.astral.sh/uv/guides/scripts/)

```bash
# Standard input/output mode (recommended for development)
uv run fund-nav-mcp stdio

# SSE server mode (for production)
uv run fund-nav-mcp sse --host 0.0.0.0 --port 8000

# Streamable HTTP mode
uv run fund-nav-mcp streamable-http --host 0.0.0.0 --port 8000

# UI development mode (launch Apps preview interface)
uv run fund-nav-mcp ui --dev-port 8080 --mcp-port 8000 --reload
```

#### Using Traditional Way

```bash
# Standard input/output mode
python -m fund_nav_mcp.server stdio

# SSE server mode
python -m fund_nav_mcp.server sse --host 0.0.0.0 --port 8000

# Streamable HTTP mode
python -m fund_nav_mcp.server streamable-http --host 0.0.0.0 --port 8000

# UI development mode
python -m fund_nav_mcp.server ui --dev-port 8080 --mcp-port 8000 --reload
```

### Running Mode Descriptions

- **stdio mode**: Standard input/output, suitable for integration with MCP clients
- **sse mode**: Server-Sent Events mode, supports web client connections
- **streamable-http mode**: HTTP streaming transfer mode
- **ui mode**: Starts the development interface for debugging and testing

## MCP Tools

### System Tools

#### Health Check Tool
- `health`: Checks the health status of the MCP server and returns whether the service is normal.

### Configuration Tools

#### Configuration Management Tools
- `get_all_config`: Get all configuration information
- `add_database`: Add database configuration
- `add_cache`: Add cache configuration
- `update_database`: Update database configuration
- `update_cache`: Update cache configuration
- `delete_database`: Delete database configuration
- `delete_cache`: Delete cache configuration

#### Configuration App Tool (UI Interface)
- `config_app`: Configuration application, provides a visual configuration interface.

### Usage Examples

Under development...

### Tool Tag Classification

- `sys_tool`: System-level tools (e.g., health check)
- `config_tool`: Configuration management tools
- Currently in the development phase, other tags will be gradually improved

## Development Guide

### Adding a New MCP Tool

1. Create a new tool file in the `fund_nav_mcp/tools/` directory
2. Define the tool function and use the `@tool()` decorator
3. If it is a global tool, add the `@global_tool()` decorator

Example:

```python
from typing import Dict, Any

from fastmcp.tools import tool

from fund_nav_mcp.tools import global_tool


@global_tool
@tool(
    name="get_fund_data",
    title="Get Fund Data",
    description="Get fund data, query fund NAV data by fund code and date",
    tags={"fund_tool"}
)
async def get_fund_data(fund_code: str, date: str) -> Dict[str, Any]:
    """
    Get fund data   
    
    Args:
        fund_code: Fund code
        date: Date
        
    Returns:
        dict: Fund NAV data
    """
    # Implementation logic...
    return {"fund_code": fund_code, "date": date, "nav": 1.2345}
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# With verbose output
pytest -v
```

## Deployment

### Docker Deployment

Under development...

## Troubleshooting

### Common Issues

#### 1. FastMCP Apps UI blank or console reports 404 / `t.custom is not a function` on Windows

**Cause**: FastMCP cached a failed front-end resource download (e.g., esm.sh temporarily unavailable).  
**Solution**: Delete the cache file and restart the service.

- **Windows (PowerShell)**:
  ```powershell
  Get-ChildItem -Path "$env:TEMP" -Filter "fastmcp-ext-apps-*bundle.json" | Remove-Item -Force
  ```

### Log Viewing

Log files are located in the `logs` directory by default.

## Contributing

Issues and Pull Requests are welcome!

1. Fork the project
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- Author: ramid
- Email: ramid@qq.com
- Project Repository: [GitHub Repository](https://github.com/RamidLab/fund-nav-mcp)

## Changelog

### v0.1.0 (2026-04-29)

- Initial release
- Basic MCP server framework
- Multi-source support
- Configuration management interface and tool integration

For detailed changes, see [CHANGELOG.md](CHANGELOG.md)