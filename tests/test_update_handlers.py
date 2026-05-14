from datetime import date

import pytest
from sqlalchemy import select

from fund_nav_mcp.handlers.update_handlers import UpdateHandler
from fund_nav_mcp.models.orm import (
    Fund, FundCategory, FundHolding, FundManager,
    FundManagerPerson, FundNav, FundReturn,
)
from fund_nav_mcp.models.pydantic.fund import (
    FundCategoryUpdate, FundHoldingUpdate, FundManagerPersonUpdate,
    FundManagerUpdate, FundNavUpdate, FundReturnUpdate, FundUpdate,
)
from fund_nav_mcp.utils.enums import (
    Errcode, FundNavStatus, FundStatus,
)
from tests.conftest import HANDLER_DB_NAME


@pytest.fixture
def handler():
    return UpdateHandler()


@pytest.mark.asyncio
async def test_update_fund_by_id(handler_db, seeded_fund: Fund, handler: UpdateHandler) -> None:
    data = FundUpdate(fund_name="已更名的基金")
    resp = await handler.handle(Fund, data, seeded_fund.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert (resp.data.get("id") if resp.data else None) == seeded_fund.id
    async with handler_db.get_session() as session:
        result = await session.execute(select(Fund).where(Fund.id == seeded_fund.id))
        obj = result.scalars().first()
    assert obj is not None
    assert obj.fund_name == "已更名的基金"
    assert obj.fund_code == seeded_fund.fund_code


@pytest.mark.asyncio
async def test_update_fund_by_code(handler_db, seeded_fund: Fund, handler: UpdateHandler) -> None:
    data = FundUpdate(
        fund_code=seeded_fund.fund_code,
        fund_name="通过code更新",
    )
    resp = await handler.handle(Fund, data, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    async with handler_db.get_session() as session:
        result = await session.execute(select(Fund).where(Fund.id == seeded_fund.id))
        obj = result.scalars().first()
    assert obj is not None
    assert obj.fund_name == "通过code更新"


@pytest.mark.asyncio
async def test_update_no_fields(handler_db, seeded_fund: Fund, handler: UpdateHandler) -> None:
    data = FundUpdate()
    resp = await handler.handle(Fund, data, seeded_fund.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert "没有需要更新的字段" in resp.message
    assert (resp.data.get("id") if resp.data else None) == seeded_fund.id


@pytest.mark.asyncio
async def test_update_fund_change_manager(
        handler_db, seeded_fund: Fund, seeded_manager: FundManager, handler: UpdateHandler,
) -> None:
    new_mgr = FundManager(
        company_name="另一家管理公司",
        short_name="另一家",
        amac_registration_number="P3000001",
    )
    await handler_db.insert(new_mgr)
    data = FundUpdate(manager_code=new_mgr.amac_registration_number)
    resp = await handler.handle(Fund, data, seeded_fund.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    async with handler_db.get_session() as session:
        result = await session.execute(select(Fund).where(Fund.id == seeded_fund.id))
        obj = result.scalars().first()
    assert obj is not None
    assert obj.fund_manager_id == new_mgr.id


@pytest.mark.asyncio
async def test_update_fund_code_conflict_with_other(
        handler_db, seeded_fund: Fund, handler: UpdateHandler
) -> None:
    other = Fund(
        fund_code="OTHER01",
        fund_name="另一基金",
        fund_regulatory_type=seeded_fund.fund_regulatory_type,
        fund_management_type=seeded_fund.fund_management_type,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
    )
    await handler_db.insert(other)

    data = FundUpdate(fund_code=other.fund_code)
    with pytest.raises(ValueError, match="已存在"):
        await handler.handle(Fund, data, seeded_fund.id, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_update_batch(handler_db, seeded_fund: Fund, handler: UpdateHandler) -> None:
    other = Fund(
        fund_code="OTHER02",
        fund_name="另一基金2",
        fund_regulatory_type=seeded_fund.fund_regulatory_type,
        fund_management_type=seeded_fund.fund_management_type,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
    )
    await handler_db.insert(other)

    data_list = [
        FundUpdate(fund_short_name="简称A"),
        FundUpdate(fund_short_name="简称B"),
    ]
    resp = await handler.handle_batch(
        Fund, [seeded_fund.id, other.id], data_list, HANDLER_DB_NAME,
    )
    assert resp.code == Errcode.SUCCESS
    assert (resp.data.get("count") if resp.data else None) == 2
    async with handler_db.get_session() as session:
        result = await session.execute(select(Fund).where(Fund.id == seeded_fund.id))
        obj = result.scalars().first()
    assert obj is not None
    assert obj.fund_short_name == "简称A"


@pytest.mark.asyncio
async def test_update_batch_mismatched_lengths(
        handler_db, seeded_fund: Fund, handler: UpdateHandler
) -> None:
    data_list = [FundUpdate(fund_short_name="简称")]
    with pytest.raises(ValueError, match="数量不匹配"):
        await handler.handle_batch(Fund, [1, 2], data_list, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_update_batch_empty(handler_db, handler: UpdateHandler) -> None:
    resp = await handler.handle_batch(Fund, [], [], HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert (resp.data.get("count") if resp.data else None) == 0


@pytest.mark.asyncio
async def test_update_fund_manager(
        handler_db, seeded_manager: FundManager, handler: UpdateHandler
) -> None:
    data = FundManagerUpdate.model_validate({"short_name": "新简称"})
    resp = await handler.handle(FundManager, data, seeded_manager.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_update_fund_manager_person(
        handler_db, seeded_manager_person: FundManagerPerson, handler: UpdateHandler
) -> None:
    data = FundManagerPersonUpdate.model_validate({"education": "博士"})
    resp = await handler.handle(
        FundManagerPerson, data, seeded_manager_person.id, HANDLER_DB_NAME,
    )
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_update_fund_category(
        handler_db, seeded_category: FundCategory, handler: UpdateHandler
) -> None:
    data = FundCategoryUpdate.model_validate({"description": "更新后的描述"})
    resp = await handler.handle(FundCategory, data, seeded_category.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_update_fund_nav(
        handler_db, seeded_nav: FundNav, handler: UpdateHandler
) -> None:
    data = FundNavUpdate.model_validate({"nav_status": FundNavStatus.Estimate})
    resp = await handler.handle(FundNav, data, seeded_nav.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_update_fund_return(
        handler_db, seeded_return: FundReturn, handler: UpdateHandler
) -> None:
    data = FundReturnUpdate.model_validate({"rank": 1})
    resp = await handler.handle(FundReturn, data, seeded_return.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_update_fund_holding(
        handler_db, seeded_holding: FundHolding, handler: UpdateHandler
) -> None:
    data = FundHoldingUpdate.model_validate({"stock_name": "更新后的股票名"})
    resp = await handler.handle(FundHolding, data, seeded_holding.id, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
