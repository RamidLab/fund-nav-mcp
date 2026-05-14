import pytest

from fund_nav_mcp.handlers.query_handlers import QueryHandler
from fund_nav_mcp.models.orm import (
    Fund, FundCategory, FundCategoryMapping, FundHolding,
    FundManager, FundManagerPerson, FundNav, FundReturn,
)
from fund_nav_mcp.models.pydantic.filter import FundFilter
from fund_nav_mcp.models.schemas import PaginationParams
from fund_nav_mcp.utils.enums import (
    Errcode, )
from tests.conftest import HANDLER_DB_NAME


@pytest.fixture
def handler() -> QueryHandler:
    return QueryHandler()

@pytest.fixture
def params() -> PaginationParams:
    return PaginationParams()

@pytest.mark.asyncio
async def test_query_no_filter(handler_db, seeded_fund: Fund, handler: QueryHandler) -> None:
    params = PaginationParams(page=1, page_size=10)
    resp = await handler.handle(Fund, params, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data.pagination.total >= 1
    assert len(resp.data.items) >= 1


@pytest.mark.asyncio
async def test_query_pagination_second_page(handler_db, seeded_fund: Fund, handler: QueryHandler) -> None:
    params = PaginationParams(page=2, page_size=10)
    resp = await handler.handle(Fund, params, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data.pagination.page == 2


@pytest.mark.asyncio
async def test_query_empty_result(handler_db, handler: QueryHandler) -> None:
    params = PaginationParams(page=1, page_size=10)
    resp = await handler.handle(FundNav, params, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data.pagination.total == 0
    assert resp.data.items == []


@pytest.mark.asyncio
async def test_query_filter_exact_fund_code(handler_db, seeded_fund: Fund, handler: QueryHandler) -> None:
    f = FundFilter.model_validate({"fund_code": "000001"})
    params = PaginationParams(page=1, page_size=10)
    resp = await handler.handle(Fund, params, f, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data.pagination.total == 1
    assert resp.data.items[0]["fund_code"] == "000001"


@pytest.mark.asyncio
async def test_query_filter_no_match(handler_db, seeded_fund: Fund, handler: QueryHandler) -> None:
    f = FundFilter.model_validate({"fund_code": "NONEXISTENT"})
    params = PaginationParams()
    resp = await handler.handle(Fund, params, f, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    assert resp.data.pagination.total == 0


@pytest.mark.asyncio
async def test_query_fund_expands_manager_name(
        handler_db,
        seeded_fund: Fund,
        seeded_manager: FundManager,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    resp = await handler.handle(Fund, params, None, HANDLER_DB_NAME)
    assert resp.data is not None
    items = resp.data.items
    matching = [it for it in items if it.get("fund_code") == seeded_fund.fund_code]
    assert len(matching) == 1
    item = matching[0]
    assert "fund_manager_id" not in item
    assert item.get("company_name") == seeded_manager.company_name
    assert item.get("company_short_name") == seeded_manager.short_name


@pytest.mark.asyncio
async def test_query_fund_nav_expands_fund_code(
        handler_db,
        seeded_nav: FundNav,
        seeded_fund: Fund,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    resp = await handler.handle(FundNav, params, None, HANDLER_DB_NAME)
    assert resp.data is not None
    items = resp.data.items
    assert len(items) >= 1
    item = items[0]
    assert "fund_id" not in item
    assert item.get("fund_name") == seeded_fund.fund_name
    assert item.get("fund_code") == seeded_fund.fund_code


@pytest.mark.asyncio
async def test_query_fund_manager_person_expands_company(
        handler_db,
        seeded_manager_person: FundManagerPerson,
        seeded_manager: FundManager,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    resp = await handler.handle(FundManagerPerson, params, None, HANDLER_DB_NAME)
    assert resp.data is not None
    items = resp.data.items
    assert len(items) >= 1
    item = items[0]
    assert "current_company_id" not in item
    assert item.get("company_name") == seeded_manager.company_name
    assert item.get("company_short_name") == seeded_manager.short_name


@pytest.mark.asyncio
async def test_query_fund_category_expands_parent(
        handler_db,
        seeded_category: FundCategory,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    child = FundCategory(
        category_code="SUB_STOCK",
        category_name="小盘股票型",
        level=2,
        parent_id=seeded_category.id,
    )
    await handler_db.insert(child)

    params = PaginationParams()
    resp = await handler.handle(FundCategory, params, None, HANDLER_DB_NAME)
    assert resp.data is not None
    items = resp.data.items
    sub = [it for it in items if it.get("category_code") == "SUB_STOCK"]
    assert len(sub) == 1
    assert "parent_id" not in sub[0]
    assert sub[0].get("parent_category_name") == seeded_category.category_name


@pytest.mark.asyncio
async def test_query_fund_return_mapping(
        handler_db,
        seeded_return: FundReturn,
        seeded_fund: Fund,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    resp = await handler.handle(FundReturn, params, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    items = resp.data.items
    assert len(items) >= 1
    assert items[0].get("fund_name") == seeded_fund.fund_name


@pytest.mark.asyncio
async def test_query_fund_holding_mapping(
        handler_db,
        seeded_holding: FundHolding,
        seeded_fund: Fund,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    resp = await handler.handle(FundHolding, params, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    items = resp.data.items
    assert len(items) >= 1
    assert items[0].get("fund_name") == seeded_fund.fund_name


@pytest.mark.asyncio
async def test_query_category_mapping(
        handler_db,
        seeded_mapping: FundCategoryMapping,
        seeded_fund: Fund,
        seeded_category: FundCategory,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    resp = await handler.handle(FundCategoryMapping, params, None, HANDLER_DB_NAME)
    assert resp.code == Errcode.SUCCESS
    assert resp.data is not None
    items = resp.data.items
    assert len(items) >= 1
    item = items[0]
    assert "fund_id" not in item
    assert item.get("fund_name") == seeded_fund.fund_name
    assert item.get("category_name") == seeded_category.category_name

@pytest.mark.asyncio
async def test_custom_field_mapping(
        handler_db,
        seeded_fund: Fund,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    custom: dict = {
        Fund: {
            "fund_manager_id": (
                FundManager,
                [("company_name", "manager_company"), ("short_name", "manager_short")],
            ),
        },
    }
    handler = QueryHandler(field_mapping=custom)
    resp = await handler.handle(Fund, params, None, HANDLER_DB_NAME)
    assert resp.data is not None
    items = resp.data.items
    matching = [it for it in items if it.get("fund_code") == seeded_fund.fund_code]
    assert len(matching) == 1
    item = matching[0]
    assert "fund_manager_id" not in item
    assert "manager_company" in item
    assert "manager_short" in item
    assert "company_name" not in item


@pytest.mark.asyncio
async def test_query_returns_correct_values(
        handler_db,
        seeded_fund: Fund,
        handler: QueryHandler,
        params: PaginationParams
) -> None:
    f = FundFilter.model_validate({"fund_code": seeded_fund.fund_code})
    resp = await handler.handle(Fund, params, f, HANDLER_DB_NAME)
    assert resp.data is not None
    item = resp.data.items[0]
    assert item["fund_name"] == seeded_fund.fund_name
    assert item["fund_code"] == seeded_fund.fund_code
    assert item["fund_short_name"] == seeded_fund.fund_short_name
    assert item["status"] == seeded_fund.status
