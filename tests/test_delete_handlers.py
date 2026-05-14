from datetime import date

import pytest
from sqlalchemy import select

from fund_nav_mcp.handlers.delete_handlers import DeleteHandler
from fund_nav_mcp.models.orm import (
    Fund, FundCategory, FundCategoryMapping, FundHolding,
    FundManager, FundManagerPerson, FundNav, FundReturn,
)
from fund_nav_mcp.models.pydantic.fund import (
    FundCategoryDelete, FundCategoryMappingDelete, FundDelete,
    FundHoldingDelete, FundManagerDelete, FundManagerPersonDelete,
    FundNavDelete, FundReturnDelete,
)
from fund_nav_mcp.utils.enums import (
    Errcode, FundRegulatoryType, FundManagementType, FundStatus,
)
from tests.conftest import HANDLER_DB_NAME


@pytest.fixture
def get_handler():
    return DeleteHandler()


@pytest.mark.asyncio
async def test_delete_fund_by_id(handler_db, seeded_fund: Fund, get_handler: DeleteHandler) -> None:
    data = FundDelete(record_id=seeded_fund.id)
    resp = await get_handler.handle(Fund, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] == seeded_fund.id
    async with handler_db.get_session() as session:
        result = await session.execute(select(Fund).where(Fund.id == seeded_fund.id))
        obj = result.scalars().first()
    assert obj is None


