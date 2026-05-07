import asyncio
import random
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Tuple

from faker import Faker

from fund_nav_mcp.db.core import get_manager, DBManager, InfluxDBManager
from fund_nav_mcp.models.orm import FundManager, FundManagerPerson, FundCategory, Fund, FundNav, FundReturn, \
    FundHolding, FundCategoryMapping
from fund_nav_mcp.utils.enums import FundType, FundRegulatoryType, FundStatus, FundNavStatus, FundDataSource, \
    PeriodType, FundManagementType
from fund_nav_mcp.utils.log import get_logger

logger = get_logger(__name__)

fake = Faker("zh_CN")
fake_en = Faker("en_US")

TABLE_META = {
    "fund_manager": (FundManager, "fund_manager"),
    "fund_manager_person": (FundManagerPerson, "fund_person"),
    "fund_category": (FundCategory, "fund_category"),
    "fund": (Fund, "fund"),
    "fund_nav": (FundNav, "fund_nav"),
    "fund_return": (FundReturn, "fund_return"),
    "fund_holding": (FundHolding, "fund_holding"),
    "fund_category_mapping": (FundCategoryMapping, "fund_category_mapping"),
}


def generate_fund_manager_data() -> List[Dict[str, Any]]:
    """
    生成基金管理人（公司）数据

    Returns:
        基金人（公司）数据列表
    """
    managers = []
    for i in range(1, 6):
        managers.append({
            "id": i,
            "company_name": fake.unique.company(),
            "english_name": fake_en.company_suffix(),
            "short_name": fake.company_suffix(),
            "unified_code": fake.unique.ssn()[:18],
            "amac_registration_number": f"P{random.randint(10000000, 99999999)}",
            "amac_registration_date": fake.date_between(start_date="-5y", end_date="today"),
            "organization_type": random.choice(["私募证券投资基金管理人", "私募股权基金管理人"]),
            "business_type": random.choice(["私募证券投资基金", "私募股权投资基金", "创业投资基金"]),
            "registered_capital": Decimal(random.uniform(100, 5000)).quantize(Decimal("0.01")),
            "paid_up_capital": Decimal(random.uniform(50, 3000)).quantize(Decimal("0.01")),
            "capital_ratio": Decimal(random.uniform(30, 100)).quantize(Decimal("0.01")),
            "registered_address": fake.address(),
            "office_address": fake.address(),
            "employee_count": random.choice([5, 10, 20, 50, 100]),
            "fund_industry_count": random.randint(5, 50),
            "management_scale_range": random.choice(["0-1亿", "1-10亿", "10-50亿", "50-100亿", "100亿以上"]),
            "actual_controller": fake.name(),
            "is_member": random.choice([True, False]),
            "legal_representative": fake.name(),
        })
    return managers


async def generate_fund_manager_person_data(manager_ids: List[int]) -> List[Dict[str, Any]]:
    """
    生成基金经理个人数据

    Args:
        manager_ids: 基金人 ID 列表

    Returns:
        基金经理个人数据列表
    """
    persons = []
    pid = 1
    for mgr_id in manager_ids:
        for _ in range(random.randint(1, 3)):
            persons.append({
                "id": pid,
                "name": fake.name(),
                "gender": random.choice(["男", "女"]),
                "birth_date": fake.date_of_birth(minimum_age=30, maximum_age=60),
                "education": random.choice(["本科", "硕士", "博士"]),
                "qualification_number": f"AMAC{random.randint(100000, 999999)}",
                "is_qualified": True,
                "resume": fake.text(max_nb_chars=200),
                "current_company_id": mgr_id,
            })
            pid += 1
    return persons


