__all__ = [
    "DatabaseConfig", "CacheConfig",
    "SQLiteConfig", "MySQLConfig", "PostgresqlConfig", "InfluxDBConfig", "RedisConfig",
    "LoggingConfig"
]

from functools import lru_cache
from pathlib import Path
from typing import Optional, Literal, Tuple, TypeVar, Annotated, Union

from pydantic import BaseModel, Field, SecretStr, TypeAdapter

from fund_nav_mcp.models import StorageConfigBase
from fund_nav_mcp.utils.enums import NodeStatus
from fund_nav_mcp.utils.path_utils import PROJECT_ROOT

T = TypeVar("T")


@lru_cache(maxsize=1)
def _get_db_adapter() -> TypeAdapter:
    """使用单例模式获取数据库适配器"""
    return TypeAdapter(
        Annotated[
            Union[
                Annotated[SQLiteConfig, "sqlite"],
                Annotated[MySQLConfig, "mysql"],
                Annotated[PostgresqlConfig, "postgresql"],
                Annotated[InfluxDBConfig, "influxdb"],
            ],
            Field(discriminator="db_type")
        ]
    )


@lru_cache(maxsize=1)
def _get_cache_adapter() -> TypeAdapter:
    """使用单例模式获取缓存适配器"""
    return TypeAdapter(
        Annotated[
            Union[
                Annotated[RedisConfig, "redis"],
            ],
            Field(discriminator="cache_type")
        ]
    )


class DatabaseConfig(StorageConfigBase):
    """数据库配置基类"""
    db_type: Literal["sqlite", "mysql", "postgresql", "influxdb"] = Field(default="sqlite", title="数据库类型")
    db_host: str = Field(default="memory", title="数据库主机")
    db_port: int = Field(default=80, title="数据库端口")
    db_sql_echo: Literal["open", "close"] = Field(default="close", title="SQL命令输出")
    db_pool_size: int = Field(default=5, title="连接池大小")

    status: NodeStatus = Field(default=NodeStatus.Unknown, title="数据库状态")

    def __new__(cls, **data):
        if cls is DatabaseConfig:
            adapter = _get_db_adapter()
            data.setdefault("db_type", "sqlite")
            return adapter.validate_python(data)
        return object.__new__(cls)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """自定义模型验证方法，根据类型选择数据库适配器"""
        if cls is DatabaseConfig:
            return _get_db_adapter().validate_python(obj, **kwargs)
        return super().model_validate(obj, **kwargs)

    @property
    def url(self) -> str:
        raise NotImplementedError("url 属性未实现")

    def _do_test(self, timeout: int) -> None:
        raise NotImplementedError("_do_test 方法未实现")

    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        raise NotImplementedError("_classify_error 方法未实现")


class SQLiteConfig(DatabaseConfig):
    """SQLite 数据库配置"""
    db_type: Literal["sqlite"] = "sqlite"
    db_host: str = Field(
        default="memory",
        title="数据库主机",
        min_length=1,
        description="默认 memory，Sqlite 数据库可选文件路径（路径相对于项目根目录，支持绝对路径）"
    )

    def _build_url(self, async_driver: bool = True) -> str:
        """内部方法：根据需要返回同步或异步连接字符串"""
        prefix = "sqlite+aiosqlite" if async_driver else "sqlite"
        if self.db_host == "memory":
            return f"{prefix}:///:memory:"
        path = Path(self.db_host or "")
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}:///{path.as_posix()}"

    @property
    def url(self) -> str:
        return self._build_url(async_driver=True)

    def _do_test(self, timeout: int) -> None:
        from sqlalchemy import create_engine, text as sa_text
        engine = create_engine(
            self._build_url(async_driver=False),
            echo=self.db_sql_echo == "open",
        )
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        engine.dispose()

    # TODO:后面其他几个都同步sqlite现在的更新
    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        return NodeStatus.Error, f"SQLite 错误: {getattr(exc, 'orig', exc)}"


