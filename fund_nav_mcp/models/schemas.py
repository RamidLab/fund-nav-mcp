__all__ = ["DatabaseConfig", "CacheConfig", "LoggingConfig"]

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from fund_nav_mcp.utils.path_utils import PROJECT_ROOT


class DatabaseConfig(BaseModel):
    """
    数据库配置

    Args:
        url (str): 数据库连接 URL，默认 ".cache/sqlite/funds.db"
        echo (bool): 是否开启 SQL 日志，默认 False
        pool_size (int): 连接池大小，默认 5
    """
    url: str = Field(
        default=".cache/sqlite/funds.db",
        description="SQLite 数据库文件路径（相对路径相对于项目根目录，支持绝对路径）"
    )
    echo: bool = False
    pool_size: int = 5

    @property
    def _url(self) -> str:
        """生成 SQLAlchemy 连接 URL，并自动创建父目录"""
        if self.url == "memory":
            return "sqlite:///:memory:"

        path = Path(self.url)
        if not path.is_absolute():
            path = PROJECT_ROOT / path

        # 自动创建父目录
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"


class CacheConfig(BaseModel):
    """
    缓存配置

    Args:
        ttl_seconds: 缓存过期时间，默认 300 秒
        max_size: 缓存最大大小，默认 1000
        backend: 缓存后端，默认 memory，可选 memory, redis
        redis_url: Redis 连接字符串，默认 None
    """
    ttl_seconds: int = 300
    max_size: int = 1000
    backend: str = "memory"  # memory, redis
    redis_url: Optional[str] = None


class LoggingConfig(BaseModel):
    """
    日志配置

    Args:
        level: 日志级别，默认 INFO
        console: 是否开启控制台日志，默认 False
        file: 是否开启文件日志，默认 False
        file_path: 日志文件路径，默认 logs
        backup_count: 日志文件备份数量，默认 100
        max_file_size: 日志文件最大大小，默认 100MB
        json_format: 是否使用 JSON 格式，默认 True
        separate_error_file: 是否分离错误日志（ERROR+ 写入单独文件），默认 False
        error_file_base_name: 错误日志文件基础名称，如果未指定，自动使用 file_base_name + "_error"，默认 None
    """
    level: str = "INFO"
    console: bool = True
    file: bool = False
    file_path: str = "logs"
    file_base_name: str = "fund_nav_mcp"
    backup_count: int = 100
    max_file_size: int = 100 * 1024 * 1024
    json_format: bool = True
    separate_error_file: bool = False
    error_file_base_name: Optional[str] = None
