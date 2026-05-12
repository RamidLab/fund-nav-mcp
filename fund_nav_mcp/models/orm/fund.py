__all__ = ['Fund', 'FundNav', 'FundReturn', 'FundHolding']

from typing import List, TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Date, DECIMAL, UniqueConstraint, ForeignKeyConstraint, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from fund_nav_mcp.models.orm.base import Base
from fund_nav_mcp.utils.enums import (
    FundStatus, FundNavStatus, FundType, FundRegulatoryType, FundDataSource,
    PeriodType, FundManagementType, ShareClass
)

if TYPE_CHECKING:
    from fund_nav_mcp.models.orm.category import FundCategory
    from fund_nav_mcp.models.orm.manager import FundManagerPerson, FundManager


class Fund(Base):
    """基金基本信息模型"""
    __tablename__ = 'fund'

    fund_code: Mapped[str] = mapped_column(String(20), unique=True, comment='基金代码')
    fund_name: Mapped[str] = mapped_column(String(200), comment='基金名称')
    fund_short_name: Mapped[Optional[str]] = mapped_column(String(100), comment='基金简称')
    fund_type: Mapped[Optional[FundType]] = mapped_column(Integer, comment='投资标的类型：股票型/混合型/债券型/货币型等')
    fund_regulatory_type: Mapped[FundRegulatoryType] = mapped_column(
        Integer, comment='监管类型，如:public-公募，private-私募，pe-私募股权，vc-创业投资等')
    fund_manager_person_id: Mapped[Optional[int]] = mapped_column(
        Integer, comment='基金管理人（个人）ID，公募专用，私募可选')
    fund_manager_id: Mapped[Optional[int]] = mapped_column(Integer, comment='基金管理人（机构）ID')
    fund_management_type: Mapped[FundManagementType] = mapped_column(Integer, comment='基金管理类型')
    fund_custodian: Mapped[Optional[str]] = mapped_column(String(100), comment='基金托管人')
    fund_registration_address: Mapped[Optional[str]] = mapped_column(String(100), comment='注册地址')
    establishment_date: Mapped[Date] = mapped_column(Date, comment='成立日期')
    registration_date: Mapped[Date] = mapped_column(Date, comment='备案日期')
    status: Mapped[FundStatus] = mapped_column(Integer, comment='基金状态')
    share_class: Mapped[ShareClass] = mapped_column(
        Integer,
        default=ShareClass.NotApplicable,
        comment='份额类别 A/B/C/D/E：公募区分收费模式（前端/后端/服务费），私募区分结构化层级（优先级/劣后级/夹层级）')
    parent_fund_id: Mapped[Optional[int]] = mapped_column(Integer, comment='父基金ID，指向同一基金的主份额（通常为A类）')

    # 关系
    manager: Mapped['FundManager'] = relationship('FundManager', back_populates='funds')
    manager_person: Mapped['FundManagerPerson'] = relationship('FundManagerPerson', back_populates='funds')
    nav_records: Mapped[List['FundNav']] = relationship(
        "FundNav", back_populates="fund", cascade="all, delete")
    returns: Mapped[List['FundReturn']] = relationship(
        "FundReturn", back_populates="fund", cascade="all, delete")
    holdings: Mapped[List['FundHolding']] = relationship(
        "FundHolding", back_populates="fund", cascade="all, delete")
    categories: Mapped[list["FundCategory"]] = relationship(
        "FundCategory", secondary="fund_category_mapping", back_populates="funds")
    parent: Mapped[Optional['Fund']] = relationship(
        "Fund", remote_side='Fund.id', back_populates="children")
    children: Mapped[List['Fund']] = relationship(
        "Fund", back_populates="parent")
    # 列定义
    __table_args__ = (
        ForeignKeyConstraint(['fund_manager_person_id'], ['fund_manager_person.id']),
        ForeignKeyConstraint(['fund_manager_id'], ['fund_manager.id']),
        ForeignKeyConstraint(['parent_fund_id'], ['fund.id']),
        Index('idx_fund_est_date', 'establishment_date'),  # 按成立日期排序/筛选
        Index('idx_fund_name', 'fund_name'),  # 按名称搜索（如 LIKE）
        Index('idx_fund_manager_id', 'fund_manager_id'),  # 按基金经理ID查询
        Index('idx_fund_manager_person_id', 'fund_manager_person_id'),  # 按基金经理个人ID查询
        Index('idx_fund_share_class', 'share_class'),  # 按份额类别筛选
        Index('idx_fund_parent_id', 'parent_fund_id'),  # 查同一基金的所有份额
    )


