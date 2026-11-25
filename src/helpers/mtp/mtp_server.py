import mtp_queries
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("mtp-module-descriptor")


@mcp.tool()
def list_modules():
    """List MTP modules available to query."""
    return mtp_queries.list_modules()


@mcp.tool()
def list_data_assemblies(module: str):
    """List data assemblies of a module."""
    return mtp_queries.list_data_assemblies(module)

@mcp.tool()
def list_signals(module: str, da_name: str):
    """List signals of a data assembly."""
    return mtp_queries.list_signals(module, da_name)


@mcp.tool()
def get_module_overview(module: str):
    """Summarize a module's data assembliy types and metadata."""
    return mtp_queries.module_overview(module)


@mcp.tool()
def describe_data_assembly(module: str, da_name: str):
    """Describe a data assembly."""
    return mtp_queries.describe_data_assembly(module, da_name)


@mcp.tool()
def describe_signal(module: str, da_name: str, signal: str):
    """Describe a signal."""
    return mtp_queries.describe_signal(module, da_name, signal)


if __name__ == "__main__":
    mcp.run()
