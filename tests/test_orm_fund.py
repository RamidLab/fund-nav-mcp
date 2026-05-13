from datetime import date
from typing import Dict, Any

import pytest
from sqlalchemy import select, func, insert, exc as sa_exc

from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.utils.enums import (
    FundStatus, FundNavStatus, FundRegulatoryType, FundManagementType,
    FundDataSource, ShareClass, PeriodType, FundType,
)


def _col(table, name: str):
    return table.columns[name]


async def _count(db, table) -> int:
    result = await db.execute(select(func.count()).select_from(table))
    return result.scalar()


async def _insert_fund(db, **overrides: Any) -> Dict[str, Any]:
    """插入一条 Fund 记录，返回数据字典（包含 id）。"""
    data: Dict[str, Any] = {
        "fund_code": "000001",
        "fund_name": "测试基金",
        "fund_regulatory_type": FundRegulatoryType.Public,
        "fund_management_type": FundManagementType.Trust,
        "establishment_date": date(2020, 1, 1),
        "registration_date": date(2020, 2, 1),
        "status": FundStatus.Active,
    }
    data.update(overrides)
    table = Base.metadata.tables["fund"]
    await db.execute(insert(table).values(**data))
    row = await db.fetch_one(select(table).where(_col(table, "fund_code") == data["fund_code"]))
    assert row is not None, f"插入后未能查询到 fund_code={data['fund_code']}"
    data["id"] = row["id"]
    return data


class TestFundTable:
    """Fund 表结构、约束、默认值"""

    @pytest.mark.asyncio
    async def test_table_exists(self, db_manager):
        assert "fund" in Base.metadata.tables

    @pytest.mark.asyncio
    async def test_columns_exist(self, db_manager):
        table = Base.metadata.tables["fund"]
        cols = {c.name for c in table.columns}
        expected = {
            "id", "created_at", "updated_at",
            "fund_code", "fund_name", "fund_short_name", "fund_type",
            "fund_regulatory_type", "fund_manager_person_id", "fund_manager_id",
            "fund_management_type", "fund_custodian", "fund_registration_address",
            "establishment_date", "registration_date", "status", "share_class",
            "parent_fund_id",
        }
        assert expected.issubset(cols)

    @pytest.mark.asyncio
    async def test_unique_fund_code(self, db_manager):
        """fund_code 列有 UNIQUE 约束"""
        # 通过尝试插入重复值验证
        await _insert_fund(db_manager, fund_code="UNIQ01")
        with pytest.raises(sa_exc.IntegrityError):
            await _insert_fund(db_manager, fund_code="UNIQ01")

    @pytest.mark.asyncio
    async def test_share_class_default(self, db_manager):
        """share_class 默认值为 NotApplicable (0)"""
        table = Base.metadata.tables["fund"]
        await _insert_fund(db_manager, fund_code="DEFAULT01", share_class=ShareClass.NotApplicable)
        row = await db_manager.fetch_one(select(table).where(_col(table, "fund_code") == "DEFAULT01"))
        assert row is not None
        assert int(row["share_class"]) == int(ShareClass.NotApplicable)

    @pytest.mark.asyncio
    async def test_indexes_exist(self, db_manager):
        table = Base.metadata.tables["fund"]
        index_names = {idx.name for idx in table.indexes}
        expected = {
            "idx_fund_est_date", "idx_fund_name", "idx_fund_manager_id",
            "idx_fund_manager_person_id", "idx_fund_share_class", "idx_fund_parent_id",
        }
        assert expected.issubset(index_names)

    @pytest.mark.asyncio
    async def test_foreign_keys_exist(self, db_manager):
        table = Base.metadata.tables["fund"]
        fk_targets = set()
        for fk in table.foreign_key_constraints:
            for elem in fk.elements:
                fk_targets.add(elem.target_fullname)
        assert "fund_manager_person.id" in fk_targets
        assert "fund_manager.id" in fk_targets
        assert "fund.id" in fk_targets  # parent_fund_id → self


