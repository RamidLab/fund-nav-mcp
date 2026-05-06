import os

from fund_nav_mcp.models.schemas import LoggingConfig
from fund_nav_mcp.utils.log import log_basic_config, LogLevel

log_cfg = LoggingConfig(**{x.replace("MCP_LOGGING_", "").lower(): os.getenv(x, None)
                           for x in os.environ.keys() if x.startswith("MCP_LOGGING")})
# 初始化日志模块
log_basic_config(
    level=LogLevel.from_name(log_cfg.level, LogLevel.INFO),
    console=log_cfg.console,
    file=log_cfg.file,
    file_path=log_cfg.file_path,
    file_base_name=log_cfg.file_base_name,
    backup_count=log_cfg.backup_count,
    max_file_size=log_cfg.max_file_size,
    json_format=log_cfg.json_format,
    separate_error_file=log_cfg.separate_error_file,
    error_file_base_name=log_cfg.error_file_base_name,
)