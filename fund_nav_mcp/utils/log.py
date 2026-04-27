__all__ = [
    'log_basic_config', 'bind_context', 'clear_context', 'get_logger', 'get_logging_queue', 'get_logging_level',
    'init_child_logging', 'LogLevel', 'Color'
]

import atexit
import datetime
import json
import logging
import logging.handlers
import multiprocessing
import signal
import sys
import threading
import traceback
from contextvars import ContextVar
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, IO, cast

_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class _ColorEnum(str, Enum):
    """
    ANSI颜色代码枚举
    枚举成员格式： (value:str, label:str)
    使用示例：
       SOME = "颜色码", "标签"
    兼容：
       - .value -> str
       - .label -> str
    """

    def __new__(cls, value: str, label: str) -> str:
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label

        return obj

    def __str__(self):
        return f"{self.value}"


class Color(_ColorEnum):
    reset = "\033[0m", "重置"
    red = "\033[31m", "红色"
    green = "\033[32m", "绿色"
    yellow = "\033[33m", "黄色"
    cyan = "\033[36m", "青蓝色"
    bold_red = "\033[1m" + "\033[31m", "粗体红色"

    @classmethod
    def _missing_(cls, value):
        return cls.reset


class _LogLevelEnum(int, Enum):
    """
    日志级别枚举
    枚举成员格式： (value:int, label:str, color:str)
    使用示例：
       SOME = "级别", "标签", "颜色"
    兼容：
       - .value -> int
       - .label -> str
       - .color -> str
    """

    def __new__(cls, value: int, label: str, color: str) -> int:
        obj = int.__new__(cls, value)
        obj._value_ = int(value)
        obj.label = label
        obj.color = color

        return obj

    def __str__(self):
        return f"{self.value}"


class LogLevel(_LogLevelEnum):
    """
    日志级别枚举。
    """
    DEBUG = logging.DEBUG, "调试", Color.cyan
    INFO = logging.INFO, "信息", Color.green
    WARNING = logging.WARNING, "警告", Color.yellow
    ERROR = logging.ERROR, "错误", Color.red
    CRITICAL = logging.CRITICAL, "严重错误", Color.bold_red
    UNKNOWN = 0, "未知", Color.reset

    @classmethod
    def _missing_(cls, value: int) -> "LogLevel":
        return cls.INFO

    @classmethod
    def from_value(cls, value: int, default: "LogLevel" = INFO) -> "LogLevel":
        """通过值获取枚举成员（不区分大小写）"""
        try:
            return cls(value)
        except KeyError:
            return default

    @classmethod
    def from_name(cls, name: str, default: "LogLevel" = INFO) -> "LogLevel":
        """通过名称获取枚举成员（不区分大小写）"""
        try:
            return cls[name.upper()]
        except KeyError:
            return default


class CONST:
    """集中管理所有日志模块的常量和默认配置。"""
    # 项目根目录（自动检测）
    project_root: Path = Path(__file__).parent.parent.parent.resolve()

    # 需要序列化的 LogRecord 字段（用于跨进程传递）
    serializable_fields: List[str] = [
        'name', 'levelno', 'levelname', 'pathname', 'filename', 'module',
        'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
        'thread', 'threadName', 'process', 'processName', 'msg', 'args'
    ]

    # 标准日志记录字段（包含 extra_dict）
    standard_attrs = set(logging.makeLogRecord({}).__dict__.keys())


def bind_context(**kwargs: Any) -> None:
    """
    绑定日志上下文变量。

    将键值对添加到当前上下文的字典中，后续日志记录会自动包含这些字段。

    Args:
        **kwargs: 要绑定的上下文变量键值对，例如 request_id="abc", user="admin"。
    """
    current = _log_context.get()
    current.update(kwargs)
    _log_context.set(current)


def clear_context() -> None:
    """清除所有日志上下文变量。"""
    _log_context.set({})