class TestFundCRUD:

    @pytest.mark.asyncio
    async def test_insert_minimal(self, db_manager):
        """仅必填字段插入"""
        data = await _insert_fund(db_manager, fund_code="MIN001")
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_insert_full(self, db_manager):
        """所有字段插入"""
        data: Dict[str, Any] = {
            "fund_code": "FULL01",
            "fund_name": "全字段测试基金",
            "fund_short_name": "全字段简称",
            "fund_type": FundType.Mixed,
            "fund_regulatory_type": FundRegulatoryType.Public,
            "fund_management_type": FundManagementType.Advisory,
            "fund_custodian": "工商银行",
            "fund_registration_address": "北京市朝阳区",
            "establishment_date": date(2019, 6, 1),
            "registration_date": date(2019, 7, 15),
            "status": FundStatus.Active,
            "share_class": ShareClass.C,
        }
        await _insert_fund(db_manager, **data)
        table = Base.metadata.tables["fund"]
        row = await db_manager.fetch_one(
            select(table).where(_col(table, "fund_code") == "FULL01")
        )
        assert row is not None
        for k, v in data.items():
            actual = row[k]
            if hasattr(v, "value"):  # enum → int
                actual = int(actual)
                v = int(v)
            assert actual == v, f"列 {k} 不匹配: {actual} != {v}"

    @pytest.mark.asyncio
    async def test_insert_private_fund_with_share_class(self, db_manager):
        """私募基金插入份额类别（结构化层级）"""
        await _insert_fund(
            db_manager,
            fund_code="S00001",
            fund_name="私募优先级基金",
            fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
            share_class=ShareClass.A,
        )
        table = Base.metadata.tables["fund"]
        row = await db_manager.fetch_one(
            select(table).where(_col(table, "fund_code") == "S00001")
        )
        assert row is not None
        assert int(row["share_class"]) == int(ShareClass.A)

    @pytest.mark.asyncio
    async def test_insert_duplicate_fund_code_fails(self, db_manager):
        """重复 fund_code 应违反唯一约束"""
        await _insert_fund(db_manager, fund_code="DUP001")
        with pytest.raises(sa_exc.IntegrityError):
            await _insert_fund(db_manager, fund_code="DUP001")

    @pytest.mark.asyncio
    async def test_update_fund(self, db_manager):
        await _insert_fund(db_manager, fund_code="UPD001")
        table = Base.metadata.tables["fund"]
        await db_manager.execute(
            table.update().where(_col(table, "fund_code") == "UPD001").values(
                fund_name="更新后名称",
                status=FundStatus.Terminated,
            )
        )
        row = await db_manager.fetch_one(
            select(table).where(_col(table, "fund_code") == "UPD001")
        )
        assert row is not None
        assert row["fund_name"] == "更新后名称"
        assert int(row["status"]) == int(FundStatus.Terminated)

    @pytest.mark.asyncio
    async def test_delete_fund(self, db_manager):
        await _insert_fund(db_manager, fund_code="DEL001")
        table = Base.metadata.tables["fund"]
        await db_manager.execute(
            table.delete().where(_col(table, "fund_code") == "DEL001")
        )
        assert await _count(db_manager, table) == 0

    @pytest.mark.asyncio
    async def test_query_by_code(self, db_manager):
        await _insert_fund(db_manager, fund_code="QBY001", fund_name="按代码查询")
        table = Base.metadata.tables["fund"]
        row = await db_manager.fetch_one(
            select(table).where(_col(table, "fund_code") == "QBY001")
        )
        assert row is not None
        assert row["fund_name"] == "按代码查询"

    @pytest.mark.asyncio
    async def test_query_by_share_class(self, db_manager):
        """按份额类别筛选"""
        await _insert_fund(db_manager, fund_code="SC001", share_class=ShareClass.A)
        await _insert_fund(db_manager, fund_code="SC002", share_class=ShareClass.C)
        table = Base.metadata.tables["fund"]
        rows = await db_manager.fetch_all(
            select(table).where(_col(table, "share_class") == ShareClass.A)
        )
        assert len(rows) == 1
        assert rows[0]["fund_code"] == "SC001"

    @pytest.mark.asyncio
    async def test_nullable_fields_accept_none(self, db_manager):
        """可空字段应允许 None"""
        await _insert_fund(
            db_manager,
            fund_code="NULL01",
            fund_short_name=None,
            fund_custodian=None,
            fund_registration_address=None,
            fund_type=None,
            parent_fund_id=None,
            fund_manager_person_id=None,
        )
        table = Base.metadata.tables["fund"]
        row = await db_manager.fetch_one(
            select(table).where(_col(table, "fund_code") == "NULL01")
        )
        assert row is not None
        assert row["fund_short_name"] is None
        assert row["fund_custodian"] is None
        assert row["fund_type"] is None

    @pytest.mark.asyncio
    async def test_string_length_limit(self, db_manager):
        """超长字符串：SQLite 不强制长度，MySQL/PostgreSQL 会报错（DataError 或 DBAPIError）"""
        long_name = "A" * 300
        try:
            await _insert_fund(db_manager, fund_code="LEN001", fund_name=long_name)
        except (sa_exc.DataError, sa_exc.DBAPIError):
            pass  # 符合预期


