__all__ = [
    "NodeStatus", "FundStatus", "FundNavStatus", "FundType",
    "FundRegulatoryType", "PeriodType", "FundDataSource",
    "Errcode"
]

from enum import Enum
from typing import Any

from prefab_ui.components import Badge
from starlette.status import *


class _BaseIntEnum(int, Enum):
    def __new__(cls, value: int, label: str) -> int:
        obj = int.__new__(cls, value)  # type: ignore[call-overload]
        obj._value_ = value
        obj.label = label
        return obj

    def __str__(self):
        return f"{self.value}"


class _NodeStatusEnum(str, Enum):
    """
    节点状态枚举
    枚举成员格式： (value:str, label:str, component: Component)
    使用示例：
       Active = "活跃", "success", Component
    兼容：
       - .value -> str
       - .label -> str
       - .html_code -> function
    """

    def __new__(cls, value: str, label: str, component: dict[str, Any]) -> str:
        obj = str.__new__(cls, value)  # type: ignore[call-overload]
        obj._value_ = value
        obj.label = label
        obj.component = component
        return obj

    def __str__(self):
        return f"{self.value}"


class NodeStatus(_NodeStatusEnum):
    Active = "已启动", "success", Badge("已启动", variant="success").model_dump()
    Inactive = "未启动", "outline", Badge("未启动", variant="outline").model_dump()
    AuthFailed = "授权失败", "outline", Badge("授权失败", variant="outline").model_dump()
    Deactivate = "停用", "secondary", Badge("停用", variant="secondary").model_dump()
    Error = "故障", "destructive", Badge("故障", variant="destructive").model_dump()
    Unknown = "未知", "warning", Badge("未知", variant="warning").model_dump()

    @classmethod
    def _missing_(cls, value: str):
        return cls.Unknown

    @classmethod
    def from_name(cls, name: str) -> "NodeStatus":
        return getattr(cls, name, cls.Unknown)


class FundStatus(_BaseIntEnum):
    """
    基金状态枚举
    枚举成员格式： (value:int, label:str)
    使用示例：
       Active = 1, "正常运作"
    兼容：
       - .value -> int
       - .label -> str
    """
    Active = 1, "正常运作"
    NormalLiquidated = 2, "正常清算"
    EarlyLiquidated = 3, "提前清算"
    ExtendedLiquidated = 4, "延期清算"
    AbnormalLiquidated = 5, "非正常清算"
    AdvisoryTerminated = 6, "投顾协议已终止"
    ManagerCancelled = 7, "管理人已注销"
    Void = 8, "已作废"
    Terminated = 9, "已终止"
    VoluntaryWithdrawn = 10, "主动申请退会"
    PrivateToPublic = 11, "私转公"
    Unknown = 0, "未知"

    @classmethod
    def _missing_(cls, value: int):
        return cls.Unknown

    @classmethod
    def from_name(cls, name: str) -> "FundStatus":
        return getattr(cls, name, cls.Unknown)

    @classmethod
    def from_label(cls, label: str) -> "FundStatus":
        return next((status for status in cls if status.label == label), cls.Unknown)


class FundNavStatus(_BaseIntEnum):
    Valid = 1, "有效"
    Pending = 2, "待披露"
    Estimate = 3, "估算"
    Suspended = 4, "暂停披露"
    Deprecated = 5, "已废弃"
    Pre = 6, "预发布"
    Unknown = 0, "未知"

    @classmethod
    def _missing_(cls, value: str):
        return cls.Unknown

    @classmethod
    def from_name(cls, name: str) -> "FundNavStatus":
        return getattr(cls, name, cls.Unknown)

    @classmethod
    def from_label(cls, label: str) -> "FundNavStatus":
        return next((status for status in cls if status.label == label), cls.Unknown)


class FundType(_BaseIntEnum):
    Stock = 1, "股票型"
    Mixed = 2, "混合型"
    Bond = 3, "债券型"
    Money = 4, "货币型"
    Fof = 5, "组合型"
    Qdii = 6, "QDII型"
    Commodity = 7, "商品型"
    Alternative = 8, "替代型"
    Other = 9, "其他"

    @classmethod
    def _missing_(cls, value: str):
        return cls.Other

    @classmethod
    def from_name(cls, name: str) -> "FundType":
        return getattr(cls, name, cls.Other)

    @classmethod
    def from_label(cls, label: str) -> "FundType":
        return next((status for status in cls if status.label == label), cls.Other)


