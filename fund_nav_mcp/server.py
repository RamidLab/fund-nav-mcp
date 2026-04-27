import os
import sys
from importlib.resources import files

import typer
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

import fund_nav_mcp.tools as tools
from fund_nav_mcp.config import setup_settings
from fund_nav_mcp.middleware import CustomStructuredLoggingMiddleware
from fund_nav_mcp.tools.ui_tools import app
from fund_nav_mcp.utils.log import get_logger

# 初始化应用配置实例
setup_settings()
logger = get_logger(__name__)

mcp = FastMCP(
    "Fund Nav MCP",
    providers=[
        FileSystemProvider(str(files(tools))),
        app
    ],
    middleware=[
        CustomStructuredLoggingMiddleware()
    ],
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


@cli.command()
def ui(
        dev_port: int = typer.Option(8080, envvar="MCP_UI_PORT"),
        reload: bool = typer.Option(True, envvar="MCP_UI_RELOAD"),
        mcp_port: int = typer.Option(8000, envvar="MCP_PORT"),

):
    """以 UI 模式运行服务器（启动 Apps 预览界面）"""
    import subprocess
    subprocess.run(
        [
            "fastmcp", "dev",
            "apps", __file__,
            "--dev-port", str(dev_port),
            "--mcp-port", str(mcp_port),
            f"--{'reload' if reload else 'no-reload'}"]
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        cli([os.getenv("MCP_TRANSPORT", "stdio")])
    else:
        cli()
