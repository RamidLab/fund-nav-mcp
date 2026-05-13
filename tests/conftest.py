import os
from pathlib import Path
from typing import Dict, AsyncGenerator

import pytest
from sqlalchemy import event

import fund_nav_mcp.config as config_module
from fund_nav_mcp.config import MCPSettings
from fund_nav_mcp.db.core import DBManager


@pytest.fixture(autouse=True)
def clean_globals():
    """每个测试前后重置全局 _settings 变量和清除环境变量影响"""
    # 保存原始值
    original_settings = config_module._settings  # noqa
    # 重置
    config_module._settings = None
    yield
    config_module._settings = original_settings
    # 清理可能的环境变量
    for key in list(os.environ.keys()):
        if key.startswith("MCP_"):
            del os.environ[key]


@pytest.fixture
def mock_config_path(tmp_path: Path, monkeypatch):
    """模拟配置文件路径为临时目录，并替换模块中的 _TOML_CONFIG"""
    fake_config = tmp_path / "config.test.toml"

    monkeypatch.setattr(config_module, "_TOML_CONFIG", fake_config)
    return fake_config


@pytest.fixture(autouse=True)
def patch_toml_file(mock_config_path, monkeypatch, request):
    """自动将所有测试中的 MCPSettings 的 toml_file 指向临时路径"""
    if request.node.get_closest_marker("no_auto_patch"):
        yield
    else:
        monkeypatch.setitem(MCPSettings.model_config, "toml_file", mock_config_path)
        yield


@pytest.fixture
def db_urls(tmp_path) -> Dict[str, str]:
    return {
        "sqlite": "sqlite+aiosqlite:///:memory:",
        "sqlite_file": "sqlite+aiosqlite:///{}/test.db".format(tmp_path),
        "mysql": "mysql+asyncmy://root:root@127.0.0.1:3307/test",
        "postgresql": "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/test",
        "influxdb": "http://127.0.0.1:8087",
    }


@pytest.fixture(params=["sqlite", "sqlite_file", "mysql", "postgresql"])
async def db_manager(request, db_urls: Dict[str, str]) -> AsyncGenerator['DBManager', None]:
    """数据库管理器 fixture，默认只使用 SQLite 内存数据库。"""
    db_name = request.param
    mgr = DBManager(db_urls[db_name])
    await mgr.connect()
    # SQLite 默认不强制外键约束，通过事件监听器在每个连接上开启
    url = db_urls[db_name]
    if url.startswith("sqlite"):
        @event.listens_for(mgr._engine.sync_engine, "connect")  # noqa
        def set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
    await mgr.create_all()
    yield mgr
    await mgr.drop_all()
    await mgr.disconnect()