class TestFundNavTable:

    @pytest.mark.asyncio
    async def test_table_exists(self, db_manager):
        assert "fund_nav" in Base.metadata.tables

    @pytest.mark.asyncio
    async def test_columns_exist(self, db_manager):
        table = Base.metadata.tables["fund_nav"]
        cols = {c.name for c in table.columns}
        expected = {
            "id", "created_at", "updated_at",
            "fund_id", "nav_date", "unit_nav", "acc_nav", "adj_nav",
            "daily_return_rate", "nav_status", "data_source",
        }
        assert expected.issubset(cols)

    @pytest.mark.asyncio
    async def test_unique_fund_nav_date(self, db_manager):
        """同一基金+日期不允许重复"""
        table = Base.metadata.tables["fund_nav"]
        assert any("uq_fund_nav_date" == getattr(c, "name", None) for c in table.constraints)

    @pytest.mark.asyncio
    async def test_foreign_key_to_fund(self, db_manager):
        table = Base.metadata.tables["fund_nav"]
        fk_targets = set()
        for fk in table.foreign_key_constraints:
            for elem in fk.elements:
                fk_targets.add(elem.target_fullname)
        assert "fund.id" in fk_targets

    @pytest.mark.asyncio
    async def test_indexes_exist(self, db_manager):
        table = Base.metadata.tables["fund_nav"]
        names = {idx.name for idx in table.indexes}
        assert {"idx_nav_date", "idx_fund_status"}.issubset(names)


class TestFundNavCRUD:

    @staticmethod
    async def _insert_nav(db_manager, **overrides: Any):
        fund = await _insert_fund(db_manager, fund_code="NAV001")
        data: Dict[str, Any] = {
            "fund_id": fund["id"],
            "nav_date": date(2024, 1, 15),
            "unit_nav": 1.2345,
            "acc_nav": 1.5678,
            "adj_nav": 1.8901,
            "daily_return_rate": 0.0123,
            "nav_status": FundNavStatus.Valid,
            "data_source": FundDataSource.Api,
        }
        data.update(overrides)
        table = Base.metadata.tables["fund_nav"]
        await db_manager.execute(insert(table).values(**data))
        row = await db_manager.fetch_one(
            select(table).where(
                (_col(table, "fund_id") == data["fund_id"])
                & (_col(table, "nav_date") == data["nav_date"])
            )
        )
        assert row is not None, "净值记录插入后未能查询到"
        return data, row

    @pytest.mark.asyncio
    async def test_insert_nav(self, db_manager):
        data, row = await self._insert_nav(db_manager)
        assert float(row["unit_nav"]) == pytest.approx(data["unit_nav"])

    @pytest.mark.asyncio
    async def test_duplicate_fund_nav_date_fails(self, db_manager):
        """同一基金同一天不能有两条净值"""
        fund = await _insert_fund(db_manager, fund_code="nav_dup")
        table = Base.metadata.tables["fund_nav"]
        base = {
            "fund_id": fund["id"], "nav_date": date(2024, 2, 1),
            "unit_nav": 1.0, "acc_nav": 1.1,
            "nav_status": FundNavStatus.Valid,
            "data_source": FundDataSource.ManualImport,
        }
        await db_manager.execute(insert(table).values(**base))
        with pytest.raises(sa_exc.IntegrityError):
            await db_manager.execute(insert(table).values(**base))

    @pytest.mark.asyncio
    async def test_nav_must_reference_existing_fund(self, db_manager):
        """外键约束：fund_id 必须存在"""
        table = Base.metadata.tables["fund_nav"]
        with pytest.raises(sa_exc.IntegrityError):
            await db_manager.execute(insert(table).values(
                fund_id=99999, nav_date=date(2024, 1, 1),
                unit_nav=1.0, nav_status=FundNavStatus.Valid,
                data_source=FundDataSource.Api,
            ))

    @pytest.mark.asyncio
    async def test_nullable_nav_fields(self, db_manager):
        """acc_nav / adj_nav / daily_return_rate 可为空"""
        data, row = await self._insert_nav(
            db_manager, acc_nav=None, adj_nav=None, daily_return_rate=None,
        )
        assert row["acc_nav"] is None
        assert row["adj_nav"] is None
        assert row["daily_return_rate"] is None

    @pytest.mark.asyncio
    async def test_nav_query_by_date_range(self, db_manager):
        fund = await _insert_fund(db_manager, fund_code="nav_rng")
        table = Base.metadata.tables["fund_nav"]
        dates = [date(2024, 1, d) for d in (10, 15, 20)]
        for d in dates:
            await db_manager.execute(insert(table).values(
                fund_id=fund["id"], nav_date=d, unit_nav=1.0, acc_nav=1.1,
                nav_status=FundNavStatus.Valid, data_source=FundDataSource.Api,
            ))
        rows = await db_manager.fetch_all(
            select(table)
            .where(_col(table, "fund_id") == fund["id"])
            .where(_col(table, "nav_date") >= date(2024, 1, 12))
            .where(_col(table, "nav_date") <= date(2024, 1, 18))
            .order_by(_col(table, "nav_date"))
        )
        assert len(rows) == 1
        assert rows[0]["nav_date"] == date(2024, 1, 15)

    @pytest.mark.asyncio
    async def test_nav_cascade_configured(self, db_manager):
        """Fund.nav_records 关系配置了 delete 级联（cascade='all,delete'）"""
        from fund_nav_mcp.models.orm.fund import Fund
        nav_rel = Fund.__mapper__.relationships["nav_records"]
        assert "delete" in nav_rel.cascade


