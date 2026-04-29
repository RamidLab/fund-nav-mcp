__all__ = ["DatabaseConfig", "CacheConfig", "LoggingConfig"]

from pathlib import Path
from typing import Optional, Literal, Tuple

from pydantic import BaseModel, Field, SecretStr

from fund_nav_mcp.utils.enums import NodeStatus
from fund_nav_mcp.utils.path_utils import PROJECT_ROOT


class DatabaseConfig(BaseModel):
    """
    数据库配置

    Args:
        db_type: 数据库类型，默认 sqlite，可选 sqlite, mysql, postgresql, influxdb
        db_host: 数据库主机，默认 None
        db_port: 数据库端口号，默认 None
        db_username: 数据库用户名，默认 None
        db_password: 数据库密码，默认 None
        db_sql_echo: 是否开启 SQL 命令输出，默认 False
        db_pool_size: 连接池大小，默认 5
        status: 数据库状态，默认 Active
    """
    db_type: Literal[
        "sqlite", "mysql", "postgresql", "influxdb"
    ] = Field(default="sqlite", title="数据库类型", description="数据库类型，默认 sqlite")
    db_host: Optional[str] = Field(
        default="memory",
        title="数据库主机",
        description="数据库主机，默认 memory，可选文件路径（路径相对于项目根目录，支持绝对路径），如 .cache/sqlite/default.db"
    )
    db_port: int = Field(default=0, title="数据库端口号", description="数据库端口号，默认 None")
    db_username: Optional[str] = Field(default=None, title="数据库用户名", description="数据库用户名，默认 None")
    db_password: Optional[SecretStr] = Field(default=None, title="数据库密码", description="数据库密码，默认 None")
    db_sql_echo: Literal["open", "close"] = Field(default="close", title="SQL命令输出", description="SQL命令输出")
    db_pool_size: int = Field(default=5, title="连接池大小", description="连接池大小，默认 5")
    status: NodeStatus = Field(default=NodeStatus.Unknown, title="数据库状态", description="数据库状态，默认 Unknown")

    @property
    def db_url(self) -> str:
        """生成 SQLAlchemy 连接 URL，并自动创建父目录"""
        if self.db_type == "sqlite" and self.db_host == "memory":
            return "sqlite:///:memory:"
        elif self.db_type == "mysql" and self.db_port > 0:
            return "mysql+pymysql://{}:{}@{}:{}".format(
                self.db_username, self.db_password, self.db_host, self.db_port
            )
        elif self.db_type == "postgresql" and self.db_port > 0:
            return "postgresql://{}:{}@{}:{}".format(
                self.db_username, self.db_password, self.db_host, self.db_port
            )
        elif self.db_type == "influxdb" and self.db_port > 0:
            return "influxdb://{}:{}@{}:{}".format(
                self.db_username, self.db_password, self.db_host, self.db_port
            )
        else:
            path = Path(self.db_host or "")
            if not path.is_absolute():
                path = PROJECT_ROOT / path

            # 自动创建父目录
            path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{path.as_posix()}"

    def test_connection(self, timeout: int = 5) -> Tuple[bool, str, NodeStatus]:
        """
        测试数据库连接，并根据结果更新 self.status。

        Args:
            timeout: 连接超时秒数，仅对远程数据库有效。

        Returns:
            - 连接成功返回 True，否则 False。
            - 错误消息（如果有）
            - 数据库状态
        """
        try:
            if self.db_type == "influxdb":
                self._test_influxdb(timeout)
            else:
                self._test_rdbms(timeout)

            self.status = NodeStatus.Active
            return True, "", self.status
        except Exception as e:
            status, message = self._classify_db_error(e)
            self.status = status
            return False, message, self.status

    def _classify_db_error(self, exc: Exception) -> Tuple[NodeStatus, str]:
        """
        根据数据库类型和异常特征，返回 (状态, 用户友好消息)。

        Args:
            exc: 数据库异常对象。

        Returns:
            - 数据库状态
            - 响应消息
        """
        if self.db_type == "mysql":
            return self._classify_mysql_error(exc)
        elif self.db_type == "postgresql":
            return self._classify_pg_error(exc)
        elif self.db_type == "influxdb":
            return self._classify_influx_error(exc)
        else:
            # SQLite 或其他
            return NodeStatus.Error, f"数据库错误: {getattr(exc, 'orig', exc)}"

    @staticmethod
    def _classify_mysql_error(exc: Exception) -> Tuple[NodeStatus, str]:
        """
        分类 MySQL 异常，返回 (状态, 响应消息)。

        Args:
            exc: 数据库 异常对象。

        Returns:
            - 数据库状态
            - 响应消息
        """
        import pymysql
        orig = getattr(exc, 'orig', exc)
        if isinstance(orig, pymysql.err.OperationalError):
            code = orig.args[0] if orig.args else None
            # 2003: Can't connect, 2002: Socket error (UNIX)
            if code in (2003, 2002):
                return NodeStatus.Inactive, "MySQL 服务未启动或主机/端口不可达"
            # 1045: Access denied (password wrong)
            if code == 1045:
                return NodeStatus.AuthFailed, "MySQL 用户名或密码错误"
            # 1044: Access to database denied
            if code == 1044:
                return NodeStatus.AuthFailed, "MySQL 用户无权访问该数据库"
        elif isinstance(orig, pymysql.err.InternalError):
            return NodeStatus.Error, f"MySQL 内部错误: {orig}"
        elif isinstance(orig, pymysql.err.ProgrammingError):
            return NodeStatus.Error, f"MySQL 语法/配置错误: {orig}"
        return NodeStatus.Error, f"MySQL 错误: {orig}"

    @staticmethod
    def _classify_pg_error(exc: Exception) -> Tuple[NodeStatus, str]:
        """
        分类 PostgreSQL 异常，返回 (状态, 响应消息)。

        Args:
            exc: 数据库 异常对象。

        Returns:
            - 数据库状态
            - 响应消息
        """
        import psycopg2
        orig = getattr(exc, 'orig', exc)
        # PostgreSQL 异常有 pg_code
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
        # 非 PG 异常或没有 pg code 的底层错误
        error_msg = str(orig)
        # 连接拒绝 / 服务未启动
        if 'connection refused' in error_msg.lower() or 'is the server running' in error_msg:
            return NodeStatus.Inactive, "PostgreSQL 服务未启动或端口不通"
        # 主机名解析失败
        if 'could not translate host name' in error_msg.lower() or 'name or service not known' in error_msg.lower():
            return NodeStatus.Inactive, "PostgreSQL 主机地址无法解析，请检查网络配置"
        # 密码认证失败
        if 'password authentication failed' in error_msg.lower():
            return NodeStatus.AuthFailed, "PostgreSQL 密码认证失败"
        return NodeStatus.Error, f"PostgreSQL 错误: {orig}"

    @staticmethod
    def _classify_influx_error(exc: Exception) -> Tuple[NodeStatus, str]:
        """
        分类 InfluxDB 异常，返回 (状态, 响应消息)。

        Args:
            exc: 数据库 异常对象。

        Returns:
            - 数据库状态
            - 响应消息
        """
        import requests
        from influxdb_client.rest import ApiException

        orig = getattr(exc, 'orig', exc)
        # 连接被拒绝、主机不可达
        if isinstance(orig, (requests.ConnectionError, ConnectionRefusedError, ConnectionError)):
            return NodeStatus.Inactive, "InfluxDB 服务未启动或网络不可达"
        if isinstance(orig, (requests.Timeout, TimeoutError)):
            return NodeStatus.Inactive, "InfluxDB 连接超时"
        if isinstance(orig, ApiException):
            if orig.status == 401:
                return NodeStatus.AuthFailed, "InfluxDB 认证失败 (Token 或用户名密码错误)"
            if orig.status == 403:
                return NodeStatus.AuthFailed, "InfluxDB 无权限访问"
            return NodeStatus.Error, f"InfluxDB API 错误: HTTP {orig.status}"
        return NodeStatus.Error, f"InfluxDB 错误: {exc}"

    def _test_rdbms(self, timeout: int) -> None:
        """
        测试关系型数据库（SQLite/Mysql/PostgreSQL）连接

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            None
        """
        from sqlalchemy import create_engine, text as sa_text
        # 获取明文密码（需处理 SecretStr）
        pwd = self.db_password.get_secret_value() if isinstance(self.db_password, SecretStr) else self.db_password

        if self.db_type == "sqlite":
            # SQLite 无需密码和网络参数
            engine = create_engine(self.db_url, echo=bool(self.db_sql_echo == "open"))
        elif self.db_type == "mysql":
            engine = create_engine(
                f"mysql+pymysql://{self.db_username}:{pwd}@{self.db_host}:{self.db_port}",
                echo=bool(self.db_sql_echo == "open"),
                connect_args={"connect_timeout": timeout}
            )
        elif self.db_type == "postgresql":
            engine = create_engine(
                f"postgresql://{self.db_username}:{pwd}@{self.db_host}:{self.db_port}",
                echo=bool(self.db_sql_echo == "open"),
                connect_args={"connect_timeout": timeout}
            )
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")

        # 尝试获取连接并立即关闭
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        engine.dispose()

    def _test_influxdb(self, timeout: int) -> None:
        """
        测试 InfluxDB 连接（支持 1.x 和 2.x）

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            None
        """
        from influxdb_client import InfluxDBClient
        pwd = self.db_password.get_secret_value() if isinstance(self.db_password, SecretStr) else self.db_password
        host = self.db_host
        port = self.db_port

        try:
            url = f"http://{host}:{port}"  # noqa
            with InfluxDBClient(url=url, username=self.db_username, password=pwd, timeout=timeout * 1000) as client:
                client.ping()
            return
        except ImportError:
            pass

        import requests
        base_url = f"http://{host}:{port}"  # noqa
        auth = (self.db_username, pwd) if self.db_username and pwd else None

        # InfluxDB 1.x 使用 /ping，2.x 使用 /health
        for endpoint in ("/health", "/ping"):
            try:
                resp = requests.get(
                    f"{base_url}{endpoint}",
                    auth=auth,
                    timeout=timeout
                )
                if resp.ok:
                    return
            except requests.RequestException:
                continue
        raise ConnectionError(f"无法连接到 InfluxDB: {base_url}")


