"""Server connection management for MCP Client for Ollama.

This module handles connections to one or more MCP servers, including setup,
initialization, and communication.
"""

import os
import shutil
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from mcp import ClientSession, Tool
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from .discovery import (
    process_server_paths,
    process_server_urls,
    parse_server_configs,
    auto_discover_servers,
)
from .auth import AuthProviderFactory
from ..utils.constants import MCP_PROTOCOL_VERSION
from ..utils.connection import check_url_connectivity
from ..config.manager import ConfigManager


class ServerConnector:
    """Manages connections to one or more MCP servers.

    This class handles establishing connections to MCP servers, either from
    individual script paths or from configuration files, and managing the
    tools provided by those servers.
    """

    def __init__(
        self,
        exit_stack: AsyncExitStack,
        console: Optional[Console] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        """Initialize the ServerConnector.

        Args:
            exit_stack: AsyncExitStack to manage server connections
            console: Rich console for output (optional)
            config_manager: ConfigManager to access installed servers
        """
        self.exit_stack = exit_stack
        self.console = console or Console()
        self.config_manager = config_manager
        self.sessions = {}  # Dict to store multiple sessions
        self.available_tools = []  # List to store all available tools
        self.enabled_tools = {}  # Dict to store tool enabled status
        self.session_ids = {}  # Dict to store session IDs for HTTP connections

    async def connect_to_servers(
        self,
        server_paths=None,
        server_urls=None,
        config_path=None,
        auto_discovery=False,
    ) -> Tuple[dict, list, dict]:
        """Connect to one or more MCP servers

        Args:
            server_paths: List of paths to server scripts (.py or .js)
            server_urls: List of URLs for SSE or Streamable HTTP servers
            config_path: Path to JSON config file with server configurations
            auto_discovery: Whether to automatically discover servers

        Returns:
            Tuple of (sessions, available_tools, enabled_tools)
        """
        all_servers = []

        # Load installed servers from config
        if self.config_manager:
            installed_servers = self.config_manager.get_installed_servers()
            for server in installed_servers:
                if not server.get("enabled", True):
                    self.console.print(
                        f"[yellow]Skipping disabled server: {server.get('qualifiedName')}[/yellow]"
                    )
                    continue

                self.console.print(
                    f"[cyan]Found installed server: {server.get('qualifiedName')}[/cyan]"
                )

                connections = server.get("connections")
                if not connections:
                    self.console.print(
                        f"[yellow]Warning: Installed server '{server.get('qualifiedName')}' has no connection information. Skipping.[/yellow]"
                    )
                    continue

                # For now, just use the first available connection
                connection_info = connections[0]
                conn_type = connection_info.get("type")

                # The server object passed to _connect_to_server needs a 'name' and 'type'.
                # The rest of the info can be in a 'config' sub-dictionary or at the top level.
                # Let's match the structure that _connect_to_server expects.
                api_key = self.config_manager.load_configuration().get("smithery_api_key") if self.config_manager else None
                server_obj = {
                    "name": server.get("qualifiedName"),
                    "config": server.get("config", {}),  # User-provided config
                    "api_key": api_key  # Global Smithery API key for authentication
                }

                # For Smithery servers, default to streamable_http if no connection type is specified
                is_smithery_server = server.get("qualifiedName", "").startswith("@") and "/" in server.get("qualifiedName", "")

                if conn_type in ["shttp", "http"]:
                    server_obj["type"] = "streamable_http"
                    server_obj["url"] = connection_info.get(
                        "url"
                    ) or connection_info.get("deploymentUrl")
                elif conn_type == "sse":
                    server_obj["type"] = "sse"
                    server_obj["url"] = connection_info.get(
                        "url"
                    ) or connection_info.get("deploymentUrl")
                elif conn_type == "stdio":
                    # This is a stdio server. The user should have been prompted to download it
                    # and provide a local path, which is stored in the server object.
                    local_path = server.get("local_script_path")
                    if local_path:
                        server_obj["type"] = "script"
                        server_obj["path"] = local_path
                    else:
                        self.console.print(
                            f"[yellow]Warning: stdio server '{server.get('qualifiedName')}' is configured but its local path is missing. Skipping.[/yellow]"
                        )
                        continue
                elif is_smithery_server:
                    # Default Smithery servers to streamable_http
                    server_obj["type"] = "streamable_http"
                    server_obj["url"] = connection_info.get(
                        "url"
                    ) or connection_info.get("deploymentUrl")
                else:
                    self.console.print(
                        f"[yellow]Warning: Unsupported connection type '{conn_type}' for server '{server.get('qualifiedName')}'. Skipping.[/yellow]"
                    )
                    continue

                if not server_obj.get("url") and conn_type != "stdio":
                    self.console.print(
                        f"[yellow]Warning: Installed server '{server.get('qualifiedName')}' is missing a URL for its connection. Skipping.[/yellow]"
                    )
                    continue

                all_servers.append(server_obj)

        # Process server paths
        if server_paths:
            script_servers = process_server_paths(server_paths)
            for server in script_servers:
                self.console.print(
                    f"[cyan]Found server script: {server['path']}[/cyan]"
                )
            all_servers.extend(script_servers)

        # Process server URLs
        if server_urls:
            url_servers = process_server_urls(server_urls)
            for server in url_servers:
                self.console.print(
                    f"[cyan]Found server URL: {server['url']} (type: {server['type']})[/cyan]"
                )
            all_servers.extend(url_servers)

        # Process config file
        if config_path:
            try:
                config_servers = parse_server_configs(config_path)
                for server in config_servers:
                    self.console.print(
                        f"[cyan]Found server in config: {server['name']}[/cyan]"
                    )
                all_servers.extend(config_servers)
            except Exception as e:
                self.console.print(
                    f"[red]Error loading server configurations: {str(e)}[/red]"
                )

        # Auto-discover servers if enabled
        if auto_discovery:
            discovered_servers = auto_discover_servers()
            for server in discovered_servers:
                self.console.print(
                    f"[cyan]Auto-discovered server: {server['name']}[/cyan]"
                )
            all_servers.extend(discovered_servers)

        if not all_servers:
            self.console.print(
                Panel(
                    "[yellow]No servers specified or all servers were invalid.[/yellow]\n"
                    "The client will continue without tool support.",
                    title="Warning",
                    border_style="yellow",
                    expand=False,
                )
            )
            return self.sessions, self.available_tools, self.enabled_tools

        # Check all servers url connectivity (skip connectivity check for Smithery servers)
        servers_to_connect = []
        skipped_servers = []
        for server in all_servers:
            server_name = server.get("name", "")
            server_url = server.get("url")

            # Special handling for Smithery servers - skip connectivity check
            # Smithery servers (@owner/server-name) may not have accessible URLs
            # or require special authentication
            is_smithery_server = server_name.startswith("@") and "/" in server_name

            if (
                server.get("type") in ["sse", "streamable_http"]
                and not is_smithery_server
            ):
                if not server_url:
                    self.console.print(
                        f"[yellow]Warning: Server '{server_name}' missing URL[/yellow]"
                    )
                    skipped_servers.append(server_name)
                    continue
                elif not check_url_connectivity(server_url):
                    self.console.print(
                        f"[yellow]Warning: Server '{server_name}' failed connectivity check[/yellow]"
                    )
                    skipped_servers.append(server_name)
                    continue
            elif (
                server.get("type") in ["sse", "streamable_http"] and is_smithery_server
            ):
                # For Smithery servers, show a different message and try to connect anyway
                self.console.print(
                    f"[cyan]🔄 Smithery server '{server_name}' - skipping connectivity check[/cyan]"
                )
                if not server_url:
                    self.console.print(
                        f"[red]Smithery server '{server_name}' missing URL, skipping[/red]"
                    )
                    skipped_servers.append(server_name)
                    continue
            servers_to_connect.append(server)
        all_servers = servers_to_connect

        if skipped_servers:
            self.console.print(
                f"[red]Skipping servers: {', '.join(skipped_servers)}[/red]"
            )
            self.console.print(
                "[yellow]Check server URLs and ensure servers are accessible.[/yellow]"
            )

        # Connect to each server
        for server in all_servers:
            await self._connect_to_server(server)

        if not self.sessions:
            self.console.print(
                Panel(
                    "[bold red]Could not connect to any MCP servers![/bold red]\n"
                    "Check that server paths exist and are accessible.",
                    title="Error",
                    border_style="red",
                    expand=False,
                )
            )

        return self.sessions, self.available_tools, self.enabled_tools

    async def _connect_to_server(self, server: Dict[str, Any]) -> bool:
        """Connect to a single MCP server

        Args:
            server: Server configuration dictionary

        Returns:
            bool: True if connection was successful, False otherwise
        """
        server_name = server["name"]
        self.console.print(f"[cyan]Connecting to server: {server_name}[/cyan]")

        try:
            server_type = server.get("type", "script")
            session = None

            # Connect based on server type
            if server_type == "sse":
                # Connect to SSE server
                url = self._get_url_from_server(server)
                if not url:
                    self.console.print(
                        f"[red]Error: SSE server {server_name} missing URL[/red]"
                    )
                    return False

                headers = self._get_headers_from_server(server)

                # Connect using SSE transport
                sse_transport = await self.exit_stack.enter_async_context(
                    sse_client(url, headers=headers)
                )
                read_stream, write_stream = sse_transport
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

            elif server_type == "streamable_http":
                # Connect to Streamable HTTP server
                url = self._get_url_from_server(server)
                if not url:
                    self.console.print(
                        f"[red]Error: HTTP server {server_name} missing URL[/red]"
                    )
                    return False

                # For Smithery servers, check if we need OAuth provider
                is_smithery_server = (
                    server_name.startswith("@") and "/" in server_name
                ) or "smithery.ai" in url
                auth_provider = None

                if is_smithery_server:
                    self.console.print(
                        f"[cyan]🔄 Setting up OAuth provider for Smithery server[/cyan]"
                    )

                    # Get API key from config manager if available
                    api_key = None
                    if self.config_manager:
                        config_data = self.config_manager.load_configuration()
                        api_key = config_data.get("smithery_api_key")

                    auth_provider = AuthProviderFactory.create_provider(
                        url, api_key, "smithery"
                    )
                    if auth_provider:
                        self.console.print(
                            f"[green]✅ OAuth provider created for {server_name}[/green]"
                        )
                    else:
                        self.console.print(
                            f"[yellow]⚠️ Failed to create OAuth provider for {server_name}[/yellow]"
                        )

                # Get headers with OAuth authentication if needed
                headers = self._get_headers_from_server(server)

                # Use the streamablehttp_client for Streamable HTTP connections
                # Authentication is handled through headers only
                transport = await self.exit_stack.enter_async_context(
                    streamablehttp_client(url, headers=headers, auth=auth_provider)
                )

                read_stream, write_stream, session_info = transport
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                # Store session ID if provided
                if hasattr(session_info, "session_id") and session_info.session_id:
                    self.session_ids[server_name] = session_info.session_id

            elif server_type == "script":
                # Connect to script-based server using STDIO
                server_params = self._create_script_params(server)
                if server_params is None:
                    return False

                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                read_stream, write_stream = stdio_transport
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

            else:
                # Connect to config-based server using STDIO
                server_params = self._create_config_params(server)
                if server_params is None:
                    return False

                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                read_stream, write_stream = stdio_transport
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

            # Initialize the session
            await session.initialize()

            # Store the session
            self.sessions[server_name] = {"session": session, "tools": []}

            # Get tools from this server
            response = await session.list_tools()

            # Store and merge tools, prepending server name to avoid conflicts
            server_tools = []
            for tool in response.tools:
                # Create a qualified name for the tool that includes the server
                qualified_name = f"{server_name}.{tool.name}"
                # Clone the tool but update the name
                tool_copy = Tool(
                    name=qualified_name,
                    description=(
                        f"[{server_name}] {tool.description}"
                        if hasattr(tool, "description")
                        else f"Tool from {server_name}"
                    ),
                    inputSchema=tool.inputSchema,
                    outputSchema=(
                        tool.outputSchema if hasattr(tool, "outputSchema") else None
                    ),
                )
                server_tools.append(tool_copy)
                self.enabled_tools[qualified_name] = True

            self.sessions[server_name]["tools"] = server_tools
            self.available_tools.extend(server_tools)

            self.console.print(
                f"[green]Successfully connected to {server_name} with {len(server_tools)} tools[/green]"
            )
            return True

        except FileNotFoundError as e:
            self.console.print(
                f"[red]Error connecting to {server_name}: File not found - {str(e)}[/red]"
            )
            return False
        except PermissionError:
            self.console.print(
                f"[red]Error connecting to {server_name}: Permission denied[/red]"
            )
            return False
        except Exception as e:
            error_str = str(e)
            if "authentication" in error_str.lower() or "unauthorized" in error_str.lower() or "bearer" in error_str.lower():
                self.console.print(
                    f"[red]Error connecting to {server_name}: Authentication failed[/red]"
                )
                if "smithery" in server_name.lower() or "@" in server_name:
                    self.console.print(
                        "[yellow]Hint: Your Smithery API key may be invalid or expired.[/yellow]"
                    )
                    self.console.print(
                        "[blue]Please update your API key at https://smithery.ai[/blue]"
                    )
                    self.console.print(
                        "[blue]Then use MCP-HUB option 11 to configure the new key.[/blue]"
                    )
                else:
                    self.console.print(
                        "[yellow]Hint: Check server credentials or authentication settings.[/yellow]"
                    )
            else:
                self.console.print(
                    f"[red]Error connecting to {server_name}: {error_str}[/red]"
                )
            return False

    def _create_script_params(
        self, server: Dict[str, Any]
    ) -> Optional[StdioServerParameters]:
        """Create server parameters for a script-type server

        Args:
            server: Server configuration dictionary

        Returns:
            StdioServerParameters or None if invalid
        """
        path = server["path"]
        is_python = path.endswith(".py")
        is_js = path.endswith(".js")

        if not (is_python or is_js):
            self.console.print(
                f"[yellow]Warning: Server script {path} must be a .py or .js file. Skipping.[/yellow]"
            )
            return None

        command = "python" if is_python else "node"

        # Validate the command exists in PATH
        if not shutil.which(command):
            self.console.print(
                f"[yellow]Warning: Command '{command}' not found in PATH. Skipping server {server['name']}.[/yellow]"
            )
            return None

        return StdioServerParameters(command=command, args=[path], env=None)

    def _create_config_params(
        self, server: Dict[str, Any]
    ) -> Optional[StdioServerParameters]:
        """Create server parameters for a config-type server

        Args:
            server: Server configuration dictionary

        Returns:
            StdioServerParameters or None if invalid
        """
        server_config = server.get("config")
        if not server_config:
            self.console.print(
                f"[yellow]Warning: Server '{server['name']}' has a config-type connection but is missing the 'config' object. Skipping.[/yellow]"
            )
            return None

        command = server_config.get("command")

        # Validate the command exists in PATH
        if not command or not shutil.which(command):
            self.console.print(
                f"[yellow]Warning: Command '{command}' for server '{server['name']}' not found in PATH. Skipping.[/yellow]"
            )
            return None

        args = server_config.get("args", [])
        env = server_config.get("env")

        # Fix and validate directory arguments
        fixed_args, dir_exists, missing_dir = self._fix_directory_args(args)

        if not dir_exists:
            self.console.print(
                f"[yellow]Warning: Server '{server['name']}' specifies a directory that doesn't exist: {missing_dir}[/yellow]"
            )
            self.console.print(f"[yellow]Skipping server '{server['name']}'[/yellow]")
            return None

        return StdioServerParameters(command=command, args=fixed_args, env=env)

    def _fix_directory_args(
        self, args: List[str]
    ) -> Tuple[List[str], bool, Optional[str]]:
        """Fix common issues with directory arguments and validate directory existence

        Args:
            args: List of command line arguments

        Returns:
            Tuple containing:
            - List of fixed arguments
            - bool indicating if all directories exist
            - Optional[str] containing the first missing directory path if any
        """
        if not args:
            return args, True, None

        fixed_args = args.copy()

        for i, arg in enumerate(fixed_args):
            if arg == "--directory" and i + 1 < len(fixed_args):
                dir_path = fixed_args[i + 1]

                # If the path is a file, use its parent directory
                if os.path.isfile(dir_path) and (
                    dir_path.endswith(".py") or dir_path.endswith(".js")
                ):
                    self.console.print(
                        f"[yellow]Warning: Server specifies a file as directory: {dir_path}[/yellow]"
                    )
                    self.console.print(
                        f"[green]Automatically fixing to use parent directory instead[/green]"
                    )
                    dir_path = os.path.dirname(dir_path) or "."
                    fixed_args[i + 1] = dir_path

                # Check if directory exists
                if not os.path.exists(dir_path):
                    return fixed_args, False, dir_path

        return fixed_args, True, None

    def get_sessions(self) -> Dict[str, Any]:
        """Get the current server sessions

        Returns:
            Dict of server sessions
        """
        return self.sessions

    def get_available_tools(self) -> List[Tool]:
        """Get the available tools from all connected servers

        Returns:
            List of available tools
        """
        return self.available_tools

    def get_enabled_tools(self) -> Dict[str, bool]:
        """Get the current enabled status of all tools

        Returns:
            Dict mapping tool names to enabled status
        """
        return self.enabled_tools

    def set_tool_status(self, tool_name: str, enabled: bool):
        """Set the enabled status of a specific tool

        Args:
            tool_name: Name of the tool to modify
            enabled: Whether the tool should be enabled
        """
        if tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = enabled

    def enable_all_tools(self):
        """Enable all available tools"""
        for tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = True

    def disable_all_tools(self):
        """Disable all available tools"""
        for tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = False

    def _get_url_from_server(self, server: Dict[str, Any]) -> Optional[str]:
        """Extract URL from server configuration.

        Args:
            server: Server configuration dictionary

        Returns:
            URL string or None if not found
        """
        # Try to get URL directly from server dict
        url = server.get("url")

        # If not there, try the config subdict
        if not url and "config" in server:
            url = server["config"].get("url")

        return url

    def _get_headers_from_server(self, server: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from server configuration and add required authentication.

        Args:
            server: Server configuration dictionary

        Returns:
            Dictionary of headers
        """
        # Try to get headers directly from server dict
        headers = server.get("headers", {})

        # If not there, try the config subdict
        if not headers and "config" in server:
            headers = server["config"].get("headers", {})

        # Always add MCP Protocol Version header for HTTP connections
        server_type = server.get("type", "script")
        server_name = server["name"]

        # Get the server URL for Smithery detection
        server_url = server.get("url")
        if not server_url and "config" in server:
            server_url = server["config"].get("url")

        if server_type in ["sse", "streamable_http"]:
            headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION

        # For Smithery servers, use OAuth authentication
        # Smithery servers are identified by the format @owner/server-name
        is_smithery_server = (server_name.startswith("@") and "/" in server_name) or (
            "smithery.ai" in server_url if server_url else False
        )

        if is_smithery_server:
            self.console.print(f"[cyan]Detected Smithery server: {server_name}[/cyan]")
            self.console.print(
                f"[green]🔄 Using API key authentication for Smithery server...[/green]"
            )

            # Use API key directly as Bearer token for Smithery authentication
            api_key = server.get("api_key")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                self.console.print(
                    f"[green]✅ Using API key authentication for {server_name}[/green]"
                )
            else:
                self.console.print(
                    f"[yellow]⚠️ No API key configured for Smithery server {server_name}[/yellow]"
                )
                self.console.print(
                    f"[blue]Note: You can configure your API key later using MCP-HUB option 11[/blue]"
                )
        else:
            self.console.print(
                f"[cyan]Non-Smithery server: {server_name}, using standard authentication flow[/cyan]"
            )
        return headers

    async def disconnect_all_servers(self):
        """Disconnect from all servers and reset state"""
        # Close all existing connections via exit stack
        await self.exit_stack.aclose()

        # Create a new exit stack for future connections
        self.exit_stack = AsyncExitStack()

        # Clear all state
        self.sessions.clear()
        self.available_tools.clear()
        self.enabled_tools.clear()
        self.session_ids.clear()
