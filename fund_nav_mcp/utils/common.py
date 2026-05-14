__all__ = ["check_result"]

from typing import TypeVar

from fund_nav_mcp.models.common import UtilResponse
from fund_nav_mcp.utils.enums import Errcode
from fund_nav_mcp.utils.log import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def check_result(result: UtilResponse[T]) -> UtilResponse[T]:
    """
    检查结果是否成功

    Args:
        result: API 调用结果

    Returns:
        通用响应
    """
    if result.code not in {Errcode.SUCCESS, Errcode.DONE, Errcode.CONTINUE, Errcode.PROCESS}:
        raise Exception(result.message)
    return result
