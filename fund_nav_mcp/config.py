from __future__ import annotations

__all__ = ['MCPSettings', 'setup_settings', 'get_settings', 'store_settings']

import os
from typing import Any, Dict

import tomli_w
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource, PydanticBaseSettingsSource

from fund_nav_mcp.models.schemas import DatabaseConfig, CacheConfig, LoggingConfig
from fund_nav_mcp.utils.log import get_logger, log_basic_config, LogLevel
from fund_nav_mcp.utils.path_utils import get_config_path

_CONFIG_PATH = get_config_path()

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

logger = get_logger(__name__)


class MCPSettings(BaseSettings):
    """
    应用配置类

    包含数据库、缓存、日志配置等。

    Attributes:
        databases (Dict[str, DatabaseConfig]): 数据库配置字典，键为数据库名称
        caches (Dict[str, CacheConfig]): 缓存配置字典，键为缓存名称
        timezone (str): 时区，默认 Asia/Shanghai
        default_currency (str): 默认货币，默认 CNY
    """
    databases: Dict[str, DatabaseConfig] = Field(default_factory=dict)
    caches: Dict[str, CacheConfig] = Field(default_factory=dict)

    timezone: str = "Asia/Shanghai"
    default_currency: str = "CNY"  # 用于处理货币相关的计算和显示，默认人民币

    model_config = SettingsConfigDict(
        toml_file=_CONFIG_PATH,  # TOML 文件路径
        env_prefix="MCP_",  # 环境变量前缀，如 MCP_DEBUG=true
        env_nested_delimiter="__",  # 嵌套字段分隔符，如 MCP_DATABASE__URL=xxx
        validate_assignment=True,
        extra="ignore",
    )

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not _CONFIG_PATH.exists():
            self.store()

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        自定义配置源顺序:

        变量名称：MCP_CONFIG_PRIORITY
        环境变量值        优先级顺序（从高到低）	        说明
        "toml_first"	TOML > 环境变量 > 显式参数	    TOML 文件覆盖一切
        "env_first"	    环境变量 > TOML > 显式参数	    环境变量优先于文件
        "init_first"	显式参数 > 环境变量 > TOML	    代码中直接传参优先（默认行为）
        "env_only"	    环境变量 > 显式参数（忽略 TOML）	不使用 TOML 文件
        "toml_only"	    TOML > 显式参数（忽略环境变量）	只读文件，忽略环境变量
        """
        if os.getenv("MCP_CONFIG_PRIORITY") == "toml_first":
            return (
                TomlConfigSettingsSource(settings_cls), env_settings, init_settings,
            )
        elif os.getenv("MCP_CONFIG_PRIORITY") == "env_first":
            return (
                env_settings, TomlConfigSettingsSource(settings_cls), init_settings,
            )
        elif os.getenv("MCP_CONFIG_PRIORITY") == "toml_only":
            return (
                TomlConfigSettingsSource(settings_cls), init_settings,
            )
        elif os.getenv("MCP_CONFIG_PRIORITY") == "env_only":
            return (
                env_settings, init_settings,
            )
        else:
            return (
                init_settings, env_settings, TomlConfigSettingsSource(settings_cls),
            )

    @model_validator(mode='after')
    def set_default_db_with_cache(self) -> 'MCPSettings':
        if not self.databases:
            self.databases = {"default": DatabaseConfig()}
        if not self.caches:
            self.caches = {"default": CacheConfig()}
        return self

    def _to_toml(self) -> str:
        """
        将当前配置转换为 TOML 字符串。

        Returns:
             TOML 字符串
        """
        return tomli_w.dumps(self.model_dump(exclude_none=True))

    def store(self) -> None:
        """
        将当前配置保存到 TOML 文件。

        Returns:
            None
        """
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(self._to_toml(), encoding="utf-8")


_settings: MCPSettings | None = None


def setup_settings() -> MCPSettings:
    """
    初始化应用配置实例。

    Returns:
         MCPSettings 实例
    """
    global _settings
    _settings = MCPSettings()
    return _settings


def get_settings(reload: bool = False) -> MCPSettings:
    """
    获取当前应用配置实例。

    Args:
        reload: 是否重新加载配置文件，默认 False
    Returns:
        MCPSettings 实例
    """
    global _settings
    if _settings is None or reload:
        _settings = MCPSettings()
    return _settings


def store_settings(settings: MCPSettings | None = None) -> None:
    """
    保存当前应用配置到 TOML 文件。

    Args:
        settings: MCPSettings 实例，默认 None，如果为 None 则使用当前实例
    Returns:
        None
    """
    if settings is None:
        settings = get_settings()
    settings.store()