async def generate_category_data() -> List[Dict[str, Any]]:
    """
    生成基金分类数据（自引用树形结构）

    Returns:
        基金分类数据列表
    """
    categories = [
        {"id": 1, "category_code": "EQUITY", "category_name": "股票型", "parent_id": None, "level": 1,
         "description": "主要投资于股票市场"},
        {"id": 2, "category_code": "MIXED", "category_name": "混合型", "parent_id": None, "level": 1,
         "description": "股票和债券混合投资"},
        {"id": 3, "category_code": "BOND", "category_name": "债券型", "parent_id": None, "level": 1,
         "description": "主要投资于债券"},
        {"id": 4, "category_code": "MONETARY", "category_name": "货币型", "parent_id": None, "level": 1,
         "description": "货币市场工具"},
        {"id": 5, "category_code": "EQUITY_LARGE", "category_name": "大盘股基金", "parent_id": 1, "level": 2,
         "description": "投资于大盘股"},
        {"id": 6, "category_code": "EQUITY_SMALL", "category_name": "小盘股基金", "parent_id": 1, "level": 2,
         "description": "投资于小盘股"},
        {"id": 7, "category_code": "BOND_GOV", "category_name": "国债基金", "parent_id": 3, "level": 2,
         "description": "主要投资国债"},
    ]
    return categories


async def generate_fund_data(manager_ids: List[int], person_ids: List[int]) -> List[Dict[str, Any]]:
    """
    生成基金数据

    Args:
        manager_ids: 基金人 ID 列表
        person_ids: 基金经理人 ID 列表

    Returns:
        基金数据列表
    """
    funds = []
    for i in range(1, 11):  # 生成10只基金
        start_date = fake.date_between(start_date="-10y", end_date="-1y")
        funds.append({
            "id": i,
            "fund_code": f"{random.choice(['00', '11', '22'])}{random.randint(10000, 99999)}",
            "fund_name": f"基金{fake.word()}",
            "fund_short_name": fake.word(),
            "fund_type": random.choice(list(FundType.__members__.values())),
            "fund_regulatory_type": random.choice(list(FundRegulatoryType.__members__.values())),
            "fund_manager_person_id": random.choice(person_ids) if person_ids else None,
            "fund_manager_id": random.choice(manager_ids),
            "fund_management_type": random.choice(list(FundManagementType.__members__.values())),
            "fund_custodian": fake.company(),
            "fund_registration_address": fake.address(),
            "establishment_date": start_date,
            "registration_date": start_date,
            "status": random.choice(list(FundStatus.__members__.values())),
        })
    return funds


async def generate_fund_nav_data(fund_ids: List[int]) -> List[Dict[str, Any]]:
    """
    生成基金净值数据

    Args:
        fund_ids: 基金 ID 列表

    Returns:
        基金净值数据列表
    """
    navs = []
    nav_id = 1
    end_date = date.today()
    start_date = end_date - timedelta(days=365)  # 最近一年
    for fund_id in fund_ids:
        # 为每只基金生成最近100个交易日的净值数据
        current_date = start_date
        while current_date <= end_date:
            # 跳过周末，简单模拟只取工作日
            if current_date.weekday() < 5:
                unit_nav = Decimal(random.uniform(0.8, 2.5)).quantize(Decimal("0.0001"))
                acc_nav = unit_nav + Decimal(random.uniform(0, 0.5)).quantize(Decimal("0.0001"))
                adj_nav = unit_nav
                daily_return = Decimal(random.uniform(-0.05, 0.05)).quantize(Decimal("0.0001"))
                navs.append({
                    "id": nav_id,
                    "fund_id": fund_id,
                    "nav_date": current_date,
                    "unit_nav": unit_nav,
                    "acc_nav": acc_nav,
                    "adj_nav": adj_nav,
                    "daily_return_rate": daily_return,
                    "nav_status": random.choice(list(FundNavStatus.__members__.values())),
                    "data_source": random.choice(list(FundDataSource.__members__.values())),
                })
                nav_id += 1
            current_date += timedelta(days=1)
            if len(navs) > 500:  # 限制数据量
                break
    return navs


async def generate_fund_return_data(fund_ids: List[int]) -> List[Dict[str, Any]]:
    """
    生成基金收益率排名数据

    Args:
        fund_ids: 基金 ID 列表

    Returns:
        基金收益率排名数据列表
    """
    returns = []
    ret_id = 1
    calc_date = date.today()
    for fund_id in fund_ids:
        for period in list(PeriodType.__members__.values()):
            rank = random.randint(1, 100)
            total = random.randint(50, 200)
            returns.append({
                "id": ret_id,
                "fund_id": fund_id,
                "period_type": period,
                "return_rate": Decimal(random.uniform(-0.2, 0.5)).quantize(Decimal("0.0001")),
                "rank": rank,
                "total_funds": total,
                "calculation_date": calc_date,
            })
            ret_id += 1
    return returns