class MySQLConfig(DatabaseConfig):
    """MySQL 数据库配置"""
    db_type: Literal["mysql"] = "mysql"
    db_host: str = Field(default="127.0.0.1", title="数据库主机")
    db_port: int = Field(default=3306, title="数据库端口号")
    db_username: str = Field(default="root", title="数据库用户名")
    db_password: SecretStr = Field(default="root", title="数据库密码")
    db_main: Optional[str] = Field(default=None, title="数据库主键")

    def _build_url(self, async_driver: bool = True) -> str:
        driver = "asyncmy" if async_driver else "pymysql"
        user = self.db_username
        pwd = self.db_password.get_secret_value()
        base = f"mysql+{driver}://{user}:{pwd}@{self.db_host}:{self.db_port}"
        if self.db_main:
            base += f"/{self.db_main}"
        return base

    @property
    def url(self) -> str:
        return self._build_url(async_driver=True)

    def _do_test(self, timeout: int) -> None:
        from sqlalchemy import create_engine, text as sa_text
        engine = create_engine(
            self._build_url(async_driver=False),
            echo=self.db_sql_echo == "open",
            connect_args={"connect_timeout": timeout}
        )
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        engine.dispose()

    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        return self._classify_mysql_error(exc)

    @staticmethod
    def _classify_mysql_error(exc: Exception) -> Tuple[NodeStatus, str]:
        import pymysql
        orig = getattr(exc, 'orig', exc)
        if isinstance(orig, pymysql.err.OperationalError):
            code = orig.args[0] if orig.args else None
            if code in (2003, 2002):
                return NodeStatus.Inactive, "MySQL 服务未启动或主机/端口不可达"
            if code == 1045:
                return NodeStatus.AuthFailed, "MySQL 用户名或密码错误"
            if code == 1044:
                return NodeStatus.AuthFailed, "MySQL 用户无权访问该数据库"
        elif isinstance(orig, pymysql.err.InternalError):
            return NodeStatus.Error, f"MySQL 内部错误: {orig}"
        elif isinstance(orig, pymysql.err.ProgrammingError):
            return NodeStatus.Error, f"MySQL 语法/配置错误: {orig}"
        return NodeStatus.Error, f"MySQL 错误: {orig}"


class PostgresqlConfig(DatabaseConfig):
    """PostgreSQL 数据库配置"""
    db_type: Literal["postgresql"] = "postgresql"
    db_host: str = Field(default="127.0.0.1", title="数据库主机")
    db_port: int = Field(default=5432, title="数据库端口号")
    db_username: str = Field(default="postgres", title="数据库用户名")
    db_password: SecretStr = Field(default="postgres", title="数据库密码")
    db_main: Optional[str] = Field(default=None, title="数据库主键")

    def _build_url(self, async_driver: bool = True) -> str:
        driver = "asyncpg" if async_driver else "psycopg2"
        user = self.db_username
        pwd = self.db_password.get_secret_value()
        base = f"postgresql+{driver}://{user}:{pwd}@{self.db_host}:{self.db_port}"
        if self.db_main:
            base += f"/{self.db_main}"
        return base

    @property
    def url(self) -> str:
        return self._build_url(async_driver=True)

    def _do_test(self, timeout: int) -> None:
        from sqlalchemy import create_engine, text as sa_text
        engine = create_engine(
            self._build_url(async_driver=False),
            echo=self.db_sql_echo == "open",
            connect_args={"connect_timeout": timeout}
        )
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        engine.dispose()

    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        return self._classify_pg_error(exc)

    @staticmethod
    def _classify_pg_error(exc: Exception) -> Tuple[NodeStatus, str]:
        import psycopg2
        orig = getattr(exc, 'orig', exc)
        if isinstance(orig, psycopg2.Error):
            pg_code = getattr(orig, 'pgcode', "")  # noqa
            if pg_code:
                if pg_code.startswith('08'):
                    return NodeStatus.Inactive, f"PostgreSQL 服务未启动或连接被拒绝 (SQLSTATE: {pg_code})"
                if pg_code == '28P01':
                    return NodeStatus.AuthFailed, "PostgreSQL 密码错误"
                if pg_code == '28000':
                    return NodeStatus.AuthFailed, "PostgreSQL 认证失败 (用户或配置错误)"
                if pg_code == '53300':
                    return NodeStatus.Error, "PostgreSQL 连接数过多"
                if pg_code in ('3D000', '3F000'):
                    return NodeStatus.Error, "PostgreSQL 数据库或 schema 不存在"
        error_msg = str(orig)
        if 'connection refused' in error_msg.lower() or 'is the server running' in error_msg:
            return NodeStatus.Inactive, "PostgreSQL 服务未启动或端口不通"
        if 'could not translate host name' in error_msg.lower() or 'name or service not known' in error_msg.lower():
            return NodeStatus.Inactive, "PostgreSQL 主机地址无法解析，请检查网络配置"
        if 'password authentication failed' in error_msg.lower():
            return NodeStatus.AuthFailed, "PostgreSQL 密码认证失败"
        return NodeStatus.Error, f"PostgreSQL 错误: {orig}"


