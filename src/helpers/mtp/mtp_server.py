import mtp_queries
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("mtp-module-descriptor")


@mcp.tool()
def list_modules():
    """List MTP modules available to query."""
    return mtp_queries.list_modules()


@mcp.tool()
def get_module_overview(module: str):
    """Summarize a module's data assemblies and metadata. `module` is its MTP module ID."""
    return mtp_queries.module_overview(module)


if __name__ == "__main__":
    mcp.run()
