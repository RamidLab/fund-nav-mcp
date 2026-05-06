__all__ = ['FundManager', 'FundManagerPerson']

from datetime import date
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, DECIMAL, Integer, Text, Index, ForeignKeyConstraint, UniqueConstraint, \
    text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from fund_nav_mcp.models.orm.base import Base

if TYPE_CHECKING:
    from fund_nav_mcp.models.orm.fund import Fund


class FundManager(Base):
    """基金管理人/公司信息表（基于 amac 公示数据）"""
    __tablename__ = 'fund_manager'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 基础信息
    company_name: Mapped[str] = mapped_column(String(100), unique=True, comment='公司全称')
    english_name: Mapped[Optional[str]] = mapped_column(String(200), comment='英文名称')
    short_name: Mapped[Optional[str]] = mapped_column(String(50), comment='公司简称')
    unified_code: Mapped[Optional[str]] = mapped_column(String(18), unique=True, comment='统一社会信用代码')
    # 登记信息
    amac_registration_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True, comment='中基协登记编号')
    amac_registration_date: Mapped[Optional[date]] = mapped_column(Date, comment='登记时间')
    organization_type: Mapped[Optional[str]] = mapped_column(String(50), comment='机构类型（如：私募证券投资基金管理人）')
    business_type: Mapped[Optional[str]] = mapped_column(String(200), comment='业务类型')
    # 资本与地址
    registered_capital: Mapped[Optional[float]] = mapped_column(DECIMAL(15, 2), comment='注册资本（万元）')
    paid_up_capital: Mapped[Optional[float]] = mapped_column(DECIMAL(15, 2), comment='实缴资本（万元）')
    capital_ratio: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2), comment='实缴比例（%）')
    registered_address: Mapped[Optional[str]] = mapped_column(String(200), comment='注册地址')
    office_address: Mapped[Optional[str]] = mapped_column(String(200), comment='办公地址')
    # 人员与规模
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, comment='全职员工人数')
    fund_industry_count: Mapped[Optional[int]] = mapped_column(Integer, comment='取得基金从业人数')
    management_scale_range: Mapped[Optional[str]] = mapped_column(String(50), comment='管理规模区间')
    # 实际控制人（可单独建表，简单起见存文本）
    actual_controller: Mapped[Optional[str]] = mapped_column(String(100), comment='实际控制人')
    # 状态
    is_member: Mapped[bool] = mapped_column(default=False, comment='是否为会员')
    legal_representative: Mapped[Optional[str]] = mapped_column(String(50), comment='法定代表人')
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # 关系
    funds: Mapped[List['Fund']] = relationship('Fund', back_populates='manager')
    manager_person: Mapped[List['FundManagerPerson']] = relationship('FundManagerPerson',
                                                                     back_populates='current_company')

    __table_args__ = (
        Index('idx_company_name', 'company_name'),  # 查找公司
        Index('idx_amac_number', 'amac_registration_number'),  # 查找中基协登记编号
    )


class FundManagerPerson(Base):
    """基金经理个人（公募）或投资经理（私募）信息表"""
    __tablename__ = 'fund_manager_person'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), comment='姓名')
    gender: Mapped[Optional[str]] = mapped_column(String(10), comment='性别')
    birth_date: Mapped[Optional[Date]] = mapped_column(Date, comment='出生日期')
    education: Mapped[Optional[str]] = mapped_column(String(50), comment='学历')
    qualification_number: Mapped[Optional[str]] = mapped_column(String(50), comment='基金从业资格证号')
    is_qualified: Mapped[bool] = mapped_column(default=True, comment='是否有基金从业资格')
    resume: Mapped[Optional[str]] = mapped_column(Text, comment='工作履历')
    current_company_id: Mapped[Optional[int]] = mapped_column(Integer, comment='当前任职公司ID')
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    current_company: Mapped['FundManager'] = relationship('FundManager', back_populates='manager_person')
    funds: Mapped[List['Fund']] = relationship('Fund', back_populates='manager_person')

    __table_args__ = (
        UniqueConstraint('name', 'current_company_id'),
        ForeignKeyConstraint(['current_company_id'], ['fund_manager.id']),
        Index('idx_person_name', 'name'),
    )