class ContextAdapter(logging.LoggerAdapter):
    """
    日志上下文适配器，自动将上下文变量注入日志记录。

    继承自 logging.LoggerAdapter，重写 process 方法，将 ContextVar 中的内容合并到日志的 extra 字段中。
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        处理日志消息，将上下文变量注入 extra 字段。

        Args:
            msg: 日志消息字符串。
            kwargs: 日志调用时传递的关键字参数（可能包含 'extra'）。

        Returns:
            元组 (msg, kwargs)，其中 kwargs 已包含更新后的 extra 字段。
        """
        extra = kwargs.get("extra", {})
        ctx = _log_context.get()
        if ctx:
            extra.update(ctx)
        kwargs["extra"] = extra
        return msg, kwargs


def _get_extra(record: logging.LogRecord) -> Dict[str, Any]:
    """从日志记录中获取 extra_dict 属性（自定义字段）。"""
    return getattr(record, 'extra_dict', {})


class ClickableConsoleFormatter(logging.Formatter):
    """
    控制台日志格式化器，支持彩色输出和可点击的文件位置链接。

    继承自 logging.Formatter，重写 format 方法，添加可点击的文件位置链接。

    格式示例：
        YYYY-MM-DD HH:MM:SS INFO     [PID:12345 MainProcess:MainThread] test:1 - Message
          File "path/to/file.py", line 1 in func_name
    """

    @staticmethod
    def _format_process_thread(record: logging.LogRecord) -> str:
        """
        格式化进程ID和线程信息。

        Args:
            record: 日志记录对象。

        Returns:
            格式化后的字符串，包含进程ID、进程类型和线程类型。
        """
        pid = record.process
        process_type = "MainProcess" if record.processName == "MainProcess" else "ChildProcess"
        thread_name = record.threadName
        if process_type == "MainProcess":
            thread_type = "MainThread" if thread_name == "MainThread" else thread_name
        else:
            thread_type = thread_name if thread_name != "MainThread" else "ChildThread"
        return f"[PID:{pid} {process_type}:{thread_type}]"

    @staticmethod
    def _format_location(record: logging.LogRecord) -> str:
        """
        格式化文件位置，显示相对于项目根目录的路径。

        Args:
            record: 日志记录对象。

        Returns:
            格式化后的字符串，包含文件路径和行号。
        """
        try:
            rel_path = Path(record.pathname).relative_to(CONST.project_root)
        except ValueError:
            rel_path = Path(record.pathname)
        return f'File "{rel_path}", line {record.lineno}'

    @staticmethod
    def _decode_repr_bytes(s: str) -> str:
        """将字符串中的 b'...' 或 b"..." 片段解码为可读文本"""
        import re

        def decode_match(match):
            # match.group(0) 是整个匹配的 b'...'
            quoted = match.group(0)
            # 去掉 b' 和 ' 或 b" 和 "
            if quoted.startswith("b'") and quoted.endswith("'"):
                inner = quoted[2:-1]
            elif quoted.startswith('b"') and quoted.endswith('"'):
                inner = quoted[2:-1]
            else:
                return quoted
            # 将转义序列还原为字节
            # noinspection PyBroadException
            try:
                raw = inner.encode('utf-8').decode('unicode_escape')
                # 将 latin1 编码的字符串转为 utf-8
                decoded = raw.encode('latin1').decode('utf-8')
                return decoded
            except Exception:
                return quoted

        # 匹配 b'...' 或 b"..."，其中 ... 包含任意转义字符
        pattern = r"b'(?:[^'\\]|\\.)*'|b\"(?:[^\"\\]|\\.)*\""
        return re.sub(pattern, decode_match, s)

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为可读的控制台输出。

        Args:
            record: 日志记录对象。

        Returns:
            格式化后的字符串，包含颜色、进程/线程信息、可点击位置和异常堆栈。
        """
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        msecs = int(record.msecs)
        level_color = LogLevel.from_value(record.levelno, LogLevel.UNKNOWN).color
        colored_level = f"{level_color}{record.levelname.ljust(8)}{Color.reset}"
        proc_thread = self._format_process_thread(record)
        location = self._format_location(record)
        func = f" in {record.funcName}" if record.funcName else ""

        msg = self._decode_repr_bytes(record.getMessage()).__repr__()

        main_line = f"{timestamp}.{msecs:03d} {colored_level} {proc_thread} {record.name}:{record.lineno} - {msg}"
        extra = _get_extra(record)
        if extra:
            main_line += " " + " ".join(f"{k}={v}" for k, v in extra.items())
        lines = [main_line, f"  {location}{func}"]
        if record.exc_info:
            if hasattr(record, "exc_text") and record.exc_text:
                exc_lines = record.exc_text.rstrip().splitlines()
            else:
                exc_lines = self.formatException(record.exc_info).rstrip().splitlines()
            lines.extend(f"  {line}" for line in exc_lines)
        return "\n".join(lines)


class JSONFormatter(logging.Formatter):
    """
    JSON 格式的日志格式化器，用于生产环境。

    继承自 logging.Formatter，重写 format 方法，将日志记录转换为 JSON 字符串。
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        将日志记录格式化为 JSON 字符串。

        Args:
            record: 日志记录对象。

        Returns:
            JSON 字符串。
        """
        dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
        timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(record.msecs):03d}Z"

        log_entry: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "path": record.pathname,
            "process": record.process,
            "processName": record.processName,
            "thread": record.thread,
            "threadName": record.threadName,
        }
        if record.exc_info:
            if hasattr(record, "exc_text") and record.exc_text:
                log_entry["exception"] = record.exc_text
            else:
                exc_type, exc_value, exc_tb = record.exc_info
                log_entry["exception"] = traceback.format_exception(exc_type, exc_value, exc_tb)
        ctx = _log_context.get()
        if ctx:
            log_entry["context"] = ctx
        extra = _get_extra(record)
        if extra:
            log_entry["extra"] = extra
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class TimestampRotatingFileHandler(logging.Handler):
    """
    按时间戳滚动写入的日志文件处理器。

    每次启动或文件大小超限时，创建一个新的日志文件，文件名包含时间戳。
    保留最近 backup_count 个文件，自动删除更旧的。
    """

    def __init__(self,
                 log_dir: Union[str, Path],
                 file_base_name: str,
                 max_bytes: int,
                 backup_count: int,
                 encoding: str = "utf-8") -> None:
        """
        初始化处理器。

        Args:
            log_dir: 日志文件存放目录。
            file_base_name: 日志文件基名（例如 "fund_nav_mcp"），实际文件名会追加时间戳。
            max_bytes: 单个文件最大字节数，超限后滚动。
            backup_count: 最多保留的日志文件数量。
            encoding: 文件编码，默认为 utf-8。
        """
        super().__init__()
        self.log_dir: Path = Path(log_dir)
        self.file_base_name: str = file_base_name
        self.max_bytes: int = max_bytes
        self.backup_count: int = backup_count
        self.encoding: str = encoding
        self.current_file: Optional[Path] = None
        self.current_stream: Optional[IO[str]] = None
        self._open_next_file()

    def _open_next_file(self) -> None:
        """创建新的日志文件，并清理超过备份数量的旧文件。"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.current_file = self.log_dir / f"{self.file_base_name}_{ts}.log"
        self.current_stream = open(self.current_file, "a", encoding=self.encoding)
        self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        """删除超出 backup_count 数量的旧日志文件。"""
        pattern = f"{self.file_base_name}_*.log"
        files = sorted(self.log_dir.glob(pattern))
        for old in files[:-self.backup_count]:
            try:
                old.unlink()
            except OSError:
                pass

    def emit(self, record: logging.LogRecord) -> None:
        """写入日志记录到当前文件。"""
        # noinspection PyBroadException
        try:
            self.current_stream.write(self.format(record) + "\n")
            self.current_stream.flush()
            if self.current_stream.tell() >= self.max_bytes:
                self.current_stream.close()
                self._open_next_file()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """关闭文件流并释放资源。"""
        if self.current_stream:
            self.current_stream.close()
        super().close()


