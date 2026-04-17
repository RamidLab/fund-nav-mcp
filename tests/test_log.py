import json
import logging
import multiprocessing
import os
import sys
import time
from pathlib import Path

import pytest

from fund_nav_mcp.utils.log import LogLevel

sys.path.insert(0, str(Path(__file__).parent.parent))

from fund_nav_mcp.utils import log


@pytest.fixture(autouse=True)
def reset_logging():
    """
    在每个测试前重置日志配置，确保测试之间相互隔离。

    清理现有的 handlers、重置管理器内部状态（包括 _started、队列、子进程状态等），
    并将配置字典恢复为默认值，避免前一个测试的配置泄漏。
    """
    # 清空 root logger 的所有处理器
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()
    # 强制重置全局管理器的内部状态
    # noinspection PyProtectedMember
    log._manager._started = False
    # noinspection PyProtectedMember
    log._manager._queue = None
    # noinspection PyProtectedMember
    log._manager._listener_proc = None
    # noinspection PyProtectedMember
    log._manager._child_queue = None
    # noinspection PyProtectedMember
    log._manager._child_level = logging.INFO
    yield
    # 测试结束后，关闭监听进程（如果存在）
    # noinspection PyProtectedMember
    log._manager._shutdown()


@pytest.fixture
def temp_log_dir(tmp_path):
    """临时目录，用于存放测试中生成的日志文件。"""
    return tmp_path / "logs"


def test_console_logging():
    """
    测试控制台日志输出功能。

    启用控制台，禁用文件，手动观察控制台输出（需要 -s 标志显示打印）。
    包括常规 INFO/WARNING 和带异常堆栈的 ERROR。
    """
    log.log_basic_config(
        level=LogLevel.INFO,
        console=True,
        file=False,
    )
    print("\n")
    logger = log.get_logger("test_console")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")

    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.error("Error message: An error occurred", exc_info=True)


def test_basic_file_logging(temp_log_dir):
    """
    测试基本的文件日志输出。

    验证 DEBUG/INFO/WARNING/ERROR 级别的消息都被写入同一个日志文件，
    并且文件中包含正确的内容（级别名、记录器名、文件位置等）。
    """
    log.log_basic_config(
        level=LogLevel.DEBUG,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_basic_file",
        json_format=False,
    )
    logger = log.get_logger("test_basic")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    time.sleep(0.3)  # 等待异步日志写入完成

    log_files = list(temp_log_dir.glob("test_basic_file_*.log"))

    assert len(log_files) == 1
    assert log_files[0].name.startswith("test_basic_file")
    content = open(log_files[0], "r", encoding="utf-8").read()
    assert "DEBUG" in content
    assert "INFO" in content
    assert "WARNING" in content
    assert "ERROR" in content
    assert "test_basic:" in content
    assert 'File "tests/test_log.py"' in content or 'File "tests\\test_log.py"' in content


def test_separate_error_file_logging(temp_log_dir):
    """
    测试分离错误日志文件的功能。

    启用 separate_error_file=True 后，普通日志（INFO/WARNING）和错误日志（ERROR+）
    应分别写入不同的文件，文件名后缀分别为基名和基名_error。
    """
    log.log_basic_config(
        level=LogLevel.INFO,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_separate_error_file",
        json_format=False,
        separate_error_file=True,
        error_file_base_name="test_separate_error_file_error",  # 使用默认错误文件名
    )
    logger = log.get_logger("test_separate_error_file")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    time.sleep(0.3)
    log_files = list(temp_log_dir.glob("test_separate_error_file_*.log"))

    assert len(log_files) == 2
    assert [i for i in log_files if i.name.startswith("test_separate_error_file")] != []
    assert [i for i in log_files if i.name.startswith("test_separate_error_file_error")] != []


def test_log_with_extra_context(temp_log_dir):
    """
    测试在日志调用时通过 extra 参数传递自定义字段。

    验证 extra 字典中的键值对是否正确出现在日志输出中。
    """
    log.log_basic_config(
        level=LogLevel.INFO,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_extra_context",
        json_format=False,
    )
    logger = log.get_logger("test_context")
    logger.info("User action", extra={"user_id": 123, "action": "login"})

    time.sleep(0.3)
    log_files = list(temp_log_dir.glob("test_extra_context_*.log"))
    assert len(log_files) == 1
    assert log_files[0].name.startswith("test_extra_context")
    content = open(log_files[0], "r", encoding="utf-8").read()
    assert "user_id=123" in content
    assert "action=login" in content


def test_bind_context(temp_log_dir):
    """
    测试 bind_context 函数，该函数可以为当前上下文（协程/线程/进程）绑定全局字段。

    验证绑定后所有后续日志自动携带这些字段，clear_context 后字段消失。
    """
    log.log_basic_config(
        level=LogLevel.INFO,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_bind_context",
        json_format=False,
    )
    logger = log.get_logger("test_bind")
    log.bind_context(request_id="req-abc", session="xyz")
    logger.info("Processing request")

    time.sleep(0.3)
    log_files = list(temp_log_dir.glob("test_bind_context_*.log"))
    assert len(log_files) == 1
    assert log_files[0].name.startswith("test_bind_context")
    content = open(log_files[0], "r", encoding="utf-8").read()
    assert "request_id=req-abc" in content
    assert "session=xyz" in content

    log.clear_context()
    logger.info("After clear")
    time.sleep(0.3)
    content = open(log_files[0], "r", encoding="utf-8").read()
    lines = content.strip().splitlines()
    assert len(lines) >= 2
    assert "request_id" not in lines[-1]
    assert "session" not in lines[-1]