@pytest.mark.asyncio
async def test_delete_nonexistent_id(handler_db, get_handler: DeleteHandler) -> None:
    data = FundDelete(record_id=99999)
    with pytest.raises(ValueError, match="未找到"):
        await get_handler.handle(Fund, data, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_delete_fund_by_code(handler_db, seeded_fund: Fund, get_handler: DeleteHandler) -> None:
    data = FundDelete(fund_code=seeded_fund.fund_code)
    resp = await get_handler.handle(Fund, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] == seeded_fund.id


@pytest.mark.asyncio
async def test_delete_fund_category_by_code(
        handler_db, seeded_category: FundCategory, get_handler: DeleteHandler
) -> None:
    data = FundCategoryDelete(category_code=seeded_category.category_code)
    resp = await get_handler.handle(FundCategory, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_fund_by_name(handler_db, seeded_fund: Fund, get_handler: DeleteHandler) -> None:
    data = FundDelete(fund_name=seeded_fund.fund_name)
    resp = await get_handler.handle(Fund, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] == seeded_fund.id


@pytest.mark.asyncio
async def test_delete_nonexistent_name(handler_db, get_handler: DeleteHandler) -> None:
    data = FundDelete(fund_name="不存在的基金名称")
    with pytest.raises(ValueError, match="未找到"):
        await get_handler.handle(Fund, data, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_delete_ambiguous_name(handler_db, seeded_fund: Fund, get_handler: DeleteHandler) -> None:
    dup = Fund(
        fund_code="DUP001",
        fund_name=seeded_fund.fund_name,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
    )
    await handler_db.insert(dup)

    data = FundDelete(fund_name=seeded_fund.fund_name)
    with pytest.raises(ValueError, match="匹配到 2 条记录"):
        await get_handler.handle(Fund, data, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_delete_fund_manager_by_amac_number(
        handler_db, seeded_manager: FundManager, get_handler: DeleteHandler
) -> None:
    data = FundManagerDelete(
        amac_registration_number=seeded_manager.amac_registration_number,
    )
    resp = await get_handler.handle(FundManager, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] == seeded_manager.id


@pytest.mark.asyncio
async def test_delete_fund_manager_by_unified_code(
        handler_db, seeded_manager: FundManager, get_handler: DeleteHandler
) -> None:
    await handler_db.update_by_id(
        FundManager, seeded_manager.id, {"unified_code": "91110000MA12345678"},
    )
    data = FundManagerDelete(unified_code="91110000MA12345678")
    resp = await get_handler.handle(FundManager, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_fund_manager_person_by_qualification(
        handler_db, seeded_manager_person: FundManagerPerson, get_handler: DeleteHandler
) -> None:
    data = FundManagerPersonDelete(
        qualification_number=seeded_manager_person.qualification_number,
    )
    resp = await get_handler.handle(FundManagerPerson, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_fund_nav_by_compound(
        handler_db, seeded_nav: FundNav, seeded_fund: Fund, get_handler: DeleteHandler
) -> None:
    data = FundNavDelete(
        fund_code=seeded_fund.fund_code,
        nav_date=seeded_nav.nav_date,
    )
    resp = await get_handler.handle(FundNav, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] == seeded_nav.id


@pytest.mark.asyncio
async def test_delete_fund_return_by_compound(
        handler_db, seeded_return: FundReturn, seeded_fund: Fund, get_handler: DeleteHandler
) -> None:
    data = FundReturnDelete(
        fund_code=seeded_fund.fund_code,
        period_type=seeded_return.period_type,
        calculation_date=seeded_return.calculation_date,
    )
    resp = await get_handler.handle(FundReturn, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_fund_holding_by_compound(
        handler_db, seeded_holding: FundHolding, seeded_fund: Fund, get_handler: DeleteHandler
) -> None:
    data = FundHoldingDelete(
        fund_code=seeded_fund.fund_code,
        report_date=seeded_holding.report_date,
        stock_code=seeded_holding.stock_code,
    )
    resp = await get_handler.handle(FundHolding, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_fund_category_mapping_by_compound(
        handler_db,
        seeded_mapping: FundCategoryMapping,
        seeded_fund: Fund,
        seeded_category: FundCategory,
        get_handler: DeleteHandler,
) -> None:
    data = FundCategoryMappingDelete(
        fund_code=seeded_fund.fund_code,
        category_code=seeded_category.category_code,
    )
    resp = await get_handler.handle(FundCategoryMapping, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_batch(handler_db, seeded_fund: Fund, get_handler: DeleteHandler) -> None:
    other = Fund(
        fund_code="DELETE",
        fund_name="批量删除基金",
        fund_regulatory_type=seeded_fund.fund_regulatory_type,
        fund_management_type=seeded_fund.fund_management_type,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
    )
    await handler_db.insert(other)

    data_list = [
        FundDelete(record_id=seeded_fund.id),
        FundDelete(fund_code=other.fund_code),
    ]
    resp = await get_handler.handle_batch(Fund, data_list, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["count"] == 2
    assert set(resp.data["ids"]) == {seeded_fund.id, other.id}


@pytest.mark.asyncio
async def test_delete_batch_empty(handler_db) -> None:
    resp = await DeleteHandler().handle_batch(Fund, [], HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["count"] == 0


@pytest.mark.asyncio
async def test_delete_batch_nonexistent_id(
        handler_db, seeded_fund: Fund, get_handler: DeleteHandler,
) -> None:
    data_list = [
        FundDelete(record_id=seeded_fund.id),
        FundDelete(record_id=99999),
    ]
    with pytest.raises(ValueError, match="未找到"):
        await get_handler.handle_batch(Fund, data_list, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_delete_batch_ambiguous_name(
        handler_db, seeded_fund: Fund, get_handler: DeleteHandler,
) -> None:
    dup = Fund(
        fund_code="DUP002",
        fund_name=seeded_fund.fund_name,
        fund_regulatory_type=FundRegulatoryType.Public,
        fund_management_type=FundManagementType.Trust,
        establishment_date=date(2021, 1, 1),
        registration_date=date(2021, 1, 10),
        status=FundStatus.Active,
    )
    await handler_db.insert(dup)

    data_list = [
        FundDelete(fund_name=seeded_fund.fund_name),
    ]
    with pytest.raises(ValueError, match="匹配到 2 条记录"):
        await get_handler.handle_batch(Fund, data_list, HANDLER_DB_NAME)


@pytest.mark.asyncio
async def test_delete_batch_dedup(
        handler_db, seeded_fund: Fund, get_handler: DeleteHandler,
) -> None:
    """同一记录通过不同方式定位时，自动去重，只删除一次"""
    data_list = [
        FundDelete(record_id=seeded_fund.id),
        FundDelete(fund_code=seeded_fund.fund_code),
    ]
    resp = await get_handler.handle_batch(Fund, data_list, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["count"] == 1
    assert resp.data["ids"] == [seeded_fund.id]


@pytest.mark.asyncio
async def test_delete_person_by_name(
        handler_db, seeded_manager_person: FundManagerPerson, get_handler: DeleteHandler
) -> None:
    data = FundManagerPersonDelete(name=seeded_manager_person.name)
    resp = await get_handler.handle(FundManagerPerson, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS


@pytest.mark.asyncio
async def test_delete_person_by_name_with_company_code(
        handler_db,
        seeded_manager_person: FundManagerPerson,
        seeded_manager: FundManager,
        get_handler: DeleteHandler,
) -> None:
    data = FundManagerPersonDelete(
        name=seeded_manager_person.name,
        company_code=seeded_manager.amac_registration_number,
    )
    resp = await get_handler.handle(FundManagerPerson, data, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data["id"] == seeded_manager_person.id


@pytest.mark.asyncio
async def test_delete_no_lookup_fields_raises() -> None:
    with pytest.raises(ValueError, match="至少需要提供"):
        FundDelete()


@pytest.mark.asyncio
async def test_delete_cannot_locate(handler_db, get_handler: DeleteHandler) -> None:
    data = FundNavDelete(fund_code="NONEXIST", nav_date=date(2020, 1, 1))
    with pytest.raises(ValueError, match="未找到"):
        await get_handler.handle(FundNav, data, HANDLER_DB_NAME)