class TestFundReturnTable:

    @pytest.mark.asyncio
    async def test_table_exists(self, db_manager):
        assert "fund_returns" in Base.metadata.tables

    @pytest.mark.asyncio
    async def test_columns_exist(self, db_manager):
        table = Base.metadata.tables["fund_returns"]
        cols = {c.name for c in table.columns}
        expected = {
            "id", "created_at", "updated_at",
            "fund_id", "period_type", "return_rate", "rank",
            "total_funds", "calculation_date",
        }
        assert expected.issubset(cols)

    @pytest.mark.asyncio
    async def test_unique_constraint(self, db_manager):
        table = Base.metadata.tables["fund_returns"]
        assert any("uq_fund_return" == getattr(c, "name", None) for c in table.constraints)

    @pytest.mark.asyncio
    async def test_foreign_key_to_fund(self, db_manager):
        table = Base.metadata.tables["fund_returns"]
        fk_targets = set()
        for fk in table.foreign_key_constraints:
            for elem in fk.elements:
                fk_targets.add(elem.target_fullname)
        assert "fund.id" in fk_targets

    @pytest.mark.asyncio
    async def test_indexes_exist(self, db_manager):
        table = Base.metadata.tables["fund_returns"]
        names = {idx.name for idx in table.indexes}
        assert {"idx_return_calc_date", "idx_return_period_calc", "idx_return_rank"}.issubset(names)