class MaxLevelFilter(logging.Filter):
    """只允许低于或等于指定级别的日志通过（用于分离普通日志和错误日志）。"""

    def __init__(self, max_level: int):
        """
        初始化过滤器。

        Args:
            max_level: 允许通过的最大日志级别（例如 logging.INFO）。
        """
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录。

        Args:
            record: 日志记录对象。

        Returns:
            是否允许通过该记录（True 表示允许，False 表示拒绝）。
        """
        return record.levelno <= self.max_level


def _record_to_dict(record: logging.LogRecord) -> Dict[str, Any]:
    """
    将 LogRecord 转换为可 pickle 的字典。

    Args:
        record: 日志记录对象。

    Returns:
        包含可序列化字段的字典。
    """
    d = {f: getattr(record, f) for f in CONST.serializable_fields}
    if record.exc_info:
        exc_type, exc_value, exc_tb = record.exc_info
        d['exc_text'] = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    extra = getattr(record, 'extra_dict', None)
    if extra:
        d['extra_dict'] = extra
    return d


def _dict_to_record(d: Dict[str, Any]) -> logging.LogRecord:
    """
    从字典重建 LogRecord 对象。

    Args:
        d: 由 _record_to_dict 生成的字典。

    Returns:
        重建的 LogRecord 对象。
    """
    record = logging.LogRecord(
        name=d['name'], level=d['levelno'], pathname=d['pathname'],
        lineno=d['lineno'], msg=d['msg'], args=d['args'], exc_info=None,
        func=d['funcName']
    )
    for f in CONST.serializable_fields:
        if f not in ('name', 'levelno', 'pathname', 'lineno', 'msg', 'args', 'funcName'):
            setattr(record, f, d.get(f))
    if 'exc_text' in d:
        record.exc_text = d['exc_text']
        record.exc_info = (None, None, None)
    if 'extra_dict' in d:
        record.extra_dict = d['extra_dict']
    return record


class MPQueueHandler(logging.Handler):
    """
    多进程安全的队列处理器。

    将日志记录序列化为字典后放入 multiprocessing.Queue，供监听进程消费。
    """

    def __init__(self, queue: multiprocessing.Queue) -> None:
        """初始化队列处理器。

        Args:
            queue: 多进程队列，用于传递序列化的日志字典。
        """
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        """将日志记录放入队列。"""
        if not hasattr(record, 'extra_dict'):
            extra = {k: v for k, v in record.__dict__.items() if k not in CONST.standard_attrs}
            if extra:
                record.extra_dict = extra
        # noinspection PyBroadException
        try:
            self.queue.put_nowait(_record_to_dict(record))
        except Exception:
            pass


def _create_handlers(config: Dict[str, Any], file_base_name: str, level: int) -> List[logging.Handler]:
    """
    创建日志处理器列表，支持控制台和文件（可选分离错误日志）。

    Args:
        config: 日志配置字典。
        file_base_name: 日志文件基名。
        level: 日志级别（例如 logging.INFO）。
    Returns:
        处理器列表。
    """
    handlers = []

    # 控制台处理器
    if config.get("console", True):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(ClickableConsoleFormatter())
        console.setLevel(level)
        handlers.append(console)

    if not config.get("file", False):
        return handlers or [logging.NullHandler()]

    def _make_file_handler(base_name: str, _level: int,
                           add_filter: Optional[logging.Filter] = None) -> TimestampRotatingFileHandler:
        """
        Args:
            base_name: 日志文件基名。
            _level: 日志级别（例如 logging.INFO）。
            add_filter: 可选的过滤器对象，用于过滤日志记录。
        Returns:
            TimestampRotatingFileHandler 实例。
        """
        handler = TimestampRotatingFileHandler(
            log_dir=config["file_path"],
            file_base_name=base_name,
            max_bytes=config["max_file_size"],
            backup_count=config["backup_count"],
        )
        formatter = JSONFormatter() if config.get("json_format", True) else ClickableConsoleFormatter()
        handler.setFormatter(formatter)
        handler.setLevel(_level)
        if add_filter:
            handler.addFilter(add_filter)
        return handler

    # 根据是否分离错误日志创建文件处理器
    if config.get("separate_error_file", False):
        # 普通文件：记录从 level(变量) 到 WARNING（不包含 ERROR 及以上）
        info_level = level if level <= logging.WARNING else logging.WARNING
        handlers.append(_make_file_handler(
            base_name=file_base_name,
            _level=info_level,
            add_filter=MaxLevelFilter(logging.WARNING)
        ))
        # 错误文件：记录 ERROR 及以上（且不低于 level）
        error_level = max(level, logging.ERROR)
        error_base = config.get("error_file_base_name") or f"{file_base_name}_error"
        handlers.append(_make_file_handler(
            base_name=error_base,
            _level=error_level
        ))
    else:
        # 单文件模式（包含所有 INFO 及以上级别）
        handlers.append(_make_file_handler(
            base_name=file_base_name,
            _level=level
        ))

    return handlers


def _listener_process_target(
        queue: multiprocessing.Queue,
        config: Dict[str, Any],
        file_base_name: str,
        level: int
) -> None:
    """
    监听进程入口函数。

    从队列中获取序列化的日志字典，重建 LogRecord 并交给 root logger 处理。

    Args:
        queue: 多进程队列。
        config: 日志配置。
        file_base_name: 日志文件基名。
        level: 日志级别（例如 logging.INFO）。
    Returns:
        None
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in _create_handlers(config, file_base_name, level):
        root.addHandler(h)
    while True:
        # noinspection PyBroadException
        try:
            d = queue.get()
            if d is None:  # 哨兵值，表示停止
                break
            root.handle(_dict_to_record(d))
        except Exception:
            continue
    for h in root.handlers:
        h.flush()
        h.close()


