__all__ = ["NodeStatus", "Errcode"]

from enum import Enum

from prefab_ui.components import Badge, Component
from starlette.status import *


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

    def __new__(cls, value: str, label: str, component: Component) -> str:
        obj = str.__new__(cls, value)
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
    def _missing_(cls, value):
        return cls.Unknown

    @classmethod
    def from_name(cls, name: str) -> "NodeStatus":
        return getattr(cls, name, cls.Unknown)


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

    def __new__(cls, value: int, label: str, http: int):
        obj = int.__new__(cls, value)
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