async def generate_fund_holding_data(fund_ids: List[int]) -> List[Dict[str, Any]]:
    """
    生成基金持仓数据

    Args:
        fund_ids: 基金 ID 列表

    Returns:
        基金持仓数据列表
    """
    holdings = []
    hold_id = 1
    report_date = date(date.today().year - 1, 12, 31)  # 上一年年报
    stocks = [
        ("000001", "平安银行"), ("000002", "万科A"), ("600036", "招商银行"),
        ("600519", "贵州茅台"), ("000858", "五粮液"), ("300750", "宁德时代"),
        ("002415", "海康威视"), ("601318", "中国平安"), ("000333", "美的集团"),
    ]
    for fund_id in fund_ids:
        # 每只基金随机持仓 5-10 只股票
        for stock_code, stock_name in random.sample(stocks, k=random.randint(5, len(stocks))):
            holding_ratio = Decimal(random.uniform(0.5, 10)).quantize(Decimal("0.0001"))
            market_value = Decimal(random.uniform(100, 50000)).quantize(Decimal("0.01"))
            shares_held = Decimal(random.uniform(10, 5000)).quantize(Decimal("0.01"))
            holdings.append({
                "id": hold_id,
                "fund_id": fund_id,
                "report_date": report_date,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "holding_ratio": holding_ratio,
                "market_value": market_value,
                "shares_held": shares_held,
            })
            hold_id += 1
    return holdings


async def generate_fund_category_mapping_data(fund_ids: List[int], category_ids: List[int]) -> List[Dict[str, Any]]:
    """
    生成基金-分类映射数据

    Args:
        fund_ids: 基金 ID 列表
        category_ids: 分类 ID 列表

    Returns:
        基金-分类映射数据列表
    """
    mapping = []
    map_id = 1
    for fund_id in fund_ids:
        # 每只基金随机关联 1-3 个分类
        for cat_id in random.sample(category_ids, k=random.randint(1, 3)):
            mapping.append({
                "id": map_id,
                "fund_id": fund_id,
                "category_id": cat_id,
            })
            map_id += 1
    return mapping


