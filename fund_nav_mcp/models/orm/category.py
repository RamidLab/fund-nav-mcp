__all__ = ['FundCategory', 'FundCategoryMapping']

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Integer, String, DateTime,
    Text, UniqueConstraint,
    ForeignKeyConstraint, Index, text
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from fund_nav_mcp.models.orm.base import Base

if TYPE_CHECKING:
    from fund_nav_mcp.models.orm.fund import Fund


class FundCategory(Base):
    """基金分类模型"""
    __tablename__ = 'fund_category'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_code: Mapped[str] = mapped_column(String(20), unique=True, comment='分类代码')
    category_name: Mapped[str] = mapped_column(String(100), comment='分类名称')
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, comment='父级分类ID')
    level: Mapped[int] = mapped_column(Integer, default=1, comment='分类层级')
    description: Mapped[Optional[str]] = mapped_column(Text, comment='分类描述')
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # 自引用关系
    parent: Mapped[Optional["FundCategory"]] = relationship("FundCategory", remote_side='FundCategory.id',
                                                            back_populates="children")
    children: Mapped[list["FundCategory"]] = relationship("FundCategory", back_populates="parent")
    # 关系
    funds: Mapped[list["Fund"]] = relationship("Fund", secondary="fund_category_mapping", back_populates="categories")

    # 列定义
    __table_args__ = (
        ForeignKeyConstraint(['parent_id'], ['fund_category.id']),
        Index('idx_category_parent', 'parent_id'),  # 查找子分类
        Index('idx_category_level', 'level'),  # 按层级筛选
    )


class FundCategoryMapping(Base):
    """基金分类关联模型"""
    __tablename__ = 'fund_category_mapping'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column(Integer, comment='基金ID')
    category_id: Mapped[int] = mapped_column(Integer, comment='分类ID')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('fund_id', 'category_id', name='uq_fund_category'),
        ForeignKeyConstraint(['fund_id'], ['fund.id']),
        ForeignKeyConstraint(['category_id'], ['fund_category.id']),
        Index('idx_mapping_category_id', 'category_id'),  # 查某分类下的基金
    )
