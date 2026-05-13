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

import re
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from fund_nav_mcp.models.pydantic.fund_validators import (
    FundValidators, FundNavValidators, FundReturnValidators, FundHoldingValidators,
    FundManagerValidators, FundManagerPersonValidators, FundCategoryValidators,
)
from fund_nav_mcp.utils.enums import (
    FundNavStatus, FundStatus, FundType, FundRegulatoryType, PeriodType,
    FundDataSource, FundManagementType, ManagementScaleRange, ShareClass,
)


# ================================================================
# ShareClassDescription
# ================================================================

class ShareClassDescription(BaseModel):
    """份额类别描述模型，集中管理描述数据与查询逻辑。"""

    share_class: ShareClass
    fund_type: Optional[FundType] = None
    fund_regulatory_type: Optional[FundRegulatoryType] = None
    description: str

    @classmethod
    @lru_cache(maxsize=None)
    def _descriptions(cls) -> List[ShareClassDescription]:
        """返回所有份额描述定义（缓存，仅构建一次）。"""
        return [
            # ── 货币基金 ──
            ShareClassDescription(
                share_class=ShareClass.A, fund_type=FundType.Money,
                description="A类（货币基金·散客份额）：申购门槛低（100元起），销售服务费较高，面向个人投资者，收益相对B类较低",
            ),
            ShareClassDescription(
                share_class=ShareClass.B, fund_type=FundType.Money,
                description="B类（货币基金·机构份额）：申购门槛高（通常500万元起），销售服务费较低，面向机构和大额投资者，收益高于A类",
            ),
            ShareClassDescription(
                share_class=ShareClass.C, fund_type=FundType.Money,
                description="C类（货币基金·新增份额）：申购门槛高于A类，如中欧货币C",
            ),
            ShareClassDescription(
                share_class=ShareClass.D, fund_type=FundType.Money,
                description="D类（货币基金·高门槛份额）：申购门槛比C类更高，如中欧货币D；或通过公司指定的交易平台办理",
            ),
            ShareClassDescription(
                share_class=ShareClass.E, fund_type=FundType.Money,
                description="E类（货币基金·代销/场内份额）：仅在指定代销机构（如互联网平台）销售；或为场内交易型货币基金，面值100元",
            ),
            # ── 债券基金 ──
            ShareClassDescription(
                share_class=ShareClass.A, fund_type=FundType.Bond,
                description="A类（债券基金·前端收费）：申购时收取申购费，费率较低，适合投资期不确定的投资者",
            ),
            ShareClassDescription(
                share_class=ShareClass.B, fund_type=FundType.Bond,
                description="B类（债券基金·后端收费）：赎回时收取申购费，费率高于A类前端，但持有时间越长收费越少（超3年通常免申购费），适合长期投资",
            ),
            ShareClassDescription(
                share_class=ShareClass.C, fund_type=FundType.Bond,
                description="C类（债券基金·销售服务费）：免申购费，但有0.3%/年销售服务费，3年累计约0.9%低于A类申购费，适合短期投资（<3年）",
            ),
            # ── 分级基金 ──
            ShareClassDescription(
                share_class=ShareClass.A, fund_type=FundType.Other,
                description="A类（分级基金·优先级份额）：约定固定收益率，预期风险较低，享有优先收益权",
            ),
            ShareClassDescription(
                share_class=ShareClass.B, fund_type=FundType.Other,
                description="B类（分级基金·进取份额）：浮动收益，预期风险和收益较高，净值下跌时B类优先承担亏损，上涨时获得杠杆增值",
            ),
            # ── 特殊类型 ──
            ShareClassDescription(
                share_class=ShareClass.D, fund_type=FundType.Commodity,
                description="D类（黄金ETF·官网直销）：如博时黄金ETF D，在基金公司官网上直销",
            ),
            ShareClassDescription(
                share_class=ShareClass.E, fund_type=FundType.Bond,
                description="E类（债券基金·网上直销）：仅通过基金公司网上交易系统、直销中心开放销售，如中欧纯债E",
            ),
            # ── 私募基金（结构化产品，按风险收益层级划分）──
            ShareClassDescription(
                share_class=ShareClass.A,
                fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
                description="A类（优先级份额）：风险较低，收益相对固定优先分配，预期收益为约定收益率",
            ),
            ShareClassDescription(
                share_class=ShareClass.B,
                fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
                description="B类（劣后级份额）：风险较高，净值下跌时优先承担亏损，净值上涨时博取杠杆超额收益",
            ),
            ShareClassDescription(
                share_class=ShareClass.C,
                fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
                description="C类（夹层级/中间级份额）：风险收益介于优先级和劣后级之间；有时也模仿公募C类收取销售服务费",
            ),
            ShareClassDescription(
                share_class=ShareClass.D,
                fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
                description="D类（特殊层级份额）：较少出现，用于区分更细的结构化层级或特殊分配方式，需结合具体合同说明",
            ),
            ShareClassDescription(
                share_class=ShareClass.E,
                fund_regulatory_type=FundRegulatoryType.PrivateSecurities,
                description="E类（特殊层级份额）：较少出现，用于区分更细的结构化层级或特殊分配方式，需结合具体合同说明",
            ),
            # ── 通用公募（不区分类型，兜底）──
            ShareClassDescription(share_class=ShareClass.A,
                                  description="A类份额：前端收费，申购时一次性收取申购费，最常见的主份额类型"),
            ShareClassDescription(share_class=ShareClass.B,
                                  description="B类份额：后端收费，赎回时收取申购费，持有时间越长费率越低"),
            ShareClassDescription(share_class=ShareClass.C,
                                  description="C类份额：免申赎费，按年收取销售服务费，适合短期持有"),
            ShareClassDescription(share_class=ShareClass.D,
                                  description="D类份额：特定渠道或平台销售的份额类别，具体规则因基金而异"),
            ShareClassDescription(share_class=ShareClass.E,
                                  description="E类份额：特定代销渠道或场内交易的份额类别，具体规则因基金而异"),
            ShareClassDescription(share_class=ShareClass.NotApplicable,
                                  description="不适用份额分类（如非结构化私募产品通常不设份额类别）"),
        ]

    @classmethod
    def get_description(cls, share_class: ShareClass, fund_type: Optional[FundType] = None,
                        fund_regulatory_type: Optional[FundRegulatoryType] = None) -> str:
        """返回份额类别描述：精确匹配 → 私募监管类型匹配 → 公募基金类型匹配 → 通用匹配 → 降级返回标签。"""
        regulatory_is_private = (
                fund_regulatory_type is not None
                and int(fund_regulatory_type) >= 3
                and fund_regulatory_type is not FundRegulatoryType.Unknown
        )

        # ① 完全精确匹配（share_class + fund_type + fund_regulatory_type）
        for desc in cls._descriptions():
            if (desc.share_class is share_class
                    and desc.fund_type == fund_type
                    and desc.fund_regulatory_type == fund_regulatory_type):
                return desc.description

        # ② 私募结构化产品：匹配 share_class + 任一私募监管类型（不区分 fund_type）
        if regulatory_is_private:
            for desc in cls._descriptions():
                if (desc.share_class is share_class
                        and desc.fund_regulatory_type is not None
                        and int(desc.fund_regulatory_type) >= 3):
                    return desc.description

        # ③ 公募/分级：匹配 share_class + fund_type（fund_regulatory_type 为空）
        for desc in cls._descriptions():
            if (desc.share_class is share_class
                    and desc.fund_type == fund_type
                    and desc.fund_regulatory_type is None):
                return desc.description

        # ④ 通用公募兜底（share_class 匹配，fund_type 和 fund_regulatory_type 均为空）
        for desc in cls._descriptions():
            if (desc.share_class is share_class
                    and desc.fund_type is None
                    and desc.fund_regulatory_type is None):
                return desc.description

        return f"{share_class.label}份额"


