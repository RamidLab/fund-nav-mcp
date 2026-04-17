import os
from importlib.resources import files

import typer
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

import fund_nav_mcp.tools as tools
from fund_nav_mcp.config import setup_settings
from fund_nav_mcp.utils.log import get_logger

mcp = FastMCP(
    "Fund Nav MCP",
    providers=[
        FileSystemProvider(str(files(tools)))
    ]
)

cli = typer.Typer()


@cli.command()
def stdio():
    """以 stdio 模式运行服务器"""
    mcp.run(transport="stdio")


@cli.command()
def sse(
        host: str = typer.Option("127.0.0.1", envvar="MCP_HOST"),
        port: int = typer.Option(8000, envvar="MCP_PORT")
):
    """以 SSE 模式运行服务器"""
    mcp.run(transport="sse", host=host, port=port)


@cli.command()
def streamable_http(
        host: str = typer.Option("127.0.0.1", envvar="MCP_HOST"),
        port: int = typer.Option(8000, envvar="MCP_PORT")
):
    """以 streamable-http 模式运行服务器"""
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    # 初始化应用配置实例
    setup_settings()
    logger = get_logger(__name__)

    # 使用 stdio 传输（MCP 标准），也可改为 sse 或 streamable-http
    cli([os.getenv("MCP_TRANSPORT", "stdio")])
