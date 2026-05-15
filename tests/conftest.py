import os
from datetime import date
from pathlib import Path
from typing import Dict, AsyncGenerator

import pytest
from sqlalchemy import event

import fund_nav_mcp.config as config_module
from fund_nav_mcp.config import MCPSettings
from fund_nav_mcp.db.core import DBManager, _manager_cache  # noqa
from fund_nav_mcp.models.orm import (
    FundManager, FundManagerPerson, FundCategory, FundCategoryMapping,
    Fund, FundNav, FundReturn, FundHolding, Base,
)
from fund_nav_mcp.utils.enums import (
    FundStatus, FundNavStatus, FundType, FundRegulatoryType, FundManagementType,
    PeriodType, FundDataSource, ShareClass,
)

HANDLER_DB_NAME = "handler_test"


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


@pytest.fixture(autouse=True)
def clean_manager_cache():
    """每个测试前后清理全局 manager 缓存，确保隔离。"""
    _manager_cache.pop("db", None)
    _manager_cache.pop("cache", None)
    yield
    _manager_cache.pop("db", None)
    _manager_cache.pop("cache", None)


async def _create_handler_db() -> DBManager:
    mgr = DBManager("sqlite+aiosqlite:///:memory:")
    await mgr.connect()

    @event.listens_for(mgr._engine.sync_engine, "connect")  # noqa
    def _pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    await mgr.create_all()
    return mgr


@pytest.fixture
async def handler_db() -> AsyncGenerator[DBManager, None]:
    """为 handler 测试提供已注册的 SQLite 内存 DBManager。"""
    mgr = await _create_handler_db()
    _manager_cache.setdefault("db", {})[HANDLER_DB_NAME] = {"mgr": mgr, "db_type": "sqlite"}
    yield mgr
    await mgr.drop_all()
    await mgr.disconnect()
    _manager_cache.pop("db", None)


@pytest.fixture
async def seeded_manager(handler_db: DBManager) -> Base:
    """预置一条 FundManager 记录。"""
    obj = FundManager(
        company_name="测试基金管理有限公司",
        short_name="测试基金",
        english_name="Test Fund Management Co., Ltd.",
        amac_registration_number="P1000001",
        unified_code="91110000MA00000001",
        organization_type="私募证券投资基金管理人",
        business_type="私募证券投资基金",
        registered_address="北京市朝阳区测试路100号",
        office_address="北京市朝阳区测试路100号",
        actual_controller="王五",
        legal_representative="王五",
        is_member=True,
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_manager_person(handler_db: DBManager, seeded_manager: FundManager) -> Base:
    """预置一条 FundManagerPerson 记录。"""
    obj = FundManagerPerson(
        name="张三",
        gender="男",
        education="硕士",
        qualification_number="Q20240001",
        is_qualified=True,
        resume="多年基金管理经验",
        current_company_id=seeded_manager.id,
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_fund(
        handler_db: DBManager,
        seeded_manager: FundManager,
        seeded_manager_person: FundManagerPerson,
) -> Base:
    """预置一条完整的 Fund 记录（含关联 manager 和 person）。"""
    obj = Fund(
        fund_code="000001",
        fund_name="测试公募基金",
        fund_type=FundType.Stock,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_manager_id=seeded_manager.id,
        fund_manager_person_id=seeded_manager_person.id,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2020, 1, 1),
        registration_date=date(2020, 1, 15),
        status=FundStatus.Active,
        share_class=ShareClass.A,
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_category(handler_db: DBManager) -> Base:
    """预置一条 FundCategory 记录。"""
    obj = FundCategory(
        category_code="STOCK",
        category_name="股票型基金",
        level=1,
        description="主要投资于股票的基金",
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_nav(handler_db: DBManager, seeded_fund: Fund) -> Base:
    """预置一条 FundNav 记录。"""
    obj = FundNav(
        fund_id=seeded_fund.id,
        nav_date=date(2025, 6, 1),
        nav_unit=1.2345,
        nav_acc=2.3456,
        nav_status=FundNavStatus.Valid,
        data_source=FundDataSource.ManualImport,
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_return(handler_db: DBManager, seeded_fund: Fund) -> Base:
    """预置一条 FundReturn 记录。"""
    obj = FundReturn(
        fund_id=seeded_fund.id,
        period_type=PeriodType.Daily,
        return_rate=0.0123,
        rank=5,
        total_funds=100,
        calculation_date=date(2025, 6, 1),
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_holding(handler_db: DBManager, seeded_fund: Fund) -> Base:
    """预置一条 FundHolding 记录。"""
    obj = FundHolding(
        fund_id=seeded_fund.id,
        report_date=date(2025, 3, 31),
        stock_code="600519",
        stock_name="贵州茅台",
        holding_ratio=0.0512,
        market_value=50000.00,
        shares_held=10.00,
    )
    return await handler_db.insert(obj)


@pytest.fixture
async def seeded_mapping(
        handler_db: DBManager, seeded_fund: Fund, seeded_category: FundCategory,
) -> Base:
    """预置一条 FundCategoryMapping 记录。"""
    obj = FundCategoryMapping(
        fund_id=seeded_fund.id,
        category_id=seeded_category.id,
    )
    return await handler_db.insert(obj)