# ================================================================
# Fund
# ================================================================

class FundBase(FundValidators, BaseModel):

    @staticmethod
    def _validate_fund_code(fund_code: str, regulatory_type: FundRegulatoryType) -> None:
        code = fund_code.strip()
        if not code:
            raise ValueError("基金代码不能为空")
        if regulatory_type in (FundRegulatoryType.Public, FundRegulatoryType.PublicReit):
            if not re.match(r"^\d{6}$", code):
                raise ValueError(f"公募基金代码必须为6位数字，当前值: '{code}'")
        elif int(regulatory_type) >= 3:
            if re.match(r"^[Ss]\d{5}$", code) or \
                    re.match(r"^[A-Za-z0-9]{9,15}$", code) or \
                    re.match(r"^P\d+$", code):
                return
            if len(code) < 2:
                raise ValueError(f"私募基金代码过短（至少2位），当前值: '{code}'")
            if any(c.isspace() for c in code):
                raise ValueError("基金代码不允许包含空白字符")
        else:
            if any(c.isspace() for c in code):
                raise ValueError("基金代码不允许包含空白字符")

    fund_code: str = Field(..., title="基金代码", max_length=20)
    fund_name: str = Field(..., title="基金名称", max_length=200)
    fund_short_name: Optional[str] = Field(default=None, title="基金简称", max_length=100)
    fund_type: Optional[FundType] = Field(default=None, title="投资标的类型")
    fund_regulatory_type: FundRegulatoryType = Field(..., title="监管类型")
    manager_person_code: Optional[str] = Field(default=None, max_length=50, title="基金管理人（个人）从业资格证号")
    manager_person_name: Optional[str] = Field(default=None, max_length=50,
                                               title="基金管理人（个人）姓名（code 未传时按名称查找）")
    manager_code: Optional[str] = Field(default=None, max_length=20, title="基金管理人（机构）中基协登记编号")
    manager_name: Optional[str] = Field(default=None, max_length=100,
                                        title="基金管理人（机构）公司全称（code 未传时按名称查找）")
    fund_management_type: FundManagementType = Field(..., title="基金管理类型")
    fund_custodian: Optional[str] = Field(default=None, title="基金托管人", max_length=100)
    fund_registration_address: Optional[str] = Field(default=None, title="注册地址", max_length=100)
    establishment_date: date = Field(..., title="成立日期")
    registration_date: date = Field(..., title="备案日期")
    status: FundStatus = Field(..., title="基金状态")
    share_class: ShareClass = Field(default=ShareClass.NotApplicable, title="份额类别")
    parent_fund_code: Optional[str] = Field(default=None, max_length=20, title="父基金代码")

    @model_validator(mode="after")
    def _validate_fund_consistency(self) -> "FundBase":
        self._validate_fund_code(self.fund_code, self.fund_regulatory_type)
        if self.establishment_date > self.registration_date:
            raise ValueError(
                f"成立日期 ({self.establishment_date}) 不能晚于备案日期 ({self.registration_date})"
            )
        if (self.share_class is not ShareClass.NotApplicable
                and self.fund_regulatory_type is FundRegulatoryType.Unknown):
            raise ValueError(
                f"设置了份额类别 ({self.share_class.label})，但监管类型未知，"
                f"请指定正确的监管类型（公募/私募）"
            )
        self._validate_share_class()
        return self

    def _validate_share_class(self) -> None:
        if self.share_class is ShareClass.NotApplicable:
            return
        if self.fund_type is None:
            return
        regulatory_is_public = (
                self.fund_regulatory_type in (FundRegulatoryType.Public, FundRegulatoryType.PublicReit)
        )
        if (regulatory_is_public
                and self.fund_type == FundType.Other
                and self.share_class in (ShareClass.C, ShareClass.D, ShareClass.E)):
            raise ValueError(
                f"公募分级基金通常仅设A类(优先级)和B类(进取)，不包含{self.share_class.label}份额，"
                f"如非分级基金请调整 fund_type"
            )

    @property
    def share_class_description(self) -> str:
        """返回当前份额类别在基金类型上下文中的详细说明。"""
        return ShareClassDescription.get_description(self.share_class, self.fund_type, self.fund_regulatory_type)