class LoggingManager:
    """日志管理器单例，负责配置和获取 logger。"""

    def __init__(self) -> None:
        self._queue: Optional[multiprocessing.Queue] = None
        self._listener_proc: Optional[multiprocessing.Process] = None
        self._config: Dict[str, Any] = {}
        self._level: int = logging.INFO
        self._started: bool = False
        self._lock = threading.Lock()
        self._child_queue: Optional[multiprocessing.Queue] = None
        self._child_level: int = logging.INFO
        self._adapters: Dict[str, ContextAdapter] = {}

    def configure(self, **kwargs: Any) -> None:
        """
        配置日志系统。

        Args:
            **kwargs: 支持的参数包括 level, console, file, file_path,
                      backup_count, max_file_size, json_format。
        Raises:
            RuntimeError: 如果日志已经启动（configure 只能调用一次）。
        """
        if self._started:
            raise RuntimeError("Logging already started, cannot reconfigure")
        self._level = kwargs.pop("level", logging.INFO)
        self._config.update(kwargs)
        self._ensure_started()

    def _ensure_started(self) -> None:
        """确保主进程的日志系统已启动（队列、监听进程、根处理器）。"""
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            self._queue = multiprocessing.Queue(-1)
            if multiprocessing.current_process().name == "MainProcess":
                file_base_name = self._config.get("file_base_name", "fund_nav_mcp")
                self._listener_proc = multiprocessing.Process(
                    target=_listener_process_target,
                    args=(self._queue, self._config, file_base_name, self._level),
                    name="LogListener",
                    daemon=False,
                )
                self._listener_proc.start()
                atexit.register(self._shutdown)
            root = logging.getLogger()
            for h in root.handlers[:]:
                root.removeHandler(h)
            root.setLevel(self._level)
            root.addHandler(MPQueueHandler(self._queue))
            root.propagate = False
            self._started = True

    def _shutdown(self) -> None:
        """关闭监听进程并释放资源。"""
        if self._queue:
            # noinspection PyBroadException
            try:
                self._queue.put(None)
            except Exception:
                pass
        if self._listener_proc:
            self._listener_proc.join(timeout=5)

    @staticmethod
    def _setup_logger(logger: logging.Logger, queue: multiprocessing.Queue, level: int) -> ContextAdapter:
        """
        为 logger 添加 MPQueueHandler 并配置级别。

        Args:
            logger: 要配置的 logger 实例。
            queue: 多进程队列。
            level: 日志级别。

        Returns:
            包装后的 ContextAdapter 实例。
        """
        if not any(isinstance(h, MPQueueHandler) for h in logger.handlers):
            logger.addHandler(MPQueueHandler(queue))
        logger.setLevel(level)
        logger.propagate = False
        return ContextAdapter(logger, {})

    def get_logger(self, name: Optional[str] = None) -> ContextAdapter:
        """
        获取 logger 实例，自动识别主进程或子进程，并缓存适配器。

        Args:
            name: logger 名称，默认为 root logger。

        Returns:
            ContextAdapter 包装的 logger。
        """
        key = name or ''
        if key in self._adapters:
            return self._adapters[key]

        if self._child_queue is not None:
            # 子进程模式
            adapter = self._setup_logger(logging.getLogger(name), self._child_queue, self._child_level)
        else:
            self._ensure_started()
            adapter = self._setup_logger(logging.getLogger(name), cast(multiprocessing.Queue, self._queue), self._level)
        self._adapters[key] = adapter
        return adapter

    def init_child(self, queue: multiprocessing.Queue, level: int) -> None:
        """
        初始化子进程的日志系统（由子进程调用）。

        Args:
            queue: 主进程共享的队列。
            level: 日志级别。
        Returns:
            None
        """
        self._child_queue = queue
        self._child_level = level
        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)
        root.setLevel(level)
        root.addHandler(MPQueueHandler(queue))
        root.propagate = False

    def get_queue(self) -> Optional[multiprocessing.Queue]:
        """
        返回主进程的共享队列。

        Returns:
            主进程的共享队列，或 None 如果未初始化。
        """
        return self._queue

    def get_level(self) -> int:
        """
        返回当前配置的日志级别。

        Returns:
            当前日志级别。
        """
        return self._level