def test_exception_logging(temp_log_dir):
    """
    测试异常日志记录，验证 exc_info=True 时能输出完整的堆栈跟踪信息。
    """
    log.log_basic_config(
        level=LogLevel.ERROR,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_exc",
        json_format=False,
    )
    logger = log.get_logger("test_exc")
    try:
        raise ValueError("Test exception message")
    except ValueError:
        logger.error("An error occurred", exc_info=True)

    time.sleep(0.3)
    log_files = list(temp_log_dir.glob("test_exc_*.log"))
    assert len(log_files) == 1
    assert log_files[0].name.startswith("test_exc")
    content = open(log_files[0], "r", encoding="utf-8").read()
    assert "An error occurred" in content
    assert "Traceback (most recent call last):" in content
    assert "ValueError: Test exception message" in content
    assert "File" in content


def test_file_logging_json(temp_log_dir):
    """
    测试 JSON 格式的文件日志输出。

    验证日志记录被正确序列化为 JSON，且包含 timestamp、level、message、extra 等字段。
    """
    log.log_basic_config(
        level=LogLevel.INFO,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_file_json",
        json_format=True,
    )
    logger = log.get_logger("test_file_json")
    logger.info("Hello file", extra={"key": "value"})

    time.sleep(0.3)
    log_files = list(temp_log_dir.glob("test_file_json_*.log"))

    assert len(log_files) == 1
    content = open(log_files[0], "r", encoding="utf-8").read().strip()
    assert content

    record = json.loads(content)
    assert record["level"] == "INFO"
    assert record["message"] == "Hello file"
    assert record["extra"]["key"] == "value"
    assert "timestamp" in record


def _worker_function(queue, level):
    """
    子进程的工作函数（用于多进程测试）。

    初始化子进程日志，绑定 worker_pid 上下文，然后记录一条信息。
    """
    log.init_child_logging(queue, level)
    child_logger = log.get_logger("child_worker")
    log.bind_context(worker_pid=os.getpid())
    child_logger.info("Hello from child process")
    time.sleep(0.1)


def test_multiprocessing_logging(temp_log_dir):
    """
    测试多进程环境下的日志记录。

    验证子进程中的日志能够通过共享队列传递到主进程的监听进程，
    并最终写入文件，同时子进程的线程显示为 ChildProcess。
    """
    log.log_basic_config(
        level=LogLevel.INFO,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_multiprocessing",
        json_format=False,
    )

    queue = log.get_logging_queue()
    level = log.get_logging_level()
    p = multiprocessing.Process(target=_worker_function, args=(queue, level))
    p.start()
    p.join()

    time.sleep(0.3)
    log_files = list(temp_log_dir.glob("test_multiprocessing_*.log"))
    assert len(log_files) == 1
    content = open(log_files[0], "r", encoding="utf-8").read()
    assert "Hello from child process" in content
    assert "ChildProcess" in content
    assert "worker_pid" in content


def _faulty_worker(queue, level):
    """
    故意抛出异常的子进程工作函数，用于测试子进程异常日志。
    """
    log.init_child_logging(queue, level)
    child_logger = log.get_logger("faulty")
    try:
        raise RuntimeError("Child process error")
    except RuntimeError:
        child_logger.error("Caught exception", exc_info=True)


def test_multiprocessing_exception_propagation(temp_log_dir):
    """
    测试多进程环境中子进程抛出异常时的日志记录。

    验证子进程内部的异常堆栈能够被正确捕获并写入日志文件。
    """
    log.log_basic_config(
        level=LogLevel.ERROR,
        console=False,
        file=True,
        file_path=str(temp_log_dir),
        file_base_name="test_multiprocessing_exception",
        json_format=False,
    )

    queue = log.get_logging_queue()
    level = log.get_logging_level()
    p = multiprocessing.Process(target=_faulty_worker, args=(queue, level))
    p.start()
    p.join()
    time.sleep(0.3)

    log_files = list(temp_log_dir.glob("test_multiprocessing_exception_*.log"))
    assert len(log_files) == 1
    content = open(log_files[0], "r", encoding="utf-8").read()
    assert "Caught exception" in content
    assert "RuntimeError: Child process error" in content


def test_logger_singleton():
    """
    测试 get_logger 返回的适配器是单例。

    同一名称多次调用应返回同一个 ContextAdapter 实例。
    """
    log.log_basic_config(level=LogLevel.INFO, console=False, file=False)
    logger1 = log.get_logger("same")
    logger2 = log.get_logger("same")
    assert logger1 is logger2


def test_logger_name():
    """
    测试 logger 名称设置正确。

    get_logger("custom.name") 返回的适配器内部 logger 名称应为 "custom.name"。
    """
    log.log_basic_config(level=LogLevel.INFO, console=False, file=False)
    logger = log.get_logger("custom.name")
    assert logger.logger.name == "custom.name"


def test_configure_after_start_raises():
    """
    测试在日志系统已经启动后再次调用 log_basic_config 会引发 RuntimeError。

    确保配置只能调用一次。
    """
    log.log_basic_config(level=LogLevel.INFO)
    with pytest.raises(RuntimeError, match="already started"):
        log.log_basic_config(level=LogLevel.DEBUG)