class FundCreate(FundBase):
    pass


class FundUpdate(FundValidators, BaseModel):
    fund_code: Optional[str] = Field(default=None, max_length=20, description='基金代码')
    fund_name: Optional[str] = Field(default=None, max_length=200, description='基金名称')
    fund_short_name: Optional[str] = Field(default=None, max_length=100, description='基金简称')
    fund_type: Optional[FundType] = Field(default=None, description='投资标的类型')
    fund_regulatory_type: Optional[FundRegulatoryType] = Field(default=None, description='监管类型')
    manager_person_code: Optional[str] = Field(default=None, max_length=50, description='基金管理人（个人）从业资格证号')
    manager_person_name: Optional[str] = Field(default=None, max_length=50, description='基金管理人（个人）姓名')
    manager_code: Optional[str] = Field(default=None, max_length=20, description='基金管理人（机构）中基协登记编号')
    manager_name: Optional[str] = Field(default=None, max_length=100, description='基金管理人（机构）公司全称')
    fund_management_type: Optional[FundManagementType] = Field(default=None, description='基金管理类型')
    fund_custodian: Optional[str] = Field(default=None, max_length=100, description='基金托管人')
    fund_registration_address: Optional[str] = Field(default=None, max_length=100, description='注册地址')
    establishment_date: Optional[date] = Field(default=None, description='成立日期')
    registration_date: Optional[date] = Field(default=None, description='备案日期')
    status: Optional[FundStatus] = Field(default=None, description='基金状态')
    share_class: Optional[ShareClass] = Field(default=None, description='份额类别')
    parent_fund_code: Optional[str] = Field(default=None, max_length=20, description='父基金代码')