_manager = LoggingManager()


def log_basic_config(
        level: LogLevel = LogLevel.INFO,
        console: bool = True,
        file: bool = False,
        file_path: str = "logs",
        file_base_name: str = "fund_nav_mcp",
        backup_count: int = 100,
        max_file_size: int = 100 * 1024 * 1024,
        json_format: bool = True,
        separate_error_file: bool = False,
        error_file_base_name: str = "fund_nav_mcp_error",
) -> None:
    """
    配置全局日志系统。

    Args:
        level: 日志级别，使用 logging.DEBUG/INFO/WARNING/ERROR/CRITICAL。
        console: 是否输出到控制台。
        file: 是否输出到文件。
        file_path: 日志文件存放目录。
        file_base_name: 日志文件基名（例如 "fund_nav_mcp"）。
        backup_count: 最多保留的日志文件数量。
        max_file_size: 单个日志文件最大字节数。
        json_format: 是否使用 JSON 格式（文件输出时）。
        separate_error_file: 是否将 ERROR 及以上级别的日志分离到单独文件。
        error_file_base_name: 错误日志文件基名（若为 None，自动在 file_base_name 后加 "_error"）。
    """
    _manager.configure(
        level=level,
        console=console,
        file=file,
        file_path=file_path,
        file_base_name=file_base_name,
        backup_count=backup_count,
        max_file_size=max_file_size,
        json_format=json_format,
        separate_error_file=separate_error_file,
        error_file_base_name=error_file_base_name,
    )


def get_logger(name: Optional[str] = None) -> ContextAdapter:
    """
    获取日志记录器，自动适配主进程和子进程。

    Args:
        name: 日志记录器名称，通常使用 __name__。默认为 root logger。

    Returns:
        ContextAdapter 包装的日志记录器，支持 bind_context 注入上下文。
    """
    return _manager.get_logger(name)


def get_logging_queue() -> Optional[multiprocessing.Queue]:
    """
    获取主进程的共享日志队列（用于传递给子进程）。

    Returns:
        多进程队列对象，如果未初始化则返回 None。
    """
    return _manager.get_queue()


def get_logging_level() -> int:
    """
    获取当前配置的日志级别。

    Returns:
        日志级别常量，例如 logging.INFO。
    """
    return _manager.get_level()


def init_child_logging(queue: multiprocessing.Queue, level: LogLevel) -> None:
    """
    在子进程中初始化日志系统，必须在子进程入口函数开头调用。

    Args:
        queue: 从主进程获取的共享队列（通过 get_logging_queue()）。
        level: 日志级别，例如 logging.INFO。
    """
    _manager.init_child(queue, level)