class FundRegulatoryType(_BaseIntEnum):
    Unknown = 0, "未知"
    # 公募类
    Public = 1, "公募基金"
    PublicReit = 2, "公募REITs"
    # 私募类
    PrivateSecurities = 3, "私募证券投资基金"
    PrivateSecuritiesFof = 4, "私募证券类FOF"
    VentureCapital = 5, "创业投资基金"
    VentureCapitalFof = 6, "创投类FOF"
    PrivateEquity = 7, "私募股权投资基金"
    PrivateEquityFof = 8, "私募股权类FOF"
    PrivateOther = 9, "其他私募投资基金"
    PrivateOtherFof = 10, "其他私募FOF"
    PrivateAssetAllocation = 11, "私募资产配置基金"

    @classmethod
    def _missing_(cls, value: str):
        return cls.Unknown

    @classmethod
    def from_name(cls, name: str) -> "FundRegulatoryType":
        return getattr(cls, name, cls.Unknown)

    @classmethod
    def from_label(cls, label: str) -> "FundRegulatoryType":
        return next((status for status in cls if status.label == label), cls.Unknown)


class FundDataSource(_BaseIntEnum):
    """
    关于编码：
       - 0 —— 未知
       - 1 ~ 99 手动 / 系统导入
       - 100 ~ 299 券商 / 机构直连
       - 300 ~ 499 第三方数据平台
       - 500 ~ 699 开源数据项目
    """
    Unknown = 0, "未知"

    Email = 1, "邮箱导入"
    ManualImport = 2, "文件批量导入"
    Api = 3, "API 自动同步"

    HuaTai = 100, "华泰证券"

    HuoFuNiu = 300, "火富牛"

    Akshare = 500, "akshare"

    Other = 999, "其他"

    @classmethod
    def _missing_(cls, value: str):
        return cls.Other

    @classmethod
    def from_name(cls, name: str) -> "FundDataSource":
        return getattr(cls, name, cls.Other)

    @classmethod
    def from_label(cls, label: str) -> "FundDataSource":
        return next((status for status in cls if status.label == label), cls.Other)


class PeriodType(_BaseIntEnum):
    Daily = 1, "日"
    Weekly = 2, "周"
    Monthly = 3, "月"
    Quarterly = 4, "季度"
    HalfYear = 5, "半年"
    Yearly = 6, "年"
    TwoYear = 7, "两年"
    ThreeYear = 8, "三年"
    FiveYear = 9, "五年"
    TenYear = 10, "十年"
    SinceInception = 11, "成立以来"
    Custom = 99, "自定义"


class _ErrcodeEnum(int, Enum):
    """
    枚举成员格式： (value:int, label:str, http:int)
    使用示例：
       SOME = 100, "描述", 200
    兼容：
       - .value -> int
       - .label -> str
       - .http  -> int (HTTP 状态码)
    """

    def __new__(cls, value: int, label: str, http: int) -> int:
        obj = int.__new__(cls, value)  # type: ignore[call-overload]
        obj._value_ = int(value)
        obj.label = label
        obj.http = int(http)
        return obj

    def __str__(self):
        return f"{self.value}"