class TestFundReturnCRUD:

    @staticmethod
    async def _insert_return(db_manager, **overrides: Any):
        fund = await _insert_fund(db_manager, fund_code="RET001")
        data: Dict[str, Any] = {
            "fund_id": fund["id"],
            "period_type": PeriodType.Monthly,
            "return_rate": 0.0525,
            "rank": 10,
            "total_funds": 100,
            "calculation_date": date(2024, 3, 31),
        }
        data.update(overrides)
        table = Base.metadata.tables["fund_returns"]
        await db_manager.execute(insert(table).values(**data))
        row = await db_manager.fetch_one(
            select(table).where(
                (_col(table, "fund_id") == data["fund_id"])
                & (_col(table, "period_type") == data["period_type"])
                & (_col(table, "calculation_date") == data["calculation_date"])
            )
        )
        assert row is not None, "收益率记录插入后未能查询到"
        return data, row

    @pytest.mark.asyncio
    async def test_insert_return(self, db_manager):
        data, row = await self._insert_return(db_manager)
        assert float(row["return_rate"]) == pytest.approx(data["return_rate"])

    @pytest.mark.asyncio
    async def test_duplicate_return_fails(self, db_manager):
        """同一基金+周期+日期只能有一条收益率"""
        fund = await _insert_fund(db_manager, fund_code="return_dup")
        table = Base.metadata.tables["fund_returns"]
        base = {
            "fund_id": fund["id"], "period_type": PeriodType.Daily,
            "return_rate": 0.01, "rank": 1, "total_funds": 100,
            "calculation_date": date(2024, 6, 15),
        }
        await db_manager.execute(insert(table).values(**base))
        with pytest.raises(sa_exc.IntegrityError):
            await db_manager.execute(insert(table).values(**base))

    @pytest.mark.asyncio
    async def test_return_must_reference_existing_fund(self, db_manager):
        table = Base.metadata.tables["fund_returns"]
        with pytest.raises(sa_exc.IntegrityError):
            await db_manager.execute(insert(table).values(
                fund_id=99999, period_type=PeriodType.Daily,
                return_rate=0.01, rank=1, total_funds=100,
                calculation_date=date(2024, 1, 1),
            ))

    @pytest.mark.asyncio
    async def test_return_query_by_period(self, db_manager):
        fund = await _insert_fund(db_manager, fund_code="return_prd")
        table = Base.metadata.tables["fund_returns"]
        for pt in (PeriodType.Daily, PeriodType.Weekly, PeriodType.Monthly):
            await db_manager.execute(insert(table).values(
                fund_id=fund["id"], period_type=pt, return_rate=0.01,
                rank=1, total_funds=100, calculation_date=date(2024, 1, 1),
            ))
        rows = await db_manager.fetch_all(
            select(table).where(
                (_col(table, "fund_id") == fund["id"])
                & (_col(table, "period_type") == PeriodType.Weekly)
            )
        )
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_return_all_period_types(self, db_manager):
        """验证所有 PeriodType 枚举值均可写入"""
        fund = await _insert_fund(db_manager, fund_code="return_all")
        table = Base.metadata.tables["fund_returns"]
        for pt in PeriodType:
            await db_manager.execute(insert(table).values(
                fund_id=fund["id"], period_type=pt, return_rate=0.01,
                rank=1, total_funds=100, calculation_date=date(2024, 1, 1),
            ))
        assert await _count(db_manager, table) == len(PeriodType)


class TestFundHoldingTable:

    @pytest.mark.asyncio
    async def test_table_exists(self, db_manager):
        assert "fund_holdings" in Base.metadata.tables

    @pytest.mark.asyncio
    async def test_columns_exist(self, db_manager):
        table = Base.metadata.tables["fund_holdings"]
        cols = {c.name for c in table.columns}
        expected = {
            "id", "created_at", "updated_at",
            "fund_id", "report_date", "stock_code", "stock_name",
            "holding_ratio", "market_value", "shares_held",
        }
        assert expected.issubset(cols)

    @pytest.mark.asyncio
    async def test_unique_constraint(self, db_manager):
        table = Base.metadata.tables["fund_holdings"]
        assert any("uq_fund_holding" == getattr(c, "name", None) for c in table.constraints)

    @pytest.mark.asyncio
    async def test_foreign_key_to_fund(self, db_manager):
        table = Base.metadata.tables["fund_holdings"]
        fk_targets = set()
        for fk in table.foreign_key_constraints:
            for elem in fk.elements:
                fk_targets.add(elem.target_fullname)
        assert "fund.id" in fk_targets


