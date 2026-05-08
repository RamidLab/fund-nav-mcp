from __future__ import annotations

__all__ = [
    "FundBase", "FundCreate", "FundUpdate", "FundResponse",
    "FundNavBase", "FundNavCreate", "FundNavUpdate", "FundNavResponse",
    "FundReturnBase", "FundReturnCreate", "FundReturnUpdate", "FundReturnResponse",
    "FundHoldingBase", "FundHoldingCreate", "FundHoldingUpdate", "FundHoldingResponse",
    "FundCategoryBase", "FundCategoryCreate", "FundCategoryUpdate", "FundCategoryResponse",
    "FundCategoryMappingBase", "FundCategoryMappingCreate", "FundCategoryMappingResponse",
    "FundManagerBase", "FundManagerCreate", "FundManagerUpdate", "FundManagerResponse",
    "FundManagerPersonBase", "FundManagerPersonCreate", "FundManagerPersonUpdate", "FundManagerPersonResponse",
]

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from fund_nav_mcp.utils.enums import FundNavStatus, FundStatus, FundType, FundRegulatoryType, PeriodType, \
    FundDataSource, FundManagementType, ManagementScaleRange


class FundBase(BaseModel):
    fund_code: str = Field(..., title="基金代码", max_length=20)
    fund_name: str = Field(..., title="基金名称", max_length=200)
    fund_short_name: Optional[str] = Field(default=None, title="基金简称", max_length=100)
    fund_type: Optional[FundType] = Field(default=None, title="投资标的类型")
    fund_regulatory_type: FundRegulatoryType = Field(..., title="监管类型")
    fund_manager_person_id: Optional[int] = Field(default=None, title="基金管理人（个人）ID")
    fund_manager_id: Optional[int] = Field(default=None, title="基金管理人（机构）ID")
    fund_management_type: FundManagementType = Field(..., title="基金管理类型")
    fund_custodian: Optional[str] = Field(default=None, title="基金托管人", max_length=100)
    fund_registration_address: Optional[str] = Field(default=None, title="注册地址", max_length=100)
    establishment_date: date = Field(..., title="成立日期")
    registration_date: date = Field(..., title="备案日期")
    status: FundStatus = Field(..., title="基金状态")


class FundCreate(FundBase):
    pass


class FundUpdate(BaseModel):
    fund_code: Optional[str] = Field(default=None, max_length=20, description='基金代码')
    fund_name: Optional[str] = Field(default=None, max_length=200, description='基金名称')
    fund_short_name: Optional[str] = Field(default=None, max_length=100, description='基金简称')
    fund_type: Optional[FundType] = Field(default=None, description='投资标的类型')
    fund_regulatory_type: Optional[FundRegulatoryType] = Field(default=None, description='监管类型')
    fund_manager_person_id: Optional[int] = Field(default=None, description='基金管理人（个人）ID')
    fund_manager_id: Optional[int] = Field(default=None, description='基金管理人（机构）ID')
    fund_management_type: Optional[FundManagementType] = Field(default=None, description='基金管理类型')
    fund_custodian: Optional[str] = Field(default=None, max_length=100, description='基金托管人')
    fund_registration_address: Optional[str] = Field(default=None, max_length=100, description='注册地址')
    establishment_date: Optional[date] = Field(default=None, description='成立日期')
    registration_date: Optional[date] = Field(default=None, description='备案日期')
    status: Optional[FundStatus] = Field(default=None, description='基金状态')


class FundResponse(FundBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # 关系字段
    manager: Optional[FundManagerResponse] = None
    manager_person: Optional[FundManagerPersonResponse] = None
    nav_records: List[FundNavResponse] = []
    returns: List[FundReturnResponse] = []
    holdings: List[FundHoldingResponse] = []
    categories: List[FundCategoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FundNavBase(BaseModel):
    fund_id: int = Field(..., description='基金ID')
    nav_date: date = Field(..., description='净值日期')
    unit_nav: Decimal = Field(..., max_digits=10, decimal_places=4, description='单位净值')
    acc_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='累计净值')
    adj_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='复权净值')
    daily_return_rate: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='日增长率')
    nav_status: FundNavStatus = Field(..., description='净值状态')
    data_source: FundDataSource = Field(..., max_length=50, description='数据来源')


class FundNavCreate(FundNavBase):
    pass


