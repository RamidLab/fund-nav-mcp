from __future__ import annotations

__all__ = ['MCPSettings', 'setup_settings', 'get_settings', 'store_settings']

import os
from typing import Any, Dict, Mapping, cast, Union, Optional, Tuple, Annotated, Literal

import tomli_w
from pydantic import Field, model_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource, PydanticBaseSettingsSource

from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.models.schemas import (
    DatabaseConfig, CacheConfig, SQLiteConfig, MySQLConfig, PostgresqlConfig, InfluxDBConfig, RedisConfig)
from fund_nav_mcp.utils.enums import Errcode
from fund_nav_mcp.utils.path_utils import get_toml_config

_TOML_CONFIG = get_toml_config()


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
    databases: Dict[str, Annotated[
        Union[
            Annotated[SQLiteConfig, "sqlite"],
            Annotated[MySQLConfig, "mysql"],
            Annotated[PostgresqlConfig, "postgresql"],
            Annotated[InfluxDBConfig, "influxdb"],
        ],
        Field(discriminator="db_type")
    ]] = Field(default_factory=dict)
    caches: Dict[str, Annotated[
        Union[
            Annotated[RedisConfig, "redis"],
        ],
        Field(discriminator="cache_type")
    ]] = Field(default_factory=dict)

    cache_enabled: bool = Field(default=True, title="是否启用缓存", description="是否启用缓存，默认启用")

    timezone: str = "Asia/Shanghai"
    default_currency: str = "CNY"  # 用于处理货币相关的计算和显示，默认人民币

    model_config = SettingsConfigDict(
        toml_file=_TOML_CONFIG,  # TOML 文件路径
        env_prefix="MCP_",  # 环境变量前缀，如 MCP_DEBUG=true
        env_nested_delimiter="__",  # 嵌套字段分隔符，如 MCP_DATABASE__URL=xxx
        validate_assignment=True,
        extra="ignore",
    )

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not _TOML_CONFIG.exists():
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
        """设置默认数据库和缓存配置。"""
        if not self.databases:
            default_db = DatabaseConfig()
            default_db.test_connection()
            self.databases = {"default": default_db}
        if self.cache_enabled and not self.caches:
            default_cache = CacheConfig()
            self.caches = {"default": default_cache}
        return self

    def get_storage(self, config: Union[DatabaseConfig, CacheConfig]) -> Tuple[dict, str]:
        """根据配置类型获取对应的存储字典。"""
        if isinstance(config, DatabaseConfig):
            return self.databases, "数据库"
        elif isinstance(config, CacheConfig):
            return self.caches, "缓存"
        else:
            raise ValueError(f"未知配置类型: {type(config)}")

    def _add_config(self, name: str, config: Union[DatabaseConfig, CacheConfig]) -> UtilResponse[None]:
        """
        添加配置项

        Args:
            name: 配置项名称
            config: 配置项值

        Returns:
            通用响应
        """
        storage, config_type = self.get_storage(config)
        if name not in storage:
            storage[name] = config
            return UtilResponse(code=Errcode.SUCCESS, message=f"{config_type}配置 {name} 添加成功")
        return UtilResponse(code=Errcode.UNIQUE_CONFLICT, message=f"{config_type}配置 {name} 已存在，无法添加")

    def _update_config(
            self, name: str, config: Union[DatabaseConfig, CacheConfig], new_name: Optional[str]
    ) -> UtilResponse[None]:
        """
        更新配置项

        Args:
            name: 配置项名称
            config: 配置项值
            new_name: 新配置项名称，可选

        Returns:
            通用响应
        """
        storage, config_type = self.get_storage(config)
        if name not in storage:
            return UtilResponse(code=Errcode.RECORD_NOT_FOUND, message=f"{config_type}配置 {name} 不存在，无法修改")

        if new_name:
            if new_name in storage:
                return UtilResponse(code=Errcode.UNIQUE_CONFLICT,
                                    message=f"{config_type}配置 {new_name} 已存在，无法修改")
            # 删除旧键
            del storage[name]
            name = new_name

        storage[name] = config
        return UtilResponse(code=Errcode.SUCCESS, message=f"{config_type}配置 {name} 修改成功")

    def _delete_config(self, _class: Literal["db", "cache"], name: str) -> UtilResponse[None]:
        """
        删除配置项

        Args:
            name: 配置项名称

        Returns:
            通用响应
        """
        if _class == "db":
            if name not in self.databases:
                return UtilResponse(code=Errcode.RECORD_NOT_FOUND, message=f"数据库配置 {name} 不存在，无法删除")
            del self.databases[name]
            return UtilResponse(code=Errcode.SUCCESS, message=f"数据库配置 {name} 删除成功")
        elif _class == "cache":
            if name not in self.caches:
                return UtilResponse(code=Errcode.RECORD_NOT_FOUND, message=f"缓存配置 {name} 不存在，无法删除")
            del self.caches[name]
            return UtilResponse(code=Errcode.SUCCESS, message=f"缓存配置 {name} 删除成功")
        else:
            return UtilResponse(code=Errcode.TOOL_INVALID_PARAMS, message=f"未知配置类型: {_class}")

    def add_database(self, db_name: str, db_config: DatabaseConfig) -> UtilResponse[None]:
        """添加数据库配置"""
        return self._add_config(db_name, db_config)

    def update_database(self, db_name: str, db_config: DatabaseConfig, new_db_name: str = None) -> UtilResponse[None]:
        """更新数据库配置"""
        return self._update_config(db_name, db_config, new_db_name)

    def delete_database(self, db_name: str) -> UtilResponse[None]:
        """删除数据库配置"""
        return self._delete_config("db", db_name)

    def add_cache(self, cache_name: str, cache_config: CacheConfig) -> UtilResponse[None]:
        """添加缓存配置"""
        return self._add_config(cache_name, cache_config)

    def update_cache(
            self, cache_name: str, cache_config: CacheConfig, new_cache_name: str = None
    ) -> UtilResponse[None]:
        """更新缓存配置"""
        return self._update_config(cache_name, cache_config, new_cache_name)

    def delete_cache(self, cache_name: str) -> UtilResponse[None]:
        """删除缓存配置"""
        return self._delete_config("cache", cache_name)

    @staticmethod
    def test_connection(
            config: Union[DatabaseConfig, CacheConfig]
    ) -> UtilResponse[Union[DatabaseConfig, CacheConfig]]:
        """
        测试数据库或缓存连接。

        Args:
            config: 数据库或缓存配置

        Returns:
            UtilResponse
        """

        result, error_msg, status = config.test_connection()
        config.status = status
        return UtilResponse(
            code=Errcode.SUCCESS if result else (Errcode.DB_CONNECTION_FAILED
                                                 if isinstance(config, DatabaseConfig)
                                                 else Errcode.CACHE_CONNECTION_FAILED),
            message=f"{'数据库' if isinstance(config, DatabaseConfig) else '缓存'}连接测试成功" if result else f"{error_msg}",
            data=config
        )

    def _prepare_for_toml(self, obj) -> dict | list | str:
        """递归将 SecretStr 转为明文，其余保持原样，使对象可被 TOML 序列化。"""
        if isinstance(obj, SecretStr):
            return obj.get_secret_value()
        if isinstance(obj, dict):
            return {k: self._prepare_for_toml(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._prepare_for_toml(v) for v in obj]
        return obj

    def _to_toml(self) -> str:
        """
        将当前配置转换为 TOML 字符串。

        Returns:
             TOML 字符串
        """
        config = self.model_dump(exclude_none=True)
        safe_config = self._prepare_for_toml(config)
        return tomli_w.dumps(cast(Mapping[str, Any], safe_config))

    def store(self) -> None:
        """
        将当前配置保存到 TOML 文件。

        Returns:
            None
        """
        _TOML_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        _TOML_CONFIG.write_text(self._to_toml(), encoding="utf-8")


_settings = None


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


def store_settings(settings: MCPSettings) -> None:
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