class InfluxDBConfig(DatabaseConfig):
    """InfluxDB 配置"""
    db_type: Literal["influxdb"] = Field(default="influxdb", title="数据库类型")
    db_host: str = Field(default="localhost", title="数据库主机")
    db_port: int = Field(default=8086, title="数据库端口")
    db_ssl_enabled: bool = Field(default=False, title="是否启用 HTTPS")
    db_main: Optional[str] = Field(..., title="默认桶")
    influxdb_org: str = Field(..., title="组织")
    influxdb_token: SecretStr = Field(..., alias="influxdb_token", title="Token")

    @property
    def url(self) -> str:
        scheme = "https" if self.db_ssl_enabled else "http"
        return f"{scheme}://{self.db_host}:{self.db_port}"

    def _do_test(self, timeout: int) -> None:
        from influxdb_client import InfluxDBClient

        tok = self.influxdb_token.get_secret_value()
        with InfluxDBClient(url=self.url, token=tok, org=self.influxdb_org,
                            timeout=timeout * 1000) as client:
            if not client.ping():
                raise ConnectionError("InfluxDB ping 失败")

    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        return self._classify_influx_error(exc)

    @staticmethod
    def _classify_influx_error(exc: Exception) -> Tuple[NodeStatus, str]:
        import requests
        from influxdb_client.rest import ApiException

        orig = getattr(exc, 'orig', exc)
        if isinstance(orig, (requests.ConnectionError, ConnectionRefusedError, ConnectionError)):
            return NodeStatus.Inactive, "InfluxDB 服务未启动或网络不可达"
        if isinstance(orig, (requests.Timeout, TimeoutError)):
            return NodeStatus.Inactive, "InfluxDB 连接超时"
        if isinstance(orig, ApiException):
            if orig.status == 401:
                return NodeStatus.AuthFailed, "InfluxDB 认证失败 (Token 错误)"
            if orig.status == 403:
                return NodeStatus.AuthFailed, "InfluxDB 无权限访问"
            return NodeStatus.Error, f"InfluxDB API 错误: HTTP {orig.status}"
        return NodeStatus.Error, f"InfluxDB 错误: {exc}"


class CacheConfig(StorageConfigBase):
    """缓存配置基类（自动注册子类）"""
    cache_type: Literal["redis"] = Field(default="redis", title="缓存类型")
    cache_host: str = Field(default="127.0.0.1", title="缓存主机")
    cache_port: int = Field(default=6379, title="缓存绑定端口")

    status: NodeStatus = Field(default=NodeStatus.Unknown, title="缓存服务状态")

    def __new__(cls, **data):
        if cls is CacheConfig:
            adapter = _get_cache_adapter()
            data.setdefault("cache_type", "redis")
            return adapter.validate_python(data)
        return object.__new__(cls)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """自定义模型验证方法，根据类型选择缓存适配器"""
        if cls is CacheConfig:
            return _get_cache_adapter().validate_python(obj, **kwargs)
        return super().model_validate(obj, **kwargs)

    @property
    def url(self) -> str:
        raise NotImplementedError("url 属性未实现")

    def _do_test(self, timeout: int) -> None:
        raise NotImplementedError("_do_test 方法未实现")

    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        raise NotImplementedError("_classify_error 方法未实现")