class Errcode(_ErrcodeEnum):
    """
    API 错误代码枚举，第一个值为错误码，第二个值为标签，第三个值为 HTTP 状态码。
    格式: A BB CCC
    - A：错误级别（-4 客户端错误，-5 服务端错误，-9 第三方）
    - BB：模块编号（见下表）
    - CCC：具体错误编号（从 001 开始）

    模块编号分配
    BB	模块名
    00	通用
    10	工具（Tools）
    11	资源（Resources）
    12	提示词（Prompts）
    13	会话与连接
    14	认证与授权
    20	数据库（存储）
    21	缓存
    30	第三方服务
    """
    # 通用错误码
    PROCESS = 3, '处理中', HTTP_200_OK
    CONTINUE = 2, '继续', HTTP_200_OK
    DONE = 1, '完成', HTTP_200_OK
    SUCCESS = 0, "成功", HTTP_200_OK
    FAIL = -1, "失败", HTTP_500_INTERNAL_SERVER_ERROR

    MCP_INTERNAL_ERROR = -500000, "MCP 内部错误", HTTP_500_INTERNAL_SERVER_ERROR
    MCP_NOT_IMPLEMENTED = -500001, "功能未实现", HTTP_501_NOT_IMPLEMENTED
    MCP_BAD_REQUEST = -400000, "MCP 请求格式错误", HTTP_400_BAD_REQUEST

    # 客户端错误
    TOOL_NOT_FOUND = -410001, "工具不存在", HTTP_404_NOT_FOUND
    TOOL_INVALID_PARAMS = -410002, "工具参数无效", HTTP_422_UNPROCESSABLE_CONTENT
    TOOL_MISSING_REQUIRED_PARAM = -410003, "缺少必需参数", HTTP_422_UNPROCESSABLE_CONTENT
    TOOL_EXECUTION_NOT_ALLOWED = -410004, "不允许执行该工具", HTTP_403_FORBIDDEN

    # 服务端错误
    TOOL_EXECUTION_FAILED = -510001, "工具执行失败", HTTP_500_INTERNAL_SERVER_ERROR
    TOOL_TIMEOUT = -510002, "工具执行超时", HTTP_504_GATEWAY_TIMEOUT
    TOOL_CONFIG_ERROR = -510003, "工具配置错误", HTTP_500_INTERNAL_SERVER_ERROR

    # 资源错误
    RESOURCE_NOT_FOUND = -511001, "资源不存在", HTTP_404_NOT_FOUND
    RESOURCE_LOAD_FAILED = -511002, "资源加载失败", HTTP_500_INTERNAL_SERVER_ERROR
    RESOURCE_PERMISSION_DENIED = -411003, "无权限访问资源", HTTP_403_FORBIDDEN
    RESOURCE_URI_INVALID = -411004, "资源 URI 格式无效", HTTP_400_BAD_REQUEST

    # 提示词错误
    PROMPT_NOT_FOUND = -512001, "提示词模板不存在", HTTP_404_NOT_FOUND
    PROMPT_RENDER_FAILED = -512002, "提示词渲染失败", HTTP_500_INTERNAL_SERVER_ERROR
    PROMPT_INVALID_ARGUMENTS = -412003, "提示词参数无效", HTTP_422_UNPROCESSABLE_CONTENT

    # 会话与连接错误
    SESSION_NOT_INITIALIZED = -413001, "会话未初始化", HTTP_400_BAD_REQUEST
    SESSION_TIMEOUT = -413002, "会话已超时", HTTP_408_REQUEST_TIMEOUT
    CONNECTION_ERROR = -513003, "底层连接错误", HTTP_502_BAD_GATEWAY
    CLIENT_DISCONNECTED = -413004, "客户端已断开", HTTP_400_BAD_REQUEST

    # 认证与授权错误
    AUTH_FAILED = -414001, "认证失败", HTTP_401_UNAUTHORIZED
    AUTH_TOKEN_EXPIRED = -414002, "认证令牌已过期", HTTP_401_UNAUTHORIZED
    AUTH_INSUFFICIENT_SCOPE = -414003, "权限范围不足", HTTP_403_FORBIDDEN

    # 数据库错误
    DB_CONNECTION_FAILED = -520001, "数据库连接失败", HTTP_503_SERVICE_UNAVAILABLE
    DB_QUERY_FAILED = -520002, "数据库查询失败", HTTP_500_INTERNAL_SERVER_ERROR
    DB_TIMEOUT = -520003, "数据库操作超时", HTTP_504_GATEWAY_TIMEOUT
    DB_TRANSACTION_ERROR = -520004, "数据库事务错误", HTTP_500_INTERNAL_SERVER_ERROR
    DB_INTEGRITY_ERROR = -520005, "数据完整性错误", HTTP_409_CONFLICT

    UNIQUE_CONFLICT = -420006, "数据唯一性冲突", HTTP_409_CONFLICT
    RECORD_NOT_FOUND = -420007, "记录不存在", HTTP_404_NOT_FOUND

    # 缓存错误
    CACHE_CONNECTION_FAILED = -521001, "缓存连接失败", HTTP_503_SERVICE_UNAVAILABLE
    CACHE_WRITE_FAILED = -521002, "缓存写入失败", HTTP_500_INTERNAL_SERVER_ERROR
    CACHE_TIMEOUT = -521003, "缓存操作超时", HTTP_504_GATEWAY_TIMEOUT
    CACHE_SERIALIZATION_ERROR = -521004, "缓存序列化错误", HTTP_500_INTERNAL_SERVER_ERROR

    # 第三方服务错误
    THIRD_PARTY_ERROR = -930001, "第三方服务错误", HTTP_502_BAD_GATEWAY
    THIRD_PARTY_TIMEOUT = -930002, "第三方服务超时", HTTP_504_GATEWAY_TIMEOUT
    THIRD_PARTY_INVALID_RESPONSE = -930003, "第三方返回无效响应", HTTP_502_BAD_GATEWAY
