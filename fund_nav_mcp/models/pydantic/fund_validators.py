from __future__ import annotations

__all__ = [
    "FundValidators", "FundNavValidators", "FundReturnValidators", "FundHoldingValidators",
    "FundManagerValidators", "FundManagerPersonValidators", "FundCategoryValidators",
    "FundCategoryMappingValidators",
]

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import field_validator, model_validator

from fund_nav_mcp.utils.common import to_date_flexible


class FundValidators:
    """Fund 模型通用字段校验器 Mixin。

    提供 fund_code、fund_name 等字段的字符串修剪与基本非空校验。
    适用于 FundBase / FundCreate / FundUpdate 等模型。
    """

    @field_validator("fund_code")
    @classmethod
    def _strip_fund_code(cls, v: Optional[str]) -> Optional[str]:
        """去除基金代码的首尾空白。None 值直接返回。"""
        if v is None:
            return v
        return v.strip()

    @field_validator("fund_name", "fund_short_name")
    @classmethod
    def _strip_fund_name(cls, v: Optional[str]) -> Optional[str]:
        """去除基金名称/简称的空白，若结果为空则抛出 ValueError。"""
        if v is None:
            return v
        s = v.strip()
        if not s:
            raise ValueError("基金名称不能为空白")
        return s

    @field_validator(
        "fund_custodian", "fund_registration_address",
        "parent_fund_code", "manager_code", "manager_person_code",
        "manager_name", "manager_person_name",
    )
    @classmethod
    def _strip_fund_opt(cls, v: Optional[str]) -> Optional[str]:
        """去除可选字符串字段的空白，保留原值（允许空字符串）。"""
        if v is None:
            return v
        return v.strip()


class FundNavValidators:
    """FundNav 模型通用字段校验器 Mixin。

    校验基金代码非空、单位净值为正、净值日期不晚于今天，
    并检查累计净值与单位净值的大小关系。
    """

    @field_validator("fund_code")
    @classmethod
    def _strip_fund_code(cls, v: Optional[str]) -> Optional[str]:
        """去除基金代码空白，要求非空。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("基金代码不能为空白")
        return code

    @field_validator("nav_unit")
    @classmethod
    def _positive_nav_unit(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """单位净值必须大于 0。None 值直接返回。"""
        if v is None:
            return v
        if v <= 0:
            raise ValueError(f"单位净值必须大于0，当前值: {v}")
        return v

    @field_validator("nav_date")
    @classmethod
    def _nav_date_not_future(cls, v: Optional[str]) -> Optional[str]:
        """净值日期不能晚于今天。"""
        if v is None:
            return v
        if to_date_flexible(v) > datetime.today().date():
            raise ValueError(f"净值日期不能晚于今天，当前值: {v}")
        return v

    @model_validator(mode="after")
    def _validate_nav_consistency(self: Any) -> Any:
        """若同时提供了累计净值与单位净值，则累计净值不得小于单位净值。"""
        acc = getattr(self, "nav_acc", None)
        unit = getattr(self, "nav_unit", None)
        if acc is not None and unit is not None and acc < unit:
            raise ValueError(f"累计净值 ({acc}) 不能小于单位净值 ({unit})")
        return self


class FundReturnValidators:
    """FundReturn 模型通用字段校验器 Mixin。

    校验基金代码非空、排名/总数为正、计算日期不晚于今天，
    并检查排名不超过同类总数。
    """

    @field_validator("fund_code")
    @classmethod
    def _strip_fund_code(cls, v: Optional[str]) -> Optional[str]:
        """去除基金代码空白，要求非空。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("基金代码不能为空白")
        return code

    @field_validator("total_funds")
    @classmethod
    def _positive_total_funds(cls, v: Optional[int]) -> Optional[int]:
        """同类总数必须 ≥ 1。"""
        if v is None:
            return v
        if v < 1:
            raise ValueError(f"同类总数必须 ≥ 1，当前值: {v}")
        return v

    @field_validator("rank")
    @classmethod
    def _positive_rank(cls, v: Optional[int]) -> Optional[int]:
        """排名必须 ≥ 1。"""
        if v is None:
            return v
        if v < 1:
            raise ValueError(f"排名必须 ≥ 1，当前值: {v}")
        return v

    @field_validator("calculation_date")
    @classmethod
    def _calc_date_not_future(cls, v: Optional[str]) -> Optional[str]:
        """计算日期不能晚于今天。"""
        if v is None:
            return v
        if to_date_flexible(v) > datetime.today().date():
            raise ValueError(f"计算日期不能晚于今天，当前值: {v}")
        return v

    @model_validator(mode="after")
    def _validate_return_consistency(self: Any) -> Any:
        """若同时提供了排名和同类总数，排名不能超过总数。"""
        r = getattr(self, "rank", None)
        t = getattr(self, "total_funds", None)
        if r is not None and t is not None and r > t:
            raise ValueError(f"排名 ({r}) 不能大于同类总数 ({t})")
        return self