class TestFundHoldingCRUD:
    _holding_counter = 0

    @staticmethod
    async def _insert_holding(db_manager, **overrides: Any):
        # fund-specific overrides go to _insert_fund
        fund_overrides: Dict[str, Any] = {}
        holding_overrides: Dict[str, Any] = {}
        for k, v in overrides.items():
            if k in ("fund_code", "fund_name", "fund_regulatory_type", "fund_type",
                     "fund_management_type", "status", "share_class",
                     "establishment_date", "registration_date"):
                fund_overrides[k] = v
            else:
                holding_overrides[k] = v

        TestFundHoldingCRUD._holding_counter += 1
        fund_code = f"HLD{TestFundHoldingCRUD._holding_counter:03d}"
        fund = await _insert_fund(db_manager, fund_code=fund_code, **fund_overrides)
        data: Dict[str, Any] = {
            "fund_id": fund["id"],
            "report_date": date(2024, 6, 30),
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "holding_ratio": 0.0520,
            "market_value": 15000.00,
            "shares_held": 10.00,
        }
        data.update(holding_overrides)
        table = Base.metadata.tables["fund_holdings"]
        await db_manager.execute(insert(table).values(**data))
        row = await db_manager.fetch_one(
            select(table).where(
                (_col(table, "fund_id") == data["fund_id"])
                & (_col(table, "report_date") == data["report_date"])
                & (_col(table, "stock_code") == data["stock_code"])
            )
        )
        assert row is not None, "持仓记录插入后未能查询到"
        return data, row

    @pytest.mark.asyncio
    async def test_insert_holding(self, db_manager):
        data, row = await self._insert_holding(db_manager)
        assert row is not None
        assert float(row["holding_ratio"]) == pytest.approx(data["holding_ratio"])

    @pytest.mark.asyncio
    async def test_duplicate_holding_fails(self, db_manager):
        """同一基金+报告日期+股票代码必须唯一"""
        fund = await _insert_fund(db_manager, fund_code="holding_dup")
        table = Base.metadata.tables["fund_holdings"]
        base = {
            "fund_id": fund["id"], "report_date": date(2024, 3, 31),
            "stock_code": "000858", "stock_name": "五粮液",
            "holding_ratio": 0.03, "market_value": 8000.0, "shares_held": 5.0,
        }
        await db_manager.execute(insert(table).values(**base))
        with pytest.raises(sa_exc.IntegrityError):
            await db_manager.execute(insert(table).values(**base))

    @pytest.mark.asyncio
    async def test_holding_must_reference_existing_fund(self, db_manager):
        table = Base.metadata.tables["fund_holdings"]
        with pytest.raises(sa_exc.IntegrityError):
            await db_manager.execute(insert(table).values(
                fund_id=99999, report_date=date(2024, 1, 1),
                stock_code="600000", stock_name="浦发银行",
                holding_ratio=0.01, market_value=1000.0, shares_held=1.0,
            ))

    @pytest.mark.asyncio
    async def test_holding_boundary_ratio(self, db_manager):
        """持仓比例极端值 (0 和 1)"""
        for i, ratio in enumerate((0.0, 1.0)):
            data, row = await self._insert_holding(
                db_manager,
                holding_ratio=ratio,
                stock_code=f"600{100 + i:03d}",
            )
            assert float(row["holding_ratio"]) == pytest.approx(ratio)

    @pytest.mark.asyncio
    async def test_holding_query_by_fund(self, db_manager):
        """按基金查持仓"""
        fund = await _insert_fund(db_manager, fund_code="holding_qry")
        table = Base.metadata.tables["fund_holdings"]
        stocks = [("600001", "A"), ("600002", "B"), ("600003", "C")]
        for code, name in stocks:
            await db_manager.execute(insert(table).values(
                fund_id=fund["id"], report_date=date(2024, 6, 30),
                stock_code=code, stock_name=name,
                holding_ratio=0.01, market_value=1000.0, shares_held=1.0,
            ))
        rows = await db_manager.fetch_all(
            select(table).where(_col(table, "fund_id") == fund["id"])
        )
        assert len(rows) == 3


class TestShareClassCoverage:

    @pytest.mark.asyncio
    async def test_public_fund_all_share_classes(self, db_manager):
        """公募基金：A/B/C/D/E 全部可写入"""
        table = Base.metadata.tables["fund"]
        for i, sc in enumerate([ShareClass.A, ShareClass.B, ShareClass.C, ShareClass.D, ShareClass.E]):
            code = f"PUBSC{i}"
            await _insert_fund(db_manager, fund_code=code, share_class=sc)
            row = await db_manager.fetch_one(
                select(table).where(_col(table, "fund_code") == code)
            )
            assert row is not None
            assert int(row["share_class"]) == int(sc)

    @pytest.mark.asyncio
    async def test_private_fund_all_share_classes(self, db_manager):
        """私募基金：A/B/C/D/E 全部可写入（结构化层级）"""
        table = Base.metadata.tables["fund"]
        for i, sc in enumerate([ShareClass.A, ShareClass.B, ShareClass.C, ShareClass.D, ShareClass.E]):
            code = f"PVTSC{i}"
            await _insert_fund(
                db_manager,
                fund_code=code,
                share_class=sc,
                fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
            )
            row = await db_manager.fetch_one(
                select(table).where(_col(table, "fund_code") == code)
            )
            assert row is not None
            assert int(row["share_class"]) == int(sc)

    @pytest.mark.asyncio
    async def test_not_applicable_share_class(self, db_manager):
        """NotApplicable 份额类别"""
        await _insert_fund(db_manager, fund_code="NOSC01", share_class=ShareClass.NotApplicable)
        table = Base.metadata.tables["fund"]
        row = await db_manager.fetch_one(
            select(table).where(_col(table, "fund_code") == "NOSC01")
        )
        assert row is not None
        assert int(row["share_class"]) == int(ShareClass.NotApplicable)