class RedisConfig(CacheConfig):
    """
    缓存配置

    Args:
        cache_host: 缓存主机，默认 None
        cache_port: 缓存端口，默认 None
        cache_pass: 缓存密码，默认 None
        timeout: 缓存超时时间，默认 5 秒
        databases: 逻辑数据库数量，默认 16
        ttl_seconds: 缓存过期时间，默认 300 秒
        max_size: 缓存最大大小，默认 1024MB
        cache_type: 缓存类型，默认 memory，可选 memory, redis
        status: 缓存服务状态，默认 Unknown
    """
    cache_type: Literal["redis"] = Field(default="redis", title="缓存类型")
    cache_host: str = Field(default="127.0.0.1", title="缓存主机")
    cache_port: int = Field(default=6379, title="缓存绑定端口")
    cache_pass: Optional[SecretStr] = Field(default=None, title="缓存密码")
    cache_main: int = Field(default=0, title="主数据库索引")
    databases: int = Field(default=16, title="逻辑数据库数量", description="默认16个，索引从0到15")
    timeout: int = Field(default=5, title="缓存超时时间（秒）", description="缓存超时时间（秒）")
    key_prefix: Optional[str] = Field(default=None, title="键前缀", description="键前缀，默认空字符串")
    ttl_seconds: int = Field(default=300, title="缓存过期时间（秒）")
    max_size: int = Field(default=1024, title="缓存最大大小（MB）")
    cache_pool_size: int = Field(
        default=10,
        title="连接池最大连接数",
        description="根据预估的并发量调整，默认10。对于Async Web应用，建议设为5-20。"
    )

    @property
    def url(self) -> str:
        auth = f"{self.cache_pass.get_secret_value()}@" if self.cache_pass else ""
        return f"redis://{auth}{self.cache_host}:{self.cache_port}/{self.cache_main}"

    def _do_test(self, timeout: int) -> None:
        """
        执行 Redis 连接测试，包括 ping 和数据库选择

        Args:
            timeout: 连接超时秒数（覆盖 config.timeout）
        Returns:
            None
        """
        import redis
        # 处理密码（SecretStr -> 明文）
        password = self.cache_pass.get_secret_value() if self.cache_pass else None

        # 创建 Redis 客户端（连接池延迟建立实际连接）
        client = redis.Redis(
            host=self.cache_host,
            port=self.cache_port,
            password=password,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
            decode_responses=False,
        )

        # 测试基本连通性（ping 失败会抛出异常）
        client.ping()

        # 测试目标数据库是否可用（有效索引范围 0 ~ databases-1）
        cache_index = self.cache_main
        if cache_index < 0 or cache_index >= self.databases:
            raise ValueError(
                f"数据库索引 {cache_index} 超出允许范围 [0, {self.databases - 1}]，"
                f"请检查 main_db 设置"
            )

        # 执行 SELECT 命令验证数据库是否存在
        try:
            client.execute_command("SELECT", cache_index)
        except redis.exceptions.ResponseError as e:
            # Redis 返回 "ERR DB index is out of range"
            raise redis.exceptions.ResponseError(
                f"数据库索引 {cache_index} 无效或超出服务器允许范围: {e}"
            ) from e

        # 关闭连接（可选，Redis 连接会随对象销毁自动释放）
        client.close()

    def _classify_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        return self._classify_redis_error(exc)

    @staticmethod
    def _classify_redis_error(exc: Exception) -> Tuple[NodeStatus, str]:
        """
        分类 Redis 异常，返回状态枚举和消息。

        Args:
            exc: Redis 异常对象
        Returns:
            - 状态枚举
            - 响应消息
        """

        import redis.exceptions as redis_exc
        # 认证/授权类异常 (优先于 ConnectionError)
        if isinstance(exc, (redis_exc.AuthenticationError,
                            redis_exc.AuthorizationError,
                            redis_exc.NoPermissionError,
                            redis_exc.AuthenticationWrongNumberOfArgsError)):
            return NodeStatus.AuthFailed, "Redis 认证失败（用户名/密码错误或权限不足）"

        # 只读模式（也可视为权限问题）
        if isinstance(exc, redis_exc.ReadOnlyError):
            return NodeStatus.AuthFailed, "Redis 当前处于只读模式，无法执行写操作"

        # 连接层异常（服务未启动、网络不通、超时等）
        if isinstance(exc, redis_exc.ConnectionError):
            msg = str(exc).lower()
            if "invalid password" in msg or "authentication" in msg:
                # 保险：部分版本将密码错误包装在 ConnectionError 中
                return NodeStatus.AuthFailed, "Redis 认证失败（密码错误）"
            if "connection refused" in msg or "timed out" in msg:
                return NodeStatus.Inactive, "Redis 服务未启动或主机/端口不可达"
            if isinstance(exc, redis_exc.BusyLoadingError):
                return NodeStatus.Inactive, "Redis 正在加载持久化数据，请稍后重试"
            if isinstance(exc, redis_exc.MaxConnectionsError):
                return NodeStatus.Error, "Redis 连接池已达上限，请增加 max_connections 或释放连接"
            return NodeStatus.Inactive, f"Redis 连接失败: {exc}"

        # 超时异常（单独处理，redis-py 中为 TimeoutError 继承自 ConnectionError，但应独立）
        if isinstance(exc, redis_exc.TimeoutError):
            return NodeStatus.Inactive, "Redis 连接或命令执行超时"

        # 服务端错误（内存不足、集群宕机等）
        if isinstance(exc, redis_exc.OutOfMemoryError):
            return NodeStatus.Error, "Redis 内存不足且无法自动驱逐，请检查 max memory 策略"
        if isinstance(exc, (redis_exc.ClusterDownError, redis_exc.MasterDownError)):
            return NodeStatus.Inactive, "Redis 集群或主节点不可用"
        if isinstance(exc, (redis_exc.MovedError, redis_exc.AskError,
                            redis_exc.TryAgainError, redis_exc.ClusterCrossSlotError)):
            return NodeStatus.Error, f"Redis 集群配置错误或跨槽操作: {exc}"

        # 响应错误（如 SELECT 无效数据库）
        if isinstance(exc, redis_exc.ResponseError):
            err_lower = str(exc).lower()
            if "db index" in err_lower or "out of range" in err_lower:
                return NodeStatus.Error, f"Redis 数据库索引超出范围: {exc}"
            return NodeStatus.Error, f"Redis 命令执行错误: {exc}"

        # 其他未捕获异常
        return NodeStatus.Error, f"Redis 错误: {exc}"


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
