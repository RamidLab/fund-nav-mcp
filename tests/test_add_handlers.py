from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from fund_nav_mcp.handlers.add_handlers import AddHandler
from fund_nav_mcp.models.orm import (
    Fund, FundCategory, FundCategoryMapping, FundHolding,
    FundManager, FundManagerPerson, FundNav, FundReturn,
)
from fund_nav_mcp.models.pydantic.fund import (
    FundCreate, FundCategoryCreate, FundCategoryMappingCreate,
    FundHoldingCreate, FundManagerCreate, FundManagerPersonCreate,
    FundNavCreate, FundReturnCreate,
)
from fund_nav_mcp.utils.enums import (
    Errcode, FundDataSource, FundManagementType, FundNavStatus,
    FundRegulatoryType, FundStatus, FundType, PeriodType, ShareClass,
)
from tests.conftest import HANDLER_DB_NAME


@pytest.mark.asyncio
async def test_add_fund_with_all_code_fields(
        handler_db, seeded_manager: FundManager, seeded_manager_person: FundManagerPerson,
) -> None:
    handler = AddHandler()
    data = FundCreate(
        fund_code="000002",
        fund_name="测试二号基金",
        fund_type=FundType.Stock,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2021, 3, 15),
        registration_date=date(2021, 3, 20),
        status=FundStatus.Active,
        share_class=ShareClass.A,
        manager_code=seeded_manager.amac_registration_number,
        manager_person_code=seeded_manager_person.qualification_number,
    )
    resp = await handler.handle(Fund, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None

    new_id: int = resp.data["id"]
    assert new_id > 0
    async with handler_db.get_session() as session:
        result = await session.execute(select(Fund).where(Fund.id == new_id))
        obj = result.scalars().first()
    assert obj is not None
    assert obj.fund_code == "000002"


@pytest.mark.asyncio
async def test_add_fund_with_name_resolution(handler_db, seeded_manager: FundManager) -> None:
    handler = AddHandler()
    data = FundCreate(
        fund_code="000003",
        fund_name="名称解析基金",
        fund_type=FundType.Stock,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2021, 6, 1),
        registration_date=date(2021, 6, 10),
        status=FundStatus.Active,
        manager_name=seeded_manager.company_name,
    )
    resp = await handler.handle(Fund, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    async with handler_db.get_session() as session:
        result = await session.execute(
            select(Fund).where(Fund.id == resp.data["id"])
        )
        obj = result.scalars().first()
    assert obj is not None
    assert obj.fund_manager_id == seeded_manager.id


@pytest.mark.asyncio
async def test_add_fund_duplicate_code(handler_db, seeded_fund: Fund) -> None:
    handler = AddHandler()
    data = FundCreate(
        fund_code=seeded_fund.fund_code,
        fund_name="重复基金",
        fund_type=FundType.Stock,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
    )
    with pytest.raises(ValueError, match="已存在"):
        await handler.handle(Fund, data, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_add_fund_unresolvable_code(handler_db) -> None:
    handler = AddHandler()
    data = FundCreate(
        fund_code="000004",
        fund_name="无关联基金",
        fund_type=FundType.Stock,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
        manager_code="P9999999",
    )
    with pytest.raises(ValueError, match="无法解析"):
        await handler.handle(Fund, data, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_add_fund_manager(handler_db) -> None:
    handler = AddHandler()
    data = FundManagerCreate(
        company_name="新测试公司",
        short_name="新公司",
        english_name="New Test Company",
        amac_registration_number="P2000001",
        amac_registration_date=date(2023, 1, 1),
        unified_code="91110000MA00000001",
        organization_type="私募证券投资基金管理人",
        business_type="私募证券投资基金",
        registered_capital=Decimal("1000.00"),
        paid_up_capital=Decimal("500.00"),
        capital_ratio=Decimal("50.00"),
        registered_address="北京市朝阳区测试路1号",
        office_address="北京市朝阳区测试路1号",
        employee_count=20,
        fund_industry_count=15,
        management_scale_range=None,
        actual_controller="王五",
        legal_representative="王五",
        is_member=True,
    )
    resp = await handler.handle(FundManager, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_fund_manager_batch(handler_db) -> None:
    handler = AddHandler()
    data_list = [
        FundManagerCreate(
            company_name="批量公司A",
            short_name="公司A",
            english_name="Batch Company A",
            amac_registration_number="P0000011",
            amac_registration_date=None,
            unified_code=None,
            organization_type=None,
            business_type=None,
            registered_capital=None,
            paid_up_capital=None,
            capital_ratio=None,
            registered_address=None,
            office_address=None,
            employee_count=None,
            fund_industry_count=None,
            management_scale_range=None,
            actual_controller=None,
            legal_representative=None,
            is_member=False,
        ),
        FundManagerCreate(
            company_name="批量公司B",
            short_name="公司B",
            english_name="Batch Company B",
            amac_registration_number="P0000012",
            amac_registration_date=None,
            unified_code=None,
            organization_type=None,
            business_type=None,
            registered_capital=None,
            paid_up_capital=None,
            capital_ratio=None,
            registered_address=None,
            office_address=None,
            employee_count=None,
            fund_industry_count=None,
            management_scale_range=None,
            actual_controller=None,
            legal_representative=None,
            is_member=False,
        ),
    ]
    resp = await handler.handle_batch(FundManager, data_list, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["count"] == 2
    assert len(resp.data["ids"]) == 2


@pytest.mark.asyncio
async def test_add_fund_manager_person(handler_db, seeded_manager: FundManager) -> None:
    handler = AddHandler()
    data = FundManagerPersonCreate(
        name="李四",
        gender="男",
        birth_date=date(1985, 6, 15),
        education="硕士",
        qualification_number="Q20240002",
        is_qualified=True,
        resume="十年投资研究经验",
        company_code=seeded_manager.amac_registration_number,
    )
    resp = await handler.handle(FundManagerPerson, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_fund_category(handler_db) -> None:
    handler = AddHandler()
    data = FundCategoryCreate(
        category_code="BOND",
        category_name="债券型基金",
        parent_category_code=None,
        level=1,
        description="主要投资于债券的基金产品",
    )
    resp = await handler.handle(FundCategory, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_fund_category_duplicate_code(handler_db, seeded_category: FundCategory) -> None:
    handler = AddHandler()
    data = FundCategoryCreate(
        category_code=seeded_category.category_code,
        category_name="重复分类",
        parent_category_code=None,
        level=1,
        description=None,
    )
    with pytest.raises(ValueError, match="已存在"):
        await handler.handle(FundCategory, data, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_add_category_mapping(
        handler_db, seeded_fund: Fund, seeded_category: FundCategory,
) -> None:
    handler = AddHandler()
    data = FundCategoryMappingCreate(
        fund_code=seeded_fund.fund_code,
        category_code=seeded_category.category_code,
    )
    resp = await handler.handle(FundCategoryMapping, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_fund_nav(handler_db, seeded_fund: Fund) -> None:
    handler = AddHandler()
    data = FundNavCreate(
        fund_code=seeded_fund.fund_code,
        nav_date=date(2025, 7, 1),
        nav_unit=Decimal("1.5000"),
        nav_acc=Decimal("2.8000"),
        nav_adj=Decimal("1.5500"),
        daily_return_rate=Decimal("0.0035"),
        nav_status=FundNavStatus.Valid,
        data_source=FundDataSource.ManualImport,
    )
    resp = await handler.handle(FundNav, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_fund_return(handler_db, seeded_fund: Fund) -> None:
    handler = AddHandler()
    data = FundReturnCreate(
        fund_code=seeded_fund.fund_code,
        period_type=PeriodType.Monthly,
        return_rate=Decimal("0.0520"),
        rank=10,
        total_funds=200,
        calculation_date=date(2025, 7, 1),
    )
    resp = await handler.handle(FundReturn, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_fund_holding(handler_db, seeded_fund: Fund) -> None:
    handler = AddHandler()
    data = FundHoldingCreate(
        fund_code=seeded_fund.fund_code,
        report_date=date(2025, 6, 30),
        stock_code="000858",
        stock_name="五粮液",
        holding_ratio=Decimal("0.0310"),
        market_value=Decimal("30000.00"),
        shares_held=Decimal("5.00"),
    )
    resp = await handler.handle(FundHolding, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] > 0


@pytest.mark.asyncio
async def test_add_batch_funds(handler_db, seeded_manager: FundManager) -> None:
    handler = AddHandler()
    data_list = [
        FundCreate(
            fund_code="000011",
            fund_name="批量基金1",
            fund_type=FundType.Stock,
            fund_regulatory_type=FundRegulatoryType.Public,
            fund_management_type=FundManagementType.Trust,
            establishment_date=date(2022, 1, 1),
            registration_date=date(2022, 1, 5),
            status=FundStatus.Active,
            manager_code=seeded_manager.amac_registration_number,
        ),
        FundCreate(
            fund_code="000012",
            fund_name="批量基金2",
            fund_type=FundType.Stock,
            fund_regulatory_type=FundRegulatoryType.Public,
            fund_management_type=FundManagementType.Trust,
            establishment_date=date(2022, 2, 1),
            registration_date=date(2022, 2, 5),
            status=FundStatus.Active,
            manager_code=seeded_manager.amac_registration_number,
        ),
    ]
    resp = await handler.handle_batch(Fund, data_list, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["count"] == 2
