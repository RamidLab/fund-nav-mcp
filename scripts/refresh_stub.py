import importlib


def refresh():
    from fund_nav_mcp.models.pydantic.generate import clean_registry
    clean_registry()

    # 重新加载模块，触发重新注册
    import fund_nav_mcp.models.pydantic.filter as filter_mod
    import fund_nav_mcp.models.pydantic.search as search_mod
    importlib.reload(search_mod)
    importlib.reload(filter_mod)
    print("[stub] pyi 已更新。")


if __name__ == "__main__":
    refresh()