class FundHoldingValidators:
    """FundHolding 模型通用字段校验器 Mixin。

    校验基金代码、股票代码/名称非空，持仓比例在 0~1，金额/股数非负，
    报告日期不晚于今天。
    """

    @field_validator("fund_code")
    @classmethod
    def _strip_fund_code(cls, v: Optional[str]) -> Optional[str]:
        """去除基金代码空白，要求非空。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("基金代码不能为空白")
        return code

    @field_validator("stock_code")
    @classmethod
    def _strip_stock_code(cls, v: Optional[str]) -> Optional[str]:
        """去除股票代码空白，要求非空。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("股票代码不能为空")
        return code

    @field_validator("stock_name")
    @classmethod
    def _strip_stock_name(cls, v: Optional[str]) -> Optional[str]:
        """去除股票名称空白，要求非空。"""
        if v is None:
            return v
        name = v.strip()
        if not name:
            raise ValueError("股票名称不能为空")
        return name

    @field_validator("holding_ratio")
    @classmethod
    def _validate_holding_ratio(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """持仓比例必须在 0 到 1 之间。"""
        if v is None:
            return v
        if v < 0 or v > 1:
            raise ValueError(f"持仓比例必须在 0~1 之间，当前值: {v}")
        return v

    @field_validator("market_value", "shares_held")
    @classmethod
    def _non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """市值/持股数量不得为负数。"""
        if v is None:
            return v
        if v < 0:
            raise ValueError(f"不得为负数，当前值: {v}")
        return v

    @field_validator("report_date")
    @classmethod
    def _report_date_not_future(cls, v: Optional[str]) -> Optional[str]:
        """报告日期不能晚于今天。"""
        if v is None:
            return v
        if to_date_flexible(v) > datetime.today().date():
            raise ValueError(f"报告日期不能晚于今天，当前值: {v}")
        return v


class FundManagerValidators:
    """FundManager 模型通用字段校验器 Mixin。

    包含公司全称、统一信用代码、中基协登记编号、资本数据、人数等校验，
    并确保持证人数不超过全职员工总数。
    """

    @field_validator("company_name")
    @classmethod
    def _strip_company_name(cls, v: Optional[str]) -> Optional[str]:
        """去除公司全称空白，若为空则抛出错误。"""
        if v is None:
            return v
        name = v.strip()
        if not name:
            raise ValueError("公司全称不能为空")
        return name

    @field_validator(
        "short_name", "organization_type", "business_type",
        "registered_address", "office_address", "actual_controller",
        "legal_representative", "english_name",
    )
    @classmethod
    def _strip_manager_opt(cls, v: Optional[str]) -> Optional[str]:
        """去除可选字符串字段空白，若结果为空则返回 None。"""
        if v is None:
            return v
        return v.strip() or None

    @field_validator("amac_registration_number")
    @classmethod
    def _validate_amac_number(cls, v: Optional[str]) -> Optional[str]:
        """校验中基协登记编号格式：P + 6~10 位数字。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("中基协登记编号不能为空白")
        if not re.match(r"^[Pp]\d{6,10}$", code):
            raise ValueError(f"中基协登记编号格式无效，应为P+6-10位数字，当前值: '{code}'")
        return code.upper()

    @field_validator("unified_code")
    @classmethod
    def _validate_unified_code(cls, v: Optional[str]) -> Optional[str]:
        """校验统一社会信用代码为 18 位有效字符（不含 I/O/Z/S/V）。"""
        if v is None:
            return v
        code = v.strip().upper()
        if not code:
            return None
        if not re.match(r"^[0-9A-HJ-NPQRTUWXY]{18}$", code):
            raise ValueError(
                f"统一社会信用代码必须为18位字母数字组合（不含I/O/Z/S/V），当前值: '{code}'"
            )
        return code

    @field_validator("amac_registration_date")
    @classmethod
    def _registration_date_not_future(cls, v: Optional[str]) -> Optional[str]:
        """登记时间不能晚于今天。"""
        if v is None:
            return v
        if to_date_flexible(v) > datetime.today().date():
            raise ValueError(f"登记时间不能晚于今天，当前值: {v}")
        return v

    @field_validator("registered_capital", "paid_up_capital")
    @classmethod
    def _positive_capital(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """资本金额不得为负数。"""
        if v is not None and v < 0:
            raise ValueError(f"资本不得为负数，当前值: {v}")
        return v

    @field_validator("capital_ratio")
    @classmethod
    def _validate_capital_ratio(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """实缴比例必须在 0 到 100 之间。"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"实缴比例必须在 0~100 之间，当前值: {v}")
        return v

    @field_validator("employee_count", "fund_industry_count")
    @classmethod
    def _non_negative_int(cls, v: Optional[int]) -> Optional[int]:
        """员工人数不得为负数。"""
        if v is not None and v < 0:
            raise ValueError(f"人数不得为负数，当前值: {v}")
        return v

    @model_validator(mode="after")
    def _validate_manager_consistency(self: Any) -> Any:
        """基金从业人数不得超过全职员工总数。"""
        emp = getattr(self, "employee_count", None)
        ind = getattr(self, "fund_industry_count", None)
        if emp is not None and ind is not None and ind > emp:
            raise ValueError(
                f"基金从业人数 ({ind}) 不能超过全职员工人数 ({emp})"
            )
        return self


class FundManagerPersonValidators:
    """FundManagerPerson 模型通用字段校验器 Mixin。

    校验姓名非空、性别只能为“男/女”，出生日期不晚于今天，并修剪其他可选字段。
    """

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        """去除姓名空白，要求非空。"""
        if v is None:
            return v
        name = v.strip()
        if not name:
            raise ValueError("姓名不能为空")
        return name

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """性别检查：必须为“男”或“女”，空值则返回 None。"""
        if v is None:
            return v
        g = v.strip()
        if not g:
            return None
        if g not in ("男", "女"):
            raise ValueError(f"性别只能为'男'或'女'，当前值: '{g}'")
        return g

    @field_validator("birth_date")
    @classmethod
    def _birth_date_not_future(cls, v: Optional[str]) -> Optional[str]:
        """出生日期不能晚于今天。"""
        if v is None:
            return v
        if to_date_flexible(v) > datetime.today().date():
            raise ValueError(f"出生日期不能晚于今天，当前值: {v}")
        return v

    @field_validator("education", "qualification_number", "resume", "company_code")
    @classmethod
    def _strip_person_opt(cls, v: Optional[str]) -> Optional[str]:
        """去除可选字符串字段空白，空值返回 None。"""
        if v is None:
            return v
        return v.strip() or None


class FundCategoryValidators:
    """FundCategory 模型通用字段校验器 Mixin。

    校验分类代码/名称非空，层级 ≥ 1，一级分类不应设置父级代码。
    """

    @field_validator("category_code")
    @classmethod
    def _strip_category_code(cls, v: Optional[str]) -> Optional[str]:
        """去除分类代码空白，要求非空。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("分类代码不能为空")
        return code

    @field_validator("category_name")
    @classmethod
    def _strip_category_name(cls, v: Optional[str]) -> Optional[str]:
        """去除分类名称空白，要求非空。"""
        if v is None:
            return v
        name = v.strip()
        if not name:
            raise ValueError("分类名称不能为空")
        return name

    @field_validator("level")
    @classmethod
    def _positive_level(cls, v: Optional[int]) -> Optional[int]:
        """分类层级必须 ≥ 1。"""
        if v is None:
            return v
        if v < 1:
            raise ValueError(f"分类层级必须 ≥ 1，当前值: {v}")
        return v

    @field_validator("parent_category_code")
    @classmethod
    def _strip_parent_category_code(cls, v: Optional[str]) -> Optional[str]:
        """去除父级分类代码空白，空值返回 None。"""
        if v is None:
            return v
        return v.strip() or None

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: Optional[str]) -> Optional[str]:
        """去除描述文本空白，空值返回 None。"""
        if v is None:
            return v
        return v.strip() or None

    @model_validator(mode="after")
    def _validate_category_consistency(self: Any) -> Any:
        """一级分类（level=1）不允许设置父级分类代码。"""
        lv = getattr(self, "level", None)
        parent = getattr(self, "parent_category_code", None)
        if lv is not None and lv == 1 and parent is not None:
            raise ValueError("一级分类不应设置父级分类代码")
        return self


class FundCategoryMappingValidators:
    """FundCategoryMapping 模型通用字段校验器 Mixin。

    校验基金代码与分类代码非空，去除首尾空白。
    """

    @field_validator("fund_code", "category_code")
    @classmethod
    def _strip_code(cls, v: Optional[str]) -> Optional[str]:
        """去除代码空白，要求非空。None 值直接返回。"""
        if v is None:
            return v
        code = v.strip()
        if not code:
            raise ValueError("关联代码不能为空白")
        return code
