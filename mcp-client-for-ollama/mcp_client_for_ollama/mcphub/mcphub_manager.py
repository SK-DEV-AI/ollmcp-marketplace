"""
Professional MCP Server Management System
==========================================

Advanced command-line interface for MCP (Model Context Protocol) servers
with enterprise-grade configuration management.
"""

import asyncio
import functools
import httpx
import json
from typing import Dict, List, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from prompt_toolkit import PromptSession
from rich.prompt import Prompt, Confirm
from typing import Optional

from .smithery_client import SmitheryClient
from ..config.manager import ConfigManager


class MCPHubManager:
    """Professional MCP Server Management with Enterprise Features."""

    def __init__(
        self,
        console: Console,
        smithery_client: SmitheryClient,
        config_manager: ConfigManager,
        client,
        config_name: str,
        prompt_session: Optional[PromptSession] = None,
    ):
        self.console = console
        self.smithery_client = smithery_client
        self.config_manager = config_manager
        self.client = client
        self.config_name = config_name
        self.prompt_session = prompt_session or PromptSession()

        # Initialize API key from configuration
        self._initialize_api_key()

    def _initialize_api_key(self):
        """Initialize Smithery API key from current configuration."""
        api_key = self.smithery_client.get_api_key()
        if api_key is None:
            config_data = self.config_manager.load_configuration(self.config_name)
            api_key = config_data.get("smithery_api_key")
            if api_key:
                self.smithery_client.set_api_key(api_key)
        elif not api_key:  # If API key is empty string, try to get it from config
            config_data = self.config_manager.load_configuration(self.config_name)
            api_key = config_data.get("smithery_api_key")
            if api_key:
                self.smithery_client.set_api_key(api_key)

    async def _organize_servers_by_category(self, servers):
        """Organize servers into categories by their functionality."""
        categories = {
            "File System": {
                "servers": [],
                "icon": "📁",
                "description": "File management, directory operations, storage utilities",
                "total_tools": 0
            },
            "Web & HTTP": {
                "servers": [],
                "icon": "🌐",
                "description": "HTTP clients, web APIs, network utilities, scraping tools",
                "total_tools": 0
            },
            "AI & ML": {
                "servers": [],
                "icon": "🤖",
                "description": "AI assistance, machine learning, text processing, language models",
                "total_tools": 0
            },
            "Database": {
                "servers": [],
                "icon": "🗄️",
                "description": "Database interactions, SQL queries, data persistence",
                "total_tools": 0
            },
            "Development": {
                "servers": [],
                "icon": "💻",
                "description": "Code analysis, testing, building, development tools",
                "total_tools": 0
            },
            "Communication": {
                "servers": [],
                "icon": "💬",
                "description": "Email, messaging, notification systems, social platforms",
                "total_tools": 0
            },
            "Media & Content": {
                "servers": [],
                "icon": "🎬",
                "description": "Image processing, video editing, content creation",
                "total_tools": 0
            },
        }

        for server in servers:
            display_name = server.get("displayName", "")
            qualified_name = server.get("qualifiedName", "")
            description = server.get("description", "").lower()

            # Categorization logic based on keywords and server information
            if any(
                keyword in description + qualified_name
                for keyword in [
                    "filesystem",
                    "directory",
                    "folder",
                    "storage",
                    "disk",
                    "file",
                    "fs",
                ]
            ):
                category_name = "File System"
            # Web & HTTP category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "web",
                    "http",
                    "api",
                    "url",
                    "request",
                    "browser",
                    "scraping",
                ]
            ):
                category_name = "Web & HTTP"
            # AI & ML category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "ai",
                    "machine learning",
                    "ml",
                    "neural",
                    "gpt",
                    "openai",
                    "claude",
                    "anthropic",
                    "assistant",
                    "chat",
                    "text",
                    "language",
                    "nlp",
                ]
            ):
                category_name = "AI & ML"
            # Database category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "database",
                    "db",
                    "sql",
                    "mysql",
                    "postgres",
                    "postgresql",
                    "mongodb",
                    "sqlite",
                    "redis",
                ]
            ):
                category_name = "Database"
            # Development category
            elif any(
                keyword in description + qualified_name
                for keyword in ["code", "programming", "lint", "debug", "test", "build"]
            ):
                category_name = "Development"
            # Communication category
            elif any(
                keyword in description + qualified_name
                for keyword in ["email", "mail", "gmail", "message", "chat", "smtp"]
            ):
                category_name = "Communication"
            # Media & Content category
            elif any(
                keyword in description + qualified_name
                for keyword in [
                    "image",
                    "video",
                    "media",
                    "content",
                    "text",
                    "generation",
                ]
            ):
                category_name = "Media & Content"

            categories[category_name]["servers"].append(server)
            categories[category_name]["total_tools"] += len(server.get("tools", []))

        return categories

    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, check=True
            )
            return "Docker version" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    # Main interface methods
    async def run(self):
        """Main MCP-HUB interface loop."""
        welcome_message = Panel(
            Text(
                "Welcome to MCP-HUB - Professional MCP Server Manager!",
                justify="center",
            ),
            border_style="green",
        )
        self.console.print(welcome_message)

        while True:
            try:
                self.display_menu()
                choice = await self.prompt_session.prompt_async(
                    "Select option: ", is_password=False
                )

                await self._handle_menu_choice(choice)
                if choice in ["14", "q", "quit"]:
                    break

            except (KeyboardInterrupt, EOFError):
                self.console.print(
                    "\n[yellow]Operation cancelled. Back to menu.[/yellow]"
                )
                continue
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
                continue

    # Additional core methods would be implemented here
    def display_menu(self):
        """Display the professional MCP-HUB menu."""
        menu_content = """
[bold cyan]MCP-HUB Professional Server Manager[/bold cyan]

[bold blue]🔍 Discovery & Installation:[/bold blue]
1.  Search and Install Servers     | Discover and add MCP servers
2.  View Server Categories         | Browse by type (AI, Web, File, DB, etc.)

[bold green]⚙️  Server Management:[/bold green]
3.  View Installed Servers         | List and manage configured servers
4.  Enable/Disable Servers         | Toggle server availability
5.  Reconfigure Server             | Update server settings
6.  Uninstall Servers              | Remove servers (bulk support)

[bold purple]🔧 Advanced Features:[/bold purple]
7.  Server Health Check            | Check connection and status
8.  Backup/Restore Config          | Backup and restore configurations
9.  Inspect Server Registry        | View detailed server info
10. Setup Server Connectivity      | Configure local/server connections

[bold yellow]🛠️  System & Settings:[/bold yellow]
11. Configure Smithery API Key     | Set up API access
12. Clear API Cache                | Reset cached server data
13. Server Directory Info          | View organization structure

[bold gray]14. Back to Main Menu (q, quit)[/bold gray]
"""

        menu_panel = Panel(
            Text.from_markup(menu_content),
            title="[bold white]MCP-HUB Professional Edition[/bold white]",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(menu_panel)

    async def _handle_menu_choice(self, choice: str):
        """Route menu choices to appropriate methods."""
        choice = choice.strip().lower()

        menu_actions = {
            "1": self.search_servers,
            "2": self.view_server_categories,
            "11": self.configure_api_key,
            "12": lambda: self.clear_api_cache(),
        }

        if choice in menu_actions:
            try:
                await menu_actions[choice]()
                if choice in ["12"]:
                    await self.prompt_session.prompt_async(
                        "Press Enter to continue...", is_password=False
                    )
            except Exception as e:
                self.console.print(f"[red]Error executing option {choice}: {e}[/red]")
        elif choice in ["14", "q", "quit"]:
            pass
        else:
            self.console.print("[red]Invalid option. Please select 1-14.[/red]")

    # Placeholder implementations for main methods
    async def search_servers(self) -> None:
        """Search and install servers with advanced features.

        This method implements the full search and installation workflow using the Smithery registry.
        """
        # Prompt for search query
        query_panel = Panel(
            "[bold]Advanced Server Search[/bold]\n\n"
            "[dim]Tip: Use filters like 'owner:username', 'is:verified', 'filesystem', etc.[/dim]",
            title="[search] Search Servers",
            border_style="blue",
        )
        self.console.print(query_panel)

        query: str = await self.prompt_session.prompt_async("Enter search query: ")
        if not query.strip():
            self.console.print("[yellow]No query entered. Returning to menu.[/yellow]")
            return

        try:
            # Search servers
            self.console.print(f"[cyan]Searching for servers matching '{query}'...[/cyan]")
            servers_data: Dict[str, Any] = await self.smithery_client.search_servers(query=query.strip(), page=1, page_size=10)

            if not servers_data or "servers" not in servers_data or not servers_data["servers"]:
                self.console.print("[yellow]No servers found for your query.[/yellow]")
                await self.prompt_session.prompt_async("Press Enter to continue...")
                return

            servers: List[Dict[str, Any]] = servers_data["servers"]
            total_servers: int = len(servers)

            # Display results in a table
            table = Table(title=f"Search Results for '{query}' ({total_servers} server(s))")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="bold magenta")
            table.add_column("Description", style="dim white")
            table.add_column("Tools", justify="right", style="green")
            table.add_column("Security", justify="right", style="yellow")

            for i, server in enumerate(servers, 1):
                name: str = server.get("displayName", server.get("qualifiedName", "Unknown"))
                desc: str = server.get("description", "")[:100] + "..." if len(server.get("description", "")) > 100 else server.get("description", "")
                tools_count: int = len(server.get("tools", []))
                security: str = server.get("security", "Unverified")

                table.add_row(str(i), name, desc, str(tools_count), security)

            self.console.print(table)

            # Prompt for server selection
            selection_panel = Panel(
                "[bold]Select Server to Install[/bold]\n\n"
                f"[dim]Enter server ID (1-{total_servers}), (s)earch again, or (q)uit:[/dim]",
                title="[select] Choose Server",
                border_style="green",
            )
            self.console.print(selection_panel)

            selection: str = (await self.prompt_session.prompt_async("Enter server ID: ")).strip().lower()

            if selection == "s":
                await self.search_servers()  # Recursive search
                return
            elif selection == "q":
                return

            try:
                server_index: int = int(selection) - 1
                if 0 <= server_index < total_servers:
                    selected_server: Dict[str, Any] = servers[server_index]
                    selected_id: str = selected_server.get("qualifiedName", "")

                    # Preview selected server
                    preview_panel = Panel(
                        f"[bold cyan]Name:[/bold cyan] {selected_server.get('displayName', 'N/A')}\n"
                        f"[bold cyan]Description:[/bold cyan] {selected_server.get('description', 'N/A')}\n"
                        f"[bold cyan]Security:[/bold cyan] {selected_server.get('security', 'Unverified')}\n"
                        f"[bold cyan]Available Tools:[/bold cyan] {len(selected_server.get('tools', []))}\n"
                        f"[bold cyan]Qualified Name:[/bold cyan] {selected_id}",
                        title=f"[preview] Server Preview: {selected_id}",
                        border_style="blue",
                    )
                    self.console.print(preview_panel)

                    if Confirm.ask("Install this server?"):
                        await self._install_server(selected_id)
                    else:
                        self.console.print("[yellow]Installation cancelled.[/yellow]")
                else:
                    self.console.print("[red]Invalid selection.[/red]")
            except ValueError:
                self.console.print("[red]Invalid input. Please enter a number.[/red]")

            await self.prompt_session.prompt_async("Press Enter to continue...")

        except Exception as e:
            self.console.print(f"[red]Error during search: {str(e)}[/red]")
            await self.prompt_session.prompt_async("Press Enter to continue...")

    async def _install_server(self, server_id: str) -> None:
        """Install a specific server from the registry.

        Args:
            server_id: The qualified name of the server to install.
        """
        try:
            # Fetch full server details
            self.console.print(f"[cyan]Fetching details for {server_id}...[/cyan]")
            server_details: Dict[str, Any] = await self.smithery_client.get_server(server_id)

            if not server_details:
                self.console.print("[red]Failed to fetch server details.[/red]")
                return

            # Prepare server data for config
            qualified_name: str = server_details.get("qualifiedName", server_id)
            server_data: Dict[str, Any] = {
                "qualifiedName": qualified_name,
                "displayName": server_details.get("displayName", qualified_name),
                "description": server_details.get("description", ""),
                "tools": server_details.get("tools", []),
                "security": server_details.get("security", "Unverified"),
                "connections": server_details.get("connections", []),
                "config": {},  # Will be populated with user input
                "enabled": True,
            }

            # Set connection if not present
            if not server_details.get("connections"):
                self.console.print("[cyan]No connection information from registry. Setting up connection...[/cyan]")
                conn_type: str = Prompt.ask("Connection type (stdio/sse/http)", default="stdio")
                if conn_type == "stdio":
                    local_path: str = Prompt.ask("Enter local script path for the server", default="")
                    if local_path:
                        server_data["local_script_path"] = local_path
                    server_data["connections"] = [{"type": "stdio"}]
                else:
                    url: str = Prompt.ask("Enter server URL")
                    server_data["connections"] = [{"type": conn_type, "url": url}]
            else:
                # Check if stdio connection and prompt for local path if missing
                connections: List[Dict[str, Any]] = server_details.get("connections", [])
                for conn in connections:
                    if conn.get("type") == "stdio" and "local_script_path" not in server:
                        local_path: str = Prompt.ask("Enter local script path for stdio server", default="")
                        if local_path:
                            server["local_script_path"] = local_path
                        break

            # Add to installed servers
            self.config_manager.add_installed_server(server_data, self.config_name)

            # Success message
            success_panel = Panel(
                f"[bold green]Installation Successful![/bold green]\n\n"
                f"[bold cyan]Server:[/bold cyan] {qualified_name}\n"
                f"[bold cyan]Config:[/bold cyan] {len(server_data['config'])} parameters set\n"
                f"[bold cyan]Status:[/bold cyan] Enabled and ready to use\n\n"
                f"[dim]Configuration:[/dim]\n"
                f"{json.dumps(server_data['config'], indent=2)}",
                title=f"[installed] {qualified_name}",
                border_style="green",
            )
            self.console.print(success_panel)

            # Reload servers in main client
            await self.client.reload_servers()

        except Exception as e:
            self.console.print(f"[red]Installation failed: {str(e)}[/red]")

    async def view_server_categories(self):
        """View servers organized by categories."""
        installed_servers = self.config_manager.get_installed_servers(self.config_name)
        if not installed_servers:
            self.console.print("[yellow]No installed servers to categorize.[/yellow]")
            await self.prompt_session.prompt_async("Press Enter to return to main menu...")
            return

        categories = await self._organize_servers_by_category(installed_servers)

        category_table = Table(title="Server Categories")
        category_table.add_column("Category", style="bold cyan")
        category_table.add_column("Icon", style="magenta")
        category_table.add_column("Servers", style="white")
        category_table.add_column("Total Tools", justify="right", style="green")

        for category_name, category_data in categories.items():
            if category_data["servers"]:
                servers_list = ", ".join([s.get("displayName", s.get("qualifiedName", "Unknown")) for s in category_data["servers"]])[:50] + ("..." if len(", ".join([s.get("displayName", s.get("qualifiedName", "Unknown")) for s in category_data["servers"]])) > 50 else "")
                category_table.add_row(
                    category_name,
                    category_data["icon"],
                    servers_list,
                    str(category_data["total_tools"])
                )

        self.console.print(category_table)

        # Prompt to continue
        await self.prompt_session.prompt_async("Press Enter to return to main menu...")

    async def configure_api_key(self):
        """Configure Smithery API key."""
        api_config_panel = Panel(
            "[bold]Smithery API Key Configuration[/bold]\n\n"
            "[dim]The API key is required to access the Smithery MCP server registry.\n"
            "Get your key at: https://smithery.io[/dim]",
            title="[api] API Key Setup",
            border_style="yellow",
        )
        self.console.print(api_config_panel)

        try:
            api_key = await self.prompt_session.prompt_async(
                "Enter Smithery API Key: ", is_password=True
            )

            if api_key:
                self.smithery_client.set_api_key(api_key)
                success_panel = Panel(
                    "[bold green]API key configured successfully![/bold green]",
                    title="[success] API Key Set",
                    border_style="green",
                )
                self.console.print(success_panel)
            else:
                self.console.print("[yellow]API key configuration cancelled.[/yellow]")
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]API key configuration cancelled.[/yellow]")

    def clear_api_cache(self):
        """Clear the Smithery API cache."""
        self.smithery_client.clear_cache()
        cache_panel = Panel(
            "[bold green]API cache cleared successfully![/bold green]\n\n"
            "[dim]Next requests will fetch fresh data from Smithery registry.[/dim]",
            title="[cache] Cache Cleared",
            border_style="green",
        )
        self.console.print(cache_panel)