class CacheConfig(BaseModel):
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
        cache_pool_size: 连接池大小，默认 5
        cache_type: 缓存类型，默认 memory，可选 memory, redis
        status: 缓存服务状态，默认 Unknown
    """
    cache_host: str = Field(default="127.0.0.1", title="缓存主机", description="缓存主机")
    cache_port: int = Field(default=6379, title="缓存绑定端口", description="缓存绑定端口")
    cache_pass: Optional[SecretStr] = Field(default=None, title="缓存密码", description="缓存密码")
    timeout: int = Field(default=5, title="缓存超时时间（秒）", description="缓存超时时间（秒）")
    main_db: int = Field(default=0, title="主数据库索引", description="默认数据库索引")
    databases: int = Field(default=16, title="逻辑数据库数量", description="默认16个，索引从0到15")
    key_prefix: Optional[str] = Field(default=None, title="键前缀", description="键前缀，默认空字符串")
    ttl_seconds: int = Field(default=300, title="缓存过期时间（秒）", description="缓存过期时间（秒）")
    max_size: int = Field(default=1024, title="缓存最大大小（MB）", description="缓存最大大小（MB）")
    cache_pool_size: int = Field(default=5, title="连接池大小", description="连接池大小，默认 5")
    cache_type: Literal["redis"] = Field(default="redis", title="缓存类型", description="可选 redis")
    status: NodeStatus = Field(default=NodeStatus.Unknown, title="缓存服务状态", description="缓存服务状态")

    def test_connection(self, timeout: int = 5) -> Tuple[bool, str, NodeStatus]:
        """
        测试 Redis 连接，并根据结果更新 self.config.status。

        Args:
            timeout: 连接超时秒数（覆盖 config.timeout）

        Returns:
            tuple: (成功标志, 错误消息, 状态枚举)
        """
        try:
            self._test_redis(timeout)
            self.status = NodeStatus.Active
            return True, "", self.status
        except Exception as e:
            status, message = self._classify_cache_error(e)
            self.status = status
            return False, message, self.status

    def _test_redis(self, timeout: int) -> None:
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
        cache_index = self.main_db
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

    @staticmethod
    def _classify_cache_error(exc: Exception) -> Tuple[NodeStatus, str]:
        """
        分类缓存异常，返回状态枚举和消息。

        Args:
            exc: 缓存异常对象
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