class FundNav(Base):
    """基金净值模型"""
    __tablename__ = 'fund_nav'

    fund_id: Mapped[int] = mapped_column(Integer, comment='基金产品ID，关联fund表的ID')
    nav_date: Mapped[Date] = mapped_column(Date, comment='净值日期')
    unit_nav: Mapped[float] = mapped_column(DECIMAL(10, 4), comment='单位净值')
    acc_nav: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 4), comment='累计净值')
    adj_nav: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 4), comment='复权净值')
    daily_return_rate: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 4), comment='日增长率')
    nav_status: Mapped[FundNavStatus] = mapped_column(Integer, comment='净值状态')
    data_source: Mapped[FundDataSource] = mapped_column(Integer, comment='数据来源')

    # 关系
    fund: Mapped['Fund'] = relationship("Fund", back_populates="nav_records")

    # 列定义
    __table_args__ = (
        UniqueConstraint('fund_id', 'nav_date', name='uq_fund_nav_date'),
        ForeignKeyConstraint(['fund_id'], ['fund.id']),
        Index('idx_nav_date', 'nav_date'),  # 按净值日期查询
        Index('idx_fund_status', 'fund_id', 'nav_status'),  # 按基金+净值状态查询
    )


class FundReturn(Base):
    """基金收益率模型"""
    __tablename__ = 'fund_returns'

    fund_id: Mapped[int] = mapped_column(Integer, comment='基金产品ID，关联fund表的ID')
    period_type: Mapped[PeriodType] = mapped_column(Integer, comment='周期类型')
    return_rate: Mapped[float] = mapped_column(DECIMAL(10, 4), comment='收益率')
    rank: Mapped[int] = mapped_column(Integer, comment='同类排名')
    total_funds: Mapped[int] = mapped_column(Integer, comment='同类总数')
    calculation_date: Mapped[Date] = mapped_column(Date, nullable=False, comment='计算日期')

    # 关系
    fund: Mapped['Fund'] = relationship("Fund", back_populates="returns")

    # 列定义
    __table_args__ = (
        UniqueConstraint('fund_id', 'period_type', 'calculation_date', name='uq_fund_return'),
        ForeignKeyConstraint(['fund_id'], ['fund.id']),
        Index('idx_return_calc_date', 'calculation_date'),  # 按计算日期查询
        Index('idx_return_period_calc', 'period_type', 'calculation_date'),  # 按周期+日期
        Index('idx_return_rank', 'rank'),  # 按排名排序
    )


class FundHolding(Base):
    """基金持仓信息模型"""
    __tablename__ = 'fund_holdings'

    fund_id: Mapped[int] = mapped_column(Integer, comment='基金产品ID，关联fund表的ID')
    report_date: Mapped[Date] = mapped_column(Date, comment='报告日期')
    stock_code: Mapped[str] = mapped_column(String(20), comment='股票代码')
    stock_name: Mapped[str] = mapped_column(String(100), comment='股票名称')
    holding_ratio: Mapped[float] = mapped_column(DECIMAL(6, 4), comment='持仓比例')
    market_value: Mapped[float] = mapped_column(DECIMAL(15, 2), comment='市值（万元）')
    shares_held: Mapped[float] = mapped_column(DECIMAL(15, 2), comment='持股数量（万股）')

    # 关系
    fund: Mapped['Fund'] = relationship("Fund", back_populates="holdings")

    # 列定义
    __table_args__ = (
        UniqueConstraint('fund_id', 'report_date', 'stock_code', name='uq_fund_holding'),
        ForeignKeyConstraint(['fund_id'], ['fund.id']),
    )