class FundResponse(FundBase):
    id: int
    created_at: datetime
    updated_at: datetime
    fund_manager_person_id: Optional[int] = None
    fund_manager_id: Optional[int] = None
    parent_fund_id: Optional[int] = None
    manager: Optional[FundManagerResponse] = None
    manager_person: Optional[FundManagerPersonResponse] = None
    nav_records: List[FundNavResponse] = []
    returns: List[FundReturnResponse] = []
    holdings: List[FundHoldingResponse] = []
    categories: List[FundCategoryResponse] = []
    parent: Optional["FundResponse"] = None
    children: List["FundResponse"] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def share_class_description(self) -> str:
        """返回当前份额类别在基金类型上下文中的详细说明。"""
        return ShareClassDescription.get_description(self.share_class, self.fund_type, self.fund_regulatory_type)


# ================================================================
# FundNav
# ================================================================

class FundNavBase(FundNavValidators, BaseModel):
    fund_code: str = Field(..., max_length=20, description='基金代码')
    nav_date: date = Field(..., description='净值日期')
    unit_nav: Decimal = Field(..., max_digits=10, decimal_places=4, description='单位净值')
    acc_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='累计净值')
    adj_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='复权净值')
    daily_return_rate: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='日增长率')
    nav_status: FundNavStatus = Field(..., description='净值状态')
    data_source: FundDataSource = Field(..., description='数据来源')


class FundNavCreate(FundNavBase):
    pass


class FundNavUpdate(FundNavValidators, BaseModel):
    fund_code: Optional[str] = Field(None, max_length=20, description='基金代码')
    nav_date: Optional[date] = Field(None, description='净值日期')
    unit_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='单位净值')
    acc_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='累计净值')
    adj_nav: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='复权净值')
    daily_return_rate: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='日增长率')
    nav_status: Optional[FundNavStatus] = Field(None, description='净值状态')
    data_source: Optional[FundDataSource] = Field(None, description='数据来源')


class FundNavResponse(FundNavBase):
    id: int
    created_at: datetime
    fund_id: int
    fund: Optional[FundResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# FundReturn
# ================================================================

class FundReturnBase(FundReturnValidators, BaseModel):
    fund_code: str = Field(..., max_length=20, description='基金代码')
    period_type: PeriodType = Field(..., description='周期类型')
    return_rate: Decimal = Field(..., max_digits=10, decimal_places=4, description='收益率')
    rank: int = Field(..., description='同类排名')
    total_funds: int = Field(..., description='同类总数')
    calculation_date: date = Field(..., description='计算日期')


class FundReturnCreate(FundReturnBase):
    pass


class FundReturnUpdate(FundReturnValidators, BaseModel):
    fund_code: Optional[str] = Field(None, max_length=20, description='基金代码')
    period_type: Optional[PeriodType] = Field(None, description='周期类型')
    return_rate: Optional[Decimal] = Field(None, max_digits=10, decimal_places=4, description='收益率')
    rank: Optional[int] = Field(None, description='同类排名')
    total_funds: Optional[int] = Field(None, description='同类总数')
    calculation_date: Optional[date] = Field(None, description='计算日期')


class FundReturnResponse(FundReturnBase):
    id: int
    created_at: datetime
    fund_id: int
    fund: Optional[FundResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# FundHolding
# ================================================================

class FundHoldingBase(FundHoldingValidators, BaseModel):
    fund_code: str = Field(..., max_length=20, description='基金代码')
    report_date: date = Field(..., description='报告日期')
    stock_code: str = Field(..., max_length=20, description='股票代码')
    stock_name: str = Field(..., max_length=100, description='股票名称')
    holding_ratio: Decimal = Field(..., max_digits=6, decimal_places=4, description='持仓比例')
    market_value: Decimal = Field(..., max_digits=15, decimal_places=2, description='市值（万元）')
    shares_held: Decimal = Field(..., max_digits=15, decimal_places=2, description='持股数量（万股）')


class FundHoldingCreate(FundHoldingBase):
    pass


class FundHoldingUpdate(FundHoldingValidators, BaseModel):
    fund_id: Optional[int] = Field(None, description='基金ID')
    fund_code: Optional[str] = Field(None, max_length=20, description='基金代码（与 fund_id 二选一）')
    report_date: Optional[date] = Field(None, description='报告日期')
    stock_code: Optional[str] = Field(None, max_length=20, description='股票代码')
    stock_name: Optional[str] = Field(None, max_length=100, description='股票名称')
    holding_ratio: Optional[Decimal] = Field(None, max_digits=6, decimal_places=4, description='持仓比例')
    market_value: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='市值（万元）')
    shares_held: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description='持股数量（万股）')