class TestRegulatoryTypeCoverage:

    @pytest.mark.asyncio
    async def test_all_public_types(self, db_manager):
        """公募 / 公募REITs"""
        table = Base.metadata.tables["fund"]
        for i, rt in enumerate([FundRegulatoryType.Public, FundRegulatoryType.PublicReit]):
            code = f"PUBRT{i}"
            await _insert_fund(db_manager, fund_code=code, fund_regulatory_type=rt)
            row = await db_manager.fetch_one(
                select(table).where(_col(table, "fund_code") == code)
            )
            assert row is not None
            assert int(row["fund_regulatory_type"]) == int(rt)

    @pytest.mark.asyncio
    async def test_all_private_types(self, db_manager):
        """私募各监管子类型"""
        private_types = [
            FundRegulatoryType.PrivateSecurities,
            FundRegulatoryType.PrivateSecuritiesFof,
            FundRegulatoryType.VentureCapital,
            FundRegulatoryType.VentureCapitalFof,
            FundRegulatoryType.PrivateEquity,
            FundRegulatoryType.PrivateEquityFof,
            FundRegulatoryType.PrivateOther,
            FundRegulatoryType.PrivateOtherFof,
            FundRegulatoryType.PrivateAssetAllocation,
        ]
        table = Base.metadata.tables["fund"]
        for i, rt in enumerate(private_types):
            code = f"PVT{i:03d}"
            await _insert_fund(db_manager, fund_code=code, fund_regulatory_type=rt)
            row = await db_manager.fetch_one(
                select(table).where(_col(table, "fund_code") == code)
            )
            assert row is not None
            assert int(row["fund_regulatory_type"]) == int(rt)


class TestFundStatusCoverage:

    @pytest.mark.asyncio
    async def test_all_statuses(self, db_manager):
        """所有 FundStatus 枚举值均可写入"""
        table = Base.metadata.tables["fund"]
        for i, fs in enumerate(FundStatus):
            code = f"ST{i:03d}"
            await _insert_fund(db_manager, fund_code=code, status=fs)
            row = await db_manager.fetch_one(
                select(table).where(_col(table, "fund_code") == code)
            )
            assert row is not None
            assert int(row["status"]) == int(fs)


class TestNavStatusCoverage:

    @pytest.mark.asyncio
    async def test_all_nav_statuses(self, db_manager):
        """所有 FundNavStatus 枚举值均可写入"""
        fund = await _insert_fund(db_manager, fund_code="NAVST00")
        table = Base.metadata.tables["fund_nav"]
        for i, ns in enumerate(FundNavStatus):
            d = date(2024, 1, 1)
            await db_manager.execute(insert(table).values(
                fund_id=fund["id"],
                nav_date=d.replace(day=i + 1 if i + 1 <= 28 else 1),
                unit_nav=1.0, acc_nav=1.1,
                nav_status=ns,
                data_source=FundDataSource.Api,
            ))
        rows = await db_manager.fetch_all(
            select(table).where(_col(table, "fund_id") == fund["id"])
        )
        assert len(rows) == len(FundNavStatus)


class TestDataSourceCoverage:

    @pytest.mark.asyncio
    async def test_all_data_sources(self, db_manager):
        """所有 FundDataSource 枚举值均可写入"""
        fund = await _insert_fund(db_manager, fund_code="DSRC00")
        table = Base.metadata.tables["fund_nav"]
        for i, ds in enumerate(FundDataSource):
            await db_manager.execute(insert(table).values(
                fund_id=fund["id"],
                nav_date=date(2024, 1, i + 1 if i + 1 <= 28 else 1),
                unit_nav=1.0, acc_nav=1.1,
                nav_status=FundNavStatus.Valid,
                data_source=ds,
            ))
        rows = await db_manager.fetch_all(
            select(table).where(_col(table, "fund_id") == fund["id"])
        )
        assert len(rows) == len(FundDataSource)