def _build_tags_fields(table_name: str, row: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    根据表名和数据行，返回 InfluxDB 的 tags 和 fields 字典。

    Args:
        table_name: 表名（对应 ORM 的 __tablename__）
        row: 待转换的数据行字典

    Returns:
        (tags: dict, fields: dict)
    """
    if table_name == "fund_manager":
        tags = {
            "unified_code": row.get("unified_code", ""),
            "amac_registration_number": row.get("amac_registration_number", ""),
            "organization_type": row.get("organization_type", ""),
        }
        fields = {
            "company_name": row.get("company_name", ""),
            "english_name": row.get("english_name", ""),
            "short_name": row.get("short_name", ""),
            "registered_capital": float(row["registered_capital"]) if row.get("registered_capital") else 0.0,
            "paid_up_capital": float(row["paid_up_capital"]) if row.get("paid_up_capital") else 0.0,
            "capital_ratio": float(row["capital_ratio"]) if row.get("capital_ratio") else 0.0,
            "employee_count": int(row["employee_count"]) if row.get("employee_count") else 0,
            "fund_industry_count": int(row["fund_industry_count"]) if row.get("fund_industry_count") else 0,
            "is_member": bool(row.get("is_member", False)),
            "registered_address": row.get("registered_address", ""),
            "office_address": row.get("office_address", ""),
            "actual_controller": row.get("actual_controller", ""),
            "legal_representative": row.get("legal_representative", ""),
            "business_type": row.get("business_type", ""),
            "management_scale_range": row.get("management_scale_range", ""),
        }

    elif table_name == "fund_manager_person":
        tags = {
            "qualification_number": row.get("qualification_number", ""),
            "education": row.get("education", ""),
            "current_company_id": str(row["current_company_id"]) if row.get("current_company_id") else "",
        }
        fields = {
            "name": row.get("name", ""),
            "gender": row.get("gender", ""),
            "is_qualified": bool(row.get("is_qualified", True)),
            "resume": row.get("resume", ""),
        }

    elif table_name == "fund_category":
        tags = {
            "category_code": row.get("category_code", ""),
            "level": str(row["level"]) if row.get("level") else "1",
        }
        fields = {
            "category_name": row.get("category_name", ""),
            "description": row.get("description", ""),
            "parent_id": str(row["parent_id"]) if row.get("parent_id") else "",
        }

    elif table_name == "fund":
        tags = {
            "fund_code": row.get("fund_code", ""),
            "fund_type": str(row["fund_type"].value) if hasattr(row.get("fund_type"), "value") else str(
                row.get("fund_type", "")),
            "fund_regulatory_type": str(row["fund_regulatory_type"].value) if hasattr(row.get("fund_regulatory_type"),
                                                                                      "value") else str(
                row.get("fund_regulatory_type", "")),
            "fund_manager_id": str(row["fund_manager_id"]) if row.get("fund_manager_id") else "",
            "status": str(row["status"].value) if hasattr(row.get("status"), "value") else str(row.get("status", "")),
        }
        fields = {
            "fund_name": row.get("fund_name", ""),
            "fund_short_name": row.get("fund_short_name", ""),
            "fund_custodian": row.get("fund_custodian", ""),
            "fund_scale": float(row["fund_scale"]) if row.get("fund_scale") else 0.0,
            "fund_manager_person_id": str(row["fund_manager_person_id"]) if row.get("fund_manager_person_id") else "",
            "establishment_date": row["establishment_date"].isoformat() if isinstance(row.get("establishment_date"),
                                                                                      date) else str(
                row.get("establishment_date", "")),
        }

    elif table_name == "fund_nav":
        tags = {
            "fund_id": str(row["fund_id"]) if row.get("fund_id") else "",
            "nav_status": str(row["nav_status"].value) if hasattr(row.get("nav_status"), "value") else str(
                row.get("nav_status", "")),
            "data_source": str(row["data_source"].value) if hasattr(row.get("data_source"), "value") else str(
                row.get("data_source", "")),
        }
        fields = {
            "unit_nav": float(row["unit_nav"]) if row.get("unit_nav") else 0.0,
            "acc_nav": float(row["acc_nav"]) if row.get("acc_nav") else 0.0,
            "adj_nav": float(row["adj_nav"]) if row.get("adj_nav") else 0.0,
            "daily_return_rate": float(row["daily_return_rate"]) if row.get("daily_return_rate") else 0.0,
        }

    elif table_name == "fund_return":
        tags = {
            "fund_id": str(row["fund_id"]) if row.get("fund_id") else "",
            "period_type": str(row["period_type"].value) if hasattr(row.get("period_type"), "value") else str(
                row.get("period_type", "")),
        }
        fields = {
            "return_rate": float(row["return_rate"]) if row.get("return_rate") else 0.0,
            "rank": int(row["rank"]) if row.get("rank") else 0,
            "total_funds": int(row["total_funds"]) if row.get("total_funds") else 0,
            "calculation_date": row["calculation_date"].isoformat() if isinstance(row.get("calculation_date"),
                                                                                  date) else str(
                row.get("calculation_date", "")),
        }

    elif table_name == "fund_holding":
        tags = {
            "fund_id": str(row["fund_id"]) if row.get("fund_id") else "",
            "stock_code": row.get("stock_code", ""),
            "report_date": row["report_date"].isoformat() if isinstance(row.get("report_date"), date) else str(
                row.get("report_date", "")),
        }
        fields = {
            "stock_name": row.get("stock_name", ""),
            "holding_ratio": float(row["holding_ratio"]) if row.get("holding_ratio") else 0.0,
            "market_value": float(row["market_value"]) if row.get("market_value") else 0.0,
            "shares_held": float(row["shares_held"]) if row.get("shares_held") else 0.0,
        }

    elif table_name == "fund_category_mapping":
        tags = {
            "fund_id": str(row["fund_id"]) if row.get("fund_id") else "",
            "category_id": str(row["category_id"]) if row.get("category_id") else "",
        }
        fields = {}  # 映射表无额外数值字段，时间戳由框架处理

    else:
        logger.warning(f"未定义 InfluxDB tags/fields 映射: {table_name}")
        tags, fields = {}, {}

    return tags, fields


async def insert_data(mgr: DBManager | InfluxDBManager, table_name: str, data: List[Dict[str, Any]]) -> None:
    """
    通用数据插入，根据表名选择 ORM 类或 InfluxDB 写入

    Args:
        mgr: 数据库管理器实例
        table_name: 表名
        data: 要插入的记录数据列表，每个记录是一个字典，键为字段名，值为字段值
    """
    orm_class, measurement = TABLE_META.get(table_name, (None, None))
    if orm_class is None:
        raise ValueError(f"不支持的表: {table_name}")

    if isinstance(mgr, InfluxDBManager):
        points = []
        for row in data:
            tags, fields = _build_tags_fields(table_name, row)

            # 确定时间戳
            for ts_field in ["nav_date", "report_date", "amac_registration_date", "calculation_date",
                             "establishment_date"]:
                ts = row.get(ts_field)
                if ts:
                    break
            if ts is None:
                ts = datetime.now(timezone.utc)
            elif isinstance(ts, date) and not isinstance(ts, datetime):
                ts = datetime.combine(ts, datetime.min.time(), tzinfo=timezone.utc)

            points.append({
                "measurement": measurement,
                "tags": tags,
                "fields": fields,
                "time": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            })
        await mgr.write(points)
        logger.info(f"已向 InfluxDB 写入 {len(data)} 条记录 ({table_name})")

    elif isinstance(mgr, DBManager):
        async with mgr.get_session() as session:
            orm_objects = [orm_class(**row) for row in data]
            session.add_all(orm_objects)
            await session.commit()
        logger.info(f"已向 RDBMS 写入 {len(data)} 条记录 ({table_name})")


async def main():
    """主函数，负责生成并插入基金数据到数据库"""
    for item in ["default", "pg-default", "mysql-default", "influxdb-default"]:
        # 获取数据库管理器（异步）
        manager_info = await get_manager("db", item)
        mgr = manager_info["mgr"]
        db_type = manager_info["db_type"]

        logger.info(f"开始处理数据库 {item}, 类型: {db_type}")

        try:
            if db_type != "influxdb":
                await mgr.drop_all()
                await mgr.create_all()
                logger.info("ORM 表已就绪")

            # 生成管理人数据
            manager_data = generate_fund_manager_data()
            manager_ids = [d["id"] for d in manager_data]
            await insert_data(mgr, "fund_manager", manager_data)

            # 生成基金经理人员数据（依赖管理人 ID）
            person_data = await generate_fund_manager_person_data(manager_ids)
            person_ids = [d["id"] for d in person_data]
            await insert_data(mgr, "fund_manager_person", person_data)

            # 生成分类数据（无外键依赖）
            category_data = await generate_category_data()
            category_ids = [d["id"] for d in category_data]
            await insert_data(mgr, "fund_category", category_data)

            # 生成基金数据（依赖管理人 ID + 经理 ID）
            fund_data = await generate_fund_data(manager_ids, person_ids)
            fund_ids = [d["id"] for d in fund_data]
            await insert_data(mgr, "fund", fund_data)

            # 生成净值数据（依赖基金 ID）
            nav_data = await generate_fund_nav_data(fund_ids)
            await insert_data(mgr, "fund_nav", nav_data)

            # 生成收益率排名（依赖基金 ID）
            return_data = await generate_fund_return_data(fund_ids)
            await insert_data(mgr, "fund_return", return_data)

            # 生成持仓数据（依赖基金 ID）
            holding_data = await generate_fund_holding_data(fund_ids)
            await insert_data(mgr, "fund_holding", holding_data)

            # 生成基金-分类映射（依赖基金 ID + 分类 ID）
            mapping_data = await generate_fund_category_mapping_data(fund_ids, category_ids)
            await insert_data(mgr, "fund_category_mapping", mapping_data)

            logger.info(f"所有 mock 数据已成功生成并插入 {item} 数据库")

            # 健康检查
            healthy = await mgr.health_check()
            logger.info(f"数据库 {item} 健康状态: {'正常' if healthy else '异常'}")

        except Exception as e:
            logger.exception(f"处理数据库 {item} 时发生错误: {e}")

        finally:
            # 关闭连接
            await mgr.disconnect()
            logger.info(f"数据库 {item} 连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