class FundHoldingResponse(FundHoldingBase):
    id: int
    created_at: datetime
    fund_id: int
    fund: Optional[FundResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# FundManager
# ================================================================

class FundManagerBase(FundManagerValidators, BaseModel):
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


class FundManagerUpdate(FundManagerValidators, BaseModel):
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
    funds: List[FundResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# FundManagerPerson
# ================================================================

class FundManagerPersonBase(FundManagerPersonValidators, BaseModel):
    name: str = Field(..., max_length=50, description='姓名')
    gender: Optional[str] = Field(None, max_length=10, description='性别')
    birth_date: Optional[date] = Field(None, description='出生日期')
    education: Optional[str] = Field(None, max_length=50, description='学历')
    qualification_number: Optional[str] = Field(None, max_length=50, description='基金从业资格证号')
    is_qualified: bool = Field(True, description='是否有基金从业资格')
    resume: Optional[str] = Field(None, description='工作履历')
    company_code: Optional[str] = Field(None, max_length=20, description='当前任职公司中基协登记编号')


class FundManagerPersonCreate(FundManagerPersonBase):
    pass


class FundManagerPersonUpdate(FundManagerPersonValidators, BaseModel):
    name: Optional[str] = Field(None, max_length=50, description='姓名')
    gender: Optional[str] = Field(None, max_length=10, description='性别')
    birth_date: Optional[date] = Field(None, description='出生日期')
    education: Optional[str] = Field(None, max_length=50, description='学历')
    qualification_number: Optional[str] = Field(None, max_length=50, description='基金从业资格证号')
    is_qualified: Optional[bool] = Field(None, description='是否有基金从业资格')
    resume: Optional[str] = Field(None, description='工作履历')
    company_code: Optional[str] = Field(None, max_length=20, description='当前任职公司中基协登记编号')


class FundManagerPersonResponse(FundManagerPersonBase):
    id: int
    created_at: datetime
    updated_at: datetime
    current_company_id: Optional[int] = None
    current_company: Optional[FundManagerResponse] = None
    funds: List[FundResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# FundCategory
# ================================================================

class FundCategoryBase(FundCategoryValidators, BaseModel):
    category_code: str = Field(..., max_length=20, description='分类代码')
    category_name: str = Field(..., max_length=100, description='分类名称')
    parent_category_code: Optional[str] = Field(None, max_length=20, description='父级分类代码')
    level: int = Field(1, description='分类层级')
    description: Optional[str] = Field(None, description='分类描述')


class FundCategoryCreate(FundCategoryBase):
    pass


class FundCategoryUpdate(FundCategoryValidators, BaseModel):
    category_code: Optional[str] = Field(None, max_length=20, description='分类代码')
    category_name: Optional[str] = Field(None, max_length=100, description='分类名称')
    parent_category_code: Optional[str] = Field(None, max_length=20, description='父级分类代码')
    level: Optional[int] = Field(None, description='分类层级')
    description: Optional[str] = Field(None, description='分类描述')


class FundCategoryResponse(FundCategoryBase):
    id: int
    created_at: datetime
    parent_id: Optional[int] = None
    parent: Optional[FundCategoryResponse] = None
    children: List[FundCategoryResponse] = []
    funds: List[FundResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# FundCategoryMapping
# ================================================================

class FundCategoryMappingBase(BaseModel):
    fund_code: str = Field(..., max_length=20, description='基金代码')
    category_code: str = Field(..., max_length=20, description='分类代码')

    @field_validator("fund_code", "category_code")
    @classmethod
    def _strip_code(cls, v: str) -> str:
        code = v.strip()
        if not code:
            raise ValueError("关联代码不能为空白")
        return code


class FundCategoryMappingCreate(FundCategoryMappingBase):
    pass


class FundCategoryMappingResponse(FundCategoryMappingBase):
    id: int
    created_at: datetime
    fund_id: int
    category_id: int

    model_config = ConfigDict(from_attributes=True)


# ================================================================
# Model rebuilds
# ================================================================

FundResponse.model_rebuild()
FundNavResponse.model_rebuild()
FundReturnResponse.model_rebuild()
FundHoldingResponse.model_rebuild()
FundManagerResponse.model_rebuild()
FundManagerPersonResponse.model_rebuild()
FundCategoryResponse.model_rebuild()
