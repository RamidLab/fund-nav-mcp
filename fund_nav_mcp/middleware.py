__all__ = ["CustomStructuredLoggingMiddleware"]

import os
import uuid
from typing import Callable, Any, Optional

from fastmcp.server.middleware import MiddlewareContext, CallNext
from fastmcp.server.middleware.logging import StructuredLoggingMiddleware
from pydantic import TypeAdapter

from fund_nav_mcp.utils.log import get_logger, bind_context, clear_context


class CustomStructuredLoggingMiddleware(StructuredLoggingMiddleware):
    """
    继承官方 StructuredLoggingMiddleware，实现：
    1. 使用自定义日志模块（支持多进程队列、JSON格式）
    2. 自动绑定 request_id 到日志上下文
    """

    def __init__(
            self,
            include_payloads: bool = os.getenv("MCP_LOG_INCLUDE_PAYLOADS", "false") == "true",
            include_payload_length: bool = os.getenv("MCP_LOG_INCLUDE_PAYLOADS_LENGTH", "false") == "true",
            estimate_payload_tokens: bool = os.getenv("MCP_LOG_ESTIMATE_PAYLOAD_TOKENS", "false") == "true",
            methods: Optional[list[str]] = TypeAdapter(Optional[list[str]]).validate_python(
                os.getenv("MCP_LOG_METHODS")),
            payload_serializer: Optional[Callable[[Any], str]] = None,
            *args, **kwargs
    ):
        super().__init__(
            include_payloads=include_payloads,
            include_payload_length=include_payload_length,
            estimate_payload_tokens=estimate_payload_tokens,
            methods=methods,
            payload_serializer=payload_serializer,
            *args, **kwargs
        )
        self._logger = get_logger("fastmcp.middleware")

    def _log_message(self, message: dict, log_level: Optional[int] = None) -> None:
        """
        重写：使用自己的logger进行输出

        Args:
            message: 日志消息字典
            log_level: 日志级别，默认使用配置中的默认值
        Returns:
            None
        """
        log_method = self._logger.log
        log_method(isinstance(log_level or self.log_level, int), message.get("event", "log"), extra=message)

    async def on_message(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        """
        重写：在官方逻辑前后绑定/清除上下文

        Args:
            context: FastMCP上下文
            call_next: 下一个中间件或路由处理函数
        Returns:
            处理结果
        """
        request_id = self._get_request_id(context)
        bind_context(request_id=request_id)  # 注入你的上下文

        try:
            return await super().on_message(context, call_next)
        finally:
            clear_context()

    @staticmethod
    def _get_request_id(context: MiddlewareContext) -> str:
        """
        从HTTP头中提取 request_id，若无则生成

        Args:
            context: FastMCP上下文
        Returns:
            request_id 字符串
        """
        try:
            from fastmcp.server.dependencies import get_http_headers
        except ImportError:
            def get_http_headers() -> None:
                return None

        headers = get_http_headers()
        if headers and "x-request-id" in headers:
            return headers["x-request-id"]

        if hasattr(context.message, "params") and isinstance(context.message.params, dict):
            if "_request_id" in context.message.params:
                return str(context.message.params["_request_id"])

        return str(uuid.uuid4())