class FundNavUpdate(BaseModel):
    fund_id: Optional[int] = Field(None, description='基金ID')
    nav_date: Optional[date] = Field(None, description='净值日期')
    unit_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='单位净值')
    acc_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='累计净值')
    adj_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='复权净值')
    daily_return_rate: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='日增长率')
    nav_status: Optional[FundNavStatus] = Field(None, description='净值状态')
    data_source: Optional[FundDataSource] = Field(None, max_length=50, description='数据来源')


class FundNavResponse(FundNavBase):
    id: int
    created_at: datetime
    # 关系
    fund: Optional[FundResponse] = None

    model_config = ConfigDict(from_attributes=True)


class FundReturnBase(BaseModel):
    fund_id: int = Field(..., description='基金ID')
    period_type: PeriodType = Field(..., description='周期类型')
    return_rate: Decimal = Field(..., max_digits=10, decimal_places=4, description='收益率')
    rank: int = Field(..., description='同类排名')
    total_funds: int = Field(..., description='同类总数')
    calculation_date: date = Field(..., description='计算日期')


class FundReturnCreate(FundReturnBase):
    pass


class FundReturnUpdate(BaseModel):
    fund_id: Optional[int] = Field(None, description='基金ID')
    period_type: Optional[PeriodType] = Field(None, description='周期类型')
    return_rate: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='收益率')
    rank: Optional[int] = Field(None, description='同类排名')
    total_funds: Optional[int] = Field(None, description='同类总数')
    calculation_date: Optional[date] = Field(None, description='计算日期')


class FundReturnResponse(FundReturnBase):
    id: int
    created_at: datetime
    # 关系
    fund: Optional[FundResponse] = None

    model_config = ConfigDict(from_attributes=True)


class FundHoldingBase(BaseModel):
    fund_id: int = Field(..., description='基金ID')
    report_date: date = Field(..., description='报告日期')
    stock_code: str = Field(..., max_length=20, description='股票代码')
    stock_name: str = Field(..., max_length=100, description='股票名称')
    holding_ratio: Decimal = Field(..., max_digits=6, decimal_places=4, description='持仓比例')
    market_value: Decimal = Field(..., max_digits=15, decimal_places=2, description='市值（万元）')
    shares_held: Decimal = Field(..., max_digits=15, decimal_places=2, description='持股数量（万股）')


class FundHoldingCreate(FundHoldingBase):
    pass


class FundHoldingUpdate(BaseModel):
    fund_id: Optional[int] = Field(None, description='基金ID')
    report_date: Optional[date] = Field(None, description='报告日期')
    stock_code: Optional[str] = Field(None, max_length=20, description='股票代码')
    stock_name: Optional[str] = Field(None, max_length=100, description='股票名称')
    holding_ratio: Optional[Decimal] = Field(None, max_digits=6, decimal_places=4, description='持仓比例')
    market_value: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='市值（万元）')
    shares_held: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='持股数量（万股）')


class FundHoldingResponse(FundHoldingBase):
    id: int
    created_at: datetime
    # 关系
    fund: Optional[FundResponse] = None

    model_config = ConfigDict(from_attributes=True)


class FundManagerBase(BaseModel):
    company_name: str = Field(..., max_length=100, description='公司全称')
    english_name: Optional[str] = Field(None, max_length=200, description='英文名称')
    short_name: Optional[str] = Field(None, max_length=50, description='公司简称')
    unified_code: Optional[str] = Field(None, max_length=18, description='统一社会信用代码')
    amac_registration_number: Optional[str] = Field(None, max_length=20, description='中基协登记编号')
    amac_registration_date: Optional[date] = Field(None, description='登记时间')
    organization_type: Optional[str] = Field(None, max_length=50, description='机构类型')
    business_type: Optional[str] = Field(None, max_length=200, description='业务类型')
    registered_capital: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='注册资本（万元）')
    paid_up_capital: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='实缴资本（万元）')
    capital_ratio: Optional[Decimal] = Field(None, max_digits=5, decimal_places=2, description='实缴比例（%）')
    registered_address: Optional[str] = Field(None, max_length=200, description='注册地址')
    office_address: Optional[str] = Field(None, max_length=200, description='办公地址')
    employee_count: Optional[int] = Field(None, description='全职员工人数')
    fund_industry_count: Optional[int] = Field(None, description='取得基金从业人数')
    management_scale_range: Optional[ManagementScaleRange] = Field(None, description='管理规模区间')
    actual_controller: Optional[str] = Field(None, max_length=100, description='实际控制人')
    is_member: bool = Field(False, description='是否为会员')
    legal_representative: Optional[str] = Field(None, max_length=50, description='法定代表人')


class FundManagerCreate(FundManagerBase):
    pass


class FundManagerUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=100, description='公司全称')
    english_name: Optional[str] = Field(None, max_length=200, description='英文名称')
    short_name: Optional[str] = Field(None, max_length=50, description='公司简称')
    unified_code: Optional[str] = Field(None, max_length=18, description='统一社会信用代码')
    amac_registration_number: Optional[str] = Field(None, max_length=20, description='中基协登记编号')
    amac_registration_date: Optional[date] = Field(None, description='登记时间')
    organization_type: Optional[str] = Field(None, max_length=50, description='机构类型')
    business_type: Optional[str] = Field(None, max_length=200, description='业务类型')
    registered_capital: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='注册资本（万元）')
    paid_up_capital: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='实缴资本（万元）')
    capital_ratio: Optional[Decimal] = Field(None, max_digits=5, decimal_places=2, description='实缴比例（%）')
    registered_address: Optional[str] = Field(None, max_length=200, description='注册地址')
    office_address: Optional[str] = Field(None, max_length=200, description='办公地址')
    employee_count: Optional[int] = Field(None, description='全职员工人数')
    fund_industry_count: Optional[int] = Field(None, description='取得基金从业人数')
    management_scale_range: Optional[ManagementScaleRange] = Field(None, description='管理规模区间')
    actual_controller: Optional[str] = Field(None, max_length=100, description='实际控制人')
    is_member: Optional[bool] = Field(None, description='是否为会员')
    legal_representative: Optional[str] = Field(None, max_length=50, description='法定代表人')


class FundManagerResponse(FundManagerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # 关系
    funds: List[FundResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FundManagerPersonBase(BaseModel):
    name: str = Field(..., max_length=50, description='姓名')
    gender: Optional[str] = Field(None, max_length=10, description='性别')
    birth_date: Optional[date] = Field(None, description='出生日期')
    education: Optional[str] = Field(None, max_length=50, description='学历')
    qualification_number: Optional[str] = Field(None, max_length=50, description='基金从业资格证号')
    is_qualified: bool = Field(True, description='是否有基金从业资格')
    resume: Optional[str] = Field(None, description='工作履历')
    current_company_id: Optional[int] = Field(None, description='当前任职公司ID')


class FundManagerPersonCreate(FundManagerPersonBase):
    pass


class FundManagerPersonUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description='姓名')
    gender: Optional[str] = Field(None, max_length=10, description='性别')
    birth_date: Optional[date] = Field(None, description='出生日期')
    education: Optional[str] = Field(None, max_length=50, description='学历')
    qualification_number: Optional[str] = Field(None, max_length=50, description='基金从业资格证号')
    is_qualified: Optional[bool] = Field(None, description='是否有基金从业资格')
    resume: Optional[str] = Field(None, description='工作履历')
    current_company_id: Optional[int] = Field(None, description='当前任职公司ID')


class FundManagerPersonResponse(FundManagerPersonBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # 关系
    current_company: Optional[FundManagerResponse] = None
    funds: List[FundResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FundCategoryBase(BaseModel):
    category_code: str = Field(..., max_length=20, description='分类代码')
    category_name: str = Field(..., max_length=100, description='分类名称')
    parent_id: Optional[int] = Field(None, description='父级分类ID')
    level: int = Field(1, description='分类层级')
    description: Optional[str] = Field(None, description='分类描述')


class FundCategoryCreate(FundCategoryBase):
    pass


class FundCategoryUpdate(BaseModel):
    category_code: Optional[str] = Field(None, max_length=20, description='分类代码')
    category_name: Optional[str] = Field(None, max_length=100, description='分类名称')
    parent_id: Optional[int] = Field(None, description='父级分类ID')
    level: Optional[int] = Field(None, description='分类层级')
    description: Optional[str] = Field(None, description='分类描述')


class FundCategoryResponse(FundCategoryBase):
    id: int
    created_at: datetime
    # 自引用关系
    parent: Optional[FundCategoryResponse] = None
    children: List[FundCategoryResponse] = []
    funds: List[FundResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FundCategoryMappingBase(BaseModel):
    fund_id: int = Field(..., description='基金ID')
    category_id: int = Field(..., description='分类ID')


class FundCategoryMappingCreate(FundCategoryMappingBase):
    pass


class FundCategoryMappingResponse(FundCategoryMappingBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


FundResponse.model_rebuild()
FundNavResponse.model_rebuild()
FundReturnResponse.model_rebuild()
FundHoldingResponse.model_rebuild()
FundManagerResponse.model_rebuild()
FundManagerPersonResponse.model_rebuild()
FundCategoryResponse.model_rebuild()
